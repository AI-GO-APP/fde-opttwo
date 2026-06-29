"""一次性建立 Opttwo 的 tenant 共用自訂物件（x_opt_*），idempotent。

⚠️ 重要：AIGO 的「x_ 表」不是實體 Postgres 表，是平台的 Custom Object（EAV/JSONB）。
   - 沒有外鍵、沒有 SQL JOIN；關聯只存對方 id，在 action 內用 Python in-memory join。
   - action 用 ctx.db.query_object/insert_object/update_object 存取；
     前端走 /data/objects/{uuid}/records；都不走 AppDataReference。
   - 為避免與同 tenant 其他 app 撞名，一律用 x_opt_ 前綴。

欄位型別：平台 Custom Object 欄位這裡一律用 text（與 sc1984 x_product_image 一致最保險）。
   金額/日期以字串存，於 action 內 parse。Phase 0 若確認平台支援 number/date 型別再優化。

用法：
  set -a && source .env && set +a
  python3 vfs/scripts/create_reloop_objects.py

注意：建立 tenant 物件（app_id=None）需登入帳號有 builder.admin 權限；
若回 403，需平台管理員協助建立。
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from deploy_lib import require_env, login, _req, API_BASE


def _f(key, name, seq, required=False):
    return {"name": name, "field_key": key, "field_type": "text",
            "is_required": required, "sequence": seq}


# 每個物件：api_slug → (顯示名, [fields])。所有物件都帶 migration_batch_id 供回滾精準清除。
OBJECTS = {
    "x_opt_cases": ("案件", [
        _f("supplier_id", "退場商家ID", 1),
        _f("assigned_agent_id", "負責業務ID", 2),
        _f("total_package_price", "總包價", 3),
        _f("estimate_price", "評估報價", 4),
        _f("formal_price", "正式報價", 5),
        _f("status", "狀態", 6),
        _f("site_address", "場勘地址", 7),
        _f("region", "地區", 8),
        _f("created_at", "建立時間", 9),
        _f("migration_batch_id", "搬遷批次", 10),
    ]),
    "x_opt_equipment": ("設備清單", [
        _f("case_id", "案件ID", 1, required=True),
        _f("name", "設備名稱", 2),
        _f("category", "設備分類", 3),
        _f("condition", "狀況", 4),
        _f("floor_price", "底價", 5),
        _f("floor_price_status", "底價狀態(none/pending/approved)", 6),
        _f("floor_price_by", "底價填寫人", 7),
        _f("floor_price_approved_by", "底價核可人", 8),
        _f("floor_price_updated_at", "底價更新時間", 9),
        _f("photos", "照片(JSON)", 10),
        _f("migration_batch_id", "搬遷批次", 11),
    ]),
    "x_opt_bids": ("回收商競標", [
        _f("equipment_id", "設備ID", 1),
        _f("case_id", "案件ID", 2),
        _f("recycler_customer_id", "回收商customer_id", 3),
        _f("bid_amount", "投標金額", 4),
        _f("status", "狀態", 5),
        _f("payment_last5", "付款帳號末五碼", 6),
        _f("payment_deadline_at", "付款截止", 7),
        _f("created_at", "建立時間", 8),
        _f("migration_batch_id", "搬遷批次", 9),
    ]),
    "x_opt_settings": ("系統設定(KV)", [
        _f("key", "鍵", 1, required=True),
        _f("value", "值(JSON)", 2),
        _f("updated_at", "更新時間", 3),
    ]),
    "x_opt_permission_groups": ("使用者權限組指派", [
        _f("user_id", "使用者ID", 1, required=True),
        _f("group_key", "權限組", 2, required=True),
        _f("assigned_by", "指派人", 3),
        _f("created_at", "建立時間", 4),
    ]),
    "x_opt_recycler_pref": ("回收商偏好補充", [
        _f("customer_id", "回收商customer_id", 1, required=True),
        _f("accepted_conditions", "接受條款(JSON)", 2),
        _f("custom", "其他偏好(JSON)", 3),
    ]),
    "x_opt_contracts": ("合約(委任同意書)", [
        _f("customer_id", "回收商customer_id", 1),
        _f("template_key", "範本鍵", 2),
        _f("signed_at", "簽署時間", 3),
        _f("signature_img", "簽名圖", 4),
        _f("status", "狀態", 5),
    ]),
    "x_opt_contract_templates": ("合約範本", [
        _f("key", "鍵", 1, required=True),
        _f("title", "標題", 2),
        _f("body", "內文", 3),
        _f("version", "版本", 4),
    ]),
    "x_opt_invite_tokens": ("邀請連結", [
        _f("token", "邀請碼", 1, required=True),
        _f("role", "角色", 2),
        _f("target", "目標(JSON)", 3),
        _f("created_by_user_id", "建立人", 4),
        _f("created_at", "建立時間", 5),
        _f("expires_at", "過期時間", 6),
        _f("redeemed_at", "兌換時間", 7),
    ]),
}


def main():
    token = login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD"))
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    status, body = _req("GET", f"{API_BASE}/data/objects", h)
    if status != 200:
        sys.exit(f"❌ 取得物件清單失敗：{status} {body}")
    existing = {o.get("api_slug"): o for o in (body or [])}

    for slug, (name, fields) in OBJECTS.items():
        if slug in existing:
            keys = [f.get("field_key") for f in (existing[slug].get("fields") or [])]
            print(f"✅ {slug} 已存在（id={existing[slug].get('id')}）field_keys={keys}，略過")
            continue
        payload = {"app_id": None, "name": name, "api_slug": slug, "fields": fields}
        s2, b2 = _req("POST", f"{API_BASE}/data/objects/batch", h, payload)
        if s2 not in (200, 201):
            sys.exit(f"❌ 建立 {slug} 失敗：{s2} {b2}\n"
                     f"   （若 403：登入帳號缺 builder.admin 權限，需平台管理員協助建 tenant 物件）")
        print(f"✅ 已建立 {slug}：id={(b2 or {}).get('id')}")


if __name__ == "__main__":
    main()
