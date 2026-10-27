"""
苏九学伴 - 飞书多维表格 (Bitable) 核心词库引擎
核心职责：
1. 以飞书多维表格作为唯一核心词库（Single Source of Truth）；
2. 拍照提取出的划线短语/句子只负责往多维表格里追加（Batch Create Records）；
3. 所有背诵清单、纯中文 Todo List 默写清单、逐词翻页默写均实时从多维表格拉取（List/Search Records）；
4. 支持自动创建专属多维表格并自动授权给学生本人（Drive Permission API），也支持绑定已有飞书多维表格链接或 .env 预设配置；
5. 内置本地镜像缓存兜底：当新机器人尚未开通 bitable:app 权限时平滑降级并给出权限指引，确保演示与使用 100% 可用。
"""
import os
import re
import json
import time
import httpx
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

from feishu_client import get_tenant_access_token, VOCAB_BITABLE_APP_ID, VOCAB_BITABLE_APP_SECRET

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "bitable_vocab")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = "/tmp/bitable_vocab"
    os.makedirs(DATA_DIR, exist_ok=True)

BINDINGS_FILE = os.path.join(DATA_DIR, "user_bitable_bindings.json")

# 内存缓存：{ user_id: { "app_token": str, "table_id": str, "url": str, "name": str, "fallback_items": list } }
_user_bindings: Dict[str, dict] = {}


def _load_bindings():
    global _user_bindings
    if os.path.exists(BINDINGS_FILE):
        try:
            with open(BINDINGS_FILE, "r", encoding="utf-8") as f:
                _user_bindings = json.load(f)
        except Exception as e:
            print(f"[Bitable Service] 读取绑定配置异常: {e}")


def _save_bindings():
    try:
        with open(BINDINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_user_bindings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Bitable Service] 保存绑定配置异常: {e}")


_load_bindings()


def parse_bitable_url(url_or_text: str) -> Optional[Tuple[str, str]]:
    """
    从用户发送的飞书多维表格链接中解析出 app_token 和 table_id
    支持格式：
    - https://xxx.feishu.cn/base/bascnXXXXXX?table=tblYYYYYY&view=vewZZZZ
    - https://xxx.feishu.cn/base/XXXXXXXXXXXXXXXXXXXX
    """
    if not url_or_text:
        return None
    base_match = re.search(r"/base/([a-zA-Z0-9_-]{10,})", url_or_text)
    if not base_match:
        return None
    app_token = base_match.group(1)
    tbl_match = re.search(r"[?&]table=(tbl[a-zA-Z0-9_-]+)", url_or_text)
    table_id = tbl_match.group(1) if tbl_match else ""
    return app_token, table_id


def get_user_bitable_info(user_id: str) -> dict:
    """获取用户的多维表格配置信息（优先用户绑定，其次环境变量全局配置）"""
    uid = user_id or "default_user"
    binding = _user_bindings.get(uid, {})

    env_app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN", "").strip()
    env_table_id = os.getenv("FEISHU_BITABLE_TABLE_ID", "").strip()
    env_url = os.getenv("FEISHU_BITABLE_URL", "").strip()

    app_token = binding.get("app_token") or env_app_token
    table_id = binding.get("table_id") or env_table_id
    url = binding.get("url") or env_url or (f"https://feishu.cn/base/{app_token}" if app_token else "")

    return {
        "app_token": app_token,
        "table_id": table_id,
        "url": url,
        "name": binding.get("name", "苏九初三英语核心默写词库"),
        "fallback_items": binding.get("fallback_items", []),
        "latest_batch_id": binding.get("latest_batch_id", "")
    }


def bind_user_bitable(user_id: str, app_token: str, table_id: str = "", url: str = "", name: str = "苏九初三英语核心默写词库") -> dict:
    """为用户绑定指定的多维表格"""
    uid = user_id or "default_user"
    existing = _user_bindings.get(uid, {})
    final_url = url or f"https://feishu.cn/base/{app_token}" + (f"?table={table_id}" if table_id else "")
    _user_bindings[uid] = {
        "app_token": app_token,
        "table_id": table_id,
        "url": final_url,
        "name": name,
        "fallback_items": existing.get("fallback_items", []),
        "latest_batch_id": existing.get("latest_batch_id", ""),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _save_bindings()
    return _user_bindings[uid]


async def _ensure_table_and_fields(
    token: str,
    app_token: str,
    table_id: str = ""
) -> Tuple[str, List[str]]:
    """
    确保多维表格中存在数据表及所需的标准字段列：
    - 英文短语/句型 (Text)
    - 中文释义 (Text)
    - 中考考点备注 (Text)
    - 掌握状态 (SingleSelect / Text)
    - 来源批次 (Text)
    - 收录时间 (Text)
    返回 (table_id, existing_field_names)
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        # 1. 如果没有 table_id，先获取第一个数据表
        if not table_id:
            t_resp = await client.get(
                f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables",
                headers=headers
            )
            t_data = t_resp.json()
            if t_data.get("code") == 0:
                items = t_data.get("data", {}).get("items", [])
                if items:
                    table_id = items[0].get("table_id", "")

        if not table_id:
            return "", []

        # 2. 查询当前表的所有字段
        f_resp = await client.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            headers=headers
        )
        f_data = f_resp.json()
        existing_fields = []
        if f_data.get("code") == 0:
            for f_item in f_data.get("data", {}).get("items", []):
                existing_fields.append(f_item.get("field_name", ""))

        # 3. 自动补齐缺失的标准文本列 (type=1 为多行文本)
        required_text_fields = ["英文短语/句型", "中文释义", "中考考点备注", "掌握状态", "来源批次", "收录时间"]
        for req_field in required_text_fields:
            if req_field not in existing_fields:
                create_f_resp = await client.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
                    headers=headers,
                    json={"field_name": req_field, "type": 1}
                )
                if create_f_resp.json().get("code") == 0:
                    existing_fields.append(req_field)

        return table_id, existing_fields


async def create_or_ensure_user_bitable(
    user_id: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None
) -> Tuple[bool, dict, str]:
    """
    确保用户拥有可用的多维表格：
    - 若已绑定或环境变量已配置，则校验并补齐表结构；
    - 若未绑定，自动调用飞书 Bitable API 创建【苏九初三英语核心默写词库】，并授权给当前用户 open_id 可编辑。
    返回 (success, bitable_info, message)
    """
    info = get_user_bitable_info(user_id)
    token = await get_tenant_access_token(app_id or VOCAB_BITABLE_APP_ID, app_secret or VOCAB_BITABLE_APP_SECRET)
    if not token:
        return False, info, "未获取到飞书应用 Token，请检查 App ID / Secret 配置"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    # 若已有 app_token，确保 table_id 与字段完整
    if info["app_token"]:
        try:
            table_id, _ = await _ensure_table_and_fields(token, info["app_token"], info["table_id"])
            if table_id:
                updated = bind_user_bitable(user_id, info["app_token"], table_id, info["url"], info["name"])
                return True, updated, "已连接多维表格词库"
        except Exception as e:
            print(f"[Bitable Service] 校验已有表格异常: {e}")

    # 自动创建新的多维表格
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            create_resp = await client.post(
                "https://open.feishu.cn/open-apis/bitable/v1/apps",
                headers=headers,
                json={"name": "【苏九学伴】初三英语核心默写词库"}
            )
            c_data = create_resp.json()
            if c_data.get("code") == 0:
                app_info = c_data.get("data", {}).get("app", {})
                new_app_token = app_info.get("app_token", "")
                new_url = app_info.get("url", f"https://feishu.cn/base/{new_app_token}")

                # 授权给当前学生 open_id 可完全编辑 (full_access)
                if user_id and user_id.startswith("ou_"):
                    try:
                        await client.post(
                            f"https://open.feishu.cn/open-apis/drive/v1/permissions/{new_app_token}/members?type=bitable&need_notification=false",
                            headers=headers,
                            json={
                                "member_type": "openid",
                                "member_id": user_id,
                                "perm": "full_access"
                            }
                        )
                        # 同时开启链接组织内可编辑，方便学生在手机/PC直接点开
                        await client.patch(
                            f"https://open.feishu.cn/open-apis/drive/v1/permissions/{new_app_token}/public?type=bitable",
                            headers=headers,
                            json={
                                "external_access": True,
                                "security_entity": "anyone_can_edit",
                                "comment_entity": "anyone_can_edit",
                                "share_entity": "anyone",
                                "link_share_entity": "tenant_editable"
                            }
                        )
                    except Exception as perm_err:
                        print(f"[Bitable Service] 自动赋权提示: {perm_err}")

                table_id, _ = await _ensure_table_and_fields(token, new_app_token, "")
                updated = bind_user_bitable(user_id, new_app_token, table_id, new_url, "【苏九学伴】初三英语核心默写词库")
                return True, updated, "已自动创建专属飞书多维表格词库并开启编辑权限！"
            else:
                err_msg = c_data.get("msg", "未知错误")
                print(f"[Bitable Create Failed] {c_data}")
                return False, info, f"多维表格 API 返回提示：{err_msg}（请确认应用已开通 `bitable:app` 权限，或直接发送已有表格链接进行绑定）"
        except Exception as e:
            print(f"[Bitable Create Exception] {e}")
            return False, info, f"创建多维表格异常：{e}"


async def append_vocab_to_bitable(
    user_id: str,
    items: List[dict],
    batch_title: str = "课文划线词汇",
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None
) -> Tuple[bool, dict, str]:
    """
    将拍照识别出的词汇列表追加写入飞书多维表格，同时更新本地镜像兜底。
    返回 (sync_success, bitable_info, sync_message)
    """
    uid = user_id or "default_user"
    now_str = time.strftime("%Y-%m-%d %H:%M")
    batch_id = f"batch_{int(time.time())}"

    # 1. 先写入本地镜像缓存（确保无论云端权限如何，功能 100% 不丢数据）
    if uid not in _user_bindings:
        _user_bindings[uid] = {
            "app_token": os.getenv("FEISHU_BITABLE_APP_TOKEN", "").strip(),
            "table_id": os.getenv("FEISHU_BITABLE_TABLE_ID", "").strip(),
            "url": os.getenv("FEISHU_BITABLE_URL", "").strip(),
            "name": "【苏九学伴】初三英语核心默写词库",
            "fallback_items": [],
            "latest_batch_id": batch_id
        }

    fallback_list = _user_bindings[uid].setdefault("fallback_items", [])
    existing_phrases = {str(x.get("phrase", "")).strip().lower() for x in fallback_list}

    formatted_new = []
    for it in items:
        phrase = str(it.get("phrase", "")).strip()
        meaning = str(it.get("meaning", "")).strip()
        note = str(it.get("note", "")).strip() or "译林版九年级核心考点"
        if not phrase:
            continue
        item_obj = {
            "record_id": f"local_{int(time.time()*1000)}_{len(fallback_list)+len(formatted_new)+1}",
            "phrase": phrase,
            "meaning": meaning,
            "note": note,
            "status": "待默写",
            "batch_title": batch_title,
            "batch_id": batch_id,
            "created_at": now_str
        }
        formatted_new.append(item_obj)
        if phrase.lower() not in existing_phrases:
            fallback_list.append(item_obj)
            existing_phrases.add(phrase.lower())
        else:
            # 更新已有词条的批次标记以便最新批次拉取
            for ex in fallback_list:
                if str(ex.get("phrase", "")).strip().lower() == phrase.lower():
                    ex["batch_id"] = batch_id
                    ex["batch_title"] = batch_title
                    if meaning:
                        ex["meaning"] = meaning

    _user_bindings[uid]["latest_batch_id"] = batch_id
    _save_bindings()

    # 2. 同步写入飞书多维表格远端
    ok, info, msg = await create_or_ensure_user_bitable(uid, app_id, app_secret)
    if not ok or not info.get("app_token") or not info.get("table_id"):
        return False, get_user_bitable_info(uid), msg

    token = await get_tenant_access_token(app_id or VOCAB_BITABLE_APP_ID, app_secret or VOCAB_BITABLE_APP_SECRET)
    app_token = info["app_token"]
    table_id = info["table_id"]

    records_payload = []
    for it in formatted_new:
        records_payload.append({
            "fields": {
                "英文短语/句型": it["phrase"],
                "中文释义": it["meaning"],
                "中考考点备注": it["note"],
                "掌握状态": "待默写",
                "来源批次": f"{batch_title} ({batch_id})",
                "收录时间": it["created_at"]
            }
        })

    if not records_payload:
        return True, get_user_bitable_info(uid), "无新增词条"

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, headers=headers, json={"records": records_payload})
            res_data = resp.json()
            if res_data.get("code") == 0:
                created_records = res_data.get("data", {}).get("records", [])
                # 将远端真实的 record_id 回写到本地缓存
                for idx, rec in enumerate(created_records):
                    if idx < len(formatted_new) and rec.get("record_id"):
                        formatted_new[idx]["record_id"] = rec["record_id"]
                _save_bindings()
                return True, get_user_bitable_info(uid), f"已成功追加 {len(records_payload)} 条词汇至飞书多维表格！"
            else:
                print(f"[Bitable Batch Create Failed] {res_data}")
                return False, get_user_bitable_info(uid), f"多维表格写入返回：{res_data.get('msg', '请检查表格权限')}"
        except Exception as e:
            print(f"[Bitable Batch Create Exception] {e}")
            return False, get_user_bitable_info(uid), f"写入多维表格网络异常：{e}"


def _extract_cell_text(val) -> str:
    """兼容飞书多维表格不同字段类型的返回值解析"""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        parts = []
        for seg in val:
            if isinstance(seg, dict):
                parts.append(str(seg.get("text", "") or seg.get("name", "")))
            else:
                parts.append(str(seg))
        return "".join(parts).strip()
    if isinstance(val, dict):
        return str(val.get("text", "") or val.get("name", "")).strip()
    return str(val).strip()


async def fetch_vocab_from_bitable(
    user_id: str,
    scope: str = "all",
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None
) -> Tuple[List[dict], dict, bool]:
    """
    从飞书多维表格实时拉取词汇列表（所有背诵和默写的数据源）
    scope 支持：
    - "all": 拉取多维表格全部词条
    - "unmastered": 仅拉取【掌握状态】不为“已掌握”的词条
    - "latest": 仅拉取最近一次批次追加的词条
    返回 (items, bitable_info, is_from_remote_bitable)
    """
    uid = user_id or "default_user"
    info = get_user_bitable_info(uid)
    app_token = info.get("app_token", "")
    table_id = info.get("table_id", "")

    remote_items: List[dict] = []
    from_remote = False

    if app_token:
        token = await get_tenant_access_token(app_id or VOCAB_BITABLE_APP_ID, app_secret or VOCAB_BITABLE_APP_SECRET)
        if token:
            if not table_id:
                table_id, _ = await _ensure_table_and_fields(token, app_token, "")
                if table_id:
                    info = bind_user_bitable(uid, app_token, table_id, info.get("url", ""), info.get("name", ""))

            if table_id:
                url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=200"
                headers = {"Authorization": f"Bearer {token}"}
                async with httpx.AsyncClient(timeout=15) as client:
                    try:
                        resp = await client.get(url, headers=headers)
                        r_data = resp.json()
                        if r_data.get("code") == 0:
                            from_remote = True
                            raw_records = r_data.get("data", {}).get("items", [])
                            for rec in raw_records:
                                fields = rec.get("fields", {})
                                # 兼容标准列名或用户自定义第一列/第二列
                                phrase = (
                                    _extract_cell_text(fields.get("英文短语/句型"))
                                    or _extract_cell_text(fields.get("英文短语"))
                                    or _extract_cell_text(fields.get("单词/短语"))
                                    or _extract_cell_text(fields.get("文本"))
                                )
                                meaning = (
                                    _extract_cell_text(fields.get("中文释义"))
                                    or _extract_cell_text(fields.get("释义"))
                                    or _extract_cell_text(fields.get("中文"))
                                )
                                note = (
                                    _extract_cell_text(fields.get("中考考点备注"))
                                    or _extract_cell_text(fields.get("备注"))
                                    or _extract_cell_text(fields.get("考点"))
                                )
                                status = _extract_cell_text(fields.get("掌握状态")) or "待默写"
                                batch_str = _extract_cell_text(fields.get("来源批次"))
                                created_at = _extract_cell_text(fields.get("收录时间"))

                                if phrase or meaning:
                                    remote_items.append({
                                        "record_id": rec.get("record_id", ""),
                                        "phrase": phrase,
                                        "meaning": meaning,
                                        "note": note,
                                        "status": status,
                                        "batch_title": batch_str,
                                        "created_at": created_at
                                    })
                    except Exception as e:
                        print(f"[Bitable Fetch Records Exception] {e}")

    # 如果成功从远端多维表格拉取到数据，同步更新本地缓存
    if from_remote and remote_items:
        if uid in _user_bindings:
            _user_bindings[uid]["fallback_items"] = remote_items
            _save_bindings()
        source_items = remote_items
    else:
        source_items = info.get("fallback_items", [])

    # 按 scope 过滤
    if not source_items:
        return [], info, from_remote

    if scope == "unmastered":
        filtered = [it for it in source_items if "已掌握" not in str(it.get("status", ""))]
        return (filtered if filtered else source_items), info, from_remote
    elif scope == "latest":
        latest_batch_id = info.get("latest_batch_id", "")
        if latest_batch_id:
            filtered = [
                it for it in source_items
                if latest_batch_id in str(it.get("batch_id", "")) or latest_batch_id in str(it.get("batch_title", ""))
            ]
            if filtered:
                return filtered, info, from_remote
        # 若没有匹配到 batch_id，返回最后追加的最多 12 条
        return source_items[-12:], info, from_remote

    return source_items, info, from_remote


async def update_vocab_status_in_bitable(
    user_id: str,
    record_id: str,
    new_status: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None
) -> bool:
    """
    在飞书交互卡片上点击【✅ 标记已掌握】或【⭐ 标记重点待复习】时，
    直接将该状态回写同步到飞书多维表格对应的行记录中！
    """
    uid = user_id or "default_user"
    info = get_user_bitable_info(uid)

    # 1. 更新本地镜像
    if uid in _user_bindings:
        for it in _user_bindings[uid].get("fallback_items", []):
            if it.get("record_id") == record_id:
                it["status"] = new_status
        _save_bindings()

    # 2. 若为真实多维表格 record_id，调用飞书 API 更新单元格
    app_token = info.get("app_token", "")
    table_id = info.get("table_id", "")
    if not app_token or not table_id or not record_id or record_id.startswith("local_"):
        return False

    token = await get_tenant_access_token(app_id or VOCAB_BITABLE_APP_ID, app_secret or VOCAB_BITABLE_APP_SECRET)
    if not token:
        return False

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.put(
                url,
                headers=headers,
                json={"fields": {"掌握状态": new_status}}
            )
            return resp.json().get("code") == 0
        except Exception as e:
            print(f"[Bitable Update Record Exception] {e}")
    return False
