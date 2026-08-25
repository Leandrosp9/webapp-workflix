import {
  BarChart3,
  Award,
  BookOpen,
  ChevronDown,
  GraduationCap,
  Home,
  LogOut,
  Menu,
  Route,
  FileText,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import type { PropsWithChildren } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";
import { Brand } from "./Brand";

const employeeNavigation = [
  { to: "/app", label: "Início", icon: Home },
  { to: "/app/catalog", label: "Meus treinamentos", icon: GraduationCap },
  { to: "/app/paths", label: "Minhas trilhas", icon: Route },
  { to: "/app/certificates", label: "Certificados", icon: Award },
];

const adminNavigation = [
  { to: "/admin", label: "Visão geral", icon: BarChart3 },
  { to: "/admin/trainings", label: "Treinamentos", icon: BookOpen },
  { to: "/admin/paths", label: "Trilhas", icon: Route },
  { to: "/admin/users", label: "Colaboradores", icon: Users },
  { to: "/admin/reports", label: "Relatórios", icon: FileText },
];

export function AppShell({ children }: PropsWithChildren) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navigation = user?.role === "ADMIN" ? adminNavigation : employeeNavigation;
  const active = navigation.find((item) =>
    item.to === "/app" || item.to === "/admin"
      ? location.pathname === item.to
      : location.pathname.startsWith(item.to),
  );

  return (
    <div className="app-frame">
      <button
        className="mobile-menu-button"
        type="button"
        aria-label="Abrir menu"
        onClick={() => setOpen(true)}
      >
        <Menu size={20} />
      </button>
      {open && (
        <button className="sidebar-scrim" onClick={() => setOpen(false)} aria-label="Fechar" />
      )}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand-row">
          <Brand />
          <button
            className="sidebar-close"
            type="button"
            aria-label="Fechar menu"
            onClick={() => setOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <span className="workspace-label">NovaTech Academy</span>
        <nav className="sidebar-nav" aria-label="Navegação principal">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/app" || to === "/admin"}
              className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              <Icon size={18} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className={`sidebar-profile ${profileOpen ? "open" : ""}`}>
          <button
            className="sidebar-user"
            type="button"
            aria-expanded={profileOpen}
            aria-controls="sidebar-account-menu"
            aria-label={`${profileOpen ? "Fechar" : "Abrir"} menu da conta de ${user?.full_name}`}
            onClick={() => setProfileOpen((current) => !current)}
          >
            <span className="avatar">{user?.full_name.slice(0, 1).toUpperCase()}</span>
            <span className="sidebar-user-copy">
              <strong>{user?.full_name}</strong>
              <span>{user?.role === "ADMIN" ? "Administrador" : "Colaborador"}</span>
            </span>
            <ChevronDown className="sidebar-user-chevron" size={15} />
          </button>
          {profileOpen && (
            <div className="sidebar-account-menu" id="sidebar-account-menu">
              <span>Conta conectada</span>
              <strong>{user?.email}</strong>
              <button type="button" onClick={() => void logout()}>
                <LogOut size={16} /> Sair da conta
              </button>
            </div>
          )}
        </div>
      </aside>
      <div className="app-main">
        <header className="app-topbar">
          <div>
            <span className="page-context">
              Workflix / {user?.role === "ADMIN" ? "Admin" : "Academy"}
            </span>
            <strong>{active?.label ?? "Treinamento"}</strong>
          </div>
          <div className="topbar-status">
            <span /> ambiente demo
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
