import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { useAuth } from "../features/auth/AuthProvider";
import type { Role } from "../types/api";
import { AppProviders } from "./providers";

const LoginPage = lazy(() => import("../pages/LoginPage"));
const EmployeeHomePage = lazy(() => import("../pages/EmployeeHomePage"));
const CatalogPage = lazy(() => import("../pages/CatalogPage"));
const TrainingPlayerPage = lazy(() => import("../pages/TrainingPlayerPage"));
const QuizPage = lazy(() => import("../pages/QuizPage"));
const AdminDashboardPage = lazy(() => import("../pages/admin/AdminDashboardPage"));
const AdminTrainingsPage = lazy(() => import("../pages/admin/AdminTrainingsPage"));
const AdminTrainingEditorPage = lazy(() => import("../pages/admin/AdminTrainingEditorPage"));
const AdminUsersPage = lazy(() => import("../pages/admin/AdminUsersPage"));

function RouteFallback() {
  return (
    <main className="route-fallback" aria-busy="true" aria-label="Carregando Workflix">
      <div className="brand-mark" aria-hidden="true">
        W
      </div>
      <span>Preparando seu espaço…</span>
    </main>
  );
}

function Protected({ role }: { role: Role }) {
  const { user, loading } = useAuth();
  if (loading) return <RouteFallback />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/app"} replace />;
  }
  return <Outlet />;
}

function Shell() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

function ApplicationRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Protected role="EMPLOYEE" />}>
          <Route element={<Shell />}>
            <Route path="/app" element={<EmployeeHomePage />} />
            <Route path="/app/catalog" element={<CatalogPage />} />
            <Route path="/app/training/:trainingId" element={<TrainingPlayerPage />} />
            <Route path="/app/training/:trainingId/quiz" element={<QuizPage />} />
          </Route>
        </Route>
        <Route element={<Protected role="ADMIN" />}>
          <Route element={<Shell />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/trainings" element={<AdminTrainingsPage />} />
            <Route path="/admin/trainings/:trainingId" element={<AdminTrainingEditorPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
}

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <ApplicationRoutes />
      </BrowserRouter>
    </AppProviders>
  );
}
