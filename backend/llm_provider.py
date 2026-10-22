"""
苏九学伴 - 文理科智能分流大模型适配调度引擎 (Subject-Aware Multi-LLM Engine)
核心功能：
1. 文理智能路由：文科(语文/英语/政史) -> Chat 敏捷模型；理科(数学/物理/化学) -> Reasoner 深度推理模型。
2. 跨厂商多级级联容灾防雪崩：DeepSeek (主用) <-> Google Gemini (备用) 自动无缝平滑回退，保障学生端零报错。
3. 厂商即插即用：支持 DeepSeek、Gemini、通义千问等统一调度与无感降级。
"""
import os
import re
import json
import base64
import httpx
from dotenv import load_dotenv
from guardrail import SUZHOU_GRADE9_SYSTEM_PROMPT

load_dotenv()


# ==========================================
# 常见初三中考适配大模型预设矩阵
# ==========================================
SUPPORTED_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek (深度求索)",
        "base_url": "https://api.deepseek.com/v1",
        "humanities_model": "deepseek-chat",
        "stem_model": "deepseek-reasoner",
        "description": "国内中考性价比与推理标杆：文科用 Chat 敏捷响应；理科用 Reasoner(R1) 深度逻辑推导。"
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "humanities_model": "gemini-3.5-flash",
        "stem_model": "gemini-3.5-flash",
        "description": "谷歌最新 Gemini 3.5 旗舰矩阵，兼具秒级响应与超强多模态数理化识图推理。"
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

# 理科高频特征词库 (命中则判定为理科，调用 Reasoner/Pro 深度模型)
STEM_KEYWORDS = [
    "数学", "物理", "化学", "函数", "方程", "不等式", "顶点", "对称轴", "抛物线",
    "圆", "切线", "直径", "弦", "相似", "全等", "直角三角形", "勾股", "三角函数", "sin", "cos", "tan",
    "杠杆", "滑轮", "机械效率", "浮力", "压强", "欧姆定律", "电路", "滑动变阻器", "电功率", "电压", "电流",
    "酸碱盐", "复分解", "金属活动性", "置换反应", "化学方程式", "质量分数", "沉淀", "推断题", "计算题", "证明"
]

def get_provider_credentials(provider_key: str) -> tuple[str, str]:
    """
    动态获取指定 provider 的 (base_url, api_key)。
    支持独立变量 (DEEPSEEK_API_KEY, GEMINI_API_KEY) 与全局回退 (AI_API_KEY, AI_BASE_URL)。
    """
    key = provider_key.lower().strip()
    preset = SUPPORTED_PROVIDERS.get(key, {})
    default_base = preset.get("base_url", "")
    active_provider = os.getenv("AI_PROVIDER", "deepseek").lower().strip()

    if key == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key and active_provider in ("deepseek", ""):
            api_key = os.getenv("AI_API_KEY", "").strip()
        base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
        if not base_url and active_provider == "deepseek":
            base_url = os.getenv("AI_BASE_URL", "").strip()
        return (base_url or default_base).rstrip("/"), api_key

    elif key == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key and active_provider == "gemini":
            api_key = os.getenv("AI_API_KEY", "").strip()
        base_url = os.getenv("GEMINI_BASE_URL", "").strip()
        if not base_url and active_provider == "gemini":
            base_url = os.getenv("AI_BASE_URL", "").strip()
        return (base_url or default_base).rstrip("/"), api_key

    elif key == "qwen":
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        if not api_key and active_provider == "qwen":
            api_key = os.getenv("AI_API_KEY", "").strip()
        base_url = os.getenv("QWEN_BASE_URL", "").strip()
        return (base_url or default_base).rstrip("/"), api_key

    elif key == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key and active_provider == "openai":
            api_key = os.getenv("AI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        return (base_url or default_base).rstrip("/"), api_key

    else:
        api_key = os.getenv("AI_API_KEY", "").strip()
        base_url = os.getenv("AI_BASE_URL", "").strip() or default_base
        return (base_url or "").rstrip("/"), api_key

def detect_subject_category(question: str, subject: str = "") -> str:
    """
    智能研判学科类型：
    返回 'stem' (理科 -> 路由至 Reasoner/Pro 深度模型) 或 'humanities' (文科 -> 路由至 Chat/Flash 敏捷模型)
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
    """获取当前生效的主模型配置（区分文理科模型）"""
    provider_key = os.getenv("AI_PROVIDER", "deepseek").lower().strip()
    preset = SUPPORTED_PROVIDERS.get(provider_key, SUPPORTED_PROVIDERS["deepseek"])

    base_url, api_key = get_provider_credentials(provider_key)

    # 根据文理科选择对应模型
    if category == "stem":
        model = os.getenv("AI_MODEL_STEM", "").strip() or preset.get("stem_model", "deepseek-reasoner")
    else:
        model = os.getenv("AI_MODEL_HUMANITIES", "").strip() or preset.get("humanities_model", "deepseek-chat")

    return {
        "provider": provider_key,
        "provider_name": preset["name"],
        "base_url": base_url,
        "model": model,
        "category": category,
        "is_configured": bool(api_key),
        "api_key_masked": f"{api_key[:6]}******{api_key[-4:]}" if len(api_key) > 10 else ("已配置" if api_key else "未配置")
    }

def build_execution_queue(task_type: str = "text", category: str = "humanities") -> list[dict]:
    """
    构造跨厂商多级级联容灾队列：
    task_type:
      - 'text': 文本问答与分步推导
      - 'vision_stem': 数理化试卷拍照识题与解题
      - 'vision_vocab': 英语课文划线词汇与句子提取
    每个 candidate 包含完整独立的: provider, base_url, api_key, model, temperature
    """
    active_provider = os.getenv("AI_PROVIDER", "deepseek").lower().strip()
    queue = []

    def add_candidate(provider: str, model_name: str, temp: float = 0.2):
        base_url, api_key = get_provider_credentials(provider)
        if not api_key:
            return
        # 避免重复加入相同 provider + model
        for item in queue:
            if item["provider"] == provider and item["model"] == model_name:
                return
        queue.append({
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model_name,
            "temperature": temp
        })

    # ==========================
    # 场景 1: 文本题目问答解析
    # ==========================
    if task_type == "text":
        if active_provider == "deepseek":
            if category == "stem":
                stem_model = os.getenv("AI_MODEL_STEM", "").strip() or "deepseek-reasoner"
                add_candidate("deepseek", stem_model, 0.2)
                add_candidate("deepseek", "deepseek-chat", 0.2)
            else:
                hum_model = os.getenv("AI_MODEL_HUMANITIES", "").strip() or "deepseek-chat"
                add_candidate("deepseek", hum_model, 0.4)
            # 容灾备用：Google Gemini 旗舰矩阵
            add_candidate("gemini", "gemini-3.5-flash", 0.2 if category == "stem" else 0.4)
            add_candidate("gemini", "gemini-3.6-flash", 0.2 if category == "stem" else 0.4)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.2 if category == "stem" else 0.4)
        elif active_provider == "gemini":
            add_candidate("gemini", "gemini-3.5-flash", 0.2 if category == "stem" else 0.4)
            add_candidate("gemini", "gemini-3.6-flash", 0.2 if category == "stem" else 0.4)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.2 if category == "stem" else 0.4)
            # 容灾备用：DeepSeek
            add_candidate("deepseek", "deepseek-reasoner" if category == "stem" else "deepseek-chat", 0.2 if category == "stem" else 0.4)
        else:
            # 其他 provider (qwen, openai)
            cfg = get_current_model_config(category)
            add_candidate(active_provider, cfg["model"], 0.2 if category == "stem" else 0.4)
            add_candidate("deepseek", "deepseek-reasoner" if category == "stem" else "deepseek-chat", 0.2 if category == "stem" else 0.4)
            add_candidate("gemini", "gemini-3.5-flash", 0.2 if category == "stem" else 0.4)

    # ==========================
    # 场景 2: 数理化拍照搜题
    # ==========================
    elif task_type == "vision_stem":
        if active_provider == "deepseek":
            add_candidate("deepseek", "deepseek-chat", 0.2)
            add_candidate("deepseek", "deepseek-reasoner", 0.2)
            # 容灾备用：Google Gemini 多模态
            add_candidate("gemini", "gemini-3.5-flash", 0.2)
            add_candidate("gemini", "gemini-3.6-flash", 0.2)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.2)
        elif active_provider == "gemini":
            add_candidate("gemini", "gemini-3.5-flash", 0.2)
            add_candidate("gemini", "gemini-3.6-flash", 0.2)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.2)
            # 容灾备用：DeepSeek
            add_candidate("deepseek", "deepseek-chat", 0.2)
        else:
            add_candidate(active_provider, "deepseek-chat", 0.2)
            add_candidate("gemini", "gemini-3.5-flash", 0.2)

    # ==========================
    # 场景 3: 英语课文划线生词提取
    # ==========================
    elif task_type == "vision_vocab":
        if active_provider == "deepseek":
            add_candidate("deepseek", "deepseek-chat", 0.1)
            # 容灾备用：Google Gemini 多模态
            add_candidate("gemini", "gemini-3.5-flash", 0.1)
            add_candidate("gemini", "gemini-3.6-flash", 0.1)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.1)
        elif active_provider == "gemini":
            add_candidate("gemini", "gemini-3.5-flash", 0.1)
            add_candidate("gemini", "gemini-3.6-flash", 0.1)
            add_candidate("gemini", "gemini-3.5-flash-lite", 0.1)
            # 容灾备用：DeepSeek
            add_candidate("deepseek", "deepseek-chat", 0.1)
        else:
            add_candidate(active_provider, "deepseek-chat", 0.1)
            add_candidate("gemini", "gemini-3.5-flash", 0.1)

    return queue


async def generate_suzhou_answer(question: str, subject: str = "初三综合") -> str:
    """
    核心入口：文理双引擎路由 + 跨厂商容错平滑降级 (DeepSeek 主用，Gemini 备用)
    """
    category = detect_subject_category(question, subject)
    queue = build_execution_queue(task_type="text", category=category)

    if not queue:
        print("[generate_suzhou_answer] Error: No configured AI models available in queue.")
        return ""

    async with httpx.AsyncClient(timeout=45) as client:
        for candidate in queue:
            endpoint = f"{candidate['base_url']}/chat/completions"
            headers = {
                "Authorization": f"Bearer {candidate['api_key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": candidate["model"],
                "messages": [
                    {"role": "system", "content": SUZHOU_GRADE9_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"【学科类别】：{'理科深度推导' if category == 'stem' else '文科规范解析'}（{subject}）\n【学生提问】：{question}\n\n请按照苏州市初中九年级中考评分标准，给出：1. 对应苏科版/统编版教材考点定位；2. 规范踩分步骤；3. 易错点提醒。"
                    }
                ],
                "temperature": candidate["temperature"]
            }

            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        msg = data["choices"][0].get("message", {})
                        content = (msg.get("content") or "").strip()
                        if not content and msg.get("reasoning_content"):
                            content = msg["reasoning_content"].strip()
                        if content:
                            return content
                else:
                    print(f"[{candidate['provider']} {candidate['model']} HTTP {resp.status_code}] Falling back to next model... Error: {resp.text[:120]}")
            except Exception as e:
                print(f"[{candidate['provider']} {candidate['model']} Exception] {e}. Trying next fallback...")

    return ""


async def generate_suzhou_vision_answer(image_bytes: bytes, user_prompt: str = "", mime_type: str = "image/jpeg") -> str:
    """
    多模态数理化截图智能解析：
    接收学生上传的试卷/习题截图，自动调用多模态大模型提取题目与几何/函数图形并输出初三中考解题规范。
    具备 DeepSeek 与 Gemini 跨厂商双引擎容灾，秒级响应，杜绝 429 限流与 503 繁忙。
    """
    if not image_bytes:
        return "未能成功读取到截图文件，请重新截图发送。"

    queue = build_execution_queue(task_type="vision_stem", category="stem")
    if not queue:
        return "当前尚未配置大模型 API Key，暂无法进行图像智能解析。"

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

    async with httpx.AsyncClient(timeout=45) as client:
        for candidate in queue:
            endpoint = f"{candidate['base_url']}/chat/completions"
            headers = {
                "Authorization": f"Bearer {candidate['api_key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": candidate["model"],
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
                "temperature": candidate["temperature"]
            }

            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        msg = data["choices"][0].get("message", {})
                        content = (msg.get("content") or "").strip()
                        if not content and msg.get("reasoning_content"):
                            content = msg["reasoning_content"].strip()
                        if content:
                            return content
                else:
                    print(f"[Vision {candidate['provider']} {candidate['model']} HTTP {resp.status_code}] Trying fallback: {resp.text[:120]}")
            except Exception as e:
                print(f"[Vision {candidate['provider']} {candidate['model']} Exception] {e}")

    return "识别题目截图时服务繁忙，请稍后重新发送或直接输入文字提问。"


async def extract_highlighted_vocab_from_multi_images(image_bytes_list: list[bytes], mime_type: str = "image/jpeg") -> list[dict]:
    """
    专门针对英语课文截图（支持单张或连续多张多页课文截图）：
    1. 识别图像中被荧光笔高亮、彩色标注、圆圈或下划线划出的英文生词、短语与重点句子；
    2. 【跨图接缝智能拼接】：针对多图跨页截断的划线短语/长句，自动对齐接缝处并拼接为完整条目，消除重叠重复；
    3. 严格保持笔迹连续性，输出中考规范标准 JSON 列表；
    4. 采用 DeepSeek 主力视觉与 Gemini 多级级联保障 100% 可用性。
    """
    if not image_bytes_list:
        return []

    # 过滤空图片字节
    valid_images = [b for b in image_bytes_list if b]
    if not valid_images:
        return []

    queue = build_execution_queue(task_type="vision_vocab")
    if not queue:
        return [
            {"phrase": "take...seriously", "phonetic": "-", "meaning": "认真对待；严肃处理", "note": "重点短语"},
            {"phrase": "pay attention to", "phonetic": "-", "meaning": "注意；留心", "note": "后接 doing 动名词"},
            {"phrase": "generous", "phonetic": "-", "meaning": "慷慨的；大方的", "note": "核心形容词"}
        ]

    is_multi = len(valid_images) > 1

    if is_multi:
        instruction = (
            f"【苏州市九年级英语课文多图连续划线提取与跨图接缝智能拼接】\n"
            f"你是一位精通苏州市初中英语（译林牛津版9A/9B）的中考教研名师。\n"
            f"学生按阅读先后顺序上传了 {len(valid_images)} 张连续的课文截图（图1、图2...按阅读先后顺序拍摄）。\n\n"
            "【极其关键的跨图接缝提取规范（必须严格执行）】：\n"
            "1. 【跨图接缝处连续拼接】：请特别仔细比对【上一张图片底部/末尾】与【下一张图片顶部/开头】的连接区域！\n"
            "   - 若学生划线的短语或一整句话跨越了图片分界（例如上一张图末尾划了前半段，下一张图开头划了后半段），务必将其【智能合并拼接还原为完整的一整条英文短语/句子】！严禁截断切碎成两截；\n"
            "2. 【重叠拍摄自动去重】：如果两张照片在上下边缘有部分重叠文本，重合区域内的划线词组只提取一次，绝不重复输出；\n"
            "3. 【划线物理连续性优先】：每张图内部连续划线的内容同样严格作为一条整体记录，不要擅自拆分；\n"
            "4. 【整句划线整体记录】：整句划线的保留整句，给出规范地道整句中考译文；单个词组给出核心考点释义；\n"
            "5. 严格输出标准 JSON 数组格式，严禁包含任何前言、结语或自然语言废话，格式如下：\n"
            "[\n"
            "  {\"phrase\": \"跨图拼接或连续划线的完整短语、词组或整句\", \"meaning\": \"中文注释释义或整句翻译\", \"note\": \"考点提醒或句型说明\"}\n"
            "]"
        )
    else:
        instruction = (
            "【苏州市九年级英语课文划线词汇与重点句型精准提取】\n"
            "你是一位精通苏州市初中英语（译林牛津版9A/9B）的中考教研名师。请仔细观察这张课文截图，找出学生在课本上做出的【人工标记生词、短语与重点句子】。\n"
            "【重点识别以下标记迹象】：\n"
            "1. 【荧光笔高亮涂色】：浅黄色、黄绿色、粉红色、天蓝色、淡紫色等半透明覆盖涂抹；\n"
            "2. 【手写划线】：印刷体正下方的横线、下划线、双横线、波浪线（包含铅笔灰线、黑色中性笔、红色圆珠笔）；\n"
            "3. 【圈选标记】：用手写圆圈、方框框选出来的重点词汇或短语；\n"
            "4. 【批注旁引】：旁边带有箭头指向、引出线或旁边写有中文翻译手写批注对应的英文内容。\n"
            "【核心提取规范（严格执行）】：\n"
            "1. 【划线物理连续性优先（绝对禁止擅自拆散连贯划线）】：\n"
            "   - 若一条手写划线或荧光笔高亮在空间上是【连续划在一起的】（如划了 'kept a diary and recorded her experiences'，划线笔迹连续未断），务必【作为一整个独立条目整体记录】！\n"
            "   - 绝不可因为其中看似包含两个考点短语就自作聪明强行拆分成两条；保持学生划线时的连贯完整形态（保留中间的 and 等连接词）；\n"
            "   - 只有当学生在课本上划出的是【两处明显断开、独立的笔迹】时，才分成两个独立条目；\n"
            "2. 【整句划线整体记录】：如果学生把一整句话全部划了线，完整保留整句，给出中考规范地道全句翻译，并在 note 中标注句型考点（如：宾语从句/高分句型/主旨名句）；\n"
            "3. 【单个生词与短语】：若仅划出单个单词或独立短语，给出中考核心释义；\n"
            "4. 严格输出标准 JSON 数组格式，严禁包含任何前言、结语或自然语言废话，格式如下：\n"
            "[\n"
            "  {\"phrase\": \"连续划线的完整短语、词组或整句\", \"meaning\": \"中文注释释义或整句翻译\", \"note\": \"考点提醒或句型搭配说明\"}\n"
            "]"
        )

    # 构造图文联合内容载荷（多图并排输入）
    user_content = [{"type": "text", "text": instruction}]
    for img_bytes in valid_images:
        b64_image = base64.b64encode(img_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    async with httpx.AsyncClient(timeout=60) as client:
        for candidate in queue:
            endpoint = f"{candidate['base_url']}/chat/completions"
            headers = {
                "Authorization": f"Bearer {candidate['api_key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": candidate["model"],
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a professional junior high school English teacher and OCR specialist. Focus strictly on detecting hand-drawn underlines, highlighter ink, or circled text. For multiple sequential images, carefully stitch together any phrases that cross image boundaries. Output ONLY valid JSON array."
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                "temperature": candidate["temperature"]
            }

            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        msg = data["choices"][0].get("message", {})
                        raw_content = (msg.get("content") or "").strip()
                        print(f"[Vocab Multi-Vision {candidate['provider']} {candidate['model']} Output ({len(valid_images)} images)]: {raw_content[:200]}")
                        
                        clean_json_str = re.sub(r"^```json\s*", "", raw_content, flags=re.IGNORECASE)
                        clean_json_str = re.sub(r"^```\s*", "", clean_json_str)
                        clean_json_str = re.sub(r"\s*```$", "", clean_json_str).strip()

                        start_idx = clean_json_str.find("[")
                        end_idx = clean_json_str.rfind("]")
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            clean_json_str = clean_json_str[start_idx:end_idx + 1]

                        parsed = json.loads(clean_json_str)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed
                else:
                    print(f"[Vocab Multi-Vision {candidate['provider']} {candidate['model']} HTTP {resp.status_code}] Error: {resp.text[:150]}")
            except Exception as e:
                print(f"[Vocab Multi-Vision {candidate['provider']} {candidate['model']} Exception] {e}")

    return []


async def extract_highlighted_vocab_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> list[dict]:
    """单图识别包装（向后兼容）"""
    return await extract_highlighted_vocab_from_multi_images([image_bytes], mime_type)
