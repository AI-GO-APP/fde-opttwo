def execute(ctx):
    """資料摘要 — 示範前後端 Action 協作"""
    from datetime import datetime
    from collections import Counter

    # 從前端傳入的參數取得 records
    records = ctx.params.get("records", [])

    # 統計各狀態數量
    status_list = []
    with_email = 0
    latest_name = "-"
    for r in records:
        data = r.get("data", r) if isinstance(r, dict) else {}
        status_list.append(data.get("status", "未分類"))
        if data.get("email"):
            with_email += 1
        latest_name = data.get("name", latest_name)

    status_counts = dict(Counter(status_list))

    # 回傳 JSON 給前端
    ctx.response.json({
        "total": len(records),
        "with_email": with_email,
        "latest_name": latest_name,
        "status_counts": status_counts,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
