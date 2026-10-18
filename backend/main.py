from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import json
import re
import time

from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT, check_for_out_of_bounds
from knowledge_db import (
    query_english_word, query_ancient_text,
    query_physics_concept, query_chemistry_concept
)
from card_builder import (
    SUBJECT_METAS, build_menu_card, build_subject_workbench_card,
    build_physics_card, build_chemistry_card, build_word_card,
    build_ancient_card, build_qa_result_card,
    build_vocab_list_card, build_vocab_dictation_card,
    build_vocab_checklist_card,
    build_vocab_bot_welcome_card, build_image_batch_received_card,
    build_image_processing_card
)
from feishu_client import reply_interactive_card, send_chat_card, download_image_resource
from llm_provider import (
    generate_suzhou_answer, generate_suzhou_vision_answer, 
    extract_highlighted_vocab_from_image,
    get_current_model_config, SUPPORTED_PROVIDERS
)
from vocab_service import create_vocab_session, get_vocab_session, update_vocab_session
from vocab_aggregator import (
    add_image_to_batch, trigger_immediate_batch_extraction,
    get_batch_image_count
)
import httpx
from dotenv import load_dotenv

load_dotenv()

VOCAB_APP_ID = os.getenv("FEISHU_VOCAB_APP_ID", "").strip() or os.getenv("FEISHU_APP_ID", "").strip()
VOCAB_APP_SECRET = os.getenv("FEISHU_VOCAB_APP_SECRET", "").strip() or os.getenv("FEISHU_APP_SECRET", "").strip()

app = FastAPI(
    title="苏九学伴 - 学习助手中台",
    description="针对苏州市9年级学生的学习助手中台后端 API 与飞书消息机器人引擎（含独立背单词机器人网关）",
    version="1.7.0"
)

# 内存会话管理：记录每位学生当前选定的复习学科（默认为数学 math）
# 格式：{ "open_id_or_chat_id": "physics" | "chemistry" | "math" | "english" | "chinese" | "politics" }
user_active_subjects: dict[str, str] = {}

# 飞书事件幂等去重缓存：记录最近已处理的 event_id 和 message_id
# 杜绝飞书 Webhook 3秒超时重试导致的大模型重复运算与重复推送卡片
_processed_event_ids: dict[str, float] = {}
EVENT_ID_EXPIRE_SECONDS = 600  # 缓存 10 分钟

def check_and_mark_event_processed(event_id: str, message_id: str = "") -> bool:
    """
    判断飞书事件是否重复投递。
    若已在处理或已处理过，返回 True；
    若为新事件，记录时间戳并返回 False。
    """
    now = time.time()
    # 定期清理 10 分钟前的过期 ID，防止内存膨胀
    if len(_processed_event_ids) > 200:
        expired = [k for k, ts in _processed_event_ids.items() if now - ts > EVENT_ID_EXPIRE_SECONDS]
        for k in expired:
            _processed_event_ids.pop(k, None)

    is_dup = False
    if event_id and event_id in _processed_event_ids:
        is_dup = True
    if message_id and message_id in _processed_event_ids:
        is_dup = True

    if not is_dup:
        if event_id:
            _processed_event_ids[event_id] = now
        if message_id:
            _processed_event_ids[message_id] = now

    return is_dup


# 挂载前端页面静态资源
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
@app.get("/welcome")
async def get_welcome_page():
    """返回飞书工作台嵌入的欢迎页面"""
    index_file = os.path.join(frontend_dir, "welcome.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome page not found"}

@app.get("/vocab")
@app.get("/suzhou/vocab")
async def get_vocab_workbench_page():
    """返回英语划线词汇确认、默写与 A4 纸打印页面"""
    page_file = os.path.join(frontend_dir, "vocab_workbench.html")
    if os.path.exists(page_file):
        return FileResponse(page_file)
    return {"message": "Vocab workbench page not found"}

@app.get("/api/vocab/session/{session_id}")
@app.get("/suzhou/api/vocab/session/{session_id}")
async def get_vocab_session_api(session_id: str):
    """读取背诵会话数据"""
    data = get_vocab_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data

class VocabUpdateRequest(BaseModel):
    items: list
    title: str = ""

@app.post("/api/vocab/session/{session_id}/update")
@app.post("/suzhou/api/vocab/session/{session_id}/update")
async def update_vocab_session_api(session_id: str, req: VocabUpdateRequest):
    """保存学生对中文注释的在线修改"""
    updated = update_vocab_session(session_id, req.items, req.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"code": 0, "msg": "success", "data": updated}



class QuestionRequest(BaseModel):
    subject: str = "math"
    question: str

@app.post("/api/ask")
async def ask_assistant(req: QuestionRequest):
    """
    接收初三学生提问，经由防超纲安全审查后返回标准解析
    """
    input_check = check_for_out_of_bounds(req.question)
    
    # 优先调用大模型，若未配置 key 则使用苏科版结构化模拟
    llm_resp = await generate_suzhou_answer(req.question, req.subject)
    if llm_resp:
        final_answer = llm_resp
    else:
        final_answer = (
            f"【苏州中考考点定位】{req.subject} 核心考查\n\n"
            f"针对问题：'{req.question}'\n\n"
            "【苏科版标准解题步骤】\n"
            "1. 规范设未知数并列出等量关系；\n"
            "2. 按照九年级课本规范进行配方/因式分解；\n"
            "3. 验根并写出答语。\n\n"
            "【踩分点提醒】步骤中切勿遗漏定义域讨论与单位书写。"
        )

    output_check = check_for_out_of_bounds(final_answer)

    return {
        "status": "success",
        "scope": "苏州市9年级考纲范围",
        "guardrail_status": "Passed" if output_check["is_safe"] else "Blocked",
        "answer": final_answer,
        "input_warning": None if input_check["is_safe"] else f"检测到包含超纲词汇：{input_check['violations']}"
    }

def clean_message_text(raw_text: str) -> str:
    """去除飞书消息中的 @ 机器人标签及前后空白"""
    cleaned = re.sub(r"@_user_\d+", "", raw_text)
    cleaned = re.sub(r"@苏九学伴", "", cleaned)
    cleaned = re.sub(r"@助手", "", cleaned)
    return cleaned.strip()

async def process_feishu_im_message_task(event: dict):
    """
    异步处理飞书消息核心任务：
    包括文本提问、各学科考标匹配、大模型推导、拍照搜题视觉解析及结果卡片回复。
    通过 BackgroundTasks 异步执行，确保飞书 Webhook 接口 3 秒内秒级响应，彻底消除飞书超时重试风暴。
    """
    try:
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type")
        chat_id = message.get("chat_id")
        sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id") or chat_id or "default_user"
        active_subj = user_active_subjects.get(sender_id, "math")

        if msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)
            card_to_send = None

            # 意图 1：@助手、呼出菜单、帮助、清空只 @了机器人
            if not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "助学菜单", "选择科目", "科目"]:
                card_to_send = build_menu_card()

            # 意图 2：文字快捷切换科目（如输入“物理”、“换化学”）
            elif any(user_query == k or user_query == f"切换{k}" or user_query == f"换{k}" or user_query == f"选{k}" for k in ["数学", "物理", "化学", "英语", "语文", "道法", "历史"]):
                subj_map = {
                    "数学": "math", "物理": "physics", "化学": "chemistry",
                    "英语": "english", "语文": "chinese", "道法": "politics", "历史": "politics"
                }
                for k, v in subj_map.items():
                    if k in user_query:
                        user_active_subjects[sender_id] = v
                        card_to_send = build_subject_workbench_card(v)
                        break

            # 意图 3：英语单词查询（包含关键词或在英语模式下的纯英文词汇）
            elif user_query.startswith("查单词") or user_query.startswith("单词") or (active_subj == "english" and re.match(r"^[a-zA-Z\s\-]+$", user_query)):
                search_word = re.sub(r"^(查单词|单词|word)\s*", "", user_query, flags=re.IGNORECASE).strip()
                if not search_word:
                    card_to_send = build_subject_workbench_card("english")
                else:
                    word_result = query_english_word(search_word)
                    if word_result.get("matched"):
                        card_to_send = build_word_card(word_result)
                    else:
                        llm_ans = await generate_suzhou_answer(f"初三英语考纲单词与搭配：{search_word}", "九年级英语")
                        card_to_send = build_qa_result_card(f"单词：{search_word}", llm_ans or "词库正在收录中", "九年级英语", "english")

            # 意图 4：初三古文古诗查询（篇目名称或名句）
            elif user_query.startswith("查古文") or user_query.startswith("古文") or user_query.startswith("古诗") or any(k in user_query for k in ["岳阳楼记", "醉翁亭记", "出师表", "水调歌头", "先天下"]):
                search_title = re.sub(r"^(查古文|古文|古诗|诗词)\s*", "", user_query).strip()
                if not search_title:
                    card_to_send = build_subject_workbench_card("chinese")
                else:
                    ancient_result = query_ancient_text(search_title)
                    if ancient_result.get("matched"):
                        card_to_send = build_ancient_card(ancient_result)
                    else:
                        llm_ans = await generate_suzhou_answer(f"统编九年级文言考点与释义：{search_title}", "九年级语文")
                        card_to_send = build_qa_result_card(search_title, llm_ans or "篇目正在收录中", "九年级语文", "chinese")

            # 意图 5：在当前激活科目下进行针对性提问（优先匹配本地考标库，未命中则调用专属大模型推导）
            else:
                guard_check = check_for_out_of_bounds(user_query)
                if not guard_check["is_safe"]:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 苏州9年级考纲防超纲拦截"}},
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"tag": "lark_md", "content": f"**抱歉，检测到提问包含高中/超纲内容**：`{guard_check['violations']}`。\n\n苏九学伴严格遵循苏州市初中学业水平考试考标，初中阶段不使用高中推导与概念。请尝试以初中课本方法提问。"}
                            },
                            {
                                "tag": "action",
                                "actions": [
                                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回当前工作台"}, "type": "default", "value": {"action": "select_subject", "subject": active_subj}},
                                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔄 更换学科"}, "type": "default", "value": {"action": "back_to_menu"}}
                                ]
                            }
                        ]
                    }
                else:
                    # 针对物理/化学进行本地权威知识库秒级命中
                    if active_subj == "physics":
                        p_res = query_physics_concept(user_query)
                        if p_res.get("matched"):
                            card_to_send = build_physics_card(p_res["data"])
                    elif active_subj == "chemistry":
                        c_res = query_chemistry_concept(user_query)
                        if c_res.get("matched"):
                            card_to_send = build_chemistry_card(c_res["data"])

                    if not card_to_send:
                        subj_info = SUBJECT_METAS.get(active_subj, SUBJECT_METAS["math"])
                        llm_answer = await generate_suzhou_answer(user_query, f"{subj_info['name']} ({subj_info['book']})")
                        if llm_answer:
                            out_check = check_for_out_of_bounds(llm_answer)
                            if out_check["is_safe"]:
                                card_to_send = build_qa_result_card(user_query, llm_answer, subj_info["name"], active_subj)
                            else:
                                card_to_send = {
                                    "config": {"wide_screen_mode": True},
                                    "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 答题输出防超纲拦截"}},
                                    "elements": [
                                        {"tag": "div", "text": {"tag": "lark_md", "content": f"生成内容包含高中超纲内容：`{out_check['violations']}`，已熔断保护。请换个问法。"}},
                                        {"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回工作台"}, "type": "default", "value": {"action": "select_subject", "subject": active_subj}}]}
                                    ]
                                }
                        else:
                            card_to_send = build_subject_workbench_card(active_subj)

            if card_to_send and message_id:
                await reply_interactive_card(message_id, card_to_send)

        elif msg_type == "image":
            # 学生直接发送题目或课文截图
            subj_info = SUBJECT_METAS.get(active_subj, SUBJECT_METAS["math"])
            card_to_send = None
            try:
                content_obj = json.loads(message.get("content", "{}"))
                image_key = content_obj.get("image_key", "")
            except Exception:
                image_key = ""

            if image_key and message_id:
                # 从飞书开放平台下载图片原始二进制数据
                img_bytes = await download_image_resource(message_id, image_key)
                if img_bytes:
                    # 场景 1：当前为英语学科 -> 自动识别课文高亮划线词组并生成背诵/默写/打印会话（支持多图30秒防抖聚合与跨图接缝智能拼接）
                    if active_subj == "english":
                        await add_image_to_batch(
                            user_id=sender_id,
                            chat_id=chat_id,
                            message_id=message_id,
                            img_bytes=img_bytes,
                            app_id=os.getenv("FEISHU_APP_ID", "").strip(),
                            app_secret=os.getenv("FEISHU_APP_SECRET", "").strip()
                        )
                        return

                    # 场景 2：数理化或其他学科 -> 中考题目分步解题推导
                    if not card_to_send:
                        prompt_hint = f"当前复习学科：{subj_info['name']}，匹配教材考标：{subj_info['book']}。"
                        vision_answer = await generate_suzhou_vision_answer(img_bytes, user_prompt=prompt_hint)
                        out_check = check_for_out_of_bounds(vision_answer)
                        if out_check["is_safe"]:
                            card_to_send = build_qa_result_card(
                                "📸 学生试卷/习题截图题目",
                                vision_answer,
                                f"{subj_info['name']} 图像解析",
                                active_subj
                            )
                        else:
                            card_to_send = {
                                "config": {"wide_screen_mode": True},
                                "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 防超纲安全拦截"}},
                                "elements": [
                                    {
                                        "tag": "div",
                                        "text": {"tag": "lark_md", "content": f"**检测到题目包含高中超纲内容**：`{out_check['violations']}`。\n\n苏九学伴严格遵循苏州市初中学业水平考试要求，不使用高中方法。请确认题目是否为初三内容。"}
                                    },
                                    {
                                        "tag": "action",
                                        "actions": [
                                            {"tag": "button", "text": {"tag": "plain_text", "content": f"🔙 返回{subj_info['name']}工作台"}, "type": "default", "value": {"action": "select_subject", "subject": active_subj}},
                                            {"tag": "button", "text": {"tag": "plain_text", "content": "🔄 更换学科"}, "type": "default", "value": {"action": "back_to_menu"}}
                                        ]
                                    }
                                ]
                            }
                else:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⚠️ 图片读取提示"}},
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"tag": "lark_md", "content": "未能读取到截图。请检查飞书开放平台应用权限中是否已勾选开通 **`im:resource`（获取与上传图片或文件资源）** 权限。"}
                            }
                        ]
                    }

            if card_to_send and message_id:
                await reply_interactive_card(message_id, card_to_send)

    except Exception as e:
        print(f"[Feishu Async Task Error] 消息处理异常: {e}")

@app.post("/api/feishu/event")
async def feishu_event_handler(request: Request, background_tasks: BackgroundTasks):
    """
    飞书开放平台核心网关：
    1. URL Verification (飞书首次配置事件回调时的安全握手)
    2. 卡片回传交互 (点击助学菜单按钮或卡片交互，就地刷新)
    3. IM 接收消息事件 (基于 event_id/message_id 幂等去重 + BackgroundTasks 异步处理，避免飞书超时重发)
    """
    try:
        body = await request.json()
    except Exception:
        return {"code": 0, "msg": "invalid json"}

    # 1. 飞书 URL 校验握手
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}

    # 2. 飞书交互式卡片点击回传 (card.action.trigger)
    if "action" in body and ("open_message_id" in body or "open_id" in body):
        action_val = body.get("action", {}).get("value", {})
        action_type = action_val.get("action")
        sender_id = body.get("open_id") or body.get("user_id") or body.get("open_chat_id", "")

        if action_type == "back_to_menu":
            return {"card": build_menu_card()}
        elif action_type == "select_subject":
            subj = action_val.get("subject", "math")
            if sender_id:
                user_active_subjects[sender_id] = subj
            return {"card": build_subject_workbench_card(subj)}
        elif action_type == "quick_topic":
            subj = action_val.get("subject", "math")
            topic = action_val.get("topic", "")
            if sender_id:
                user_active_subjects[sender_id] = subj

            if subj == "physics":
                res = query_physics_concept(topic)
                if res.get("matched"):
                    return {"card": build_physics_card(res["data"])}
                else:
                    ans = await generate_suzhou_answer(topic, "九年级物理")
                    return {"card": build_qa_result_card(topic, ans or "暂无解析", "九年级物理", "physics")}
            elif subj == "chemistry":
                res = query_chemistry_concept(topic)
                if res.get("matched"):
                    return {"card": build_chemistry_card(res["data"])}
                else:
                    ans = await generate_suzhou_answer(topic, "九年级化学")
                    return {"card": build_qa_result_card(topic, ans or "暂无解析", "九年级化学", "chemistry")}
            elif subj == "english":
                res = query_english_word(topic)
                return {"card": build_word_card(res)}
            elif subj == "chinese":
                res = query_ancient_text(topic)
                return {"card": build_ancient_card(res)}
            else:
                subj_name = SUBJECT_METAS.get(subj, {}).get("name", "九年级综合")
                ans = await generate_suzhou_answer(topic, subj_name)
                return {"card": build_qa_result_card(topic, ans or "暂无解析", subj_name, subj)}

        elif action_type == "switch_mode":
            mode = action_val.get("mode", "english")
            return {"card": build_subject_workbench_card(mode)}
        elif action_type == "query_word":
            word = action_val.get("word", "")
            res = query_english_word(word)
            return {"card": build_word_card(res)}
        elif action_type == "query_ancient":
            title = action_val.get("title", "")
            res = query_ancient_text(title)
            return {"card": build_ancient_card(res)}
        elif action_type == "generate_dictation_checklist" or action_type == "dictate_step":
            session_id = action_val.get("session_id", "demo")
            session = get_vocab_session(session_id)
            items = session.get("items", []) if session else []
            checklist_card = build_vocab_checklist_card(session_id, items, show_answers=False)
            open_message_id = body.get("open_message_id", "")
            if open_message_id:
                background_tasks.add_task(
                    reply_interactive_card,
                    open_message_id,
                    checklist_card,
                    os.getenv("FEISHU_APP_ID", "").strip(),
                    os.getenv("FEISHU_APP_SECRET", "").strip()
                )
            return {"toast": {"type": "success", "content": "📝 默写清单已生成！"}, "card": checklist_card}
        elif action_type == "toggle_checklist_answers":
            session_id = action_val.get("session_id", "demo")
            show_ans = action_val.get("show_answers", False)
            session = get_vocab_session(session_id)
            items = session.get("items", []) if session else []
            return {
                "toast": {"type": "info", "content": "已显示参考答案" if show_ans else "已隐藏参考答案"},
                "card": build_vocab_checklist_card(session_id, items, show_answers=show_ans)
            }
        elif action_type == "show_vocab_full_list" or action_type == "dictate_exit":
            session_id = action_val.get("session_id", "")
            session = get_vocab_session(session_id)
            items = session.get("items", []) if session else []
            return {"toast": {"type": "info", "content": "已切换为英汉对照清单"}, "card": build_vocab_list_card(session_id, items)}
        elif action_type == "trigger_immediate_extraction":
            target_user = action_val.get("user_id") or sender_id
            img_count = get_batch_image_count(target_user)
            background_tasks.add_task(
                trigger_immediate_batch_extraction,
                target_user,
                os.getenv("FEISHU_APP_ID", "").strip(),
                os.getenv("FEISHU_APP_SECRET", "").strip()
            )
            return {"card": build_image_processing_card(img_count)}
        
        return {"toast": {"type": "info", "content": "功能已就绪"}}

    # 3. 飞书 v2.0 事件订阅 (im.message.receive_v1)
    header = body.get("header", {})
    event_type = header.get("event_type")

    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
        sender_type = event.get("sender", {}).get("sender_type")
        # 忽略机器人的自身发信，避免循环处理
        if sender_type == "app":
            return {"code": 0, "msg": "ignore bot message"}

        event_id = header.get("event_id", "")
        message = event.get("message", {})
        message_id = message.get("message_id", "")

        # 飞书事件幂等性校验：如果该事件已在处理中或已处理过，直接返回成功，坚决避免重复执行与反复发消息
        if check_and_mark_event_processed(event_id, message_id):
            print(f"[Feishu Deduplicate] 拦截到重复投递事件: event_id={event_id}, message_id={message_id}，已忽略")
            return {"code": 0, "msg": "duplicate event ignored"}

        # 启动后台异步任务进行大模型分析与回复，本接口立即返回 HTTP 200，杜绝飞书 3 秒超时重试机制
        background_tasks.add_task(process_feishu_im_message_task, event)
        return {"code": 0, "msg": "success"}

    return {"code": 0, "msg": "success"}

async def process_vocab_bot_im_message_task(event: dict):
    """
    专属英语背单词机器人（苏九背词伴读）异步消息处理器：
    专精课文高亮划线词汇提取、默写卡片推进与中考考标词汇互动。
    """
    try:
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type")
        chat_id = message.get("chat_id")
        sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id") or chat_id or "default_user"

        card_to_send = None

        if msg_type == "image":
            # 专属背词机器人：发截图 100% 直接走英语课文划线词汇识别与提取
            try:
                content_obj = json.loads(message.get("content", "{}"))
                image_key = content_obj.get("image_key", "")
            except Exception:
                image_key = ""

            if image_key and message_id:
                img_bytes = await download_image_resource(
                    message_id, image_key, 
                    app_id=VOCAB_APP_ID, app_secret=VOCAB_APP_SECRET
                )
                if img_bytes:
                    # 加入 30 秒防抖聚合队列，重置倒计时并自动跨图接缝智能拼接
                    await add_image_to_batch(
                        user_id=sender_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        img_bytes=img_bytes,
                        app_id=VOCAB_APP_ID,
                        app_secret=VOCAB_APP_SECRET
                    )
                    # 结果由聚合器在 30 秒静默期结束后统一推送卡片，无需在此即刻回复
                    return
                else:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⚠️ 图片读取失败"}},
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": "未能成功获取图片资源，请确认该背词机器人应用是否已开通 `im:resource` 权限。"}}
                        ]
                    }

        elif msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)

            # 意图 1：呼出主导航 / 帮助 / 问候
            if not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "你好", "hi", "hello", "背单词", "背词"]:
                card_to_send = build_vocab_bot_welcome_card()

            # 意图 2：开始默写 / 练习
            elif any(k in user_query for k in ["默写", "自测", "练习"]):
                demo_items = [
                    {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                    {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing 动名词"},
                    {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
                ]
                session = create_vocab_session(sender_id, demo_items, "课文高亮划线默写自测")
                card_to_send = build_vocab_dictation_card(session["session_id"], session["items"], 0, False)

            # 意图 3：打印 / A4
            elif any(k in user_query for k in ["打印", "a4", "导出", "试卷"]):
                workbench_url = "https://dilonclaw.cloud/suzhou/vocab?tab=print"
                card_to_send = {
                    "config": {"wide_screen_mode": True},
                    "header": {"template": "blue", "title": {"tag": "plain_text", "content": "🖨️ A4 纸打印排版工作台"}},
                    "elements": [
                        {"tag": "div", "text": {"tag": "lark_md", "content": "已为您准备好【苏州市初三英语课文默写卷】与【考前背诵清单】A4 纸排版。\n\n点击下方按钮即可进入专属页面一键打印："}},
                        {
                            "tag": "action",
                            "actions": [
                                {"tag": "button", "text": {"tag": "plain_text", "content": "🖨️ 打开打印页面"}, "type": "primary", "multi_url": {"url": workbench_url, "pc_url": workbench_url}}
                            ]
                        }
                    ]
                }

            # 意图 4：查单词 / 查词
            elif user_query.startswith("查单词") or user_query.startswith("单词") or re.match(r"^[a-zA-Z\s\-]+$", user_query):
                search_word = re.sub(r"^(查单词|单词|word)\s*", "", user_query, flags=re.IGNORECASE).strip()
                word_result = query_english_word(search_word)
                if word_result.get("matched"):
                    card_to_send = build_word_card(word_result)
                else:
                    llm_ans = await generate_suzhou_answer(f"初三英语考纲单词与搭配：{search_word}", "九年级英语")
                    card_to_send = build_qa_result_card(f"单词：{search_word}", llm_ans or "词库正在收录中", "九年级英语", "english")

            # 意图 5：普通提问或建议
            else:
                card_to_send = {
                    "config": {"wide_screen_mode": True},
                    "header": {"template": "blue", "title": {"tag": "plain_text", "content": "🇬🇧 苏九背词伴读 · 专属提示"}},
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"tag": "lark_md", "content": f"收到您的消息：`{user_query}`\n\n📸 **想要背单词/默写？** 请直接将课本中带有荧光笔划线或手写标记的照片发送给我，我将自动提取并生成默写卡片！"}
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 查看使用导航"}, "type": "default", "value": {"action": "back_to_vocab_menu"}}
                            ]
                        }
                    ]
                }

        if card_to_send and message_id:
            await reply_interactive_card(
                message_id, card_to_send, 
                app_id=VOCAB_APP_ID, app_secret=VOCAB_APP_SECRET
            )

    except Exception as e:
        print(f"[Vocab Bot Async Task Error] 异常: {e}")

@app.post("/api/feishu/vocab_event")
@app.post("/api/feishu/vocab/event")
async def feishu_vocab_event_handler(request: Request, background_tasks: BackgroundTasks):
    """
    专属英语背单词机器人 Webhook 网关端点：
    1. URL Verification 安全握手
    2. 卡片 Action 原地刷新交互 (dictate_step, dictate_exit, vocab_bot_demo, back_to_vocab_menu)
    3. IM 接收消息事件 (幂等去重 + BackgroundTasks 异步处理，避免飞书超时重试)
    """
    try:
        body = await request.json()
    except Exception:
        return {"code": 0, "msg": "invalid json"}

    # 1. 飞书 URL 校验握手
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}

    # 2. 飞书交互式卡片点击回传 (card.action.trigger)
    if "action" in body and ("open_message_id" in body or "open_id" in body):
        action_val = body.get("action", {}).get("value", {})
        action_type = action_val.get("action")

        if action_type == "back_to_vocab_menu":
            return {"card": build_vocab_bot_welcome_card()}
        elif action_type == "vocab_bot_demo":
            demo_items = [
                {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"},
                {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
            ]
            session = create_vocab_session("demo_user", demo_items, "课文高亮划线提取示例")
            return {"card": build_vocab_list_card(session["session_id"], session["items"])}
        elif action_type == "generate_dictation_checklist" or action_type == "dictate_step":
            session_id = action_val.get("session_id", "demo")
            session = get_vocab_session(session_id)
            if not session:
                demo_items = [
                    {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                    {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"},
                    {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
                ]
                session = create_vocab_session("demo_user", demo_items, "课文重点词汇默写清单")
            items = session.get("items", [])
            checklist_card = build_vocab_checklist_card(session["session_id"], items, show_answers=False)
            open_message_id = body.get("open_message_id", "")
            if open_message_id:
                background_tasks.add_task(
                    reply_interactive_card,
                    open_message_id,
                    checklist_card,
                    VOCAB_APP_ID,
                    VOCAB_APP_SECRET
                )
            return {"toast": {"type": "success", "content": "📝 默写清单已生成！"}, "card": checklist_card}
        elif action_type == "toggle_checklist_answers":
            session_id = action_val.get("session_id", "demo")
            show_ans = action_val.get("show_answers", False)
            session = get_vocab_session(session_id)
            items = session.get("items", []) if session else []
            return {
                "toast": {"type": "info", "content": "已显示参考答案" if show_ans else "已隐藏参考答案"},
                "card": build_vocab_checklist_card(session_id, items, show_answers=show_ans)
            }
        elif action_type == "show_vocab_full_list" or action_type == "dictate_exit":
            session_id = action_val.get("session_id", "demo")
            session = get_vocab_session(session_id)
            items = session.get("items", []) if session else []
            return {"toast": {"type": "info", "content": "已切换为英汉对照清单"}, "card": build_vocab_list_card(session_id, items)}
        elif action_type == "trigger_immediate_extraction":
            sender_id = body.get("open_id") or body.get("user_id") or body.get("open_chat_id", "")
            target_user = action_val.get("user_id") or sender_id
            img_count = get_batch_image_count(target_user)
            background_tasks.add_task(
                trigger_immediate_batch_extraction,
                target_user,
                VOCAB_APP_ID,
                VOCAB_APP_SECRET
            )
            return {"card": build_image_processing_card(img_count)}
        
        return {"toast": {"type": "info", "content": "功能已就绪"}}

    # 3. 飞书 v2.0 事件订阅 (im.message.receive_v1)
    header = body.get("header", {})
    event_type = header.get("event_type")

    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
        sender_type = event.get("sender", {}).get("sender_type")
        if sender_type == "app":
            return {"code": 0, "msg": "ignore bot message"}

        event_id = header.get("event_id", "")
        message = event.get("message", {})
        message_id = message.get("message_id", "")

        if check_and_mark_event_processed(event_id, message_id):
            print(f"[Vocab Bot Deduplicate] 拦截到重复事件: event_id={event_id}, message_id={message_id}")
            return {"code": 0, "msg": "duplicate event ignored"}

        background_tasks.add_task(process_vocab_bot_im_message_task, event)
        return {"code": 0, "msg": "success"}

    return {"code": 0, "msg": "success"}

@app.get("/api/system/model_status")

async def get_model_status():
    """查看当前激活的大模型配置与系统预设的全部支持厂商"""
    return {
        "active_humanities": get_current_model_config("humanities"),
        "active_stem": get_current_model_config("stem"),
        "supported_providers": {
            k: {
                "name": v["name"],
                "humanities_model": v.get("humanities_model", ""),
                "stem_model": v.get("stem_model", ""),
                "description": v["description"]
            }
            for k, v in SUPPORTED_PROVIDERS.items()
        }
    }

# 开发者测试预览接口
@app.get("/api/test/menu_card")
async def test_menu_card():
    """测试获取助学菜单卡片 JSON"""
    return build_menu_card()

@app.get("/api/test/subject_card")
async def test_subject_card(subject: str = "physics"):
    """测试获取各学科专属答疑台卡片 JSON"""
    return build_subject_workbench_card(subject)

@app.get("/api/test/physics_card")
async def test_physics_card(topic: str = "欧姆定律"):
    """测试获取苏科版物理考点卡片 JSON"""
    res = query_physics_concept(topic)
    return build_physics_card(res["data"]) if res.get("matched") else res

@app.get("/api/test/chemistry_card")
async def test_chemistry_card(topic: str = "酸碱盐"):
    """测试获取初三化学考点卡片 JSON"""
    res = query_chemistry_concept(topic)
    return build_chemistry_card(res["data"]) if res.get("matched") else res

@app.get("/api/test/word_card")
async def test_word_card(word: str = "generous"):
    """测试获取单词解析卡片 JSON"""
    return build_word_card(query_english_word(word))

@app.get("/api/test/ancient_card")
async def test_ancient_card(title: str = "岳阳楼记"):
    """测试获取古文解析卡片 JSON"""
    return build_ancient_card(query_ancient_text(title))

@app.get("/api/test/vocab_card")
async def test_vocab_card():
    """测试获取课文划线词组清单卡片 JSON"""
    demo_items = [
        {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
        {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"},
        {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
    ]
    session = create_vocab_session("test_user", demo_items, "课文重点划线词组")
    return build_vocab_list_card(session["session_id"], session["items"])

@app.get("/api/test/dictate_card")
async def test_dictate_card(index: int = 0, reveal: bool = False):
    """测试获取逐词翻页默写自测卡片 JSON"""
    demo_items = [
        {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
        {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"}
    ]
    session = create_vocab_session("test_user", demo_items, "课文重点划线词组")
    return build_vocab_dictation_card(session["session_id"], session["items"], index, reveal)

@app.get("/api/test/vocab_welcome_card")
async def test_vocab_welcome_card():
    """测试获取专属背单词机器人欢迎卡片 JSON"""
    return build_vocab_bot_welcome_card()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

