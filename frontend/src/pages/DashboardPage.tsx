import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

export function DashboardPage() {
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const data = await api.me();
      setUser(data);
      return data;
    },
  });

  const statsQuery = useQuery({ queryKey: ["dashboard-stats"], queryFn: api.dashboardStats });

  const stats = statsQuery.data;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Dashboard</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="text-sm text-slate-500">Signed in as</div>
          <div className="mt-1 truncate text-lg font-medium">{user?.full_name || meQuery.data?.full_name || "—"}</div>
          <div className="truncate text-sm text-slate-500">{meQuery.data?.email}</div>
        </div>
        <StatCard label="Active projects" value={stats?.projects} />
        <StatCard label="Tasks" value={stats?.tasks} />
        <StatCard label="Teams" value={stats?.teams} />
        <StatCard label="Unread notifications" value={stats?.unread_notifications} />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold">{value ?? "—"}</div>
    </div>
  );
}
