import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import CustomerWorkspacePage from "../pages/CustomerWorkspacePage";
import DashboardPage from "../pages/DashboardPage";
import ConsultantPage from "../pages/ConsultantPage";
import ForbiddenPage from "../pages/ForbiddenPage";
import HomePage from "../pages/HomePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import PublicRoute from "./PublicRoute";
import RoleGuard from "./RoleGuard";
import WorkspacePage from "../pages/WorkspacePage";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/403" element={<ForbiddenPage />} />
        <Route path="/customer/workspace" element={<RoleGuard allow={["user", "customer", "consultant", "admin"]}><CustomerWorkspacePage /></RoleGuard>} />
        <Route path="/consultant" element={<RoleGuard allow={["consultant", "admin"]}><ConsultantPage /></RoleGuard>} />
        <Route path="/dashboard" element={<RoleGuard allow={["admin"]}><DashboardPage /></RoleGuard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
