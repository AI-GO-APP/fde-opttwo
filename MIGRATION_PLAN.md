# FDE-ReLoop → AIGO Custom App 搬遷規劃

> 目標：把 FDE-ReLoop（Supabase + 純 HTML 的設備回收媒合工具）搬遷成 AIGO 平台的 custom app，
> 結構與慣例參考 `fde-sc1984`。**全量搬進 AIGO、淘汰 Supabase。**
>
> 狀態：規劃已確認，待 Phase 0 平台能力驗證後動工。

---

## 0. 已確認的關鍵決策

1. **回收商（外部買方）→ 原生 `customers`**（LINE/統編/聯絡人存 `custom_data`）。
2. **退場商家（設備來源、賣方）→ 原生 `suppliers`**。
3. **案件得標後 → 生成原生 `sale_orders`(customer=回收商) + `account_payments`**，走 AIGO 原生收款/發票。
4. **全量搬進 AIGO**，Supabase 淘汰。

金流方向（解釋為何上面這樣分）：

```
退場商家 ──(整批廢機, 總包價)──▶ 盤商 ──(逐台競標賣出)──▶ 回收商
   賣方 / suppliers                             買方 / customers
```

- 毛利 = Σ(回收商得標金額) − 總包價（向退場商家收的整批價）
- 底價(floor_price) = 每台設備不得低於的賣價，確保總和 ≥ 總包價
- **sale_order 上只會出現回收商**，退場商家掛在案件層，不需要在 order/payment 加欄位區分。

---

## 1. 兩邊架構對照（為什麼不是直接複製）

| 面向 | FDE-ReLoop（現況） | AIGO Custom App（目標） |
|---|---|---|
| 前端 | 純 HTML + 原生 JS（單檔 5000 行） | React + TypeScript，上傳 `vfs/`，Shadow DOM 執行 |
| 後端邏輯 | Supabase Edge Functions (Deno/TS) | Python Server-Side Actions（沙盒，有完整 DB 寫權） |
| 資料庫 | 自有 Supabase Postgres + migration | Odoo 原生表(proxy) + `x_` 自訂表 + `custom_data` JSONB |
| 權限 | **大多在前端**（hasPermission 隱藏按鈕），RLS 待補 | 平台無 row-level security，**寫入/身分過濾一律走 action** |
| 認證 | Supabase Auth + 自寫 LINE OAuth function | 平台原生 Custom App 登入 + **原生 LINE OAuth** |
| 部署 | Docker + nginx + 環境變數注入 | `deploy_*.py` → 設 REFS → 上傳 VFS → compile → publish |

> **附帶效益**：AIGO 強制「寫入走 action 做身分驗證」，剛好補掉 FDE-ReLoop 目前「權限只在前端、開 console 就能繞過」的資安債。

---

## 2. 資料模型搬遷對照（核心）

原則（沿用 sc1984）：**能用 Odoo 原生表就貼合 → 1對1延伸屬性塞 `custom_data` → 真的沒有才建 `x_` 自訂表 → 設定類用 `x_app_settings`**。

> ⚠️ **關鍵前提（已從平台原始碼確認，見 §6）：AIGO 的「`x_` 表」不是實體 Postgres 表，而是平台的 Custom Object（EAV / JSONB 鍵值物件）。**
> 影響：
> - **沒有外鍵、沒有 SQL JOIN**。`x_recycling_cases` ↔ `x_equipment_listings` ↔ `x_recycler_bids` 的關聯只能存對方 id，**在 action 裡用 Python in-memory join**。
> - 這些物件**只能用 `ctx.db.query_object / insert_object / update_object`**，前端不能直接走 proxy 讀（會 500），要讀得透過 Custom Object records API（需 UUID）或 server-side action。
> - 查詢條件走 `data->>'key'`，沒有關聯式索引/查詢優化——資料量大時要在 action 內自己控分頁與篩選。
> - 好處：**部署腳本可程式化建立/drop**（`/data/objects/batch` 建、`/objects/{id}/promote` 設 app_id=null、`DELETE` 刪），不需平台方手動建表，回滾也能自動化。

| FDE-ReLoop 實體 | 對策 | 落點 | 理由 / 備註 |
|---|---|---|---|
| `dealer_accounts`（盤商內部員工） | 貼合 | `custom_app_users`(登入) + `hr_employees`(員工資料) | 內部帳號天然對應 |
| 回收商 `recycler_onboarding_accounts`（外部買方） | 貼合 | **`customers`** | line_user_id / 統編 / 聯絡人存 `custom_data` |
| 退場商家 `clients`（設備來源、賣方） | 貼合 | **`suppliers`** | 案件的設備來源 |
| `recycler_onboarding_preferences`（服務地區/設備分類偏好） | 半貼合 | 地區/分類用 `customer_tags`(驅動媒合)，其餘條款存 `x_recycler_preferences` | tag 機制本就用來驅動配對 |
| `cases`（案件＝一批待處理設備） | 自建 | `x_recycling_cases`（含 `supplier_id`→退場商家、`total_package_price` 總包價、`assigned_agent_id`） | 競標前無買方，不塞 sale_orders |
| `equipment_listings`（單台設備＋底價） | 自建 | `x_equipment_listings`（`case_id`, `floor_price`, `floor_price_status`, `floor_price_by`, `floor_price_approved_by`, `floor_price_updated_at`） | 二手單品非目錄商品 |
| 底價審核（主管填→admin審） | 貼合自建表欄位 | 做在 `x_equipment_listings` 欄位 + action 控權 | 沿用 none→pending→approved 狀態機 |
| `recycler_matches`（回收商投標/競標） | 自建 | `x_recycler_bids`（`equipment_id`/`case_id`, `recycler_customer_id`, `bid_amount`, `status`, `payment_last5`, `payment_deadline_at`） | 反向競標，Odoo 無原生對應 |
| 得標收款 | 貼合 | 得標後生成 `sale_orders`(customer=回收商) + `sale_order_lines` + `account_payments` | 走原生財務 |
| 付退場商家貨款（可選） | 貼合 | `purchase_orders`(supplier=退場商家) + outbound `account_payments` | 看商業上是否要記整批貨款 |
| `dealer_system_settings`（流程參數/權限組定義/LINE文案） | 貼合 | `x_app_settings`(key-value) | AIGO 就有這張 key-value 設定表 |
| `dealer_account_permission_groups`（權限組指派） | 自建 | `x_user_permission_groups`(`user_id`, `group_key`) | 沿用權限組模型，action 讀來判權 |
| `contracts` / `contract_templates`（委任同意書） | 自建 | `x_contracts` / `x_contract_templates` | 小型，自建乾淨 |
| `recycler_invites`（邀請連結） | 貼合 | 比照 sc1984 的 `x_invite_tokens` 模式 | sc1984 有現成邀請碼機制可抄 |
| `activity_logs`（審計） | 丟棄自建 | 平台原生 audit `/api/v1/audit`（自動記 CRUD） | 不用自己做 |

### 2.1 權限模型搬遷

沿用現有權限組設計（sales / supervisor / finance / delivery / operations + admin 全權）：

- 權限組「定義」（每組有哪些權限）→ `x_app_settings` 的 `permission_groups` key。
- 權限組「指派」（某 user 屬於哪些組）→ `x_user_permission_groups`。
- 判權邏輯由 action `get_my_permissions.py` 統一提供；前端 `hasPermission()` 保留控 UI 顯示，**真正關卡在 action 後端**。
- 關鍵權限 key 沿用：`view_all_cases`, `set_floor_price`, `approve_floor_price`, `confirm_recommendations`, `propose_winner`, `approve_winner`, `confirm_payment`, `schedule_delivery`, `complete_delivery`, `close_case`, `manage_recyclers`, `manage_staff`, `manage_workflow_parameters`, `manage_permission_groups`, `manage_line_templates`, `view_case_financials`。

### 2.2 LINE 整合搬遷

| 現況（Supabase function） | 搬遷對策 |
|---|---|
| `line-auth`（OAuth 登入/綁定） | **改用平台原生 LINE OAuth**（已確認 `custom_app_oauth.py` 完整實作 Web Flow + LIFF swap），function 刪除。LINE 身分綁到平台 `CustomAppUser`/`CustomAppUserIdentity`（provider_uid = LINE userId）；channel id/secret 設在 `CustomAppAuthProvider`。**注意：OAuth 只建 CustomAppUser，不會自動連到 customer**，回收商↔customer 連結要另用 action 建（比照 sc1984 redeem_invite_token）|
| `line-notify`（推播媒合/得標/付款/交付通知） | **優先用平台原生 `ctx.messaging`**（在 backend 直接打 LINE reply/push，最簡單）；若要自打 LINE Messaging API，則 outbound 須走 **egress gateway**（把 LINE 註冊成 EgressService 並授權/發布），token 放 `ctx.secrets`。文案模板存設定物件（見下）|

---

## 3. 前端搬遷對照（拆成兩個 app）

沿用 sc1984 的雙 app 結構：

| FDE-ReLoop HTML | → AIGO App | 對應 sc1984 範本 |
|---|---|---|
| `dealer_portal.html`（盤商後台, 5178 行） | **`vfs/admin/`** | Admin App（Tab + 子頁面、proxy 讀、action 寫） |
| `recycler_onboarding_v2.html`（回收商前台） | **`vfs/ordering/`** | Ordering App（流程式頁面、全程走 action、LINE 登入） |
| `index.html`（登入） | 併入兩 app 各自登入流程 | 平台 Custom App 登入 |
| `reloop_poc.html` | 丟棄（PoC） | — |

要逐一改寫的模組：設備管理、底價審核、案件/媒合、競標名單、付款確認、交付排程、權限/參數設定、人員管理、回收商管理、毛利彙總。

---

## 4. 分階段執行計畫

### Phase 0｜骨架與平台能力確認（先做、最重要）
- 建 repo 骨架：`vfs/admin`、`vfs/ordering`、`vfs/scripts`（`db_admin.py` / `db_ordering.py` / `deploy_*.py` / `deploy_lib.py`）、`ARCHITECTURE.md`、`AGENT_PLAN.md`、`.env`。
- 從 sc1984 抄 `deploy_lib.py`、`db.ts`、`action.ts`、SDK/CSS(Shadow DOM) 慣例。
- 跑通一個 Hello World app 的 部署→compile→publish 全鏈路。
- **完成 §6 平台能力驗證清單**後才進 Phase 1。

### Phase 1｜資料層落地
- 建立所有 `x_` 表；設定 `customer_tags`（地區/分類）。
- 把 `dealer_system_settings` 內容（流程參數、權限組定義、LINE 文案）灌進 `x_app_settings`。
- 在 `db_admin.py` / `db_ordering.py` 宣告 AppDataReference（表名複數、欄位白名單）。

### Phase 2｜後端 Actions（業務邏輯＋權限）
- 權限基礎：`get_my_permissions.py`
- 底價：`set_floor_price.py` / `approve_floor_price.py`（後端驗權、狀態機）
- 媒合：`match_recyclers.py`（依 tag 配對）→ `send_line_notify.py`
- 競標/得標：`submit_bid.py`、`propose_winner.py`、`approve_winner.py`（得標時生成 sale_order）
- 付款/交付：`confirm_payment.py`、`schedule_delivery.py`、`complete_delivery.py`
- 毛利彙總：`case_financial_summary.py`（後端驗 `view_case_financials`）

### Phase 3｜Admin 前端（盤商後台）
- 把 dealer_portal 各模組改寫成 React 頁面（Tab + 子頁面，路由驅動）。

### Phase 4｜Ordering 前端（回收商前台）
- 含原生 LINE 登入、註冊綁定、偏好、投標、合約簽署、交付狀態。

### Phase 5｜測試與上線
- 移植 `test/run.js` 的單元/整合測試（底價狀態機、毛利、LINE 模板）到 sc1984 的 Python `tests/` 模式。
- 重點驗收：**所有權限關卡在 action 後端確實生效**（資安債修補）。
- `--no-publish` 測 action → publish 上線。

---

## 5. 主要風險

- **EAV ↔ 關聯式的落差（最大風險）**：核心資料（案件→設備→競標）是高度關聯的，但 AIGO 自訂資料只有 EAV（無外鍵、無 JOIN、查詢走 `data->>'key'`）。所有跨物件關聯與彙總（毛利、媒合篩選、底價加總）都要在 action 內用 Python 自己組，且要顧分頁/效能。**這會明顯增加 action 層工作量，也是搬遷成敗關鍵**——建議先用一個「案件+設備+競標」的垂直切片驗證查詢與效能可行，再全量展開。
- **領域語意反向**：Odoo 是正向賣貨，FDE 是反向競標收廢機。核心案件/設備/競標只能用自建 Custom Object；貼合的主要是帳號、tag、收款、audit、LINE OAuth。
- **5000 行純 JS 沒有元件邊界**：改寫 React 工作量大，建議照模組逐塊搬、邊搬邊用測試守。
- **LINE outbound 路徑未定**：通知要走 `ctx.messaging`（backend 直打）還是 egress gateway（需註冊 EgressService）尚待實機確認（見 §6 Q4）。

---

## 6. Phase 0 平台能力確認（已從平台原始碼 `urfit-tech/AI-GO` 求證）

> 來源：`backend/app/` FastAPI 原始碼 + sc1984 用法佐證。除特別標 🔴/🟡 外皆有 file:line 證據。

| # | 項目 | 判定 | 結論（含關鍵實作位置） |
|---|---|---|---|
| 1 | x_ 表建/drop/promote | ✅ | **不是實體表，是 Custom Object（EAV）**。部署腳本可程式化：`POST /api/v1/data/objects/batch`(app_id=null) 建、`POST /objects/{id}/promote` 升 tenant 層、`DELETE /objects/{id}` 刪（`backend/app/api/custom_data.py`、`models/custom_data.py`）。action 用 `ctx.db.query_object`（`core/action_context.py:193`） |
| 2 | 原生 LINE OAuth | ✅ | 完整實作 Web Flow（authorize/callback、CSRF state、id_token HMAC 驗章）+ LIFF swap（`backend/app/api/custom_app_oauth.py`）。綁到 `CustomAppUser`/`CustomAppUserIdentity`；channel 設定在 `CustomAppAuthProvider`（secret AES 加密）。**line-auth function 可刪** |
| 3 | ctx.secrets | ✅ | `ctx.secrets.get/list_keys` 唯讀（`action_context.py:1536/591`），KMS envelope 加密，`/secrets` CRUD 端點齊（`api/action.py:440+`），解密留 backend |
| 4 | sandbox / outbound | 🟡 | 有 timeout（預設 30s，`infra/runner/runner/sandbox.py`、`server.py:142`）、記憶體僅 advisory。**outbound 要走 egress gateway 並把 LINE 註冊成 EgressService**（`api/connector_proxy.py`、SSRF 防護 `core/egress_http.py`）；或改用 backend 端 `ctx.messaging`（`action_context.py:1289`）。🔴 pod network policy manifest 未在 repo 讀到，需實機/平台方確認 |
| 5 | customers/suppliers 寫入 | ✅ | 兩張獨立實體表（`models/client.py:75`、`supplier.py:12`，對應 res.partner），有 `custom_data` JSONB。外部 app 經 ext/proxy 或 action 在 AppDataReference 授權下可建（`api/app_data_proxy.py:551`） |
| 6 | sale_orders/account_payments | ✅ | 必填極少（SO: date_order；payment: payment_type/amount/date，`models/sale.py:142`、`account.py:342`）。權限看 AppDataReference；狀態轉換有 trigger 自動化（draft→sale 自動編號+建出庫 picking，`triggers/sale_triggers.py:198`） |
| 7 | 設定承載（原 x_app_settings） | 🟡 | **平台無原生 KV 設定機制**（grep 零筆）；sc1984 的 x_app_settings 是租戶自建 Custom Object。前端不能 proxy 讀（500），要走 records API 或 action。→ 我們的流程參數/權限組定義/LINE 文案照樣用一個自建 Custom Object 承載 |
| 8 | 原生 audit | 🟡 | DB Trigger 稽核（`alembic/.../k2b3c4d5e6f7_*.py`→`audit_logs`，`models/audit.py`）。custom_records 在稽核清單內 → **x_ 物件 CRUD 會被記**，可取代 activity_logs。但逐表掛 trigger 由 `backend/scripts/migrate_audit_triggers.py` 負責、非預設部署鏈自動跑 |
| 9 | AppDataReference 授權 | ✅ | 實體表欄位/CRUD 白名單 + dev/published 雙快照（`models/custom_app.py:103`、`api/app_references.py`、執行期 `api/app_data_proxy.py`）。`published_columns`=發布快照，線上路徑讀它 |

**仍需跟平台方拿 / 實機確認的（無法從 repo 得到）：**
- 兩個 custom app 的 `ADMIN_APP_ID`/`ORDERING_APP_ID`、slug、`AIGO_EMAIL`/`AIGO_PASSWORD`（`.env`，repo 內 gitignored）。
- Q4 runner pod 的實際 network egress policy（決定 action 能否、或須經 gateway 才能打 LINE）。
- 平台是否願意/如何替我們把 LINE 註冊成 EgressService（若走 egress gateway 路線）。

---

## 7. 搬遷回滾策略（三層）

> AIGO 與原本 Supabase 不同：**多個 custom app 共用同一個 tenant DB**（sc1984 的 admin/ordering 就共用一份 Odoo 資料）。
> 因此回滾**絕不能**用「清空 customers」這類粗暴手法——只能精準移除「這次搬遷新增的東西」。
> 細節取決於 Phase 0 §6-1（x_ 表由誰建、能否 drop），以下為骨架，待驗證後填實。

### 7.1 三層回滾對象

| 層 | 回滾對象 | 做法 | 風險 |
|---|---|---|---|
| **① 前端 / App** | VFS 上傳、publish 的版本快照 | unpublish 或 revert 到前一個 snapshot（`deploy_lib.py` 已有版本概念）。**不動資料，最安全** | 低 |
| **② Schema / 設定** | 新建的 `x_` 表、AppDataReference(REFS)、灌進 `x_app_settings` 的 key、新增的 `customer_tags` | `rollback_schema.py`：drop x_ 表、刪 REFS、刪掉本次新增的 settings key / tags | 中 |
| **③ 資料** | 從 Supabase 匯入到 `customers`/`suppliers`/`x_` 表的那批資料 | `rollback_data.py`：依**批次標記**精準刪除本次匯入列 | 高 |

### 7.2 安全回滾的關鍵：批次標記（batch_id）

第 ③ 層能否安全回滾，完全取決於匯入時有沒有打標記。

- **匯入時**：每一筆搬進去的列都寫 `custom_data.migration_batch_id = "reloop-<yyyymmdd>"`（x_ 表同理加一個欄位或 custom_data）。
- **回滾時**：只刪 `migration_batch_id == 本次批次` 的列，平台上其他 app 的既有資料完全不受影響。
- **驗收**：回滾前先 count 一次本批次列數，回滾後該批次列數應為 0，且其他 app 既有資料筆數不變。

### 7.3 原生財務單據要特別小心

- 一旦得標流程生成了真實的 `sale_orders` / `account_payments`，回滾可能牽動帳務。
- **建議**：搬遷期間先全程用測試資料；正式資料另立一個 cutover 步驟，與測試階段分開。
- 財務單據回滾優先用「作廢/取消狀態」而非硬刪，保留稽核軌跡（平台原生 audit 會留底）。

### 7.4 腳本骨架

```
vfs/scripts/
  rollback_app.py       # ① 回滾 VFS/publish 到前一版快照
  rollback_schema.py    # ② drop x_ 表、刪 REFS、移除本次 x_app_settings key / customer_tags
  rollback_data.py      # ③ 依 migration_batch_id 精準刪除匯入列；財務單據改作廢
```

執行順序與正向部署相反：**③ 資料 → ② Schema → ① App**（先撤資料再撤結構，最後才換回前端）。
每支腳本都接受 `--batch-id` 與 `--dry-run`（先印出將影響的筆數，確認後才真的執行）。

### 7.5 Phase 0 確認後的回滾定案

- ✅ **x_（Custom Object）可程式化 drop**：`DELETE /api/v1/data/objects/{id}` 連帶 cascade 刪欄位與記錄 → ② Schema 層回滾可全自動，不需平台方手動。
- ✅ **audit 涵蓋 custom_records**（x_ 物件 CRUD 會被記）→ 回滾後可用 audit 查核「確實只動了本批次」。但要先確認 audit trigger 已掛（非預設部署鏈自動跑）。
- 🟡 **財務單據作廢**：`account_payments.state` 有 `cancel`、sale_orders 有狀態機 → ③ 的財務回滾用「轉 cancel 狀態」而非硬刪，保留稽核。實際可轉路徑待 Phase 2 試作確認。
- ⚠️ **EAV 沒有外鍵 cascade**：刪 `x_recycling_cases` 不會自動刪它底下的 `x_equipment_listings`/`x_recycler_bids`（沒有 FK）。`rollback_data.py` 要**自己依 batch_id 逐物件清**，不能靠資料庫 cascade。

---

## 附錄：來源 repo 重點檔案

**FDE-ReLoop（被搬遷方）**
- `dealer_portal.html`：盤商後台全模組
- `recycler_onboarding_v2.html`：回收商前台
- `supabase/migrations/*.sql`：權限組、底價、LINE 文案 RLS
- `supabase/functions/line-auth|line-notify`：LINE 整合
- `test/run.js`：冒煙/單元/整合測試

**fde-sc1984（AIGO 範本）**
- `ARCHITECTURE.md`：資料模型/API/前端聖經（決策前必讀）
- `.claude/CLAUDE.md`：部署流程、SDK 限制、已知陷阱
- `vfs/scripts/db_admin.py` / `db_ordering.py`：AppDataReference REFS 定義
- `vfs/scripts/deploy_lib.py`：登入/REFS/上傳/發布
- `.agent/skills/`：aigo-db-access / call-ai-go / ctx-db-query-patterns
- `demo/`：官方 SDK 參考（唯讀）
