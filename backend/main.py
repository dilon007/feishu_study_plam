from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT, check_for_out_of_bounds

app = FastAPI(
    title="苏九学伴 - 学习助手中台",
    description="针对苏州市9年级学生的学习助手中台后端 API",
    version="1.0.0"
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
    subject: str = "math"  # math, physics, english, etc.
    question: str

@app.post("/api/ask")
async def ask_assistant(req: QuestionRequest):
    """
    接收初三学生提问，经由防超纲安全审查后返回标准解析
    """
    # 1. 检查提问输入是否超纲
    input_check = check_for_out_of_bounds(req.question)
    
    # 模拟知识检索与LLM回答（后续可无缝接入DeepSeek/ChatGPT/通义千问等模型）
    simulated_answer = (
        f"【苏州中考考点定位】{req.subject} 核心考查\n\n"
        f"针对问题：'{req.question}'\n\n"
        "【苏科版标准解题步骤】\n"
        "1. 规范设未知数并列出等量关系；\n"
        "2. 按照九年级课本规范进行配方/因式分解；\n"
        "3. 验根并写出答语。\n\n"
        "【踩分点提醒】步骤中切勿遗漏定义域讨论与单位书写。"
    )

    # 2. 检查输出是否安全
    output_check = check_for_out_of_bounds(simulated_answer)

    return {
        "status": "success",
        "scope": "苏州市9年级考纲范围",
        "guardrail_status": "Passed" if output_check["is_safe"] else "Blocked",
        "answer": simulated_answer,
        "input_warning": None if input_check["is_safe"] else f"检测到包含超纲词汇：{input_check['violations']}"
    }

@app.post("/api/feishu/event")
async def feishu_event_handler():
    """
    飞书开放平台事件订阅入口（接收飞书消息、加好友通知、卡片交互回传等）
    """
    # 实际对接时由 lark-oapi 的 EventDispatcher 进行解密与分发
    return {"code": 0, "msg": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
