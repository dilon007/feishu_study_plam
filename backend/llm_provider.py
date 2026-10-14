"""
苏九学伴 - 多模型统一适配调度引擎 (Multi-LLM Provider Engine)
支持一键平滑切换：Google Gemini (当前默认)、DeepSeek、通义千问 (Qwen)、火山豆包 (Doubao)、自定义 OpenAI/Ollama 等。
"""
import os
import httpx
from dotenv import load_dotenv
from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT

load_dotenv()

# ==========================================
# 常见初三中考适配大模型预设矩阵
# ==========================================
SUPPORTED_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini (当前默认)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-1.5-flash",
        "description": "谷歌官方旗舰模型，海外首尔节点超低延迟直连，推导步骤规范敏捷。"
    },
    "deepseek": {
        "name": "DeepSeek (深度求索)",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "description": "国内解题性价比标杆，支持 deepseek-chat 或 deepseek-reasoner (R1深度推理)。"
    },
    "qwen": {
        "name": "阿里云通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "description": "阿里自研大模型，语文文言文与历史道法综合理解极强。"
    },
    "doubao": {
        "name": "火山引擎豆包 (字节跳动)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "description": "字节跳动自研大模型，对话响应快速。"
    },
    "openai": {
        "name": "OpenAI 官方或中转",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "description": "OpenAI 官方接口或代理中转服务。"
    },
    "custom": {
        "name": "自定义/本地私有化 (如 Ollama / OneAPI)",
        "base_url": "http://127.0.0.1:11434/v1",
        "default_model": "qwen2.5:7b",
        "description": "支持接入云服务器本地私有部署模型或第三方聚合 API 网关。"
    }
}

def get_current_model_config() -> dict:
    """获取当前生效的模型提供商与参数"""
    provider_key = os.getenv("AI_PROVIDER", "gemini").lower().strip()
    preset = SUPPORTED_PROVIDERS.get(provider_key, SUPPORTED_PROVIDERS["gemini"])

    # 优先采用用户环境变量中的显式指定，未指定时采用预设最佳值
    base_url = os.getenv("AI_BASE_URL", "").strip() or preset["base_url"]
    model = os.getenv("AI_MODEL", "").strip() or preset["default_model"]
    api_key = os.getenv("AI_API_KEY", "").strip()

    return {
        "provider": provider_key,
        "provider_name": preset["name"],
        "base_url": base_url.rstrip("/"),
        "model": model,
        "is_configured": bool(api_key),
        "api_key_masked": f"{api_key[:6]}******{api_key[-4:]}" if len(api_key) > 10 else ("已配置" if api_key else "未配置")
    }

async def generate_suzhou_answer(question: str, subject: str = "初三综合") -> str:
    """
    统一入口：向当前激活的大模型发起解答请求
    自动附带苏州市9年级骨干名师提示词与防超纲要求
    """
    config = get_current_model_config()
    api_key = os.getenv("AI_API_KEY", "").strip()

    if not api_key:
        return ""

    endpoint = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SUZHOU_GRADE9_SYSTEM_PROMPT},
            {
                "role": "user", 
                "content": f"【学生学科】：{subject}\n【提问题目】：{question}\n\n请按照苏州市初中九年级中考评分标准，给出：1. 对应教材考点定位；2. 规范推导步骤；3. 易错踩分点提醒。"
            }
        ],
        "temperature": 0.25
    }

    async with httpx.AsyncClient(timeout=35) as client:
        try:
            resp = await client.post(endpoint, headers=headers, json=payload)
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"[LLM {config['provider_name']} Error] Response: {data}")
        except Exception as e:
            print(f"[LLM {config['provider_name']} Exception] {e}")

    return ""
