import { Routes, Route, Navigate } from "react-router-dom";
import HomePage from "./pages/HomePage";

// 回收商前台路由骨架。Phase 4 逐一補上：LINE 登入 / 註冊綁定 / 偏好設定 /
// 合約簽署 / 競標 / 付款資訊 / 交付狀態。
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
