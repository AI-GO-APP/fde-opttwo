"""測試 Phase 2 權限 + 底價狀態機（admin 已 publish，走正式 /run）。

流程：建設備 → 無權限設底價(擋) → 指派 supervisor → 設底價=pending →
      supervisor 核可(擋) → 指派 admin → 核可=approved → 清掉測試指派。

  set -a && source .env && set +a
  python3 vfs/scripts/test_permissions.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from deploy_lib import require_env, login, _req, API_BASE

H = None
ADMIN = None


def run(name, params):
    s, b = _req("POST", f"{API_BASE}/actions/apps/{ADMIN}/run/{name}", H, {"params": params}, timeout=90)
    if s != 200:
        sys.exit(f"❌ {name} HTTP {s}：{b}")
    if isinstance(b, dict):
        if b.get("status") == "error":
            sys.exit(f"❌ {name} 執行錯誤：{b.get('error')} logs={b.get('logs')}")
        return b.get("result") or b.get("data") or b
    return b


def obj_uuid(slug):
    s, b = _req("GET", f"{API_BASE}/data/objects", H)
    return next(o.get("id") for o in (b or []) if o.get("api_slug") == slug)


def assign_group(pg_uuid, uid, group):
    s, b = _req("POST", f"{API_BASE}/data/objects/{pg_uuid}/records", H,
                {"data": {"user_id": uid, "group_key": group}})
    if s not in (200, 201):
        sys.exit(f"❌ 指派 {group} 失敗：{s} {b}")
    return b.get("id")


def main():
    global H, ADMIN
    H = {"Authorization": "Bearer " + login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD")),
         "Content-Type": "application/json"}
    ADMIN = require_env("ADMIN_APP_ID")
    pg = obj_uuid("x_opt_permission_groups")
    created = []
    fails = []

    def check(label, cond):
        print(("  ✅ " if cond else "  ❌ ") + label)
        if not cond:
            fails.append(label)

    print("── 0. 基準：我的權限 ──")
    me = run("get_my_permissions", {})
    uid = me["user_id"]
    print("   uid =", uid, "groups =", me["groups"], "is_admin =", me["is_admin"])
    check("基準無 admin", me["is_admin"] is False)
    check("基準無 set_floor_price", me["permissions"]["set_floor_price"] is False)

    print("── 1. 建案件 + 設備（無底價）──")
    case_id = run("create_case", {"total_package_price": "100000"})["case"]["id"]
    eid = run("add_equipment", {"case_id": case_id, "name": "測試機"})["equipment"]["id"]

    print("── 2. 無權限設底價（應被擋）──")
    r = run("set_floor_price", {"equipment_id": eid, "floor_price": "30000"})
    check("無權限被擋", r.get("code") == "forbidden")

    print("── 3. 指派 supervisor → 設底價（應 pending）──")
    created.append(assign_group(pg, uid, "supervisor"))
    r = run("set_floor_price", {"equipment_id": eid, "floor_price": "30000"})
    check("supervisor 可設底價", r.get("success") is True)
    check("非 admin → pending", r.get("floor_price_status") == "pending")

    print("── 4. supervisor 核可底價（應被擋，supervisor 無 approve_floor_price）──")
    r = run("approve_floor_price", {"equipment_id": eid})
    check("supervisor 不能核可", r.get("code") == "forbidden")

    print("── 5. 指派 admin → 核可（應 approved）──")
    created.append(assign_group(pg, uid, "admin"))
    me2 = run("get_my_permissions", {})
    check("已是 admin", me2["is_admin"] is True)
    r = run("approve_floor_price", {"equipment_id": eid})
    check("admin 核可成功", r.get("floor_price_status") == "approved")

    print("── 6. 清除測試指派 ──")
    for rid in created:
        _req("DELETE", f"{API_BASE}/data/records/{rid}", H)
    print(f"   已刪 {len(created)} 筆指派")

    print("\n" + ("✅ 全部通過" if not fails else f"❌ {len(fails)} 項失敗：{fails}"))


if __name__ == "__main__":
    main()
