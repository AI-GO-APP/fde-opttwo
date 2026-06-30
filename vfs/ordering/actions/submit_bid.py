"""回收商對某台設備投標（x_opt_bids）。由 ordering（external）app 呼叫。

驗證重點：external app 能否寫入 tenant 共用的 Custom Object。
case_id 由設備反查帶入（EAV 無外鍵，自己補關聯）。

params:
  equipment_id (必填)
  bid_amount   (必填)
  recycler_customer_id - 回收商 customers.id（選填；切片先可省略，預設用登入者 id）
"""
from datetime import datetime, timezone


def execute(ctx):
    p = ctx.params
    equipment_id = str(p.get("equipment_id") or "").strip()
    bid_amount = str(p.get("bid_amount") or "").strip()
    if not equipment_id or not bid_amount:
        ctx.response.json({"error": "equipment_id 與 bid_amount 為必填"})
        return

    # 反查設備取得 case_id（無 JOIN）
    all_equip = ctx.db.query_object("x_opt_equipment", limit=10000) or []
    eq = next((e for e in all_equip if str(e.get("id")) == equipment_id), None)
    if not eq:
        ctx.response.json({"error": f"找不到設備（id={equipment_id}）"})
        return

    uid = str(getattr(ctx, "user_id", "") or "")
    now = datetime.now(timezone.utc).isoformat()
    rec = ctx.db.insert_object(slug="x_opt_bids", data={
        "equipment_id": equipment_id,
        "case_id": str(eq.get("case_id") or ""),
        "recycler_customer_id": str(p.get("recycler_customer_id") or uid),
        "bid_amount": bid_amount,
        "status": "submitted",
        "payment_last5": "",
        "payment_deadline_at": "",
        "created_at": now,
        "migration_batch_id": "",
    })
    ctx.response.json({"success": True, "bid": rec})
