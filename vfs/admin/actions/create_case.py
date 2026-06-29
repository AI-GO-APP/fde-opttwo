"""建立案件（x_opt_cases）。盤商承接退場商家一批設備時開案。

params:
  total_package_price (必填) - 向退場商家收的整批總包價
  supplier_id   - 退場商家（suppliers.id），選填
  region        - 地區（驅動媒合），選填
  site_address  - 場勘地址，選填
"""
from datetime import datetime, timezone


def execute(ctx):
    p = ctx.params
    total = str(p.get("total_package_price") or "").strip()
    if not total:
        ctx.response.json({"error": "total_package_price 為必填"})
        return

    now = datetime.now(timezone.utc).isoformat()
    rec = ctx.db.insert_object(slug="x_opt_cases", data={
        "supplier_id": str(p.get("supplier_id") or ""),
        "assigned_agent_id": str(getattr(ctx.user, "id", "") or ""),
        "total_package_price": total,
        "estimate_price": str(p.get("estimate_price") or ""),
        "formal_price": str(p.get("formal_price") or ""),
        "status": "open",
        "site_address": str(p.get("site_address") or ""),
        "region": str(p.get("region") or ""),
        "created_at": now,
        "migration_batch_id": "",
    })
    ctx.response.json({"success": True, "case": rec})
