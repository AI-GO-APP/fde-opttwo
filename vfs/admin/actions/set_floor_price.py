"""設定某台設備的底價（x_opt_equipment）。後端權限把關（補 Supabase 版前端權限的資安債）。

狀態機（沿用 FDE-ReLoop）：
  admin 填 → approved（直接生效，approved_by = 自己）
  有 set_floor_price 權限的非 admin（主管）填 → pending（待 admin 核可）
  無權限 → 拒絕

params: equipment_id (必填), floor_price (必填)
"""
import json
from datetime import datetime, timezone

ALL_PERMISSION_KEYS = [
    "view_all_cases", "set_floor_price", "approve_floor_price", "confirm_recommendations",
    "propose_winner", "approve_winner", "confirm_payment", "schedule_delivery",
    "complete_delivery", "close_case", "manage_recyclers", "manage_staff",
    "manage_workflow_parameters", "manage_permission_groups", "manage_line_templates",
    "view_case_financials",
]


def _can(ctx, uid, perm):
    """回傳 (is_admin, allowed)。admin bypass 一切。"""
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
    p = ctx.params
    equipment_id = str(p.get("equipment_id") or "").strip()
    floor = str(p.get("floor_price") or "").strip()
    if not equipment_id or not floor:
        ctx.response.json({"error": "equipment_id 與 floor_price 為必填"})
        return

    uid = str(getattr(ctx, "user_id", "") or "")
    is_admin, allowed = _can(ctx, uid, "set_floor_price")
    if not allowed:
        ctx.response.json({"error": "無權限設定底價（需 set_floor_price）", "code": "forbidden"})
        return

    eq = next((e for e in (ctx.db.query_object("x_opt_equipment", limit=10000) or [])
               if str(e.get("id")) == equipment_id), None)
    if not eq:
        ctx.response.json({"error": f"找不到設備（id={equipment_id}）"})
        return

    now = datetime.now(timezone.utc).isoformat()
    status = "approved" if is_admin else "pending"
    ctx.db.update_object(slug="x_opt_equipment", record_id=equipment_id, data={
        "floor_price": floor,
        "floor_price_status": status,
        "floor_price_by": uid,
        "floor_price_approved_by": uid if is_admin else "",
        "floor_price_updated_at": now,
    })
    ctx.response.json({"success": True, "equipment_id": equipment_id,
                       "floor_price": floor, "floor_price_status": status})
