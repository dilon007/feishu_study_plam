"""
苏九学伴 - 英语高亮划线词组背诵与默写管理引擎
功能：
1. 会话生命周期管理：创建、获取、更新词汇列表；
2. 本地 JSON 轻量持久化，支持在线修改释义与同步；
3. 默写进度追踪与状态管理。
"""
import os
import json
import uuid
import time
from typing import List, Dict, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "vocab_sessions")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = "/tmp/vocab_sessions"
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass

# 内存快速缓存
_sessions_cache: Dict[str, dict] = {}
# 记录每个用户最近一次创建的 session_id: { "user_id": "session_id" }
_user_latest_session: Dict[str, str] = {}

def _get_session_path(session_id: str) -> str:
    return os.path.join(DATA_DIR, f"{session_id}.json")


def create_vocab_session(user_id: str, items: List[dict], title: str = "课文划线重点词组") -> dict:
    """
    根据识别出的词组列表创建学习会话
    items 格式: [{"phrase": "take...seriously", "phonetic": "...", "meaning": "认真对待"}]
    """
    session_id = f"voc_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    formatted_items = []
    for idx, it in enumerate(items, 1):
        formatted_items.append({
            "id": idx,
            "phrase": str(it.get("phrase", "")).strip(),
            "phonetic": str(it.get("phonetic", "")).strip(),
            "meaning": str(it.get("meaning", "")).strip(),
            "note": str(it.get("note", "")).strip()
        })

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "title": title,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(formatted_items),
        "items": formatted_items
    }

    _sessions_cache[session_id] = session_data
    if user_id:
        _user_latest_session[user_id] = session_id

    try:
        with open(_get_session_path(session_id), "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Vocab Session Save Error] {e}")

    return session_data

def get_vocab_session(session_id: str) -> Optional[dict]:
    """获取指定的背诵会话"""
    if session_id in _sessions_cache:
        return _sessions_cache[session_id]

    file_path = _get_session_path(session_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _sessions_cache[session_id] = data
                return data
        except Exception as e:
            print(f"[Vocab Session Read Error] {e}")
    return None

def get_user_latest_vocab_session(user_id: str) -> Optional[dict]:
    """获取指定用户最近一次创建的背诵会话"""
    if not user_id:
        return None
    
    # 优先从内存字典获取
    latest_id = _user_latest_session.get(user_id)
    if latest_id:
        session = get_vocab_session(latest_id)
        if session:
            return session

    # 兜底：从会话缓存或文件中寻找属于该用户的最新会话
    for s_id, s_data in reversed(list(_sessions_cache.items())):
        if s_data.get("user_id") == user_id:
            return s_data

    return None

def update_vocab_session(session_id: str, new_items: List[dict], new_title: str = "") -> Optional[dict]:
    """
    更新词组列表（支持修改中文注释、增删词条）
    """
    session = get_vocab_session(session_id)
    if not session:
        return None

    if new_title:
        session["title"] = new_title

    # 规范化新列表条目
    formatted_items = []
    for idx, it in enumerate(new_items, 1):
        formatted_items.append({
            "id": idx,
            "phrase": str(it.get("phrase", "")).strip(),
            "phonetic": str(it.get("phonetic", "")).strip(),
            "meaning": str(it.get("meaning", "")).strip(),
            "note": str(it.get("note", "")).strip()
        })

    session["items"] = formatted_items
    session["total_count"] = len(formatted_items)
    session["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    _sessions_cache[session_id] = session
    try:
        with open(_get_session_path(session_id), "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Vocab Session Update Error] {e}")

    return session
