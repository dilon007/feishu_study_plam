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
    for idx, item in enumerate(items, 1):
        phrase = item.get("phrase", "")
        meaning = item.get("meaning", "")
        vocab_lines.append(f"**{idx}. {phrase}** —— *{meaning}*")

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
                        "text": {"tag": "plain_text", "content": "📝 生成默写清单"},
                        "type": "primary",
                        "value": {"action": "generate_dictation_checklist", "session_id": session_id}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✏️ 校对与修改词条/释义"},
                        "type": "default",
                        "multi_url": {
                            "url": workbench_url,
                            "pc_url": workbench_url,
                            "android_url": workbench_url,
                            "ios_url": workbench_url
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🖨️ A4 打印自测卷"},
                        "type": "default",
                        "multi_url": {
                            "url": f"{workbench_url}&tab=print",
                            "pc_url": f"{workbench_url}&tab=print",
                            "android_url": f"{workbench_url}&tab=print",
                            "ios_url": f"{workbench_url}&tab=print"
                        }
                    }
                ]
            }
        ]
    }


def build_vocab_checklist_card(session_id: str, items: list[dict], show_answers: bool = False) -> dict:
    """
    构建中文默写清单卡片（纯中文，带 Todo List 标识）：
    满足初三学生自我默写自测需求，每个词条前带 Todo List 标识，全中文无英文泄露。
    """
    total = len(items)
    checklist_lines = []
    
    for idx, item in enumerate(items, 1):
        meaning = item.get("meaning", "").strip() or "（请根据课文记忆填空）"
        phrase = item.get("phrase", "").strip()
        note = item.get("note", "").strip()
        note_str = f" · *{note}*" if note else ""
        
        if show_answers:
            checklist_lines.append(f"- [ ] **{idx}.** {meaning}\n      👉 答案：`{phrase}`{note_str}")
        else:
            checklist_lines.append(f"- [ ] **{idx}.** {meaning}")

    content_md = "\n\n".join(checklist_lines)
    workbench_url = f"https://dilonclaw.cloud/suzhou/vocab?id={session_id}"

    action_buttons = []
    if not show_answers:
        action_buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "👀 查看参考答案"},
            "type": "primary",
            "value": {"action": "toggle_checklist_answers", "session_id": session_id, "show_answers": True}
        })
    else:
        action_buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🙈 隐藏参考答案"},
            "type": "default",
            "value": {"action": "toggle_checklist_answers", "session_id": session_id, "show_answers": False}
        })

    action_buttons.append({
        "tag": "button",
        "text": {"tag": "plain_text", "content": "📖 查看英汉对照表"},
        "type": "default",
        "value": {"action": "show_vocab_full_list", "session_id": session_id}
    })
    action_buttons.append({
        "tag": "button",
        "text": {"tag": "plain_text", "content": "🖨️ A4 纸打印"},
        "type": "default",
        "multi_url": {
            "url": f"{workbench_url}&tab=print",
            "pc_url": f"{workbench_url}&tab=print",
            "android_url": f"{workbench_url}&tab=print",
            "ios_url": f"{workbench_url}&tab=print"
        }
    })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise" if show_answers else "blue",
            "title": {
                "tag": "plain_text",
                "content": f"📝 课文词汇默写清单 (纯中文自测 · 共 {total} 条)" if not show_answers else f"🎯 默写清单参考答案 (共 {total} 条)"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"🎯 **【纯中文默写自测清单】**\n请在草稿纸或心中默写对应英文短语/整句，每默写完成一条可打勾。默写完毕后可点击下方按钮核对答案：\n\n{content_md}"
                        if not show_answers else
                        f"🎯 **【参考答案核对】**\n请仔细核对英文拼写、介词搭配与中考考点：\n\n{content_md}"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": action_buttons
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
        answer_md = f"**【英文答案】**：`{cur.get('phrase', '')}`  \n**【中考提醒】**：{cur.get('note', '苏州市初三考标核心词组')}"
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
                        "text": {"tag": "plain_text", "content": "📝 默写清单自测"},
                        "type": "default",
                        "value": {"action": "generate_dictation_checklist", "session_id": "demo"}
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

def build_image_batch_received_card(current_count: int, wait_seconds: int = 30, user_id: str = "") -> dict:
    """
    构建多图连续上传接收进度卡片：
    包含：
    1. 当前已接收图片数量
    2. 30 秒倒计时说明（支持连续发图重置倒计时并跨页拼接）
    3. 【⚡ 立即识别生成】交互按钮（点击后无需等待 30 秒，立即开始多模态提取）
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"📥 已接收第 {current_count} 张课文截图"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"⏱️ **当前模式：{wait_seconds} 秒自动聚合识别**\n\n"
                        f"- 📖 **若有连续下半页或下一页**：请继续拍照发送，系统将自动进行**跨页接缝拼接与去重**并重置倒计时；\n"
                        f"- ⚡ **若已发完且不想等待**：可直接点击下方**【⚡ 立即识别生成】**按钮立刻开始提取；\n"
                        f"- ☕ **不点击也将自动开始**：静待约 {wait_seconds} 秒无新图后，系统将自动提取。"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚡ 立即识别生成"},
                        "type": "primary",
                        "value": {
                            "action": "trigger_immediate_extraction",
                            "user_id": user_id
                        }
                    }
                ]
            }
        ]
    }

def build_image_processing_card(img_count: int = 1) -> dict:
    """构建正在识别中的卡片反馈"""
    count_str = f"（共 {img_count} 张图片）" if img_count > 1 else ""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise",
            "title": {"tag": "plain_text", "content": f"⏳ 正在识别生成中 {count_str}..."}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "🚀 已立即启动多模态视觉大模型提取！正在进行课文划线词汇识别与跨页接缝拼接，识别完成后将自动推送词汇清单卡片，请稍候约 3~5 秒..."
                }
            }
        ]
    }

def build_stem_bot_welcome_card(active_subject: str = "math") -> dict:
    """
    构建专属数理化拍照搜题机器人（苏九数理化搜题伴读）的首屏欢迎与学科选择卡片
    专精苏州市初三数学、物理、化学拍照识题与苏州中考考标分步规范解答
    """
    subj_name_map = {
        "math": "📐 数学 (苏科版)",
        "physics": "⚡ 物理 (苏科版)",
        "chemistry": "⚗️ 化学 (沪教版/初三化学)"
    }
    current_name = subj_name_map.get(active_subject, "📐 数学 (苏科版)")

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "indigo",
            "title": {"tag": "plain_text", "content": "📐 苏九数理化 · 拍照搜题伴读机器人"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "👋 **欢迎使用苏州市九年级数理化专属拍照搜题机器人！**\n\n"
                        "本助手由**苏九学伴团队**专为苏州市初三学生定制，专注于**数理化习题拍照识别、规范步骤推导与中考评分踩分点剖析**，杜绝超纲步骤。\n\n"
                        f"📌 **当前偏好学科**：`{current_name}`"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "🎯 **对齐苏州市初三官方教材与考标：**\n"
                        "• **📐 数学（苏科版）**：圆与辅助线、二次函数极值/动点问题、相似三角形判定与性质；\n"
                        "• **⚡ 物理（苏科版）**：动态电路欧姆定律计算、电功率极值、浮力压强、滑轮机械效率；\n"
                        "• **⚗️ 化学（初三化学）**：酸碱盐复分解反应、气体制取与干燥净化、常见物质转化推断题。\n\n"
                        "📸 **使用方法**：\n"
                        "直接在聊天框**发送试卷、错题本或练习题的清晰照片/截图**，多模态 AI 秒级解析并按中考规范分步给出踩分步骤！"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📐 数学工作台"},
                        "type": "primary" if active_subject == "math" else "default",
                        "value": {"action": "stem_select_subject", "subject": "math"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚡ 物理工作台"},
                        "type": "primary" if active_subject == "physics" else "default",
                        "value": {"action": "stem_select_subject", "subject": "physics"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚗️ 化学工作台"},
                        "type": "primary" if active_subject == "chemistry" else "default",
                        "value": {"action": "stem_select_subject", "subject": "chemistry"}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔍 查看数理化中考解题范例"},
                        "type": "default",
                        "value": {"action": "stem_demo_question", "subject": active_subject}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 提示：拍照时请尽量让题目文字、几何图形或电路图清晰居中，解答效果更佳！"
                    }
                ]
            }
        ]
    }

def build_stem_qa_result_card(title: str, content: str, subject_name: str, subject_key: str = "math") -> dict:
    """
    构建数理化搜题专属问答结果卡片
    """
    header_color_map = {
        "math": "blue",
        "physics": "indigo",
        "chemistry": "carmine"
    }
    color = header_color_map.get(subject_key, "indigo")

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": color,
            "title": {
                "tag": "plain_text",
                "content": f"📐 苏九数理化搜题 · {subject_name}规范解析"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📋 **题目与已知**：\n{title}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 更换学科"},
                        "type": "default",
                        "value": {"action": "back_to_stem_menu"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📐 数学"},
                        "type": "default",
                        "value": {"action": "stem_select_subject", "subject": "math"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚡ 物理"},
                        "type": "default",
                        "value": {"action": "stem_select_subject", "subject": "physics"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⚗️ 化学"},
                        "type": "default",
                        "value": {"action": "stem_select_subject", "subject": "chemistry"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "📸 遇到新题目？直接发送试卷截图即可继续秒级搜题！"
                    }
                ]
            }
        ]
    }


# ==============================================================================
# 专属文科检索问答机器人卡片组（苏九文科检索伴读）
# 专精苏州市初三语文（字词/古诗文）、英语（单词短语）、历史与道法的群聊 @ 检索问答
# ==============================================================================

def build_arts_bot_welcome_card() -> dict:
    """
    构建专属文科检索问答机器人（苏九文科检索伴读）的首屏欢迎与使用指南卡片
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "violet",
            "title": {"tag": "plain_text", "content": "📚 苏九文科 · 文科检索问答伴读机器人"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "👋 **欢迎使用苏州市九年级文科专属检索问答机器人！**\n\n"
                        "无需任何设置，**在群里 @ 本机器人**或私聊直接提问，即可秒级检索初三文科考点与规范解析。"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "🎯 **对齐苏州市初三官方文科教材与考标：**\n"
                        "• **📖 语文（统编部编版）**：字词汇音、文言古诗名句、文学常识、名著导读；\n"
                        "• **🇬🇧 英语（译林牛津版 9A/9B）**：单词短语释义、重点搭配与用法辨析；\n"
                        "• **🏛️ 历史（统编部编版）**：世界近代史大事、重要变革与条约影响；\n"
                        "• **⚖️ 道德与法治（统编部编版）**：核心概念、法律常识与国情考点。\n\n"
                        "✨ **提问示例**：\n"
                        "- `@苏九文科伴读 查单词 generous`\n"
                        "- `@苏九文科伴读 岳阳楼记 先天下之忧而忧`\n"
                        "- `@苏九文科伴读 工业革命的影响`\n"
                        "- `@苏九文科伴读 「塞翁失马」的寓意`"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 示例·查单词"},
                        "type": "default",
                        "value": {"action": "arts_query_word", "word": "generous"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📜 示例·查古文"},
                        "type": "default",
                        "value": {"action": "arts_query_ancient", "title": "岳阳楼记"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "🛡️ 所有问答均严格限定苏州市九年级考纲范围，高中超纲内容将被自动拦截。"
                    }
                ]
            }
        ]
    }

def build_arts_qa_result_card(question: str, answer: str, subject_label: str = "九年级文科") -> dict:
    """
    构建文科检索问答结果卡片
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "violet",
            "title": {
                "tag": "plain_text",
                "content": f"📚 苏九文科检索 · {subject_label}"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🔍 **检索问题**：\n{question}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": answer
                }
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 群里 @ 本机器人即可继续提问；支持语文、英语、历史、道法检索。"
                    }
                ]
            }
        ]
    }


# ==============================================================================
# 新版专属英语默写机器人卡片组（纯飞书交互卡片 + 飞书多维表格 Bitable 架构，零 HTML 网页依赖）
# 核心原则：拍照只负责往多维表格追加词条，所有背诵和默写均实时从多维表格拉取！
# ==============================================================================

def _build_bitable_open_button(bitable_url: str, label: str = "📊 打开多维表格词库") -> dict:
    """构建打开飞书多维表格的按钮（若尚未创建或绑定，则触发自动创建 Action）"""
    if bitable_url:
        return {
            "tag": "button",
            "text": {"tag": "plain_text", "content": label},
            "type": "default",
            "multi_url": {
                "url": bitable_url,
                "pc_url": bitable_url,
                "android_url": bitable_url,
                "ios_url": bitable_url
            }
        }
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": "📊 一键创建/连接多维表格词库"},
        "type": "default",
        "value": {"action": "bitable_auto_create"}
    }


def build_vocab_bitable_welcome_card(bitable_url: str = "", total_count: int = 0, sync_note: str = "") -> dict:
    """
    构建新版【飞书交互卡片 + 多维表格】专属英语默写机器人的首屏导航卡片
    """
    status_line = (
        f"✅ **已连接多维表格核心词库**（当前收录 **{total_count}** 条词汇）"
        if bitable_url else
        "📌 **核心词库状态**：首次拍照或点击下方按钮将自动为您创建/连接飞书多维表格（也可直接发送已有飞书多维表格链接进行绑定）"
    )
    if sync_note:
        status_line += f"\n💡 *{sync_note}*"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "wathet",
            "title": {"tag": "plain_text", "content": "📊 苏九背词伴读 · 飞书卡片 + 多维表格版"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "👋 **欢迎使用苏州市九年级英语默写助手（原生卡片 + 多维表格版）！**\n\n"
                        "本机器人采用 **100% 飞书原生交互卡片 + 飞书多维表格（Bitable）** 架构，无需打开任何外部 HTML 网页。\n\n"
                        f"{status_line}"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        "🚀 **核心工作流（以多维表格为唯一词库）：**\n"
                        "1. 📸 **拍照追加词条**：发送课本荧光笔高亮或下划线截图，AI 识别后**直接追加写入飞书多维表格**；\n"
                        "2. 📊 **多维表格管理**：随时在飞书多维表格内修改英文短语、中文释义、增删词条或筛选视图；\n"
                        "3. 📖 **拉取背诵清单**：一键从多维表格实时拉取最新英汉对照卡片；\n"
                        "4. 📝 **拉取默写自测**：从多维表格实时拉取生成**【纯中文 Todo List 默写单】**或**【逐词翻页默写卡】**，并在卡片上直接标记掌握状态同步回多维表格！"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 从多维表格拉取默写单"},
                        "type": "primary",
                        "value": {"action": "bitable_pull_checklist", "scope": "all"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 逐词翻页默写 (拉取表格)"},
                        "type": "default",
                        "value": {"action": "bitable_pull_dictate_step", "scope": "unmastered", "index": 0, "reveal": False}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 拉取多维表格背诵清单"},
                        "type": "default",
                        "value": {"action": "bitable_pull_recite", "scope": "all"}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    _build_bitable_open_button(bitable_url, "📊 打开飞书多维表格词库"),
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "➕ 追加示例词条到多维表格"},
                        "type": "default",
                        "value": {"action": "bitable_init_demo"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 绑定自定义多维表格：直接把您的飞书多维表格链接发到对话框，机器人即可自动绑定该表格作为您的专属词库！"
                    }
                ]
            }
        ]
    }


def build_vocab_bitable_append_result_card(
    appended_items: list[dict],
    bitable_url: str = "",
    batch_title: str = "课文划线词汇",
    sync_ok: bool = True,
    sync_msg: str = ""
) -> dict:
    """
    构建拍照识别后【追加写入多维表格成功】的反馈卡片：
    拍照只负责往多维表格里追加词条，卡片下方提供从多维表格拉取背诵/默写的快捷入口。
    """
    lines = []
    for idx, it in enumerate(appended_items, 1):
        phrase = it.get("phrase", "")
        meaning = it.get("meaning", "")
        lines.append(f"**{idx}. {phrase}** —— *{meaning}*")
    list_md = "\n".join(lines) if lines else "*(无新增词条)*"

    sync_badge = (
        f"✅ **多维表格同步状态**：{sync_msg or '已成功追加写入飞书多维表格！'}"
        if sync_ok else
        f"📦 **词库记录状态**：已存入词库缓存（{sync_msg}）"
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green" if sync_ok else "wathet",
            "title": {"tag": "plain_text", "content": f"📥 已追加 {len(appended_items)} 条词汇至多维表格"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**【来源批次】**：{batch_title}\n"
                        f"{sync_badge}\n\n"
                        f"**【本次追加写入多维表格的词条】**：\n{list_md}"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 拉取本批次生成默写单"},
                        "type": "primary",
                        "value": {"action": "bitable_pull_checklist", "scope": "latest"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 拉取全部词库默写单"},
                        "type": "default",
                        "value": {"action": "bitable_pull_checklist", "scope": "all"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 逐词翻页默写"},
                        "type": "default",
                        "value": {"action": "bitable_pull_dictate_step", "scope": "latest", "index": 0, "reveal": False}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    _build_bitable_open_button(bitable_url, "📊 打开多维表格修改/校对词条"),
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 拉取多维表格背诵清单"},
                        "type": "default",
                        "value": {"action": "bitable_pull_recite", "scope": "all"}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 如需修改英文短语或中文释义，请直接点击【打开多维表格修改/校对词条】编辑单元格，随后点击拉取默写单即可实时生效！"
                    }
                ]
            }
        ]
    }


def build_vocab_bitable_recite_card(
    items: list[dict],
    bitable_url: str = "",
    scope: str = "all",
    from_remote: bool = True
) -> dict:
    """
    构建从飞书多维表格实时拉取的【英汉对照背诵清单卡片】
    """
    scope_labels = {
        "all": "全部词库",
        "unmastered": "待默写词条",
        "latest": "最近拍照批次"
    }
    scope_name = scope_labels.get(scope, "全部词库")

    if not items:
        body_md = "📭 **当前多维表格词库暂无词条**\n请直接发送课本划线截图，或点击下方【➕ 追加示例词条到多维表格】。"
    else:
        vocab_lines = []
        for idx, item in enumerate(items, 1):
            phrase = item.get("phrase", "")
            meaning = item.get("meaning", "")
            status = item.get("status", "待默写")
            status_icon = "✅" if "已掌握" in status else ("⭐" if "重点" in status or "易错" in status else "🔹")
            vocab_lines.append(f"{status_icon} **{idx}. {phrase}** —— *{meaning}* `[{status}]`")
        body_md = "\n".join(vocab_lines)

    source_tag = "🟢 已从飞书多维表格实时同步" if from_remote else "🔵 词库镜像数据（绑定或开启多维表格权限后实时同步）"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"📖 多维表格背诵清单 · {scope_name} (共 {len(items)} 条)"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**【数据源】**：{source_tag}\n\n{body_md}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 生成纯中文默写清单"},
                        "type": "primary",
                        "value": {"action": "bitable_pull_checklist", "scope": scope}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 卡片逐词翻页默写"},
                        "type": "default",
                        "value": {"action": "bitable_pull_dictate_step", "scope": scope, "index": 0, "reveal": False}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 重新从多维表格拉取"},
                        "type": "default",
                        "value": {"action": "bitable_pull_recite", "scope": scope}
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📚 看全部"},
                        "type": "primary" if scope == "all" else "default",
                        "value": {"action": "bitable_pull_recite", "scope": "all"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🎯 仅看待默写"},
                        "type": "primary" if scope == "unmastered" else "default",
                        "value": {"action": "bitable_pull_recite", "scope": "unmastered"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🆕 仅看最近批次"},
                        "type": "primary" if scope == "latest" else "default",
                        "value": {"action": "bitable_pull_recite", "scope": "latest"}
                    },
                    _build_bitable_open_button(bitable_url, "📊 打开多维表格编辑")
                ]
            }
        ]
    }


def build_vocab_bitable_checklist_card(
    items: list[dict],
    bitable_url: str = "",
    show_answers: bool = False,
    scope: str = "all"
) -> dict:
    """
    构建从飞书多维表格实时拉取的【纯中文 Todo List 默写清单卡片】
    零 HTML 网页依赖，所有数据实时从飞书多维表格读取！
    """
    scope_labels = {
        "all": "全部词库",
        "unmastered": "待默写词条",
        "latest": "最近批次"
    }
    scope_name = scope_labels.get(scope, "全部词库")
    total = len(items)

    if total == 0:
        content_md = "📭 **多维表格中暂无符合条件的词条**，请先拍照上传课文划线图片或点击下方按钮初始化示例词条。"
    else:
        checklist_lines = []
        for idx, item in enumerate(items, 1):
            meaning = item.get("meaning", "").strip() or "（请根据课文记忆填空）"
            phrase = item.get("phrase", "").strip()
            note = item.get("note", "").strip()
            status = item.get("status", "待默写").strip()
            note_str = f" · *{note}*" if note else ""

            if show_answers:
                checklist_lines.append(f"- [ ] **{idx}.** {meaning} `[{status}]`\n      👉 答案：`{phrase}`{note_str}")
            else:
                checklist_lines.append(f"- [ ] **{idx}.** {meaning}")
        content_md = "\n\n".join(checklist_lines)

    toggle_btn = (
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "👀 查看参考答案"},
            "type": "primary",
            "value": {"action": "bitable_toggle_checklist_answers", "scope": scope, "show_answers": True}
        }
        if not show_answers else
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🙈 隐藏参考答案"},
            "type": "default",
            "value": {"action": "bitable_toggle_checklist_answers", "scope": scope, "show_answers": False}
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise" if show_answers else "blue",
            "title": {
                "tag": "plain_text",
                "content": (
                    f"📝 多维表格默写清单 ({scope_name} · 共 {total} 条)"
                    if not show_answers else
                    f"🎯 多维表格默写参考答案 ({scope_name} · 共 {total} 条)"
                )
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"🎯 **【纯中文默写自测清单（数据源：飞书多维表格 · {scope_name}）】**\n"
                        f"每默写完成一条可直接在卡片上打勾 ✅。若在多维表格中修改了释义，点击【🔄 同步最新表格】即可刷新：\n\n{content_md}"
                        if not show_answers else
                        f"🎯 **【多维表格参考答案核对（{scope_name}）】**\n"
                        f"请仔细核对英文拼写与固定搭配：\n\n{content_md}"
                    )
                }
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    toggle_btn,
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 同步最新表格"},
                        "type": "default",
                        "value": {"action": "bitable_toggle_checklist_answers", "scope": scope, "show_answers": show_answers}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✍️ 逐词翻页默写"},
                        "type": "default",
                        "value": {"action": "bitable_pull_dictate_step", "scope": scope, "index": 0, "reveal": False}
                    },
                    _build_bitable_open_button(bitable_url, "📊 打开多维表格")
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📚 全部词条"},
                        "type": "primary" if scope == "all" else "default",
                        "value": {"action": "bitable_toggle_checklist_answers", "scope": "all", "show_answers": show_answers}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🎯 仅待默写"},
                        "type": "primary" if scope == "unmastered" else "default",
                        "value": {"action": "bitable_toggle_checklist_answers", "scope": "unmastered", "show_answers": show_answers}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🆕 最近批次"},
                        "type": "primary" if scope == "latest" else "default",
                        "value": {"action": "bitable_toggle_checklist_answers", "scope": "latest", "show_answers": show_answers}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 英汉背诵表"},
                        "type": "default",
                        "value": {"action": "bitable_pull_recite", "scope": scope}
                    }
                ]
            }
        ]
    }


def build_vocab_bitable_dictation_card(
    items: list[dict],
    bitable_url: str = "",
    current_index: int = 0,
    show_answer: bool = False,
    scope: str = "all"
) -> dict:
    """
    构建基于飞书多维表格的【原生逐词翻页默写卡片】：
    支持在卡片上点击【✅ 标记已掌握】或【⭐ 标记易错】，直接回写更新飞书多维表格的“掌握状态”列！
    """
    total = len(items)
    if total == 0:
        return build_vocab_bitable_recite_card(items, bitable_url, scope)

    idx = max(0, min(current_index, total - 1))
    cur = items[idx]
    record_id = cur.get("record_id", "")
    status = cur.get("status", "待默写")

    if show_answer:
        answer_md = (
            f"**【英文答案】**：`{cur.get('phrase', '')}`\n"
            f"**【中考考点备注】**：{cur.get('note', '译林版九年级核心词组')}\n"
            f"**【多维表格当前状态】**：`{status}`"
        )
        reveal_btn = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🙈 隐藏答案"},
            "type": "default",
            "value": {"action": "bitable_pull_dictate_step", "scope": scope, "index": idx, "reveal": False}
        }
    else:
        answer_md = f"💡 *请在心中思考或在草稿纸上默写，随后点击下方揭晓答案（当前表格状态：`{status}`）*"
        reveal_btn = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "👀 揭晓英文答案"},
            "type": "primary",
            "value": {"action": "bitable_pull_dictate_step", "scope": scope, "index": idx, "reveal": True}
        }

    next_idx = (idx + 1) if (idx + 1 < total) else 0
    next_text = "➡️ 下一词" if (idx + 1 < total) else "🎉 完成一轮 (从头再来)"
    next_btn = {
        "tag": "button",
        "text": {"tag": "plain_text", "content": next_text},
        "type": "primary" if show_answer else "default",
        "value": {"action": "bitable_pull_dictate_step", "scope": scope, "index": next_idx, "reveal": False}
    }

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "wathet",
            "title": {"tag": "plain_text", "content": f"✍️ 多维表格逐词默写 · (第 {idx + 1}/{total} 题)"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"### 📌 中文释义（拉取自多维表格）：\n# **{cur.get('meaning', '（请根据课文记忆填空）')}**"
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
                    reveal_btn,
                    next_btn,
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 标记已掌握 (写回表格)"},
                        "type": "default",
                        "value": {
                            "action": "bitable_mark_status",
                            "record_id": record_id,
                            "new_status": "已掌握",
                            "scope": scope,
                            "index": next_idx
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⭐ 标记易错 (写回表格)"},
                        "type": "default",
                        "value": {
                            "action": "bitable_mark_status",
                            "record_id": record_id,
                            "new_status": "易错重点",
                            "scope": scope,
                            "index": next_idx
                        }
                    }
                ]
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📝 切换整张默写清单"},
                        "type": "default",
                        "value": {"action": "bitable_pull_checklist", "scope": scope}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 返回背诵清单"},
                        "type": "default",
                        "value": {"action": "bitable_pull_recite", "scope": scope}
                    },
                    _build_bitable_open_button(bitable_url, "📊 打开多维表格词库")
                ]
            }
        ]
    }





