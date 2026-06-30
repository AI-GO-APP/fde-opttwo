"""種入 Opttwo 系統設定（x_opt_settings KV），idempotent。

- permission_groups：權限組定義（沿用 FDE-ReLoop 的 5 組；admin 走 bypass 不列）
- workflow_parameters：流程參數（投標/付款截止小時數等）

value 欄位是 text → 存 JSON 字串，action 內 json.loads 解析。

  set -a && source .env && set +a
  python3 vfs/scripts/seed_settings.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from deploy_lib import require_env, login, _req, API_BASE

# 每組授予的權限 key（admin 不在此，靠 bypass 拿全部）
PERMISSION_GROUPS = {
    "sales":      ["confirm_recommendations", "propose_winner", "schedule_delivery", "complete_delivery"],
    "supervisor": ["view_all_cases", "set_floor_price", "confirm_recommendations", "propose_winner",
                   "approve_winner", "schedule_delivery", "close_case", "manage_workflow_parameters"],
    "finance":    ["confirm_payment"],
    "delivery":   ["schedule_delivery", "complete_delivery"],
    "operations": ["view_all_cases", "manage_recyclers", "manage_workflow_parameters"],
}

WORKFLOW_PARAMETERS = {
    "bid_deadline_hours": 24,
    "payment_deadline_hours": 48,
    "min_bid_ratio": 1.0,
}

SETTINGS = {
    "permission_groups": PERMISSION_GROUPS,
    "workflow_parameters": WORKFLOW_PARAMETERS,
}


def main():
    h = {"Authorization": "Bearer " + login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD")),
         "Content-Type": "application/json"}

    # x_opt_settings 物件 uuid
    s, b = _req("GET", f"{API_BASE}/data/objects", h)
    if s != 200:
        sys.exit(f"❌ 取得物件清單失敗：{s} {b}")
    uuid = next((o.get("id") for o in (b or []) if o.get("api_slug") == "x_opt_settings"), None)
    if not uuid:
        sys.exit("❌ 找不到 x_opt_settings，先跑 create_reloop_objects.py")

    # 現有 key
    s, recs = _req("GET", f"{API_BASE}/data/objects/{uuid}/records", h)
    existing = {}
    for r in (recs or []):
        d = r.get("data", r)
        existing[d.get("key")] = r.get("id")

    for key, val in SETTINGS.items():
        payload = {"data": {"key": key, "value": json.dumps(val, ensure_ascii=False)}}
        if key in existing:
            s2, _ = _req("PATCH", f"{API_BASE}/data/records/{existing[key]}", h, payload)
            print(f"↩️  更新 {key}：{s2}")
        else:
            s2, _ = _req("POST", f"{API_BASE}/data/objects/{uuid}/records", h, payload)
            print(f"✅ 新增 {key}：{s2}")


if __name__ == "__main__":
    main()
