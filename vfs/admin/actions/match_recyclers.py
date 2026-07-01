"""依案件的地區/設備分類，媒合符合的回收商，並渲染 LINE 通知文案。

媒合規則：
  回收商偏好（x_opt_recycler_pref）的 served_regions 含案件 region，
  且（categories 為空 = 不限）或與案件設備分類有交集 → 命中。

回傳 matched 清單（含 customer_id、命中原因、已渲染的通知訊息）。
注：實際 LINE 推送留待 Phase 4（需 LINE channel + 回收商 LINE 綁定）；
   此 action 先把「該通知誰、通知什麼文字」算好，發送是之後補的薄層。

params: case_id (必填)
"""
import json


def _load_json(s, default):
    try:
        v = json.loads(s) if s else default
        return v if isinstance(v, type(default)) else default
    except (ValueError, TypeError):
        return default


def _setting(ctx, key, default):
    for r in (ctx.db.query_object("x_opt_settings", limit=10000) or []):
        if r.get("key") == key:
            return _load_json(r.get("value"), default)
    return default


def execute(ctx):
    case_id = str(ctx.params.get("case_id") or "").strip()
    if not case_id:
        ctx.response.json({"error": "case_id 為必填"})
        return

    cases = ctx.db.query_object("x_opt_cases", limit=10000) or []
    case = next((c for c in cases if str(c.get("id")) == case_id), None)
    if not case:
        ctx.response.json({"error": f"找不到案件（id={case_id}）"})
        return
    region = str(case.get("region") or "").strip()

    equip = [e for e in (ctx.db.query_object("x_opt_equipment", limit=10000) or [])
             if str(e.get("case_id")) == case_id]
    case_cats = {str(e.get("category") or "").strip() for e in equip if e.get("category")}

    prefs = ctx.db.query_object("x_opt_recycler_pref", limit=10000) or []
    templates = _setting(ctx, "line_templates", {})
    msg_tpl = templates.get("match_notify", "")
    message = msg_tpl.format(region=region or "（未填）", count=len(equip))

    matched = []
    for pf in prefs:
        cond = _load_json(pf.get("accepted_conditions"), {})
        regions = cond.get("served_regions", []) or []
        cats = cond.get("categories", []) or []

        if region and region not in regions:
            continue
        if cats and case_cats and not (set(cats) & case_cats):
            continue
        matched.append({
            "customer_id": str(pf.get("customer_id") or ""),
            "reason": f"region={region} ∈ {regions}" + (f"; cats∩={sorted(set(cats) & case_cats)}" if cats and case_cats else ""),
            "message": message,
        })

    ctx.response.json({
        "success": True,
        "case_id": case_id,
        "region": region,
        "equipment_count": len(equip),
        "case_categories": sorted(case_cats),
        "matched_count": len(matched),
        "matched": matched,
        "notify_message": message,
        "note": "實際 LINE 發送待 Phase 4（LINE channel + 回收商綁定）",
    })
