import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");

  const usersQuery = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });

  const createMutation = useMutation({
    mutationFn: () => api.createUser({ email, password, full_name: fullName }),
    onSuccess: () => {
      setEmail("");
      setPassword("");
      setFullName("");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Create failed"),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => api.deactivateUser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const promoteMutation = useMutation({
    mutationFn: (id: number) => api.grantSuperuser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    createMutation.mutate();
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Users</h1>

      <form onSubmit={onSubmit} className="mb-6 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <input
          placeholder="Email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-56 rounded-lg border border-slate-300 px-3 py-2"
        />
        <input
          placeholder="Password"
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-40 rounded-lg border border-slate-300 px-3 py-2"
        />
        <input
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="w-40 rounded-lg border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          Add user
        </button>
        {error && <span className="self-center text-sm text-red-600">{error}</span>}
      </form>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(usersQuery.data?.items || []).map((user) => (
              <tr key={user.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3">{user.email}</td>
                <td className="px-4 py-3">{user.full_name}</td>
                <td className="px-4 py-3">{(user.role_slugs || []).join(", ")}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-2 py-0.5 text-xs ${user.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                    {user.is_active ? "active" : "disabled"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {!user.is_superuser && (
                      <button
                        onClick={() => promoteMutation.mutate(user.id)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Make admin
                      </button>
                    )}
                    {user.is_active && (
                      <button
                        onClick={() => deactivateMutation.mutate(user.id)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Disable
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
