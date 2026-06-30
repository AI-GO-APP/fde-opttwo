# CLAUDE.md — Opttwo Custom App 開發規範

Opttwo 是把 FDE-ReLoop（設備回收媒合工具）搬遷到 AIGO custom app 平台的版本。
結構與慣例參考 sibling app `fde-sc1984`。搬遷規劃見 `MIGRATION_PLAN.md`，
資料模型見 `ARCHITECTURE.md`，待辦見 `AGENT_PLAN.md`。

## 工作流程鐵則（每次變更都要遵守）

1. **每個變更都要「測通」再「commit」**：寫完 action/腳本，一定要實機跑測試（如 test_slice.py / test_permissions.py）確認全綠，才 commit + push。沒測過不 commit。
2. **逐路徑 git add，絕不 `git add -A`**：此資料夾有並行的「官網」工作會長出新檔（已 gitignore，但仍逐檔 add 最保險）。
3. 新功能盡量附對應測試腳本（放 vfs/scripts/test_*.py），讓回歸可重跑。

## 專案結構

```
vfs/
  admin/      ← 盤商後台前端（TSX/TS）+ actions/（Python）
  ordering/   ← 回收商前台前端 + actions/
  scripts/
    deploy_lib.py            ← 共用部署函式（照 AIGO 慣例，勿亂改）
    db_admin.py              ← Admin AppDataReference（SSOT，只列實體表）
    db_ordering.py           ← Ordering AppDataReference（SSOT）
    deploy_admin.py / deploy_ordering.py  ← 部署入口
    create_reloop_objects.py ← 建立 x_opt_* Custom Object（EAV）
```

## 部署

```bash
set -a && source .env && set +a
python3 vfs/scripts/create_reloop_objects.py   # 首次：建自訂物件
python3 vfs/scripts/deploy_admin.py            # 上傳 + 發布
python3 vfs/scripts/deploy_ordering.py
```

開發期測 action 不發布：`deploy_*.py --no-publish` 後用
`POST /api/v1/actions/apps/{app_id}/execute-by-name?action_name=xxx&use_dev=true`。

## 鐵則（搬遷最重要的幾條）

1. **x_opt_* 不是資料表，是 Custom Object（EAV/JSONB）**：沒有外鍵、沒有 JOIN。
   - action 內用 `ctx.db.query_object / insert_object / update_object`；
   - 前端用 `db.ts` 的 `queryCustom`（走 /data/objects/{uuid}/records）；
   - **禁止**對 x_opt_* 走 proxy / ext_proxy（會 500）。
   - 跨物件關聯（案件→設備→競標、毛利彙總）在 action 內用 Python in-memory join。
2. **權限在後端**：所有寫入、需身分過濾的讀取一律走 server-side action 做權限檢查。
   前端 `hasPermission` 只控 UI 顯示，不是安全邊界（這是要修掉 Supabase 版資安債的重點）。
3. **資料隔離**：每筆搬遷/業務資料帶 `migration_batch_id`，供回滾精準清除（EAV 無 FK cascade）。
4. **LINE**：登入用平台原生 LINE OAuth（`/custom-app-oauth/{slug}/line/...`）；
   推播優先用 `ctx.messaging`，否則走 egress gateway（需把 LINE 註冊成 EgressService）。
5. **Shadow DOM**：CSS 變數用 `:host, :root` 雙選擇器；禁用原生 alert/confirm/prompt。

## ctx.db 方法（實測，見 fde-sc1984 .agent/skills/aigo-db-access.md）

| 方法 | 用途 |
|------|------|
| `ctx.db.query(table)` | 標準 Odoo 實體表；x_ 不可用 |
| `ctx.db.query_object(slug)` | x_opt_* Custom Object（回 flat dict） |
| `ctx.db.insert/update(table, ...)` | 實體表 |
| `ctx.db.insert_object/update_object(slug, ...)` | Custom Object |
| `ctx.db.remove(table, id)` | 硬刪（方法名是 remove） |

## 參考

- 平台原始碼（唯讀研究用）：`urfit-tech/AI-GO`
- 範本 app：`fde-sc1984`（結構、deploy_lib、db.ts、action 寫法的範本）
