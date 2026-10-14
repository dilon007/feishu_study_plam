from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import json
import re

from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT, check_for_out_of_bounds
from knowledge_db import query_english_word, query_ancient_text
from card_builder import build_menu_card, build_word_card, build_ancient_card, build_mode_input_card, build_qa_result_card
from feishu_client import reply_interactive_card, send_chat_card
from llm_provider import generate_suzhou_answer, get_current_model_config, SUPPORTED_PROVIDERS
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="苏九学伴 - 学习助手中台",
    description="针对苏州市9年级学生的学习助手中台后端 API 与飞书消息机器人引擎",
    version="1.3.0"
)

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

        if action_type == "back_to_menu":
            return {"card": build_menu_card()}
        elif action_type == "switch_mode":
            mode = action_val.get("mode", "english")
            return {"card": build_mode_input_card(mode)}
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

        if msg_type == "text":
            try:
                content_obj = json.loads(message.get("content", "{}"))
                raw_text = content_obj.get("text", "")
            except Exception:
                raw_text = message.get("content", "")

            user_query = clean_message_text(raw_text)

            card_to_send = None

            # 意图 A：@助手、呼出菜单、help、或者清空只 @了机器人
            if not user_query or user_query in ["菜单", "menu", "help", "帮助", "开始", "助学菜单"]:
                card_to_send = build_menu_card()

            # 意图 B：英语单词查询（包含关键词或纯英文字符）
            elif user_query.startswith("查单词") or user_query.startswith("单词") or re.match(r"^[a-zA-Z\s\-]+$", user_query):
                search_word = re.sub(r"^(查单词|单词|word)\s*", "", user_query, flags=re.IGNORECASE).strip()
                if not search_word:
                    card_to_send = build_mode_input_card("english")
                else:
                    word_result = query_english_word(search_word)
                    card_to_send = build_word_card(word_result)

            # 意图 C：初三古文古诗查询（篇目名称或名句）
            elif user_query.startswith("查古文") or user_query.startswith("古文") or user_query.startswith("古诗") or any(k in user_query for k in ["岳阳楼记", "醉翁亭记", "出师表", "水调歌头", "先天下"]):
                search_title = re.sub(r"^(查古文|古文|古诗|诗词)\s*", "", user_query).strip()
                if not search_title:
                    card_to_send = build_mode_input_card("ancient")
                else:
                    ancient_result = query_ancient_text(search_title)
                    card_to_send = build_ancient_card(ancient_result)

            # 意图 D：学科自由问答（经由防超纲安全审查 + Gemini/大模型名师解析）
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
                                "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回助学菜单"}, "type": "default", "value": {"action": "back_to_menu"}}]
                            }
                        ]
                    }
                else:
                    # 尝试调用多模型适配引擎解答
                    llm_answer = await generate_suzhou_answer(user_query)
                    if llm_answer:
                        out_check = check_for_out_of_bounds(llm_answer)
                        if out_check["is_safe"]:
                            card_to_send = build_qa_result_card(user_query, llm_answer)
                        else:
                            card_to_send = build_menu_card()
                    else:
                        card_to_send = build_menu_card()

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
