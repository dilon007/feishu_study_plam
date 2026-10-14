"""
苏九学伴 - 文理科智能分流大模型适配调度引擎 (Subject-Aware Multi-LLM Engine)
核心功能：
1. 文理智能路由：文科(语文/英语/政史) -> Flash 极速模型；理科(数学/物理/化学) -> Pro 深度推理模型。
2. 自动降级容错：遇 429 限流或 503 繁忙时，自动无缝平滑回退，保障学生端零报错。
3. 厂商即插即用：支持 Gemini、DeepSeek、通义千问等统一调度。
"""
import os
import re
import base64
import httpx
from dotenv import load_dotenv
from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT

load_dotenv()

# ==========================================
# 常见初三中考适配大模型预设矩阵
# ==========================================
SUPPORTED_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "humanities_model": "gemini-3.5-flash",
        "stem_model": "gemini-3.5-flash",
        "description": "谷歌最新 Gemini 3.5 旗舰矩阵，兼具秒级响应与超强多模态数理化识图推理。"
    },
    "deepseek": {
        "name": "DeepSeek (深度求索)",
        "base_url": "https://api.deepseek.com/v1",
        "humanities_model": "deepseek-chat",
        "stem_model": "deepseek-reasoner",
        "description": "国内中考性价比标杆：文科用 Chat 敏捷响应；理科用 Reasoner(R1) 慢思考深度推导。"
    },
    "qwen": {
        "name": "阿里云通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "humanities_model": "qwen-plus",
        "stem_model": "qwen-max",
        "description": "阿里大模型：文科用 Plus 擅长文言与社科；理科用 Max 强化复杂数理推算。"
    },
    "openai": {
        "name": "OpenAI 官方或中转",
        "base_url": "https://api.openai.com/v1",
        "humanities_model": "gpt-4o-mini",
        "stem_model": "gpt-4o",
        "description": "标准 OpenAI 模型矩阵。"
    }
}

# 理科高频特征词库 (命中则判定为理科，调用 Pro 模型)
STEM_KEYWORDS = [
    "数学", "物理", "化学", "函数", "方程", "不等式", "顶点", "对称轴", "抛物线",
    "圆", "切线", "直径", "弦", "相似", "全等", "直角三角形", "勾股", "三角函数", "sin", "cos", "tan",
    "杠杆", "滑轮", "机械效率", "浮力", "压强", "欧姆定律", "电路", "滑动变阻器", "电功率", "电压", "电流",
    "酸碱盐", "复分解", "金属活动性", "置换反应", "化学方程式", "质量分数", "沉淀", "推断题", "计算题", "证明"
]

def detect_subject_category(question: str, subject: str = "") -> str:
    """
    智能研判学科类型：
    返回 'stem' (理科 -> 路由至 Pro 模型) 或 'humanities' (文科 -> 路由至 Flash 模型)
    """
    sub_lower = subject.lower().strip()
    q_lower = question.lower()

    # 1. 显式学科标签判定
    if any(k in sub_lower for k in ["数", "理", "化", "math", "physic", "chem"]):
        return "stem"
    if any(k in sub_lower for k in ["语", "英", "史", "道", "政", "english", "chinese"]):
        return "humanities"

    # 2. 正则公式与理科特征判定 (如 x^2, y=kx+b, 几何符号)
    if re.search(r"[xyz]\s*[\=\+\-\*\/]|\b[a-z]\s*\(x\)|\d+[\+\-\*\/]\d+|\b(sin|cos|tan)\b|[∠△⊥∥⊙]", question):
        return "stem"

    # 3. 理科关键词命中
    for kw in STEM_KEYWORDS:
        if kw in q_lower:
            return "stem"

    # 默认归入文科通用处理
    return "humanities"

def get_current_model_config(category: str = "humanities") -> dict:
    """获取当前生效的模型配置（区分文理科模型）"""
    provider_key = os.getenv("AI_PROVIDER", "gemini").lower().strip()
    preset = SUPPORTED_PROVIDERS.get(provider_key, SUPPORTED_PROVIDERS["gemini"])

    base_url = os.getenv("AI_BASE_URL", "").strip() or preset["base_url"]
    api_key = os.getenv("AI_API_KEY", "").strip()

    # 根据文理科选择对应模型
    if category == "stem":
        model = os.getenv("AI_MODEL_STEM", "").strip() or preset.get("stem_model", "gemini-1.5-pro")
    else:
        model = os.getenv("AI_MODEL_HUMANITIES", "").strip() or preset.get("humanities_model", "gemini-1.5-flash")

    return {
        "provider": provider_key,
        "provider_name": preset["name"],
        "base_url": base_url.rstrip("/"),
        "model": model,
        "category": category,
        "is_configured": bool(api_key),
        "api_key_masked": f"{api_key[:6]}******{api_key[-4:]}" if len(api_key) > 10 else ("已配置" if api_key else "未配置")
    }

async def generate_suzhou_answer(question: str, subject: str = "初三综合") -> str:
    """
    核心入口：文理双引擎路由 + 容错平滑降级
    """
    category = detect_subject_category(question, subject)
    config = get_current_model_config(category)
    api_key = os.getenv("AI_API_KEY", "").strip()

    if not api_key:
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 优先使用目标模型，并接入高可用 gemini-3.5-flash / gemini-3.6-flash / gemini-3.5-flash-lite 级联容灾保底
    candidate_models = []
    for m in [config["model"], "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    endpoint = f"{config['base_url']}/chat/completions"

    async with httpx.AsyncClient(timeout=40) as client:
        for model_name in candidate_models:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SUZHOU_GRADE9_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"【学科类别】：{'理科深度推导' if category == 'stem' else '文科规范解析'}（{subject}）\n【学生提问】：{question}\n\n请按照苏州市初中九年级中考评分标准，给出：1. 对应苏科版/统编版教材考点定位；2. 规范踩分步骤；3. 易错点提醒。"
                    }
                ],
                "temperature": 0.2 if category == "stem" else 0.4
            }
            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"].strip()
                        return content
                else:
                    print(f"[Model {model_name} HTTP {resp.status_code}] Attempting fallback if available. Error: {resp.text[:120]}")
            except Exception as e:
                print(f"[Model {model_name} Exception] {e}")

    return ""

async def generate_suzhou_vision_answer(image_bytes: bytes, user_prompt: str = "", mime_type: str = "image/jpeg") -> str:
    """
    多模态数理化截图智能解析：
    接收学生上传的试卷/习题截图，自动调用多模态大模型提取题目与几何/函数图形并输出初三中考解题规范。
    具备多层级高可用无缝切换，杜绝 429 限流与 503 繁忙。
    """
    if not image_bytes:
        return "未能成功读取到截图文件，请重新截图发送。"

    api_key = os.getenv("AI_API_KEY", "").strip()
    if not api_key:
        return "当前尚未配置大模型 API Key，暂无法进行图像智能解析。"

    provider_key = os.getenv("AI_PROVIDER", "gemini").lower().strip()
    preset = SUPPORTED_PROVIDERS.get(provider_key, SUPPORTED_PROVIDERS["gemini"])
    base_url = os.getenv("AI_BASE_URL", "").strip() or preset["base_url"]
    
    # 截图解题默认优先调用理科模型，并设置 gemini-3.5-flash 系列作为坚实兜底
    pro_model = os.getenv("AI_MODEL_STEM", "").strip() or preset.get("stem_model", "gemini-3.5-flash")
    flash_model = os.getenv("AI_MODEL_HUMANITIES", "").strip() or preset.get("humanities_model", "gemini-3.5-flash")
    candidate_models = []
    for m in [pro_model, flash_model, "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_image}"

    instruction = (
        "【苏州市九年级中考数理化截图解题规范】\n"
        "请仔细观察这张初三题目截图（注意题目中的文字、几何图形、坐标系、电路图或化学反应装置）：\n"
        "1. 【题目条件提取】：准确转写截图中的已知条件与求证/求值问题；\n"
        "2. 【考点与定理依据】：明确指出涉及的苏科版九年级教材章节（如圆周角定理、二次函数顶点式、相似三角形比、欧姆定律等）；\n"
        "3. 【规范解题步骤】：符合苏州中考评分标准的推导过程，写明设元、辅助线构造及关键计算，不跳步、不使用高中超纲知识；\n"
        "4. 【中考易错点警示】：指出该题型在阅卷中学生常犯的丢分陷阱（如定义域、检验根、单位、取值范围分类讨论）。"
    )
    if user_prompt:
        instruction += f"\n学生补充要求：{user_prompt}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=45) as client:
        for model_name in candidate_models:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SUZHOU_GRADE9_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instruction},
                            {"type": "image_url", "image_url": {"url": data_url}}
                        ]
                    }
                ],
                "temperature": 0.2
            }
            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        return data["choices"][0]["message"]["content"].strip()
                else:
                    print(f"[Vision Model {model_name} HTTP {resp.status_code}] Trying fallback: {resp.text[:120]}")
            except Exception as e:
                print(f"[Vision Model {model_name} Exception] {e}")

    return "识别题目截图时服务繁忙，请稍后重新发送或直接输入文字提问。"

