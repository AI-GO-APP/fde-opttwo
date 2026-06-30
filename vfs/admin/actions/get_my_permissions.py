"""回傳當前登入者（盤商員工）的有效權限。

權限模型（沿用 FDE-ReLoop）：
  - 指派：x_opt_permission_groups（user_id ↔ group_key）
  - 定義：x_opt_settings key='permission_groups' → {group_key: [perm_key,...]}
  - admin：屬於 group_key='admin' 者 bypass，拿全部權限。

注：平台沙盒不能跨 action import，故 _user_groups / _effective_perms 邏輯
   會在每支需判權的 action 內各自 inline 一份（與此處一致）。
"""
import json

ALL_PERMISSION_KEYS = [
    "view_all_cases", "set_floor_price", "approve_floor_price", "confirm_recommendations",
    "propose_winner", "approve_winner", "confirm_payment", "schedule_delivery",
    "complete_delivery", "close_case", "manage_recyclers", "manage_staff",
    "manage_workflow_parameters", "manage_permission_groups", "manage_line_templates",
    "view_case_financials",
]


def _user_groups(ctx, uid):
    rows = ctx.db.query_object("x_opt_permission_groups", limit=10000) or []
    return [str(r.get("group_key")) for r in rows if str(r.get("user_id")) == uid]


def _group_defs(ctx):
    rows = ctx.db.query_object("x_opt_settings", limit=10000) or []
    for r in rows:
        if r.get("key") == "permission_groups":
            try:
                return json.loads(r.get("value") or "{}")
            except (ValueError, TypeError):
                return {}
    return {}


def _effective(ctx, uid):
    groups = _user_groups(ctx, uid)
    is_admin = "admin" in groups
    if is_admin:
        return groups, True, {k: True for k in ALL_PERMISSION_KEYS}
    defs = _group_defs(ctx)
    granted = set()
    for g in groups:
        granted.update(defs.get(g, []))
    return groups, False, {k: (k in granted) for k in ALL_PERMISSION_KEYS}


def execute(ctx):
    uid = str(getattr(ctx, "user_id", "") or "")
    groups, is_admin, perms = _effective(ctx, uid)
    ctx.response.json({
        "user_id": uid,
        "groups": groups,
        "is_admin": is_admin,
        "permissions": perms,
    })
