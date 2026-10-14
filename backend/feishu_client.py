"""
飞书开放平台客户端：负责 Token 缓存与调用官方 API 发送消息卡片
"""
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

_token_cache = {
    "token": "",
    "expire_at": 0
}

async def get_tenant_access_token() -> str:
    """获取并自动缓存 tenant_access_token"""
    global _token_cache
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expire_at"]:
        return _token_cache["token"]

    if not APP_ID or not APP_SECRET:
        return ""

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json={
                "app_id": APP_ID,
                "app_secret": APP_SECRET
            })
            data = resp.json()
            if data.get("code") == 0:
                _token_cache["token"] = data["tenant_access_token"]
                _token_cache["expire_at"] = now + data.get("expire", 7200) - 300
                return _token_cache["token"]
            else:
                print(f"[Feishu Token Error] {data}")
        except Exception as e:
            print(f"[Feishu Token Request Failed] {e}")
    return ""

async def reply_interactive_card(message_id: str, card_content: dict) -> bool:
    """回复一条消息卡片"""
    token = await get_tenant_access_token()
    if not token:
        print("[Feishu] 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET，跳过主动调用")
        return False

    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "msg_type": "interactive",
        "content": str(card_content) if isinstance(card_content, str) else httpx._models.json_dumps(card_content)
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            res = resp.json()
            if res.get("code") == 0:
                return True
            else:
                print(f"[Feishu Send Card Failed] {res}")
        except Exception as e:
            print(f"[Feishu Send Card Exception] {e}")
    return False

async def send_chat_card(chat_id: str, card_content: dict) -> bool:
    """向群聊或单聊发送一条卡片消息"""
    token = await get_tenant_access_token()
    if not token:
        return False

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": httpx._models.json_dumps(card_content)
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.json().get("code") == 0
        except Exception as e:
            print(f"[Feishu Send Chat Card Exception] {e}")
    return False
