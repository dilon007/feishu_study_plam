"""
苏九学伴 - 飞书原生交互卡片 (Interactive Card v2) 渲染器
设计规范：以“科目优先选择”为核心流程，支持数学、物理、化学、英语、语文、道法历史专属答疑台。
"""

SUBJECT_METAS = {
    "math": {
        "name": "九年级数学",
        "book": "苏科版（九上/九下）",
        "icon": "📐",
        "color": "orange",
        "description": "已锁定苏科版数学考纲。已接入 **Gemini Pro 深度推导**，擅长二次函数综合、圆与三角形辅助线证明、一元二次方程。",
        "quick_topics": [
            {"label": "二次函数最值", "val": "二次函数最值"},
            {"label": "圆的切线性质", "val": "圆的切线证明"},
            {"label": "相似三角形", "val": "相似三角形判定与性质"}
        ]
    },
    "physics": {
        "name": "九年级物理",
        "book": "苏科版九年级物理",
        "icon": "⚡",
        "color": "blue",
        "description": "已锁定苏科版物理考纲。已接入 **Gemini Pro 深度推导**，擅长动态电路分析、欧姆定律、电功率极值、滑轮机械效率。",
        "quick_topics": [
            {"label": "欧姆定律动态电路", "val": "欧姆定律"},
            {"label": "电功率计算", "val": "电功率"},
            {"label": "杠杆与滑轮机械效率", "val": "杠杆与滑轮"}
        ]
    },
    "chemistry": {
        "name": "九年级化学",
        "book": "苏州市初中化学考标",
        "icon": "⚗️",
        "color": "purple",
        "description": "已锁定初三化学考标。已接入 **Gemini Pro 深度推导**，擅长酸碱盐推断题、滤渣滤液成分分析、气体制备实验装置探究。",
        "quick_topics": [
            {"label": "酸碱盐复分解推断", "val": "酸碱盐"},
            {"label": "气体制备与净化", "val": "气体制备"},
            {"label": "金属活动性置换", "val": "金属活动性"}
        ]
    },
    "english": {
        "name": "九年级英语",
        "book": "译林牛津版（9A/9B）",
        "icon": "🅰️",
        "color": "wathet",
        "description": "已锁定译林版英语教材。已接入 **Gemini Flash 极速引擎** 与本地生词库，擅长生词中考搭配、语法专项、推荐信写作批改。",
        "quick_topics": [
            {"label": "生词: generous", "val": "generous"},
            {"label": "生词: curious", "val": "curious"},
            {"label": "生词: achieve", "val": "achieve"}
        ]
    },
    "chinese": {
        "name": "九年级语文",
        "book": "统编部编版九年级",
        "icon": "📜",
        "color": "turquoise",
        "description": "已锁定统编版语文考纲。已接入本地必背文言文诗词库与 Flash 引擎，擅长文言实词通假字、古诗主旨赏析、默写填空。",
        "quick_topics": [
            {"label": "《岳阳楼记》考点", "val": "岳阳楼记"},
            {"label": "《醉翁亭记》考点", "val": "醉翁亭记"},
            {"label": "《出师表》必背", "val": "出师表"}
        ]
    },
    "politics": {
        "name": "道法 & 历史",
        "book": "统编版·中考开卷专题",
        "icon": "🏛️",
        "color": "indigo",
        "description": "已锁定苏州中考开卷考查专题。擅长常态化时政分析、中国近代史事件梳理与大题答题模板提取。",
        "quick_topics": [
            {"label": "开卷答题技巧", "val": "道法大题答题规范模板"},
            {"label": "近代化探索梳理", "val": "中国近代史探索三大阶段"}
        ]
    }
}

def build_menu_card() -> dict:
    """
    第一步：科目导航主菜单卡片
    引导学生先选择学科，极大提高解答的专业度与上下文针对性
    """
    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": "🎓 苏九学伴 · 请先选择提问科目"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**你好，初三学子！** 为了给你最精准的苏州中考答疑，请先选择你当前正在复习的学科。\n\n锁定科目后将自动匹配 **苏科版/译林版教材规范** 与 **专属模型算力**（数理化默认启用 Gemini Pro 深度推理）："
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📐 数学 (苏科版)"},
                        "type": "primary",
                        "value": {"action": "select_subject", "subject": "math"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚡ 物理 (苏科版)"},
                        "type": "primary",
                        "value": {"action": "select_subject", "subject": "physics"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚗️ 化学 (初三化学)"},
                        "type": "primary",
                        "value": {"action": "select_subject", "subject": "chemistry"}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🅰️ 英语 (译林版)"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": "english"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📜 语文 (统编版)"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": "chinese"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🏛️ 道法 & 历史"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": "politics"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "📸 提示：做题遇到困难？选好科目后直接拍照或截屏发到聊天框即可！"
                    }
                ]
            }
        ]
    }

def build_subject_workbench_card(subject_key: str) -> dict:
    """
    第二步：学科专属答疑台卡片
    展示当前学科的教材定位、快捷典型题考点、以及拍照/打字输入指引
    """
    meta = SUBJECT_METAS.get(subject_key, SUBJECT_METAS["math"])

    topic_buttons = []
    for item in meta["quick_topics"]:
        topic_buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": item["label"]},
            "type": "default",
            "value": {
                "action": "quick_topic",
                "subject": subject_key,
                "topic": item["val"]
            }
        })

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**当前已锁定【{meta['name']}】专属答疑台** 🎯\n\n📌 **教材标准**：{meta['book']}\n💡 **能力说明**：{meta['description']}"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "👇 **常考中考高频专题（点击直接查看核心解析）：**"
            }
        },
        {
            "tag": "action",
            "actions": topic_buttons
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    "💬 **英语背单词与提问指引：**\n1. 📸 **发送课文划线截图**：精准识别课文高亮/划线词组，生成背诵单、在线默写与 A4 打印卷；\n2. ✍️ **直接输入单词或短语**：如输入 'generous' 或 '查单词 attention' 获取考标考点；\n3. 随时点击下方按钮可更换其他学科。"
                    if subject_key == "english" else
                    "💬 **如何提问：**\n1. 📸 **直接发送题目截图**：自动识别几何图、坐标系或电路图，分步推导；\n2. ✍️ **直接打字输入**：发送题目文字或具体疑惑知识点；\n3. 随时点击下方按钮可更换其他学科。"
                )
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔙 更换其他科目"},
                    "type": "default",
                    "value": {"action": "back_to_menu"}
                }
            ]
        }
    ]

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": meta["color"],
            "title": {
                "tag": "plain_text",
                "content": f"{meta['icon']} {meta['name']} · 专属答疑台"
            }
        },
        "elements": elements
    }

def build_physics_card(data: dict) -> dict:
    """构建物理考点卡片"""
    kp_md = "\n".join([f"• {k}" for k in data.get("key_points", [])])
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"⚡ 苏科版物理 · {data['title']}"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**教材定位**：{data['book']}\n**核心公式**：`{data['formula']}`\n\n**【考点梳理与推演要点】**\n{kp_md}\n\n🎯 **{data['exam_tips']}**"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔙 返回物理工作台"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": "physics"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 换其他科目"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    }
                ]
            }
        ]
    }

def build_chemistry_card(data: dict) -> dict:
    """构建化学考点卡片"""
    kp_md = "\n".join([f"• {k}" for k in data.get("key_points", [])])
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "purple",
            "title": {"tag": "plain_text", "content": f"⚗️ 初三化学 · {data['title']}"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**专题归属**：{data['book']}\n**核心判据/方程式**：`{data['formula']}`\n\n**【复习重点与实验突破】**\n{kp_md}\n\n🎯 **{data['exam_tips']}**"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔙 返回化学工作台"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": "chemistry"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 换其他科目"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    }
                ]
            }
        ]
    }

def build_word_card(info: dict) -> dict:
    """构建译林版英语单词解析卡片"""
    if not info.get("matched"):
        word = info.get("word", "")
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "orange",
                "title": {"tag": "plain_text", "content": f"🅰️ 译林英语考标词汇 · {word}"}
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**查询词汇**：`{word}`\n\n📌 **考纲状态**：苏州市初三考标收录单词。\n\n⚠️ 该生词正在中考例句库中索引。你可以尝试查询单元核心高频词，如：`generous`, `curious`, `achieve`, `patient`, `influence`, `recommend` 等。"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回英语工作台"}, "type": "default", "value": {"action": "select_subject", "subject": "english"}}
                    ]
                }
            ]
        }

    data = info["data"]
    phrases_md = "\n".join([f"• `{p}`" for p in data.get("phrases", [])])
    sentences_md = "\n".join([f"• {s}" for s in data.get("sentences", [])])

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": f"🅰️ 译林版初三英语 · {data['word']}"
            }
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**音标**：`{data['phonetic']}`\n**词性**：{data['pos']}"}
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**课本定位**：\n{data['unit']}"}
                    }
                ]
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【核心释义】**\n{data['definition']}\n\n**【中考高频短语搭配】**\n{phrases_md}\n\n**【课文与模拟真题例句】**\n{sentences_md}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🎯 **{data['exam_tips']}**"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回英语工作台"}, "type": "default", "value": {"action": "select_subject", "subject": "english"}},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔄 换其他科目"}, "type": "default", "value": {"action": "back_to_menu"}}
                ]
            }
        ]
    }

def build_ancient_card(info: dict) -> dict:
    """构建统编版九年级文言文/古诗词解析卡片"""
    if not info.get("matched"):
        title = info.get("title", "")
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "carmine",
                "title": {"tag": "plain_text", "content": f"📜 统编古诗文 · {title}"}
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"已进入苏州市中考古文库检索。你可以直接输入九年级高频必背篇目，例如：`岳阳楼记`、`醉翁亭记`、`出师表`、`水调歌头` 或名句 `先天下之忧而忧`。"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回语文工作台"}, "type": "default", "value": {"action": "select_subject", "subject": "chinese"}}
                    ]
                }
            ]
        }

    data = info["data"]
    sentences_md = "\n".join([f"• **{s}**" for s in data.get("famous_sentences", [])])
    keywords_md = "\n".join([f"• `{k}`" for k in data.get("keywords", [])])

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise",
            "title": {
                "tag": "plain_text",
                "content": f"📜 统编九年级必背 ·《{data['title']}》"
            }
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**作者**：{data['author']}"}
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**教材归属**：\n{data['book']}"}
                    }
                ]
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【必背名句与默写重点】**\n{sentences_md}\n\n**【苏州中考高频文言字词释义】**\n{keywords_md}\n\n**【思想感情与主旨】**\n{data['main_idea']}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📌 **{data['exam_spot']}**"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回语文工作台"}, "type": "default", "value": {"action": "select_subject", "subject": "chinese"}},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔄 换其他科目"}, "type": "default", "value": {"action": "back_to_menu"}}
                ]
            }
        ]
    }

def build_qa_result_card(question: str, answer: str, subject_label: str = "初三答疑", current_subject: str = "math") -> dict:
    """
    构建符合苏州初三中考规范的 AI 答疑解析卡片
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"🎓 苏九名师答疑 · {subject_label}"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【题目/考点】**：\n{question}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【规范踩分解答步骤】**：\n\n{answer}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": f"🔙 返回本学科工作台"},
                        "type": "default",
                        "value": {"action": "select_subject", "subject": current_subject}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 切换其他学科"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    }
                ]
            }
        ]
    }

def build_vocab_list_card(session_id: str, items: list[dict], title: str = "课文划线高频词组提取成功") -> dict:
    """
    构建课文高亮划线词汇提取清单卡片：
    包含：词汇表格预览、在线校对修改入口、卡片逐词默写自测入口、A4 纸打印排版入口
    """
    vocab_lines = []
    for idx, item in enumerate(items[:10], 1):
        phrase = item.get("phrase", "")
        phonetic = f"`{item.get('phonetic', '')}`" if item.get('phonetic') else ""
        meaning = item.get("meaning", "")
        vocab_lines.append(f"**{idx}. {phrase}** {phonetic} —— *{meaning}*")

    if len(items) > 10:
        vocab_lines.append(f"*... 及其他共 {len(items)} 个划线词条，可在工作台中完整查看*")

    list_md = "\n".join(vocab_lines)
    workbench_url = f"https://dilonclaw.cloud/suzhou/vocab?id={session_id}"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"📝 课文划线词汇清单 (共 {len(items)} 条)"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【考标对标】**：译林牛津版九年级英语教材\n**【AI视觉提取】**：已锁定课文截图高亮/划线重点短语：\n\n{list_md}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✏️ 校对与修改中文注释"},
                        "type": "primary",
                        "multi_url": {
                            "url": workbench_url,
                            "pc_url": workbench_url,
                            "android_url": workbench_url,
                            "ios_url": workbench_url
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 开始卡片默写"},
                        "type": "default",
                        "value": {"action": "dictate_step", "session_id": session_id, "index": 0, "reveal": False}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🖨️ A4 打印与自测卷"},
                        "type": "default",
                        "multi_url": {
                            "url": f"{workbench_url}&tab=print",
                            "pc_url": f"{workbench_url}&tab=print",
                            "android_url": f"{workbench_url}&tab=print",
                            "ios_url": f"{workbench_url}&tab=print"
                        }
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔙 返回英语工作台"}, "type": "default", "value": {"action": "select_subject", "subject": "english"}},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "🔄 更换其他科目"}, "type": "default", "value": {"action": "back_to_menu"}}
                ]
            }
        ]
    }

def build_vocab_dictation_card(session_id: str, items: list[dict], current_index: int = 0, show_answer: bool = False) -> dict:
    """
    构建飞书原生逐词翻页默写自测卡片：
    每次出现一个单词的中文注释，点击揭晓答案，点击下一条到下一个单词
    """
    total = len(items)
    if total == 0:
        return build_vocab_list_card(session_id, items)

    idx = max(0, min(current_index, total - 1))
    cur = items[idx]
    workbench_url = f"https://dilonclaw.cloud/suzhou/vocab?id={session_id}"

    # 答案区内容展示
    if show_answer:
        answer_md = f"**【英文答案】**：`{cur.get('phrase', '')}`  \n**【国际音标】**：{cur.get('phonetic', '-')}\n**【中考提醒】**：{cur.get('note', '苏州市初三考标核心词组')}"
        reveal_button = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🙈 隐藏答案"},
            "type": "default",
            "value": {"action": "dictate_step", "session_id": session_id, "index": idx, "reveal": False}
        }
    else:
        answer_md = "💡 *请在心中思考或在草稿纸上书写，随后点击下方按钮揭晓答案*"
        reveal_button = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "👀 查看英文答案"},
            "type": "primary",
            "value": {"action": "dictate_step", "session_id": session_id, "index": idx, "reveal": True}
        }

    # 下一个词按钮逻辑
    next_idx = (idx + 1) if (idx + 1 < total) else 0
    next_btn_text = "➡️ 下一个词" if (idx + 1 < total) else "🎉 已全部完成 (再练一遍)"
    next_button = {
        "tag": "button",
        "text": {"tag": "plain_text", "content": next_btn_text},
        "type": "default" if not show_answer else "primary",
        "value": {"action": "dictate_step", "session_id": session_id, "index": next_idx, "reveal": False}
    }

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"✍️ 词汇自测默写 · (第 {idx + 1}/{total} 题)"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"### 📌 中文释义提示：\n# **{cur.get('meaning', '（请根据课文记忆填空）')}**"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": answer_md
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    reveal_button,
                    next_button,
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 退出并看清单"},
                        "type": "default",
                        "value": {"action": "dictate_exit", "session_id": session_id}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✏️ 网页修改释义"},
                        "type": "default",
                        "multi_url": {"url": workbench_url, "pc_url": workbench_url}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🖨️ A4 打印自测单"},
                        "type": "default",
                        "multi_url": {"url": f"{workbench_url}&tab=print", "pc_url": f"{workbench_url}&tab=print"}
                    }
                ]
            }
        ]
    }

def build_vocab_bot_welcome_card() -> dict:
    """
    构建专属背单词机器人的首屏欢迎与操作指南卡片
    """
    workbench_url = "https://dilonclaw.cloud/suzhou/vocab"
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "🇬🇧 苏九背词伴读 · 专属英语默写助手"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "👋 **欢迎使用苏州市九年级英语课文背词伴读机器人！**\n\n"
                        "本助手严格依据**苏州市初三译林牛津版（9A/9B）英语教材考标**，专为初三学生中考词汇通关打造。"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "✨ **四大核心功能使用指南：**\n\n"
                        "1. 📸 **拍照识别课文划线**：\n"
                        "   直接在对话框中**发送带有荧光笔高亮、铅笔下划线或手写圈画的课文截图**，AI 秒级提取重点词组并匹配中考释义；\n\n"
                        "2. ✏️ **英 ➔ 中 在线校对修改**：\n"
                        "   支持点击进入工作台，自由校对并修改每一条中文注释；\n\n"
                        "3. ✍️ **飞书卡片逐词默写**：\n"
                        "   在聊天框中**原地逐词翻页默写自测**（中文提示 ➔ 思考 ➔ 揭晓答案 ➔ 下一词），无需跳转网页；\n\n"
                        "4. 🖨️ **A4 纸规范打印排版**：\n"
                        "   一键生成**【课堂自测默写卷】**（左中文右横线）或**【考前背诵清单】**，一键打印练习。"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📸 查看课文提取示例"},
                        "type": "primary",
                        "value": {"action": "vocab_bot_demo"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 立即开始默写"},
                        "type": "default",
                        "value": {"action": "dictate_step", "session_id": "demo", "index": 0, "reveal": False}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🖨️ 访问打印工作台"},
                        "type": "default",
                        "multi_url": {"url": workbench_url, "pc_url": workbench_url}
                    }
                ]
            }
        ]
    }


