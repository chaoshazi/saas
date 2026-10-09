import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function NotificationsPage() {
  const queryClient = useQueryClient();

  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.listNotifications(false),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => api.markNotificationRead(id, true),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllMutation = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Notifications</h1>
        <button
          onClick={() => markAllMutation.mutate()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
        >
          Mark all read
        </button>
      </div>
      <div className="space-y-2">
        {(notificationsQuery.data?.items || []).map((notification) => (
          <div
            key={notification.id}
            onClick={() => !notification.is_read && markReadMutation.mutate(notification.id)}
            className={`cursor-pointer rounded-xl border bg-white p-4 ${
              notification.is_read ? "border-slate-200" : "border-blue-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{notification.title}</span>
              <span className="text-xs text-slate-400">{new Date(notification.created_at).toLocaleString()}</span>
            </div>
            {notification.body && <div className="mt-1 text-sm text-slate-600">{notification.body}</div>}
          </div>
        ))}
        {!notificationsQuery.isLoading && (notificationsQuery.data?.items || []).length === 0 && (
          <div className="py-10 text-center text-slate-500">No notifications</div>
        )}
      </div>
    </div>
  );
}
