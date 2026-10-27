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
    build_image_processing_card,
    build_stem_bot_welcome_card, build_stem_qa_result_card,
    build_vocab_bitable_welcome_card, build_vocab_bitable_append_result_card,
    build_vocab_bitable_recite_card, build_vocab_bitable_checklist_card,
    build_vocab_bitable_dictation_card,
    build_arts_bot_welcome_card, build_arts_qa_result_card
)
from feishu_client import (
    reply_interactive_card, send_chat_card, send_user_card,
    send_card_to_dialog, download_image_resource,
    VOCAB_APP_ID, VOCAB_APP_SECRET,
    VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET,
    STEM_APP_ID, STEM_APP_SECRET,
    ARTS_APP_ID, ARTS_APP_SECRET
)
from llm_provider import (
    generate_suzhou_answer, generate_suzhou_vision_answer, 
    extract_highlighted_vocab_from_image,
    get_current_model_config, SUPPORTED_PROVIDERS
)
from vocab_service import (
    create_vocab_session, get_vocab_session, update_vocab_session,
    get_user_latest_vocab_session
)
from bitable_service import (
    get_user_bitable_info, bind_user_bitable, parse_bitable_url,
    create_or_ensure_user_bitable, append_vocab_to_bitable,
    fetch_vocab_from_bitable, update_vocab_status_in_bitable
)
from vocab_aggregator import (
    add_image_to_batch, trigger_immediate_batch_extraction,
    get_batch_image_count
)
import httpx
from dotenv import load_dotenv

load_dotenv()

# 独立机器人凭证配置（支持多机器人隔离发信与资源读取）
VOCAB_APP_ID = os.getenv("FEISHU_VOCAB_APP_ID", "").strip() or os.getenv("FEISHU_APP_ID", "").strip()
VOCAB_APP_SECRET = os.getenv("FEISHU_VOCAB_APP_SECRET", "").strip() or os.getenv("FEISHU_APP_SECRET", "").strip()

VOCAB_BITABLE_APP_ID = os.getenv("FEISHU_VOCAB_BITABLE_APP_ID", "").strip() or VOCAB_APP_ID
VOCAB_BITABLE_APP_SECRET = os.getenv("FEISHU_VOCAB_BITABLE_APP_SECRET", "").strip() or VOCAB_APP_SECRET

STEM_APP_ID = os.getenv("FEISHU_STEM_APP_ID", "").strip() or os.getenv("FEISHU_APP_ID", "").strip()
STEM_APP_SECRET = os.getenv("FEISHU_STEM_APP_SECRET", "").strip() or os.getenv("FEISHU_APP_SECRET", "").strip()

ARTS_APP_ID = os.getenv("FEISHU_ARTS_APP_ID", "").strip() or os.getenv("FEISHU_APP_ID", "").strip()
ARTS_APP_SECRET = os.getenv("FEISHU_ARTS_APP_SECRET", "").strip() or os.getenv("FEISHU_APP_SECRET", "").strip()

app = FastAPI(
    title="苏九学伴 - 学习助手中台",
    description="针对苏州市9年级学生的学习助手中台后端 API 与飞书多机器人集群（含全科中台、独立英语背词伴读机器人、独立数理化拍照搜题机器人、新版多维表格默写机器人与独立文科检索问答机器人）",
    version="1.9.0"
)

# 内存会话管理：全科综合机器人当前学科
user_active_subjects: dict[str, str] = {}

# 专属数理化拍照搜题机器人：记录每位学生的偏好学科（默认为数学 math，可选 physics 或 chemistry）
stem_user_active_subjects: dict[str, str] = {}

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
            # 意图 2.5：在英语科目下要求生成默写清单/列表
            elif active_subj == "english" and any(k in user_query for k in ["默写", "清单", "列表", "自测"]):
                latest_session = get_user_latest_vocab_session(sender_id)
                if latest_session and latest_session.get("items"):
                    card_to_send = build_vocab_checklist_card(latest_session["session_id"], latest_session["items"], show_answers=False)
                else:
                    card_to_send = build_subject_workbench_card("english")

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
            sender_id = (
                body.get("open_id") 
                or body.get("user_id") 
                or body.get("context", {}).get("open_id", "") 
                or body.get("context", {}).get("user_id", "") 
                or ""
            )
            open_chat_id = (
                body.get("open_chat_id") 
                or body.get("context", {}).get("open_chat_id", "") 
                or ""
            )
            if not session:
                session = get_user_latest_vocab_session(sender_id)
            if not session:
                demo_items = [
                    {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                    {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"},
                    {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
                ]
                session = create_vocab_session(sender_id or "demo_user", demo_items, "课文重点词汇默写清单")
            items = session.get("items", [])
            checklist_card = build_vocab_checklist_card(session["session_id"], items, show_answers=False)
            background_tasks.add_task(
                send_card_to_dialog,
                checklist_card,
                "",  # 传空 message_id，防止在卡片下折叠回复，确保作为新消息直接出现在主对话框
                open_chat_id,
                sender_id,
                os.getenv("FEISHU_APP_ID", "").strip(),
                os.getenv("FEISHU_APP_SECRET", "").strip()
            )
            return {"toast": {"type": "success", "content": "已在对话框中发送纯中文默写列表！"}}
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

            # 意图 2：生成默写清单 / 默写列表 / 默写自测（直接在对话框中回复默写列表）
            elif any(k in user_query for k in ["默写", "清单", "列表", "自测", "练习"]):
                latest_session = get_user_latest_vocab_session(sender_id)
                if latest_session and latest_session.get("items"):
                    card_to_send = build_vocab_checklist_card(latest_session["session_id"], latest_session["items"], show_answers=False)
                else:
                    demo_items = [
                        {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                        {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing 动名词"},
                        {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
                    ]
                    session = create_vocab_session(sender_id, demo_items, "课文重点词汇默写清单")
                    card_to_send = build_vocab_checklist_card(session["session_id"], session["items"], show_answers=False)

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
            sender_id = (
                body.get("open_id") 
                or body.get("user_id") 
                or body.get("context", {}).get("open_id", "") 
                or body.get("context", {}).get("user_id", "") 
                or ""
            )
            open_chat_id = (
                body.get("open_chat_id") 
                or body.get("context", {}).get("open_chat_id", "") 
                or ""
            )
            if not session:
                session = get_user_latest_vocab_session(sender_id)
            if not session:
                demo_items = [
                    {"phrase": "take...seriously", "phonetic": "/teɪk ˈsɪəriəsli/", "meaning": "认真对待；严肃处理", "note": "Unit 1 核心短语"},
                    {"phrase": "pay attention to", "phonetic": "/peɪ əˈtenʃn tu/", "meaning": "注意；留心", "note": "后接 doing"},
                    {"phrase": "generous", "phonetic": "/ˈdʒenərəs/", "meaning": "慷慨的；大方的", "note": "核心形容词"}
                ]
                session = create_vocab_session(sender_id or "demo_user", demo_items, "课文重点词汇默写清单")
            items = session.get("items", [])
            checklist_card = build_vocab_checklist_card(session["session_id"], items, show_answers=False)
            background_tasks.add_task(
                send_card_to_dialog,
                checklist_card,
                "",  # 传空 message_id，防止在卡片下折叠回复，确保作为新消息直接出现在主对话框
                open_chat_id,
                sender_id,
                VOCAB_APP_ID,
                VOCAB_APP_SECRET
            )
            return {"toast": {"type": "success", "content": "已在对话框中发送纯中文默写列表！"}}
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


# ==============================================================================
# 新版专属英语默写机器人（飞书交互卡片 + 飞书多维表格 Bitable 架构，零 HTML 依赖）
# 核心原则：
# 1. 原版英语默写机器人 (/api/feishu/vocab_event) 完整保留；
# 2. 新机器人 (/api/feishu/vocab_bitable_event) 以飞书多维表格为核心词库：
#    - 拍照只负责往多维表格里追加词条；
#    - 所有背诵和默写均实时从多维表格拉取！
# ==============================================================================

DEMO_BITABLE_VOCAB_ITEMS = [
    {"phrase": "take...seriously", "meaning": "认真对待；严肃处理", "note": "9A Unit 1 核心短语"},
    {"phrase": "pay attention to", "meaning": "注意；留心", "note": "后接名词或 doing 动名词"},
    {"phrase": "leave a good impression on sb.", "meaning": "给某人留下好印象", "note": "苏州中考完形与写作高频短语"},
    {"phrase": "have difficulty (in) doing sth.", "meaning": "做某事有困难", "note": "in 可省略，后接 V-ing"}
]

async def process_vocab_bitable_bot_im_message_task(event: dict):
    """
    新版英语默写机器人（飞书交互卡片 + 多维表格版）异步消息处理器：
    - 发送图片 -> 识别划线短语 -> 直接追加写入飞书多维表格；
    - 发送飞书多维表格链接 -> 自动绑定为当前学生的核心词库；
    - 发送“默写”/“背诵”/“翻页” -> 直接从多维表格实时拉取数据并推送对应交互卡片。
    """
    try:
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type")
        chat_id = message.get("chat_id")
        sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id") or chat_id or "default_user"

        card_to_send = None

        if msg_type == "image":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                image_key = content_obj.get("image_key", "")
            except Exception:
                image_key = ""

            if image_key and message_id:
                img_bytes = await download_image_resource(
                    message_id, image_key,
                    app_id=VOCAB_BITABLE_APP_ID, app_secret=VOCAB_BITABLE_APP_SECRET
                )
                if img_bytes:
                    # 加入 30 秒防抖聚合队列 (mode="bitable")，识别后自动追加写入飞书多维表格
                    await add_image_to_batch(
                        user_id=sender_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        img_bytes=img_bytes,
                        app_id=VOCAB_BITABLE_APP_ID,
                        app_secret=VOCAB_BITABLE_APP_SECRET,
                        mode="bitable"
                    )
                    return
                else:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⚠️ 图片读取失败"}},
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": "未能读取图片，请确认该机器人应用已开通 `im:resource` 与 `bitable:app` 权限。"}}
                        ]
                    }

        elif msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)

            # 意图 0：如果用户直接发送了飞书多维表格链接 (包含 /base/xxx)，自动绑定为该用户的核心词库
            parsed_bt = parse_bitable_url(user_query)
            if parsed_bt:
                app_token, table_id = parsed_bt
                bind_user_bitable(sender_id, app_token, table_id, url=user_query.strip())
                ok, info, msg = await create_or_ensure_user_bitable(
                    sender_id, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                card_to_send = build_vocab_bitable_welcome_card(
                    bitable_url=b_info.get("url", ""),
                    total_count=len(items),
                    sync_note=f"已成功绑定您的飞书多维表格！（{msg}）"
                )

            # 意图 1：呼出主导航 / 帮助 / 问候
            elif not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "你好", "hi", "hello", "背单词", "多维表格"]:
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                card_to_send = build_vocab_bitable_welcome_card(
                    bitable_url=b_info.get("url", ""),
                    total_count=len(items)
                )

            # 意图 2：要求从多维表格拉取生成纯中文 Todo List 默写清单
            elif any(k in user_query for k in ["默写", "清单", "自测", "练习"]):
                scope = "latest" if "最近" in user_query or "最新" in user_query else ("unmastered" if "待默写" in user_query else "all")
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                if not items:
                    _, b_info, _ = await append_vocab_to_bitable(
                        sender_id, DEMO_BITABLE_VOCAB_ITEMS, "示例初三核心短语",
                        VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                    )
                    items, b_info, _ = await fetch_vocab_from_bitable(
                        sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                    )
                card_to_send = build_vocab_bitable_checklist_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    show_answers=False,
                    scope=scope
                )

            # 意图 3：要求从多维表格拉取背诵清单 / 词库列表
            elif any(k in user_query for k in ["背诵", "词库", "列表", "对照"]):
                items, b_info, from_remote = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                card_to_send = build_vocab_bitable_recite_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    scope="all",
                    from_remote=from_remote
                )

            # 意图 4：逐词翻页默写
            elif any(k in user_query for k in ["逐词", "翻页", "抽查"]):
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "unmastered", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                card_to_send = build_vocab_bitable_dictation_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    current_index=0,
                    show_answer=False,
                    scope="unmastered"
                )

            # 意图 5：查单词 / 其他输入
            elif user_query.startswith("查单词") or user_query.startswith("单词") or re.match(r"^[a-zA-Z\s\-]+$", user_query):
                search_word = re.sub(r"^(查单词|单词|word)\s*", "", user_query, flags=re.IGNORECASE).strip()
                word_result = query_english_word(search_word)
                if word_result.get("matched"):
                    card_to_send = build_word_card(word_result)
                else:
                    llm_ans = await generate_suzhou_answer(f"初三英语考纲单词与搭配：{search_word}", "九年级英语")
                    card_to_send = build_qa_result_card(f"单词：{search_word}", llm_ans or "词库正在收录中", "九年级英语", "english")

            else:
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                card_to_send = build_vocab_bitable_welcome_card(
                    bitable_url=b_info.get("url", ""),
                    total_count=len(items),
                    sync_note="📸 直接发送课本划线照片即可将词条追加写入多维表格；或点击下方按钮直接从多维表格拉取背诵/默写！"
                )

        if card_to_send and message_id:
            await reply_interactive_card(
                message_id, card_to_send,
                app_id=VOCAB_BITABLE_APP_ID, app_secret=VOCAB_BITABLE_APP_SECRET
            )

    except Exception as e:
        print(f"[Vocab Bitable Bot Async Task Error] 异常: {e}")


@app.post("/api/feishu/vocab_bitable_event")
@app.post("/suzhou/api/feishu/vocab_bitable_event")
@app.post("/api/feishu/vocab_bitable/event")
async def feishu_vocab_bitable_event_handler(request: Request, background_tasks: BackgroundTasks):
    """
    新版专属英语默写机器人（飞书交互卡片 + 多维表格版）Webhook 网关端点：
    1. URL Verification 安全握手
    2. 卡片 Action 交互（全量实时读写飞书多维表格，零 HTML 网页依赖）
    3. IM 消息接收（拍照追加写入多维表格 + 多维表格链接绑定 + 拉取默写）
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
        sender_id = (
            body.get("open_id")
            or body.get("user_id")
            or body.get("context", {}).get("open_id", "")
            or body.get("context", {}).get("user_id", "")
            or body.get("open_chat_id", "")
            or "default_user"
        )
        open_chat_id = (
            body.get("open_chat_id")
            or body.get("context", {}).get("open_chat_id", "")
            or ""
        )

        # 返回多维表格版首屏导航
        if action_type == "back_to_bitable_vocab_menu":
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            return {"card": build_vocab_bitable_welcome_card(b_info.get("url", ""), len(items))}

        # 一键自动创建/连接飞书多维表格
        elif action_type == "bitable_auto_create":
            ok, b_info, msg = await create_or_ensure_user_bitable(
                sender_id, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            return {
                "toast": {"type": "success" if ok else "info", "content": msg[:60]},
                "card": build_vocab_bitable_welcome_card(b_info.get("url", ""), len(items), sync_note=msg)
            }

        # 追加示例词条到多维表格
        elif action_type == "bitable_init_demo":
            sync_ok, b_info, sync_msg = await append_vocab_to_bitable(
                sender_id,
                DEMO_BITABLE_VOCAB_ITEMS,
                batch_title="9A 课文重点划线示例",
                app_id=VOCAB_BITABLE_APP_ID,
                app_secret=VOCAB_BITABLE_APP_SECRET
            )
            return {
                "toast": {"type": "success", "content": "已将示例词条追加至多维表格词库！"},
                "card": build_vocab_bitable_append_result_card(
                    appended_items=DEMO_BITABLE_VOCAB_ITEMS,
                    bitable_url=b_info.get("url", ""),
                    batch_title="9A 课文重点划线示例",
                    sync_ok=sync_ok,
                    sync_msg=sync_msg
                )
            }

        # 从多维表格实时拉取【英汉对照背诵清单】
        elif action_type == "bitable_pull_recite":
            scope = action_val.get("scope", "all")
            items, b_info, from_remote = await fetch_vocab_from_bitable(
                sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            if not items and scope == "all":
                await append_vocab_to_bitable(
                    sender_id, DEMO_BITABLE_VOCAB_ITEMS, "9A 课文重点划线示例",
                    VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                items, b_info, from_remote = await fetch_vocab_from_bitable(
                    sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
            return {
                "toast": {"type": "info", "content": f"已从多维表格实时拉取 {len(items)} 条词汇"},
                "card": build_vocab_bitable_recite_card(items, b_info.get("url", ""), scope=scope, from_remote=from_remote)
            }

        # 从多维表格实时拉取生成【纯中文 Todo List 默写清单】（直接投递至主对话框）
        elif action_type == "bitable_pull_checklist":
            scope = action_val.get("scope", "all")
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            if not items:
                await append_vocab_to_bitable(
                    sender_id, DEMO_BITABLE_VOCAB_ITEMS, "9A 课文重点划线示例",
                    VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
            checklist_card = build_vocab_bitable_checklist_card(
                items=items,
                bitable_url=b_info.get("url", ""),
                show_answers=False,
                scope=scope
            )
            background_tasks.add_task(
                send_card_to_dialog,
                checklist_card,
                "",
                open_chat_id,
                sender_id,
                VOCAB_BITABLE_APP_ID,
                VOCAB_BITABLE_APP_SECRET
            )
            return {"toast": {"type": "success", "content": f"已从多维表格拉取 {len(items)} 条词汇并在对话框生成默写单！"}}

        # 在默写清单卡片上切换显示/隐藏答案、切换范围或重新同步最新多维表格修改
        elif action_type == "bitable_toggle_checklist_answers":
            scope = action_val.get("scope", "all")
            show_ans = action_val.get("show_answers", False)
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            return {
                "toast": {"type": "info", "content": "已从多维表格同步最新词条"},
                "card": build_vocab_bitable_checklist_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    show_answers=show_ans,
                    scope=scope
                )
            }

        # 从多维表格实时拉取进行【逐词翻页默写】
        elif action_type == "bitable_pull_dictate_step":
            scope = action_val.get("scope", "all")
            idx = int(action_val.get("index", 0))
            reveal = bool(action_val.get("reveal", False))
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            if not items:
                await append_vocab_to_bitable(
                    sender_id, DEMO_BITABLE_VOCAB_ITEMS, "9A 课文重点划线示例",
                    VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
                items, b_info, _ = await fetch_vocab_from_bitable(
                    sender_id, "all", VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
                )
            return {
                "card": build_vocab_bitable_dictation_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    current_index=idx,
                    show_answer=reveal,
                    scope=scope
                )
            }

        # 在默写卡片上标记【已掌握 / 易错重点】，同步回写飞书多维表格并进入下一题
        elif action_type == "bitable_mark_status":
            record_id = action_val.get("record_id", "")
            new_status = action_val.get("new_status", "已掌握")
            scope = action_val.get("scope", "all")
            next_idx = int(action_val.get("index", 0))
            await update_vocab_status_in_bitable(
                sender_id, record_id, new_status,
                VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            items, b_info, _ = await fetch_vocab_from_bitable(
                sender_id, scope, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET
            )
            return {
                "toast": {"type": "success", "content": f"已将状态【{new_status}】同步写回多维表格！"},
                "card": build_vocab_bitable_dictation_card(
                    items=items,
                    bitable_url=b_info.get("url", ""),
                    current_index=next_idx,
                    show_answer=False,
                    scope=scope
                )
            }

        # 点击【⚡ 立即识别生成】提前结束 30 秒倒计时并追加写入多维表格
        elif action_type == "trigger_immediate_extraction":
            target_user = action_val.get("user_id") or sender_id
            img_count = get_batch_image_count(target_user, mode="bitable")
            background_tasks.add_task(
                trigger_immediate_batch_extraction,
                target_user,
                VOCAB_BITABLE_APP_ID,
                VOCAB_BITABLE_APP_SECRET,
                "bitable"
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
            print(f"[Vocab Bitable Bot Deduplicate] 拦截到重复事件: event_id={event_id}, message_id={message_id}")
            return {"code": 0, "msg": "duplicate event ignored"}

        background_tasks.add_task(process_vocab_bitable_bot_im_message_task, event)
        return {"code": 0, "msg": "success"}

    return {"code": 0, "msg": "success"}


# ==============================================================================
# 专属数理化拍照搜题机器人（苏九数理化搜题伴读）
# 专精苏州市初三数学（苏科版）、物理（苏科版）、化学（初三化学/沪教版）拍照搜题
# ==============================================================================

async def process_stem_bot_im_message_task(event: dict):
    """
    专属数理化拍照搜题机器人（苏九数理化搜题伴读）异步消息处理器：
    专精初三数学、物理、化学题目拍照识别、分步推导与中考评分踩分点剖析。
    """
    try:
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type")
        chat_id = message.get("chat_id")
        sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id") or chat_id or "default_user"
        active_subj = stem_user_active_subjects.get(sender_id, "math")
        subj_info = SUBJECT_METAS.get(active_subj, SUBJECT_METAS["math"])

        card_to_send = None

        if msg_type == "image":
            # 专属数理化搜题机器人：发截图 100% 专精数理化试卷与习题拍照解题
            try:
                content_obj = json.loads(message.get("content", "{}"))
                image_key = content_obj.get("image_key", "")
            except Exception:
                image_key = ""

            if image_key and message_id:
                img_bytes = await download_image_resource(
                    message_id, image_key,
                    app_id=STEM_APP_ID, app_secret=STEM_APP_SECRET
                )
                if img_bytes:
                    prompt_hint = (
                        f"学生当前偏好学科为【{subj_info['name']} ({subj_info['book']})】。"
                        "请先仔细观察题目截图，若题目属于数学、物理或化学，请自动按苏州市九年级（初三）对应学科中考考标进行规范分步推导。"
                        "格式必须包含：1.【考点定位】；2.【苏科版/初三标准解题步骤】；3.【苏州中考易错点与踩分提醒】。"
                        "严格杜绝使用高中或大学超纲知识（如禁止导数、向量、高中电离平衡等）！"
                    )
                    vision_answer = await generate_suzhou_vision_answer(img_bytes, user_prompt=prompt_hint)
                    out_check = check_for_out_of_bounds(vision_answer)
                    if out_check["is_safe"]:
                        card_to_send = build_stem_qa_result_card(
                            "📸 学生数理化试卷/习题拍照截图",
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
                                    "text": {"tag": "lark_md", "content": f"**检测到解题推导包含高中超纲内容**：`{out_check['violations']}`。\n\n苏九学伴严格遵循苏州市初中学业水平考试要求，初中阶段不使用高中推导与概念。请确认题目是否为初三阶段内容。"}
                                },
                                {
                                    "tag": "action",
                                    "actions": [
                                        {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回搜题工作台"}, "type": "default", "value": {"action": "back_to_stem_menu"}}
                                    ]
                                }
                            ]
                        }
                else:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⚠️ 图片读取提示"}},
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": "未能读取到截图。请检查该数理化搜题机器人应用是否已勾选开通 **`im:resource`（获取与上传图片或文件资源）** 权限。"}}
                        ]
                    }

        elif msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)

            # 意图 1：呼出导航 / 帮助 / 问候
            if not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "你好", "hi", "hello", "搜题", "拍照搜题"]:
                card_to_send = build_stem_bot_welcome_card(active_subj)

            # 意图 2：切换数理化学科偏好（数学、物理、化学）
            elif any(user_query == k or user_query == f"切换{k}" or user_query == f"换{k}" or user_query == f"选{k}" for k in ["数学", "物理", "化学"]):
                subj_map = {"数学": "math", "物理": "physics", "化学": "chemistry"}
                for k, v in subj_map.items():
                    if k in user_query:
                        stem_user_active_subjects[sender_id] = v
                        card_to_send = build_stem_bot_welcome_card(v)
                        break

            # 意图 3：文字直接输入数理化题目进行答疑
            else:
                guard_check = check_for_out_of_bounds(user_query)
                if not guard_check["is_safe"]:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 苏州9年级考纲防超纲拦截"}},
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": f"**抱歉，检测到提问包含高中超纲内容**：`{guard_check['violations']}`。\n\n本机器人严格遵循苏州市初中学业水平考试考标，初中阶段不使用高中推导。请尝试以初中课本知识提问。"}}
                        ]
                    }
                else:
                    # 优先快速命中本地知识库（如物理/化学基础概念）
                    if active_subj == "physics":
                        p_res = query_physics_concept(user_query)
                        if p_res.get("matched"):
                            card_to_send = build_physics_card(p_res["data"])
                    elif active_subj == "chemistry":
                        c_res = query_chemistry_concept(user_query)
                        if c_res.get("matched"):
                            card_to_send = build_chemistry_card(c_res["data"])

                    if not card_to_send:
                        llm_answer = await generate_suzhou_answer(user_query, f"{subj_info['name']} ({subj_info['book']})")
                        if llm_answer:
                            out_check = check_for_out_of_bounds(llm_answer)
                            if out_check["is_safe"]:
                                card_to_send = build_stem_qa_result_card(user_query, llm_answer, subj_info["name"], active_subj)
                            else:
                                card_to_send = {
                                    "config": {"wide_screen_mode": True},
                                    "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 答题输出防超纲拦截"}},
                                    "elements": [
                                        {"tag": "div", "text": {"tag": "lark_md", "content": f"生成内容包含高中超纲内容：`{out_check['violations']}`，已熔断保护。请换个问法。"}}
                                    ]
                                }
                        else:
                            card_to_send = build_stem_bot_welcome_card(active_subj)

        if card_to_send and message_id:
            await reply_interactive_card(
                message_id, card_to_send,
                app_id=STEM_APP_ID, app_secret=STEM_APP_SECRET
            )

    except Exception as e:
        print(f"[STEM Bot Async Task Error] 异常: {e}")

@app.post("/api/feishu/stem_event")
@app.post("/api/feishu/stem/event")
async def feishu_stem_event_handler(request: Request, background_tasks: BackgroundTasks):
    """
    专属数理化拍照搜题机器人 Webhook 网关端点：
    1. URL Verification 安全握手
    2. 卡片 Action 原地刷新交互 (stem_select_subject, stem_demo_question, back_to_stem_menu)
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
        sender_id = body.get("open_id") or body.get("user_id") or body.get("open_chat_id", "")

        if action_type == "back_to_stem_menu":
            cur_subj = stem_user_active_subjects.get(sender_id, "math")
            return {"card": build_stem_bot_welcome_card(cur_subj)}

        elif action_type == "stem_select_subject":
            subj = action_val.get("subject", "math")
            if sender_id:
                stem_user_active_subjects[sender_id] = subj
            subj_name = SUBJECT_METAS.get(subj, {}).get("name", subj)
            return {
                "toast": {"type": "success", "content": f"已锁定【{subj_name}】考标！现在发送照片即可精准搜题。"},
                "card": build_stem_bot_welcome_card(subj)
            }

        elif action_type == "stem_demo_question":
            subj = action_val.get("subject", "math")
            demo_q_map = {
                "math": (
                    "如图，在 Rt△ABC 中，∠C=90°，AC=6，BC=8，以 AC 为直径作 ⊙O，求过点 B 的切线长及弦长关系。",
                    "【考点定位】苏科版九年级数学下册·圆与切线的性质、勾股定理与相似三角形。\n\n"
                    "【苏科版标准解题步骤】\n"
                    "1. 连结圆心 O 与切点 D，根据切线性质定理得 OD ⊥ BD；\n"
                    "2. 在 Rt△ABC 中，由勾股定理求得 AB = √(6² + 8²) = 10；\n"
                    "3. ⊙O 半径 r = AC / 2 = 3，OB = √(OC² + BC²) = √(3² + 8²) = √73；\n"
                    "4. 在 Rt△ODB 中，切线长 BD = √(OB² - OD²) = √(73 - 9) = 8。\n\n"
                    "【中考踩分点提醒】作辅助线时务必明确标注‘连结 OD’，切线垂直必须写明‘切线性质定理’，不跳步。"
                ),
                "physics": (
                    "在如图所示的动态电路中，电源电压恒为 6V，定值电阻 R1=10Ω，滑动变阻器 R2 最大阻值为 20Ω，当滑片 P 移动时求电流表与电压表示数变化范围。",
                    "【考点定位】苏科版九年级物理下册·第十四章 欧姆定律与动态电路分析。\n\n"
                    "【苏科版标准解题步骤】\n"
                    "1. 分析电路连接方式：定值电阻 R1 与滑动变阻器 R2 串联；电压表测 R2 两端电压，电流表测串联电路电流；\n"
                    "2. 当滑片 P 移至最左端 (R2=0) 时：电路中总电阻最小 Rmin = R1 = 10Ω，此时电流最大 Imax = U / R1 = 6V / 10Ω = 0.6A；电压表示数 U2min = 0V；\n"
                    "3. 当滑片 P 移至最右端 (R2=20Ω) 时：电路总电阻最大 Rmax = R1 + R2 = 30Ω，此时电流最小 Imin = U / Rmax = 6V / 30Ω = 0.2A；电压表示数最大 U2max = Imin * R2 = 0.2A * 20Ω = 4V；\n"
                    "4. 综上：电流表示数变化范围为 0.2A ~ 0.6A，电压表示数变化范围为 0V ~ 4V。\n\n"
                    "【中考踩分点提醒】必须写明各电表所测对象，计算极值时必须交代滑片具体位置及理由，写清单位。"
                ),
                "chemistry": (
                    "某白色固体可能含有 CaCO3、Na2CO3、BaCl2、Na2SO4 中的一种或几种，加水溶解后产生白色沉淀，加入足量稀硝酸沉淀部分溶解并产生无色气体。推断原固体组成。",
                    "【考点定位】初三化学下册·酸碱盐物质推断与离子共存。\n\n"
                    "【标准推断推导步骤】\n"
                    "1. 加水产生沉淀：可能为 CaCO3，或 Na2CO3 与 BaCl2 反应生成的 BaCO3，或 Na2SO4 与 BaCl2 反应生成的 BaSO4；\n"
                    "2. 加入足量稀硝酸沉淀‘部分溶解’：\n"
                    "   • 溶解并有气体产生的沉淀必为碳酸盐（生成 CO2），说明混合物中必含碳酸根相关成分；\n"
                    "   • 不溶于稀硝酸的沉淀必为 BaSO4，由此反推混合物中必同时含有 BaCl2 和 Na2SO4！\n"
                    "3. 产生气体证明必含 Na2CO3 或 CaCO3；若混合物中无 CaCO3 则 Na2CO3 与 BaCl2 反应产生 BaCO3，二者溶解与不溶共存。\n"
                    "4. 结论：原混合物中一定含有 BaCl2、Na2SO4，至少含有 Na2CO3 或 CaCO3 中的一种。\n\n"
                    "【中考踩分点提醒】硫酸钡 BaSO4 不溶于稀硝酸是推断的关键题眼，写化学式时切勿漏写下标。"
                )
            }
            demo_tuple = demo_q_map.get(subj, demo_q_map["math"])
            demo_card = build_stem_qa_result_card(demo_tuple[0], demo_tuple[1], SUBJECT_METAS.get(subj, {}).get("name", "数理化"), subj)
            return {"card": demo_card}

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
            print(f"[STEM Bot Deduplicate] 拦截到重复事件: event_id={event_id}, message_id={message_id}")
            return {"code": 0, "msg": "duplicate event ignored"}

        background_tasks.add_task(process_stem_bot_im_message_task, event)
        return {"code": 0, "msg": "success"}

    return {"code": 0, "msg": "success"}

# ==============================================================================
# 专属文科检索问答机器人（苏九文科检索伴读）
# 专精苏州市初三语文（统编版字词/古诗文）、英语（译林牛津版单词短语）、
# 历史（统编版世界近代史）与道德与法治的群聊 @ 检索问答，即问即答无特殊流程
# ==============================================================================

def detect_arts_subject(user_query: str) -> str:
    """根据提问内容自动研判文科子学科，用于注入对应教材考标提示"""
    if any(k in user_query for k in ["历史", "朝代", "变法", "革命", "条约", "文艺复兴", "新航路", "工业革命", "一战", "二战", "十月革命", "冷战", "近代化"]):
        return "九年级历史 (统编版)"
    if any(k in user_query for k in ["道德", "法治", "宪法", "公民", "制度", "国情", "核心价值观", "民主", "法律"]):
        return "九年级道德与法治 (统编版)"
    if any(k in user_query for k in ["古文", "古诗", "文言", "字词", "拼音", "成语", "病句", "名著", "文学常识", "课文", "默写", "赏析", "名句", "诗句", "诗意", "作者"]):
        return "九年级语文 (统编版)"
    return "九年级文科综合 (统编版/译林版)"

async def process_arts_bot_im_message_task(event: dict):
    """
    专属文科检索问答机器人（苏九文科检索伴读）异步消息处理器：
    群聊 @ 或私聊直接提问，即问即答：
    - 英语单词/短语 → 优先本地译林版词库秒级命中，未命中走大模型检索；
    - 语文古诗文 → 优先本地统编版古文库秒级命中，未命中走大模型检索；
    - 其他文科问题（语文/历史/道法）→ 直接大模型规范检索解答；
    - 全流程双重防超纲审查（提问输入 + 生成输出）。
    """
    try:
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type")

        card_to_send = None

        if msg_type == "image":
            # 文科检索机器人专注文字问答，图片场景引导至对应专属机器人
            card_to_send = {
                "config": {"wide_screen_mode": True},
                "header": {"template": "orange", "title": {"tag": "plain_text", "content": "📷 暂不支持图片检索"}},
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": "本机器人专注**文科文字内容检索**（语文、英语、历史、道法），请直接在群里 @ 本机器人并输入问题。\n\n- 📸 数理化试卷拍照搜题请使用**苏九数理化搜题伴读**；\n- 🇬🇧 英语课文划线识别请使用**苏九背词伴读**。"}}
                ]
            }

        elif msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)

            # 意图 1：呼出导航 / 帮助 / 问候（群里只 @ 不带内容同样返回使用指南）
            if not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "你好", "hi", "hello", "文科", "检索"]:
                card_to_send = build_arts_bot_welcome_card()

            # 意图 2：英语单词/短语检索（优先本地译林版词库秒级命中）
            elif user_query.startswith("查单词") or user_query.startswith("单词") or re.match(r"^[a-zA-Z\s\-']+$", user_query):
                search_word = re.sub(r"^(查单词|单词|word)\s*", "", user_query, flags=re.IGNORECASE).strip()
                if not search_word:
                    card_to_send = build_arts_bot_welcome_card()
                else:
                    word_result = query_english_word(search_word)
                    if word_result.get("matched"):
                        card_to_send = build_word_card(word_result)
                    else:
                        llm_ans = await generate_suzhou_answer(
                            f"初三英语考纲单词与短语释义、常见搭配与用法辨析：{search_word}",
                            "九年级英语 (译林牛津版9A/9B)"
                        )
                        out_check = check_for_out_of_bounds(llm_ans or "")
                        if llm_ans and out_check["is_safe"]:
                            card_to_send = build_arts_qa_result_card(f"单词：{search_word}", llm_ans, "九年级英语")
                        elif llm_ans:
                            card_to_send = {
                                "config": {"wide_screen_mode": True},
                                "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 答题输出防超纲拦截"}},
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"生成内容包含超纲内容：`{out_check['violations']}`，已熔断保护。请换个问法。"}}
                                ]
                            }
                        else:
                            card_to_send = build_arts_qa_result_card(f"单词：{search_word}", "词库正在收录中，请稍后再试或换个问法。", "九年级英语")

            # 意图 3：语文古诗文检索（优先本地统编版古文古诗库秒级命中）
            elif user_query.startswith("查古文") or user_query.startswith("古文") or user_query.startswith("古诗") or any(k in user_query for k in ["岳阳楼记", "醉翁亭记", "出师表", "水调歌头", "先天下", "行路难", "酬乐天", "左迁至蓝关"]):
                search_title = re.sub(r"^(查古文|古文|古诗|诗词)\s*", "", user_query).strip()
                if not search_title:
                    card_to_send = build_arts_bot_welcome_card()
                else:
                    ancient_result = query_ancient_text(search_title)
                    if ancient_result.get("matched"):
                        card_to_send = build_ancient_card(ancient_result)
                    else:
                        llm_ans = await generate_suzhou_answer(
                            f"统编九年级文言与古诗考点、重点字词释义与名句赏析：{search_title}",
                            "九年级语文 (统编版)"
                        )
                        out_check = check_for_out_of_bounds(llm_ans or "")
                        if llm_ans and out_check["is_safe"]:
                            card_to_send = build_arts_qa_result_card(search_title, llm_ans, "九年级语文")
                        elif llm_ans:
                            card_to_send = {
                                "config": {"wide_screen_mode": True},
                                "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 答题输出防超纲拦截"}},
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"生成内容包含超纲内容：`{out_check['violations']}`，已熔断保护。请换个问法。"}}
                                ]
                            }
                        else:
                            card_to_send = build_arts_qa_result_card(search_title, "篇目正在收录中，请稍后再试或换个问法。", "九年级语文")

            # 意图 4：其他文科问题（语文/历史/道法/英语综合）直接大模型检索解答
            else:
                guard_check = check_for_out_of_bounds(user_query)
                if not guard_check["is_safe"]:
                    card_to_send = {
                        "config": {"wide_screen_mode": True},
                        "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 苏州9年级考纲防超纲拦截"}},
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": f"**抱歉，检测到提问包含高中超纲内容**：`{guard_check['violations']}`。\n\n本机器人严格遵循苏州市初中学业水平考试考标（语文/历史/道法统编版、英语译林牛津版），请尝试以初中课本知识提问。"}}
                        ]
                    }
                else:
                    subject = detect_arts_subject(user_query)
                    llm_answer = await generate_suzhou_answer(user_query, subject)
                    if llm_answer:
                        out_check = check_for_out_of_bounds(llm_answer)
                        if out_check["is_safe"]:
                            card_to_send = build_arts_qa_result_card(user_query, llm_answer, subject)
                        else:
                            card_to_send = {
                                "config": {"wide_screen_mode": True},
                                "header": {"template": "red", "title": {"tag": "plain_text", "content": "🛡️ 答题输出防超纲拦截"}},
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"生成内容包含高中超纲内容：`{out_check['violations']}`，已熔断保护。请换个问法。"}}
                                ]
                            }
                    else:
                        card_to_send = {
                            "config": {"wide_screen_mode": True},
                            "header": {"template": "orange", "title": {"tag": "plain_text", "content": "⏳ 检索服务繁忙"}},
                            "elements": [
                                {"tag": "div", "text": {"tag": "lark_md", "content": "当前检索服务暂时繁忙，请稍后重新提问。"}}
                            ]
                        }

        if card_to_send and message_id:
            await reply_interactive_card(
                message_id, card_to_send,
                app_id=ARTS_APP_ID, app_secret=ARTS_APP_SECRET
            )

    except Exception as e:
        print(f"[Arts Bot Async Task Error] 异常: {e}")

@app.post("/api/feishu/arts_event")
@app.post("/suzhou/api/feishu/arts_event")
@app.post("/api/feishu/arts/event")
async def feishu_arts_event_handler(request: Request, background_tasks: BackgroundTasks):
    """
    专属文科检索问答机器人 Webhook 网关端点：
    1. URL Verification 安全握手
    2. 卡片 Action 原地刷新交互 (arts_query_word, arts_query_ancient, back_to_arts_menu)
    3. IM 接收消息事件 (幂等去重 + BackgroundTasks 异步处理，避免飞书超时重试)
       群聊中 @ 本机器人即可提问，即问即答，无需学科切换等特殊流程。
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

        if action_type == "back_to_arts_menu":
            return {"card": build_arts_bot_welcome_card()}

        elif action_type == "arts_query_word":
            word = action_val.get("word", "")
            word_result = query_english_word(word)
            if word_result.get("matched"):
                return {"card": build_word_card(word_result)}
            ans = await generate_suzhou_answer(f"初三英语考纲单词与短语释义与搭配：{word}", "九年级英语 (译林牛津版9A/9B)")
            return {"card": build_arts_qa_result_card(f"单词：{word}", ans or "词库正在收录中", "九年级英语")}

        elif action_type == "arts_query_ancient":
            title = action_val.get("title", "")
            ancient_result = query_ancient_text(title)
            if ancient_result.get("matched"):
                return {"card": build_ancient_card(ancient_result)}
            ans = await generate_suzhou_answer(f"统编九年级文言考点与释义：{title}", "九年级语文 (统编版)")
            return {"card": build_arts_qa_result_card(title, ans or "篇目正在收录中", "九年级语文")}

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
            print(f"[Arts Bot Deduplicate] 拦截到重复事件: event_id={event_id}, message_id={message_id}")
            return {"code": 0, "msg": "duplicate event ignored"}

        background_tasks.add_task(process_arts_bot_im_message_task, event)
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

@app.get("/api/test/vocab_bitable_welcome_card")
async def test_vocab_bitable_welcome_card():
    """测试获取新版【飞书交互卡片 + 多维表格】专属英语默写机器人欢迎卡片 JSON"""
    return build_vocab_bitable_welcome_card("https://feishu.cn/base/demo_token", 4)

@app.get("/api/test/stem_welcome_card")
async def test_stem_welcome_card(subject: str = "math"):
    """测试获取专属数理化拍照搜题机器人欢迎卡片 JSON"""
    return build_stem_bot_welcome_card(subject)

@app.get("/api/test/arts_welcome_card")
async def test_arts_welcome_card():
    """测试获取专属文科检索问答机器人欢迎卡片 JSON"""
    return build_arts_bot_welcome_card()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

