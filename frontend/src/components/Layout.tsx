import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { useRealtime } from "../lib/realtime";
import { useAuthStore } from "../store/auth";
import { SearchBox } from "./SearchBox";

interface NavItem {
  to: string;
  key: string;
  requires?: (permissions: string[], superuser: boolean) => boolean;
}

const navItems: NavItem[] = [
  { to: "/dashboard", key: "dashboard" },
  { to: "/projects", key: "projects" },
  { to: "/documents", key: "documents" },
  { to: "/teams", key: "teams" },
  { to: "/notifications", key: "notifications" },
  { to: "/billing", key: "billing" },
  { to: "/settings", key: "settings" },
  { to: "/admin/users", key: "adminUsers", requires: (_p, s) => s },
  { to: "/admin/audit", key: "adminAudit", requires: (_p, s) => s },
];

export function Layout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const user = useAuthStore((s) => s.user);
  const [loading, setLoading] = useState(false);
  useRealtime();

  const permissions = user?.permission_codes || [];
  const visibleItems = navItems.filter((item) => !item.requires || item.requires(permissions, !!user?.is_superuser));

  async function handleLogout() {
    setLoading(true);
    try {
      await api.logout();
    } catch {
      // local logout still proceeds
    } finally {
      clear();
      navigate("/login");
    }
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white">
        <div className="px-5 py-6 text-lg font-semibold">AICRM SaaS</div>
        <nav className="space-y-1 px-3">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {t(item.key)}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="text-sm text-slate-500">Enterprise Project Management</div>
          <div className="flex items-center gap-3">
            <SearchBox />
            <button
              onClick={handleLogout}
              disabled={loading}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
            >
              {t("logout")}
            </button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
