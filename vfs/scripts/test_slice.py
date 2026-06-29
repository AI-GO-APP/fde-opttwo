"""垂直切片測試：建案件→上設備→(灌投標)→讀明細算毛利。
驗證 EAV in-memory join 可行。

平台已移除 in-process dev runner（Phase 4d），action 只能在 publish 後由真 runner 執行。
故：admin 已 publish，這裡用正式 /run 端點測 admin 的 3 支 action（builder token）；
投標資料用 data-objects records API 直接灌（submit_bid 屬 ordering external，
需回收商登入 token，留到 Phase 4 接 LINE 後驗）。

  set -a && source .env && set +a
  python3 vfs/scripts/test_slice.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from deploy_lib import require_env, login, _req, API_BASE


def unwrap(body):
    if isinstance(body, dict):
        if body.get("status") == "error":
            sys.exit(f"❌ action 失敗：{body.get('error')}  logs={body.get('logs')}")
        return body.get("result") or body.get("data") or body
    return body


def run(h, app_id, name, params):
    s, b = _req("POST", f"{API_BASE}/actions/apps/{app_id}/run/{name}", h, {"params": params})
    if s != 200:
        sys.exit(f"❌ {name} HTTP {s}：{b}")
    return unwrap(b)


def object_uuid(h, slug):
    s, b = _req("GET", f"{API_BASE}/data/objects", h)
    if s != 200:
        sys.exit(f"❌ 取得物件清單失敗：{s} {b}")
    for o in (b or []):
        if o.get("api_slug") == slug:
            return o.get("id")
    sys.exit(f"❌ 找不到物件 {slug}")


def seed_bid(h, bids_uuid, equipment_id, case_id, amount):
    data = {"equipment_id": equipment_id, "case_id": case_id, "recycler_customer_id": "test",
            "bid_amount": str(amount), "status": "submitted"}
    s, b = _req("POST", f"{API_BASE}/data/objects/{bids_uuid}/records", h, {"data": data})
    if s not in (200, 201):
        sys.exit(f"❌ 灌投標失敗：{s} {b}")


def main():
    h = {"Authorization": "Bearer " + login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD")),
         "Content-Type": "application/json"}
    admin = require_env("ADMIN_APP_ID")

    print("── 1. 建案件（總包價 100000）──")
    r = run(h, admin, "create_case", {"total_package_price": "100000", "region": "台北"})
    case_id = r["case"]["id"]
    print("   case_id =", case_id)

    print("── 2. 上兩台設備（底價 30000 / 40000）──")
    eid1 = run(h, admin, "add_equipment", {"case_id": case_id, "name": "冷氣A", "floor_price": "30000"})["equipment"]["id"]
    eid2 = run(h, admin, "add_equipment", {"case_id": case_id, "name": "冰箱B", "floor_price": "40000"})["equipment"]["id"]
    print("   equipment =", eid1, eid2)

    print("── 3. 灌投標（冷氣A 35000；冰箱B 50000、48000）──")
    bids_uuid = object_uuid(h, "x_opt_bids")
    seed_bid(h, bids_uuid, eid1, case_id, 35000)
    seed_bid(h, bids_uuid, eid2, case_id, 50000)
    seed_bid(h, bids_uuid, eid2, case_id, 48000)

    print("── 4. 讀案件明細（EAV in-memory join + 算毛利）──")
    d = run(h, admin, "get_case_detail", {"case_id": case_id})
    print(json.dumps(d, ensure_ascii=False, indent=2))

    # 預期：最高出價加總 = 35000 + 50000 = 85000；毛利 = 85000 - 100000 = -15000
    ok = abs(d.get("total_best_bid", 0) - 85000) < 0.01 and abs(d.get("margin", 0) + 15000) < 0.01
    print("\n" + ("✅ EAV join + 毛利計算正確（total_best_bid=85000, margin=-15000）"
                  if ok else f"❌ 不符：total_best_bid={d.get('total_best_bid')} margin={d.get('margin')}"))


if __name__ == "__main__":
    main()
