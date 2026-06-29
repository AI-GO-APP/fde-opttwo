# ARCHITECTURE — Opttwo 資料模型 SSOT

搬遷決策與分階段見 `MIGRATION_PLAN.md`。本檔是**實作時的資料層單一事實來源**。

## 平台原生表（走 proxy / action，宣告於 db_admin.py / db_ordering.py）

| 用途 | 表 | 關鍵欄位 / 約定 |
|---|---|---|
| 回收商（買方） | `customers` | LINE 身分綁平台 CustomAppUser；統編/聯絡人存 `custom_data` |
| 退場商家（賣方/設備來源） | `suppliers` | 案件的設備來源 |
| 盤商員工 | `hr_employees` + `custom_app_users` | 內部帳號 |
| 得標收款 | `sale_orders` / `sale_order_lines` / `account_payments` | customer=回收商；draft→sale 有 trigger 自動建出庫單 |
| 地區 / 設備分類 | `customer_tags` | 驅動媒合 |
| 帳號↔customer 代表關係 | `customer_custom_app_user_rel` | role: orderer/viewer |

## 自訂物件（Custom Object / EAV，x_opt_ 前綴）

> ⚠️ 非實體表、無外鍵、無 JOIN。action 用 `query_object/insert_object/update_object`，
> 前端用 `queryCustom`。關聯只存對方 id，跨物件彙總在 action 內 Python join。
> 由 `vfs/scripts/create_reloop_objects.py` 建立（欄位型別目前全 text）。

| 物件 | 角色 | 主要欄位 |
|---|---|---|
| `x_opt_cases` | 案件 | supplier_id, assigned_agent_id, total_package_price, estimate_price, formal_price, status, site_address, region, migration_batch_id |
| `x_opt_equipment` | 設備（含底價） | case_id, name, category, condition, **floor_price, floor_price_status(none/pending/approved), floor_price_by, floor_price_approved_by, floor_price_updated_at**, photos, migration_batch_id |
| `x_opt_bids` | 回收商競標 | equipment_id, case_id, recycler_customer_id, bid_amount, status, payment_last5, payment_deadline_at, migration_batch_id |
| `x_opt_settings` | 系統設定(KV) | key, value(JSON), updated_at（流程參數 / 權限組定義 / LINE 文案） |
| `x_opt_permission_groups` | 權限組指派 | user_id, group_key, assigned_by |
| `x_opt_recycler_pref` | 回收商偏好補充 | customer_id, accepted_conditions, custom |
| `x_opt_contracts` | 委任同意書 | customer_id, template_key, signed_at, signature_img, status |
| `x_opt_contract_templates` | 合約範本 | key, title, body, version |
| `x_opt_invite_tokens` | 邀請連結 | token, role, target, expires_at, redeemed_at |

## 核心商業規則

- **金流**：退場商家 ─(總包價)→ 盤商 ─(逐台競標)→ 回收商。
- **底價狀態機**：主管填 → `pending`（待審）；admin 填 → 直接 `approved`；admin 核可 pending → `approved`。
- **毛利** = Σ(回收商得標金額) − 案件 total_package_price。底價確保每台不低於某價、總和 ≥ 總包價。
- **權限**：sales / supervisor / finance / delivery / operations + admin 全權；
  權限 key 沿用 FDE-ReLoop（view_all_cases、set_floor_price、approve_floor_price、
  confirm_payment、view_case_financials… 等）。判權走 action，前端只控顯示。

## 平台原生能力（取代 FDE-ReLoop 自建）

| 需求 | 平台原生 |
|---|---|
| 回收商登入 | LINE OAuth（`custom_app_oauth.py`）→ 取代自寫 line-auth |
| 稽核 | DB Trigger → `audit_logs`（含 custom_records）→ 取代 activity_logs |
| secrets | `ctx.secrets`（KMS 加密）→ 放 LINE token |
| 授權 | AppDataReference（dev/published 雙快照） |
