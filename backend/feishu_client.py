"""
飞书开放平台客户端：负责多机器人 Token 缓存与调用官方 API 发送消息卡片与多媒体资源下载
支持：
1. 全科综合机器人（苏九学伴）
2. 专属英语背单词机器人（苏九背词伴读）
"""
import os
import time
import json
import httpx
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

DEFAULT_APP_ID = os.getenv("FEISHU_APP_ID", "")
DEFAULT_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

VOCAB_APP_ID = os.getenv("FEISHU_VOCAB_APP_ID", "") or DEFAULT_APP_ID
VOCAB_APP_SECRET = os.getenv("FEISHU_VOCAB_APP_SECRET", "") or DEFAULT_APP_SECRET

STEM_APP_ID = os.getenv("FEISHU_STEM_APP_ID", "") or DEFAULT_APP_ID
STEM_APP_SECRET = os.getenv("FEISHU_STEM_APP_SECRET", "") or DEFAULT_APP_SECRET

# 按 app_id 隔离存储各机器人的 token 缓存
_token_caches: Dict[str, dict] = {}

async def get_tenant_access_token(app_id: Optional[str] = None, app_secret: Optional[str] = None) -> str:
    """获取并自动缓存 tenant_access_token，支持多机器人隔离缓存"""
    target_app_id = app_id or DEFAULT_APP_ID
    target_app_secret = app_secret or DEFAULT_APP_SECRET

    if not target_app_id or not target_app_secret:
        return ""

    now = time.time()
    cache = _token_caches.get(target_app_id, {"token": "", "expire_at": 0})
    if cache["token"] and now < cache["expire_at"]:
        return cache["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={
                "app_id": target_app_id,
                "app_secret": target_app_secret
            })
            data = resp.json()
            if data.get("code") == 0:
                new_token = data["tenant_access_token"]
                _token_caches[target_app_id] = {
                    "token": new_token,
                    "expire_at": now + data.get("expire", 7200) - 300
                }
                return new_token
            else:
                print(f"[Feishu Token Error for {target_app_id[:6]}***] {data}")
        except Exception as e:
            print(f"[Feishu Token Request Failed for {target_app_id[:6]}***] {e}")
    return ""

async def reply_interactive_card(
    message_id: str, 
    card_content: dict, 
    app_id: Optional[str] = None, 
    app_secret: Optional[str] = None
) -> bool:
    """回复一条消息卡片（支持指定特定机器人应用发信）"""
    token = await get_tenant_access_token(app_id, app_secret)
    if not token:
        print("[Feishu] 未配置有效 APP_ID 或 APP_SECRET，跳过主动回复调用")
        return False

    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "msg_type": "interactive",
        "content": str(card_content) if isinstance(card_content, str) else json.dumps(card_content)
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            res = resp.json()
            if res.get("code") == 0:
                return True
            else:
                print(f"[Feishu Send Card Failed] {res}")
        except Exception as e:
            print(f"[Feishu Send Card Exception] {e}")
    return False

async def send_chat_card(
    chat_id: str, 
    card_content: dict, 
    app_id: Optional[str] = None, 
    app_secret: Optional[str] = None
) -> bool:
    """向群聊或单聊主动发送一条卡片消息"""
    token = await get_tenant_access_token(app_id, app_secret)
    if not token:
        return False

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.json().get("code") == 0
        except Exception as e:
            print(f"[Feishu Send Chat Card Exception] {e}")
    return False

async def send_user_card(
    user_id: str, 
    card_content: dict, 
    app_id: Optional[str] = None, 
    app_secret: Optional[str] = None
) -> bool:
    """向指定 open_id 单聊直接发送一条卡片消息"""
    token = await get_tenant_access_token(app_id, app_secret)
    if not token:
        return False

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card_content) if isinstance(card_content, dict) else str(card_content)
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            res = resp.json()
            if res.get("code") == 0:
                return True
            else:
                print(f"[Feishu Send User Card Failed] {res}")
        except Exception as e:
            print(f"[Feishu Send User Card Exception] {e}")
    return False

async def send_card_to_dialog(
    card_content: dict,
    message_id: str = "",
    chat_id: str = "",
    user_id: str = "",
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None
) -> bool:
    """
    通用对话框直接发送卡片函数（直接在主会话流中作为新消息气泡弹出，而非卡片下折叠回复）：
    多策略保障 100% 成功送达学生对话框：
    1. 优先按 chat_id（会话/群聊/单聊）在主对话框直接发送新消息卡片；
    2. 若无 chat_id 或发送失败，按 user_id（open_id）在单聊主对话框发送新消息卡片；
    3. 若前两者均无或失败，最后降级为按 message_id 回复。
    """
    print(f"[send_card_to_dialog] 准备投递卡片: chat_id={chat_id}, user_id={user_id}, message_id={message_id}")
    if chat_id:
        success = await send_chat_card(chat_id, card_content, app_id, app_secret)
        if success:
            print(f"[send_card_to_dialog] 成功通过 chat_id={chat_id} 直接投递至会话主界面！")
            return True
        else:
            print(f"[send_card_to_dialog] 通过 chat_id={chat_id} 投递失败，尝试 user_id...")

    if user_id:
        success = await send_user_card(user_id, card_content, app_id, app_secret)
        if success:
            print(f"[send_card_to_dialog] 成功通过 user_id={user_id} 直接投递至单聊主界面！")
            return True
        else:
            print(f"[send_card_to_dialog] 通过 user_id={user_id} 投递失败，尝试 message_id...")

    if message_id:
        success = await reply_interactive_card(message_id, card_content, app_id, app_secret)
        if success:
            print(f"[send_card_to_dialog] 已降级通过 message_id={message_id} 进行回复")
            return True

    print(f"[send_card_to_dialog] 所有投递通道均失败 (chat_id={chat_id}, user_id={user_id}, message_id={message_id})")
    return False

async def download_image_resource(
    message_id: str, 
    image_key: str, 
    app_id: Optional[str] = None, 
    app_secret: Optional[str] = None
) -> bytes:
    """
    根据 message_id 与 image_key 从飞书开放平台下载用户发送的截图原始二进制数据
    """
    token = await get_tenant_access_token(app_id, app_secret)
    if not token:
        print("[Feishu] 未获取到有效 token，无法下载图片")
        return b""

    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{image_key}?type=image"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    async with httpx.AsyncClient(timeout=25) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                print(f"[Feishu Download Image Failed] status={resp.status_code}, text={resp.text[:120]}")
        except Exception as e:
            print(f"[Feishu Download Image Exception] {e}")

    return b""
