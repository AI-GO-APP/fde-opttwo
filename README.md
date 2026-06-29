# Opttwo — 設備回收媒合（AIGO Custom App）

把 **FDE-ReLoop**（Supabase + 純 HTML 的設備回收媒合工具）搬遷到 **AIGO custom app** 平台的版本。
站點正式名稱：**Opttwo**。結構參考 sibling app `fde-sc1984`。

## 這是什麼

設計公司進案場時同步處理舊設備回收：
- **退場商家**（賣方）有一批待處理設備 → 盤商以「總包價」承接。
- 盤商把設備逐台上架、設底價，依地區/分類媒合 **回收商**（買方），回收商競標。
- 盤商選定得標者 → 收款 → 排程拉貨交付。
- 毛利 = Σ(回收商得標金額) − 總包價。

## 兩個 Custom App

| App | 對象 | VFS 目錄 |
|-----|------|---------|
| Admin（盤商後台） | 盤商內部員工 | `vfs/admin/` |
| Ordering（回收商前台） | 外部回收商 | `vfs/ordering/` |

## 文件

- `MIGRATION_PLAN.md` — 搬遷規劃（對照表、分階段、三層回滾、Phase 0 平台能力確認）
- `ARCHITECTURE.md` — 資料模型對照與 SSOT
- `AGENT_PLAN.md` — 待辦與優先序
- `.claude/CLAUDE.md` — 開發規範與鐵則

## 快速開始

```bash
cp .env.example .env          # 填入 AIGO 帳密與兩個 APP_ID（向平台方索取）
set -a && source .env && set +a
python3 vfs/scripts/create_reloop_objects.py   # 首次：建 x_opt_* 自訂物件
python3 vfs/scripts/deploy_admin.py
python3 vfs/scripts/deploy_ordering.py
```

## 現況

🚧 **骨架階段**。已完成：搬遷規劃、Phase 0 平台能力確認（從平台原始碼）、repo 骨架與部署管線。
未完成：自訂物件實機建立、business actions、前端各模組、測試。下一步見 `AGENT_PLAN.md`。
