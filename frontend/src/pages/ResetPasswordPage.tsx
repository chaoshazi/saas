import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.resetPassword(token, password);
      setMessage("Password reset. You can now sign in.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-semibold">Reset password</h1>
        {message && <div className="mb-4 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700">{message}</div>}
        {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
        <label className="mb-1 block text-sm font-medium text-slate-600">New password</label>
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full rounded-lg border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={!token}
          className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white disabled:opacity-50"
        >
          Reset password
        </button>
        <p className="mt-4 text-center text-sm text-slate-500">
          <Link to="/login" className="font-medium text-blue-600">
            Back to sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
