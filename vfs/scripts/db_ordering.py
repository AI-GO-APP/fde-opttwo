"""Opttwo Ordering（回收商前台）AppDataReference 宣告 — SSOT。

Ordering 走 /ext/proxy/（published 快照）。原則：
  - 純公開讀取可走 proxy；
  - 寫入、需身分過濾的讀取一律走 server-side action（平台 proxy 無 row-level security）。
  - 禁止前端直接對 x_opt_* Custom Object 走 ext/proxy（回 500），改走 action 或 data-objects API。

回收商前台會用到的最小集合（多數操作其實走 action）：
"""
REFS = [
    # 回收商自己的帳號（受身分過濾，實務多走 action；此處保留唯讀供公開欄位顯示）
    {"table_name": "customers",      "columns": ["id", "name", "phone", "vat", "contact_address", "custom_data", "active"], "permissions": ["read"]},
    # 地區 / 設備分類（偏好設定用，公開讀）
    {"table_name": "customer_tags",  "columns": ["id", "name", "active", "custom_data"], "permissions": ["read"]},

    # 競標、得標、合約、交付等寫入操作 → 一律走 action（submit_bid / accept_contract / ...），
    # 不在這裡開 create/update 權限，避免前端繞過業務規則直接寫表。
]
