from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import json
import re

from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT, check_for_out_of_bounds
from knowledge_db import (
    query_english_word, query_ancient_text,
    query_physics_concept, query_chemistry_concept
)
from card_builder import (
    SUBJECT_METAS, build_menu_card, build_subject_workbench_card,
    build_physics_card, build_chemistry_card, build_word_card,
    build_ancient_card, build_qa_result_card
)
from feishu_client import reply_interactive_card, send_chat_card, download_image_resource
from llm_provider import generate_suzhou_answer, generate_suzhou_vision_answer, get_current_model_config, SUPPORTED_PROVIDERS
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="苏九学伴 - 学习助手中台",
    description="针对苏州市9年级学生的学习助手中台后端 API 与飞书消息机器人引擎",
    version="1.5.0"
)

# 内存会话管理：记录每位学生当前选定的复习学科（默认为数学 math）
# 格式：{ "open_id_or_chat_id": "physics" | "chemistry" | "math" | "english" | "chinese" | "politics" }
user_active_subjects: dict[str, str] = {}


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

@app.post("/api/feishu/event")
async def feishu_event_handler(request: Request):
    """
    飞书开放平台核心网关：
    1. URL Verification (飞书首次配置事件回调时的安全握手)
    2. IM 接收消息事件 (处理单聊、群聊 @助手 呼出助学菜单与查词查文)
    3. 卡片回传交互 (点击助学菜单按钮或卡片交互)
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
        
        return {"toast": {"type": "info", "content": "功能已就绪"}}

    # 3. 飞书 v2.0 事件订阅 (im.message.receive_v1)
    header = body.get("header", {})
    event_type = header.get("event_type")

    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
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
            # 学生直接发送数理化题目截图（拍照搜题）
            sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id") or chat_id or "default_user"
            active_subj = user_active_subjects.get(sender_id, "math")
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
                    prompt_hint = f"当前复习学科：{subj_info['name']}，匹配教材考标：{subj_info['book']}。"
                    # 调用多模态大模型进行数理化视觉题目解析（优先 Pro 推理模型）
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
