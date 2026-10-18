"""
苏九学伴 - 多图连续上传防抖聚合与跨图接缝智能提取调度器
核心设计：
1. 防抖聚合窗口（Debounce Window）：支持学生连续发送多张课文截图，每次发图重置 30 秒倒计时；
2. 手动立即识别按钮（Instant Trigger）：除了等待 30 秒自动识别，提供【⚡ 立即识别生成】按钮，点击立即提取；
3. 跨图接缝处理：多图打包提交多模态视觉大模型，智能拼接跨页短语并消除重复；
4. 最终统一推送汇总卡片，支持全量词汇列表展示、在线校对与 A4 打印。
"""
import asyncio
import time
from typing import Dict, List, Optional

from llm_provider import extract_highlighted_vocab_from_multi_images
from vocab_service import create_vocab_session
from card_builder import build_vocab_list_card, build_vocab_bot_welcome_card, build_image_batch_received_card
from feishu_client import reply_interactive_card

# 防抖等待时长：最后一张图片上传后等待 30 秒
DEBOUNCE_WAIT_SECONDS = 30

class UserImageBatch:
    def __init__(self, user_id: str, chat_id: str, latest_message_id: str):
        self.user_id = user_id
        self.chat_id = chat_id
        self.latest_message_id = latest_message_id
        self.images: List[bytes] = []
        self.timer_task: Optional[asyncio.Task] = None
        self.created_at = time.time()
        self.last_updated_at = time.time()

# 内存会话池：{ "user_id": UserImageBatch }
_active_batches: Dict[str, UserImageBatch] = {}

def get_batch_image_count(user_id: str) -> int:
    """获取指定用户当前待处理批次的图片数量"""
    batch = _active_batches.get(user_id)
    return len(batch.images) if batch else 1

async def _process_batch(batch: UserImageBatch, app_id: str, app_secret: str):
    """执行批次提取、会话创建与卡片推送"""
    if not batch or not batch.images:
        return

    img_count = len(batch.images)
    print(f"[Vocab Aggregator] 开始多模态解析用户 {batch.user_id} 的 {img_count} 张连续课文图片...")

    # 调用多图接缝智能提取引擎
    vocab_items = await extract_highlighted_vocab_from_multi_images(batch.images)

    card_to_send = None
    if vocab_items:
        batch_title = f"课文高亮划线重点内容（已合并 {img_count} 张课文图片）" if img_count > 1 else "课文高亮划线重点词组"
        session = create_vocab_session(batch.user_id, vocab_items, batch_title)
        card_to_send = build_vocab_list_card(session["session_id"], session["items"])
        if img_count > 1:
            card_to_send["header"]["title"]["content"] = f"📝 课文划线词汇清单 (已合并 {img_count} 张图片 · 共 {len(session['items'])} 条)"
    else:
        card_to_send = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⚠️ 课文划线识别提示"}},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md", 
                        "content": f"已对您上传的 **{img_count} 张课文图片**进行跨图拼接扫描，未能检测到明显的荧光笔高亮涂色或铅笔下划线。\n\n💡 **小建议**：请使用黄色/粉色荧光笔或铅笔在生词短语下方划线后重新拍照发送，效果最佳！"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "📸 查看示例卡片"}, "type": "primary", "value": {"action": "vocab_bot_demo"}},
                        {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回主导航"}, "type": "default", "value": {"action": "back_to_vocab_menu"}}
                    ]
                }
            ]
        }

    if card_to_send and batch.latest_message_id:
        await reply_interactive_card(
            batch.latest_message_id, 
            card_to_send, 
            app_id=app_id, 
            app_secret=app_secret
        )
        print(f"[Vocab Aggregator] 用户 {batch.user_id} 的 {img_count} 张图片解析完成并已推送飞书卡片！")

async def _trigger_batch_extraction(user_id: str, app_id: str, app_secret: str):
    """
    30 秒倒计时到期触发：取出当前批次收集的所有图片并进行提取
    """
    try:
        await asyncio.sleep(DEBOUNCE_WAIT_SECONDS)
    except asyncio.CancelledError:
        # 被新加入的图片或手动点击打断，直接退出
        return

    batch = _active_batches.pop(user_id, None)
    if not batch or not batch.images:
        return

    print(f"[Vocab Aggregator] 30秒防抖窗口结束，自动开始解析用户 {user_id} 的图片...")
    await _process_batch(batch, app_id, app_secret)

async def trigger_immediate_batch_extraction(user_id: str, app_id: str, app_secret: str) -> bool:
    """
    用户手动点击【⚡ 立即识别生成】触发：
    立即取消正在计时的 30 秒倒计时，并马上开始多图提取与卡片推送
    """
    batch = _active_batches.pop(user_id, None)
    if not batch or not batch.images:
        print(f"[Vocab Aggregator] 用户 {user_id} 当前无待处理图片批次（可能已在处理或已完成）")
        return False

    if batch.timer_task and not batch.timer_task.done():
        batch.timer_task.cancel()

    print(f"[Vocab Aggregator] 用户 {user_id} 手动点击立即识别，提前结束 30 秒倒计时并开始处理 {len(batch.images)} 张图片！")
    # 执行批次处理与卡片回复
    await _process_batch(batch, app_id, app_secret)
    return True

async def add_image_to_batch(
    user_id: str, 
    chat_id: str, 
    message_id: str, 
    img_bytes: bytes, 
    app_id: str, 
    app_secret: str
) -> int:
    """
    接收用户发送的单张图片并加入批次池：
    1. 取消正在计时的旧 Timer；
    2. 追加图片至队列；
    3. 启动全新的 30 秒计时器；
    4. 立即回复提示卡片（含 30 秒自动倒计时说明与【⚡ 立即识别生成】手动按钮）；
    返回当前队列中的累计图片数。
    """
    batch = _active_batches.get(user_id)
    if not batch:
        batch = UserImageBatch(user_id, chat_id, message_id)
        _active_batches[user_id] = batch

    # 取消先前的计时器
    if batch.timer_task and not batch.timer_task.done():
        batch.timer_task.cancel()

    # 追加图片与更新最新消息 ID
    batch.images.append(img_bytes)
    batch.latest_message_id = message_id
    batch.last_updated_at = time.time()
    current_count = len(batch.images)

    print(f"[Vocab Aggregator] 用户 {user_id} 收到第 {current_count} 张图片，已重置 30 秒聚合等待倒计时...")

    # 启动新的 30 秒倒计时防抖任务
    batch.timer_task = asyncio.create_task(
        _trigger_batch_extraction(user_id, app_id, app_secret)
    )

    # 立即回复接收进度卡片（含 30 秒倒计时说明与【⚡ 立即识别生成】按钮）
    try:
        receipt_card = build_image_batch_received_card(current_count, DEBOUNCE_WAIT_SECONDS, user_id=user_id)
        await reply_interactive_card(message_id, receipt_card, app_id=app_id, app_secret=app_secret)
    except Exception as e:
        print(f"[Vocab Aggregator] 发送接收进度卡片异常: {e}")

    return current_count
