# AGENT_PLAN — Opttwo 待辦與優先序

詳細搬遷規劃見 `MIGRATION_PLAN.md`。本檔追蹤執行進度。

## Phase 0 — 骨架與平台能力確認
- [x] 讀懂 FDE-ReLoop / fde-sc1984 / AI-GO 平台原始碼
- [x] 寫搬遷規劃 `MIGRATION_PLAN.md`
- [x] 從平台原始碼確認 Phase 0 九題能力（見 MIGRATION_PLAN §6）
- [x] 建 repo 骨架（vfs/admin、vfs/ordering、vfs/scripts、部署管線、docs）
- [ ] **向平台方索取**：`AIGO_EMAIL/PASSWORD`、`ADMIN_APP_ID`、`ORDERING_APP_ID`
- [ ] 確認 pod egress policy（action 能否打 LINE，或須走 ctx.messaging / egress gateway）
- [ ] 跑通一次空骨架 deploy（上傳→compile→publish）驗證管線

## Phase 1 — 資料層落地
- [ ] 跑 `create_reloop_objects.py` 實機建 x_opt_* 自訂物件（確認欄位/型別）
- [ ] 建 customer_tags（地區、設備分類）
- [ ] 灌入 x_opt_settings：流程參數、權限組定義、LINE 文案
- [ ] 確認 db_admin.py / db_ordering.py REFS 在實機可建立

## Phase 2 — 後端 Actions（含後端權限）
- [ ] `get_my_permissions`（讀 x_opt_permission_groups + x_opt_settings）
- [ ] 底價：`set_floor_price` / `approve_floor_price`（狀態機 none→pending→approved）
- [ ] 媒合：`match_recyclers`（依 tag）→ `send_line_notify`
- [ ] 競標/得標：`submit_bid` / `propose_winner` / `approve_winner`（得標生成 sale_order）
- [ ] 付款/交付：`confirm_payment` / `schedule_delivery` / `complete_delivery`
- [ ] 毛利彙總：`case_financial_summary`（後端驗 view_case_financials）
- [ ] **垂直切片優先**：先做「案件+設備+競標」一條龍，驗 EAV in-memory join 與效能

## Phase 3 — Admin 前端（盤商後台）
- [ ] 設備管理 / 底價審核 / 案件媒合 / 競標名單 / 付款確認 / 交付排程
- [ ] 權限與參數設定 / 人員管理 / 回收商管理 / 毛利彙總

## Phase 4 — Ordering 前端（回收商前台）
- [ ] 原生 LINE 登入 / 註冊綁定 / 偏好設定 / 合約簽署 / 競標 / 付款資訊 / 交付狀態

## Phase 5 — 測試與上線
- [ ] 移植 FDE-ReLoop test/run.js 的單元/整合測試到 Python tests/
- [ ] 驗收：所有權限關卡在 action 後端確實生效
- [ ] 回滾腳本：rollback_app / rollback_schema / rollback_data（帶 --dry-run）
- [ ] cutover：正式資料匯入（打 migration_batch_id）

## 待平台方/實機確認（阻塞項）
- APP_ID × 2、AIGO 帳密
- pod egress policy / LINE EgressService 註冊方式
- x_opt_* 欄位型別是否支援 number/date（目前全 text）
- audit trigger 是否已對 custom_records 掛載
