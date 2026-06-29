"""Opttwo Admin（盤商後台）AppDataReference 宣告 — SSOT。

只列「平台既有實體表」。自訂資料（x_opt_* Custom Object）不在這裡宣告，
它們由 create_reloop_objects.py 建立，action 用 ctx.db.query_object 存取、
前端用 /data/objects/{uuid}/records 存取（皆不走 AppDataReference）。

搬遷對照（見 ARCHITECTURE.md / MIGRATION_PLAN.md）：
  回收商(買方)   → customers
  退場商家(賣方) → suppliers
  盤商員工       → hr_employees / custom_app_users
  得標收款       → sale_orders / sale_order_lines / account_payments
  地區/設備分類  → customer_tags
"""
REFS = [
    # 回收商（外部買方）
    {"table_name": "customers",            "columns": ["id", "name", "email", "phone", "vat", "customer_type", "ref", "contact_address", "custom_data", "salesperson_id", "is_company", "active"], "permissions": ["read", "create", "update", "delete"]},
    # 退場商家（設備來源、賣方）
    {"table_name": "suppliers",            "columns": ["id", "name", "ref", "phone", "contact_address", "vat", "status", "supplier_type", "active", "contact_person", "email", "custom_data"], "permissions": ["read", "create", "update"]},
    # 得標後生成的銷售/收款單據
    {"table_name": "sale_orders",          "columns": ["id", "name", "state", "date_order", "customer_id", "note", "amount_untaxed", "amount_tax", "amount_total", "client_order_ref", "created_at"], "permissions": ["read", "create", "update", "delete"]},
    {"table_name": "sale_order_lines",     "columns": ["id", "order_id", "product_id", "product_template_id", "product_uom_qty", "price_unit", "name", "price_subtotal", "sequence", "custom_data"], "permissions": ["read", "create", "update", "delete"]},
    {"table_name": "account_payments",     "columns": ["id", "payment_type", "partner_type", "amount", "date", "ref", "memo", "state", "customer_id", "custom_data", "created_at"], "permissions": ["read", "create", "update"]},
    # 盤商內部員工
    {"table_name": "hr_employees",         "columns": ["id", "name", "active", "job_title", "mobile_phone", "department_id", "work_email", "user_id"], "permissions": ["read", "create", "update"]},
    {"table_name": "hr_departments",       "columns": ["id", "name", "active"], "permissions": ["read", "create", "update"]},
    {"table_name": "custom_app_users",     "columns": ["id", "email", "display_name"], "permissions": ["read"]},
    # 地區 / 設備分類（驅動媒合）
    {"table_name": "customer_tags",        "columns": ["id", "name", "active", "custom_data"], "permissions": ["read", "create", "update", "delete"]},
    # 帳號↔customer 代表關係
    {"table_name": "customer_custom_app_user_rel", "columns": ["id", "customer_id", "custom_app_user_id", "role"], "permissions": ["read", "create", "update", "delete"]},

    # TODO(Phase 0 驗證)：sc1984 把 x_ Custom Object 也列進 REFS（如 x_app_settings），
    # 但平台 proxy 對 x_ 物件回 500。先不列，改用 data-objects API / query_object。
    # 若實機確認 admin proxy 對 x_ 物件可行，再補。
]
