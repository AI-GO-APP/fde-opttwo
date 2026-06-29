import { Routes, Route, Navigate } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";

// 盤商後台路由骨架。Phase 3 逐一補上：設備管理 / 底價審核 / 案件媒合 /
// 競標名單 / 付款確認 / 交付排程 / 權限參數設定 / 人員管理 / 回收商管理 / 毛利彙總。
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/admin" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}
