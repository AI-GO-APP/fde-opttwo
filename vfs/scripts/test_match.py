"""測試 match_recyclers：依地區/分類媒合回收商 + 渲染 LINE 文案。

R1 台北/不限分類、R2 台中、R3 台北+限冷氣。
案件在台北、含冷氣+冰箱 → 應命中 R1、R3（R2 地區不符排除）。

  set -a && source .env && set +a
  python3 vfs/scripts/test_match.py
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
    if isinstance(b, dict) and b.get("status") == "error":
        sys.exit(f"❌ {name} 執行錯誤：{b.get('error')} logs={b.get('logs')}")
    return b.get("result") if isinstance(b, dict) else b


def obj_uuid(slug):
    s, b = _req("GET", f"{API_BASE}/data/objects", H)
    return next(o.get("id") for o in (b or []) if o.get("api_slug") == slug)


def seed_pref(uuid, cid, regions, cats):
    cond = json.dumps({"served_regions": regions, "categories": cats}, ensure_ascii=False)
    s, b = _req("POST", f"{API_BASE}/data/objects/{uuid}/records", H,
                {"data": {"customer_id": cid, "accepted_conditions": cond}})
    if s not in (200, 201):
        sys.exit(f"❌ 灌偏好失敗：{s} {b}")
    return b.get("id")


def main():
    global H, ADMIN
    H = {"Authorization": "Bearer " + login(require_env("AIGO_EMAIL"), require_env("AIGO_PASSWORD")),
         "Content-Type": "application/json"}
    ADMIN = require_env("ADMIN_APP_ID")
    pref_uuid = obj_uuid("x_opt_recycler_pref")
    created, fails = [], []

    def check(label, cond):
        print(("  ✅ " if cond else "  ❌ ") + label)
        if not cond:
            fails.append(label)

    print("── 1. 灌 3 個回收商偏好 ──")
    created.append(seed_pref(pref_uuid, "RC1", ["台北"], []))           # 台北/不限
    created.append(seed_pref(pref_uuid, "RC2", ["台中"], []))           # 台中（不該命中）
    created.append(seed_pref(pref_uuid, "RC3", ["台北"], ["冷氣"]))     # 台北+限冷氣

    print("── 2. 建台北案件 + 冷氣/冰箱兩設備 ──")
    case_id = run("create_case", {"total_package_price": "100000", "region": "台北"})["case"]["id"]
    run("add_equipment", {"case_id": case_id, "name": "冷氣A", "category": "冷氣"})
    run("add_equipment", {"case_id": case_id, "name": "冰箱B", "category": "冰箱"})

    print("── 3. 媒合 ──")
    r = run("match_recyclers", {"case_id": case_id})
    ids = {m["customer_id"] for m in r["matched"]}
    print("   matched =", ids, "| msg =", r["notify_message"])
    check("命中數=2", r["matched_count"] == 2)
    check("命中 RC1、RC3", ids == {"RC1", "RC3"})
    check("排除台中 RC2", "RC2" not in ids)
    check("文案含台北與2台", "台北" in r["notify_message"] and "2 台" in r["notify_message"])

    print("── 4. 清除測試偏好 ──")
    for rid in created:
        _req("DELETE", f"{API_BASE}/data/records/{rid}", H)
    print(f"   已刪 {len(created)} 筆偏好")

    print("\n" + ("✅ 全部通過" if not fails else f"❌ {len(fails)} 項失敗：{fails}"))


if __name__ == "__main__":
    main()
