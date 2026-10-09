import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function AuditPage() {
  const auditQuery = useQuery({ queryKey: ["audit"], queryFn: () => api.listAudit() });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Audit log</h1>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Resource</th>
              <th className="px-4 py-3">IP</th>
            </tr>
          </thead>
          <tbody>
            {(auditQuery.data?.items || []).map((entry) => (
              <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3">{new Date(entry.created_at).toLocaleString()}</td>
                <td className="px-4 py-3">{entry.actor_id ?? "—"}</td>
                <td className="px-4 py-3">{entry.action}</td>
                <td className="px-4 py-3">
                  {entry.resource_type}
                  {entry.resource_id ? ` #${entry.resource_id}` : ""}
                </td>
                <td className="px-4 py-3">{entry.ip_address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!auditQuery.isLoading && (auditQuery.data?.items || []).length === 0 && (
          <div className="py-8 text-center text-sm text-slate-500">No audit records</div>
        )}
      </div>
    </div>
  );
}
