"""讀取單一案件的完整明細：案件 + 其設備 + 各設備競標，並算毛利。

這是「EAV 無 JOIN」的核心驗證：x_opt_cases / x_opt_equipment / x_opt_bids
三個 Custom Object 沒有外鍵、不能 JOIN，必須各自 query_object 後在 Python
用 case_id / equipment_id 做 in-memory join 與彙總。

毛利 = Σ(每台設備的最高出價) − 案件 total_package_price
底價加總 = Σ(floor_price)

params:
  case_id (必填)
"""


def _num(v):
    try:
        return float(str(v).strip())
    except (ValueError, AttributeError):
        return 0.0


def execute(ctx):
    p = ctx.params
    case_id = str(p.get("case_id") or "").strip()
    if not case_id:
        ctx.response.json({"error": "case_id 為必填"})
        return

    cases = ctx.db.query_object("x_opt_cases", limit=10000) or []
    case = next((c for c in cases if str(c.get("id")) == case_id), None)
    if not case:
        ctx.response.json({"error": f"找不到案件（id={case_id}）"})
        return

    # 無 JOIN：全撈再依 case_id / equipment_id 在 Python 過濾
    all_equip = ctx.db.query_object("x_opt_equipment", limit=10000) or []
    all_bids = ctx.db.query_object("x_opt_bids", limit=10000) or []
    equip = [e for e in all_equip if str(e.get("case_id")) == case_id]
    bids = [b for b in all_bids if str(b.get("case_id")) == case_id]

    # 每台設備的最高出價（in-memory join：bid.equipment_id → equipment.id）
    bids_by_equip = {}
    for b in bids:
        eid = str(b.get("equipment_id"))
        bids_by_equip.setdefault(eid, []).append(b)

    total_floor = 0.0
    total_best_bid = 0.0
    equip_out = []
    for e in equip:
        eid = str(e.get("id"))
        floor = _num(e.get("floor_price"))
        total_floor += floor
        ebids = bids_by_equip.get(eid, [])
        best = max((_num(b.get("bid_amount")) for b in ebids), default=0.0)
        total_best_bid += best
        equip_out.append({
            "id": eid,
            "name": e.get("name"),
            "floor_price": floor,
            "floor_price_status": e.get("floor_price_status"),
            "bid_count": len(ebids),
            "best_bid": best,
        })

    package = _num(case.get("total_package_price"))
    margin = total_best_bid - package

    ctx.response.json({
        "success": True,
        "case": {
            "id": case_id,
            "status": case.get("status"),
            "total_package_price": package,
            "region": case.get("region"),
        },
        "equipment_count": len(equip),
        "bid_count": len(bids),
        "total_floor_price": total_floor,
        "total_best_bid": total_best_bid,
        "margin": margin,                       # 毛利 = Σ最高出價 − 總包價
        "floor_vs_package": total_floor - package,  # 底價加總 vs 總包價（軟提醒用）
        "equipment": equip_out,
    })
