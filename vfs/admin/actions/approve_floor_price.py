"""核可主管填寫的待審底價（pending → approved）。僅 admin / 有 approve_floor_price 權限者。

params: equipment_id (必填)
"""
import json
from datetime import datetime, timezone


def _can(ctx, uid, perm):
    groups = [str(r.get("group_key")) for r in (ctx.db.query_object("x_opt_permission_groups", limit=10000) or [])
              if str(r.get("user_id")) == uid]
    if "admin" in groups:
        return True, True
    defs = {}
    for r in (ctx.db.query_object("x_opt_settings", limit=10000) or []):
        if r.get("key") == "permission_groups":
            try:
                defs = json.loads(r.get("value") or "{}")
            except (ValueError, TypeError):
                defs = {}
            break
    granted = set()
    for g in groups:
        granted.update(defs.get(g, []))
    return False, (perm in granted)


def execute(ctx):
    equipment_id = str(ctx.params.get("equipment_id") or "").strip()
    if not equipment_id:
        ctx.response.json({"error": "equipment_id 為必填"})
        return

    uid = str(getattr(ctx, "user_id", "") or "")
    _is_admin, allowed = _can(ctx, uid, "approve_floor_price")
    if not allowed:
        ctx.response.json({"error": "無權限核可底價（需 approve_floor_price）", "code": "forbidden"})
        return

    eq = next((e for e in (ctx.db.query_object("x_opt_equipment", limit=10000) or [])
               if str(e.get("id")) == equipment_id), None)
    if not eq:
        ctx.response.json({"error": f"找不到設備（id={equipment_id}）"})
        return
    if eq.get("floor_price_status") != "pending":
        ctx.response.json({"error": f"設備底價非待審狀態（目前 {eq.get('floor_price_status')}）", "code": "bad_state"})
        return

    now = datetime.now(timezone.utc).isoformat()
    ctx.db.update_object(slug="x_opt_equipment", record_id=equipment_id, data={
        "floor_price_status": "approved",
        "floor_price_approved_by": uid,
        "floor_price_updated_at": now,
    })
    ctx.response.json({"success": True, "equipment_id": equipment_id, "floor_price_status": "approved"})
