"""
苏九学伴 - 飞书原生交互卡片 (Interactive Card v2) 渲染器
负责构建符合飞书规范的助学菜单卡片、生词解析卡片、古文查询卡片。
"""
import json

WEB_DASHBOARD_URL = "https://dilonclaw.cloud/suzhou/welcome"

def build_menu_card() -> dict:
    """
    构建助学主菜单卡片（当用户在群聊/单聊输入 @助手 或 菜单 时触发）
    """
    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": "🎓 苏九学伴 · 苏州市9年级专属助学菜单"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "你好！我是你的初三专属学习助手。所有内容严格对齐 **苏州市九年级中考考纲**（苏科版/译林版/统编版），**已启动防超纲围栏** 🛡️。\n\n请选择你需要的功能或直接在下方输入："
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "🅰️ 译林版单词查询"
                        },
                        "type": "primary",
                        "value": {
                            "action": "switch_mode",
                            "mode": "english"
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📜 统编版古文速查"
                        },
                        "type": "default",
                        "value": {
                            "action": "switch_mode",
                            "mode": "ancient"
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📐 苏科版数理考点"
                        },
                        "type": "default",
                        "value": {
                            "action": "switch_mode",
                            "mode": "math"
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📖 网页看板"
                        },
                        "type": "default",
                        "url": WEB_DASHBOARD_URL
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "💡 快捷提示：你也可以在会话中直接发送单词 (如 generous) 或古文 (如 岳阳楼记) 快速检索。"
                    }
                ]
            }
        ]
    }

def build_word_card(info: dict) -> dict:
    """
    构建译林版英语单词解析卡片
    """
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
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                            "type": "default",
                            "value": {"action": "back_to_menu"}
                        }
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
                        "text": {
                            "tag": "lark_md",
                            "content": f"**音标**：`{data['phonetic']}`\n**词性**：{data['pos']}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**课本定位**：\n{data['unit']}"
                        }
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
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 单词默写训练"},
                        "type": "primary",
                        "url": WEB_DASHBOARD_URL
                    }
                ]
            }
        ]
    }

def build_ancient_card(info: dict) -> dict:
    """
    构建统编版九年级文言文/古诗词解析卡片
    """
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
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                            "type": "default",
                            "value": {"action": "back_to_menu"}
                        }
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
                        "text": {
                            "tag": "lark_md",
                            "content": f"**作者**：{data['author']}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**教材归属**：\n{data['book']}"
                        }
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
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 查看全篇译文"},
                        "type": "primary",
                        "url": WEB_DASHBOARD_URL
                    }
                ]
            }
        ]
    }

def build_mode_input_card(mode: str) -> dict:
    """
    当学生点击了特定功能（如单词查询、古文查询）后的引导卡片
    """
    if mode == "english":
        title = "🅰️ 译林版初三英语词汇查询"
        tip = "请在聊天框中直接发送你要查询的英文单词，例如：\n• `generous`\n• `curious`\n• `achieve`\n• `patient`"
    elif mode == "ancient":
        title = "📜 统编版九年级古文古诗速查"
        tip = "请在聊天框中直接发送篇目名或名句，例如：\n• `岳阳楼记`\n• `醉翁亭记`\n• `出师表`\n• `先天下之忧而忧`"
    else:
        title = "📐 苏科版九年级数理考点速查"
        tip = "请在聊天框中发送数理考点，例如：\n• `二次函数顶点式`\n• `一元二次方程根的判别式`\n• `简单机械滑轮组`"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "indigo",
            "title": {"tag": "plain_text", "content": title}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**已切换至专项查询模式** 🎯\n\n{tip}"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                        "type": "default",
                        "value": {"action": "back_to_menu"}
                    }
                ]
            }
        ]
    }
