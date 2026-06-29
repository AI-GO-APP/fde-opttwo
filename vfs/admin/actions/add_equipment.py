"""在案件下新增一台設備（x_opt_equipment），可同時設底價。

底價狀態機（沿用 FDE-ReLoop）：
  admin 填 → approved（直接生效）；非 admin 填 → pending（待 admin 核可）。
  此切片先用簡化版：有填 floor_price 即 pending，未填為 none。
  （Phase 2 再接 get_my_permissions 做完整 set/approve 權限判斷。）

params:
  case_id (必填)
  name, category, condition - 設備描述
  floor_price - 底價（選填）
"""
from datetime import datetime, timezone


def execute(ctx):
    p = ctx.params
    case_id = str(p.get("case_id") or "").strip()
    if not case_id:
        ctx.response.json({"error": "case_id 為必填"})
        return

    # 確認案件存在（EAV 無外鍵，需自己驗）
    cases = ctx.db.query_object("x_opt_cases", limit=10000) or []
    if not any(str(c.get("id")) == case_id for c in cases):
        ctx.response.json({"error": f"找不到案件（id={case_id}）"})
        return

    floor = str(p.get("floor_price") or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    uid = str(getattr(ctx.user, "id", "") or "")

    rec = ctx.db.insert_object(slug="x_opt_equipment", data={
        "case_id": case_id,
        "name": str(p.get("name") or ""),
        "category": str(p.get("category") or ""),
        "condition": str(p.get("condition") or ""),
        "floor_price": floor,
        "floor_price_status": "pending" if floor else "none",
        "floor_price_by": uid if floor else "",
        "floor_price_approved_by": "",
        "floor_price_updated_at": now if floor else "",
        "photos": "[]",
        "migration_batch_id": "",
    })
    ctx.response.json({"success": True, "equipment": rec})
