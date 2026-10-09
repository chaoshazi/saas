import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");

  const totpQuery = useQuery({
    queryKey: ["totp-setup"],
    queryFn: api.totpSetup,
    enabled: !!user && !user.totp_enabled,
  });

  const enableMutation = useMutation({
    mutationFn: () => api.totpEnable(code),
    onSuccess: async () => {
      setMessage("2FA enabled");
      setCode("");
      queryClient.invalidateQueries({ queryKey: ["me"] });
      const me = await api.me();
      setUser(me);
    },
    onError: (err) => setMessage(err instanceof Error ? err.message : "Enable failed"),
  });

  const avatarMutation = useMutation({
    mutationFn: (file: File) => api.uploadAvatar(file),
    onSuccess: async (updated) => {
      setUser(updated);
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Settings</h1>
      <div className="max-w-xl space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-medium">Profile</h2>
          <div className="flex items-start gap-4">
            {user?.avatar_url && <img src={user.avatar_url} alt="" className="h-14 w-14 rounded-full object-cover" />}
            <div className="text-sm text-slate-600">
              <div>Email: {user?.email || "—"}</div>
              <div>Name: {user?.full_name || "—"}</div>
              <div>Roles: {(user?.role_slugs || []).join(", ")}</div>
            </div>
          </div>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => e.target.files?.[0] && avatarMutation.mutate(e.target.files[0])}
            className="mt-3 text-sm"
          />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-medium">Two-factor authentication</h2>
          {user?.totp_enabled ? (
            <div className="text-sm text-green-600">2FA is enabled</div>
          ) : (
            <div>
              {totpQuery.data && (
                <div className="mb-3">
                  <div className="mb-2 text-sm text-slate-500">
                    Secret: <span className="font-mono">{totpQuery.data.secret}</span>
                  </div>
                  <div className="mb-2 break-all text-xs text-slate-400">{totpQuery.data.otpauth_uri}</div>
                </div>
              )}
              <div className="flex gap-2">
                <input
                  placeholder="6-digit code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2"
                />
                <button
                  onClick={() => enableMutation.mutate()}
                  disabled={code.length !== 6}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
                >
                  Enable
                </button>
              </div>
            </div>
          )}
          {message && <div className="mt-3 text-sm text-slate-600">{message}</div>}
        </div>

        <NotificationPreferences />
        {user?.is_superuser && <LicenseSection />}
      </div>
    </div>
  );
}

function NotificationPreferences() {
  const queryClient = useQueryClient();
  const prefsQuery = useQuery({ queryKey: ["notification-preferences"], queryFn: api.listNotificationPreferences });
  const updateMutation = useMutation({
    mutationFn: ({ channel, eventType, enabled }: { channel: string; eventType: string; enabled: boolean }) =>
      api.updateNotificationPreference(channel, eventType, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-preferences"] }),
  });

  const rows = [
    { channel: "in_app", eventType: "task.assigned", label: "In-app task notifications" },
    { channel: "email", eventType: "task.assigned", label: "Email task notifications" },
    { channel: "wecom", eventType: "task.assigned", label: "WeCom task notifications" },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 font-medium">Notification preferences</h2>
      <div className="space-y-2">
        {rows.map((row) => {
          const current = (prefsQuery.data || []).find((p) => p.channel === row.channel && p.event_type === row.eventType);
          const enabled = current?.enabled ?? row.channel === "in_app";
          return (
            <label key={`${row.channel}-${row.eventType}`} className="flex items-center justify-between text-sm">
              <span>{row.label}</span>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => updateMutation.mutate({ channel: row.channel, eventType: row.eventType, enabled: e.target.checked })}
              />
            </label>
          );
        })}
      </div>
    </div>
  );
}

function LicenseSection() {
  const queryClient = useQueryClient();
  const [key, setKey] = useState("");
  const [message, setMessage] = useState("");

  const licenseQuery = useQuery({ queryKey: ["license"], queryFn: api.getLicense });

  const activateMutation = useMutation({
    mutationFn: () => api.activateLicense(key),
    onSuccess: (license) => {
      setKey("");
      setMessage(`License activated (${license.status}, plan ${license.plan_code})`);
      queryClient.invalidateQueries({ queryKey: ["license"] });
    },
    onError: (err) => setMessage(err instanceof Error ? err.message : "Activation failed"),
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 font-medium">License</h2>
      {licenseQuery.data ? (
        <div className="mb-3 text-sm text-slate-600">
          <div>
            Status: <span className="font-medium capitalize">{licenseQuery.data.status}</span>
          </div>
          <div>Plan: {licenseQuery.data.plan_code}</div>
          <div>Issued to: {licenseQuery.data.issued_to || "—"}</div>
          {licenseQuery.data.expires_at && <div>Expires: {new Date(licenseQuery.data.expires_at).toLocaleString()}</div>}
        </div>
      ) : (
        <div className="mb-3 text-sm text-slate-500">No license installed</div>
      )}
      <div className="flex gap-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="License key"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm"
        />
        <button
          onClick={() => activateMutation.mutate()}
          disabled={!key.trim()}
          className="rounded-lg bg-slate-800 px-4 py-2 text-white disabled:opacity-50"
        >
          Activate
        </button>
      </div>
      {message && <div className="mt-3 text-sm text-slate-600">{message}</div>}
    </div>
  );
}
