import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { SystemConfig } from "../lib/types";
import { useAuthStore } from "../store/auth";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetMessage, setResetMessage] = useState("");
  const [demo, setDemo] = useState<SystemConfig["demo"]>(null);

  useEffect(() => {
    api
      .systemConfig()
      .then((config) => setDemo(config.demo))
      .catch(() => undefined);
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokens = await api.login({ email, password, totp_code: totpCode || undefined });
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function onForgot(event: FormEvent) {
    event.preventDefault();
    setResetMessage("");
    try {
      const result = await api.requestPasswordReset(resetEmail);
      setResetMessage(result.token ? `Reset token: ${result.token}` : result.message);
    } catch (err) {
      setResetMessage(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-semibold">{t("login")}</h1>

        {demo && (
          <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-slate-600">
            <div className="mb-2 font-medium text-blue-700">演示账号（点击自动填入 / click to fill）</div>
            <div className="flex flex-col gap-1">
              <button
                type="button"
                onClick={() => {
                  setEmail(demo.admin_email);
                  setPassword(demo.admin_password);
                }}
                className="rounded bg-white px-2 py-1 text-left hover:bg-blue-100"
              >
                管理员 Admin：{demo.admin_email} / {demo.admin_password}
              </button>
              {demo.demo_emails[0] && (
                <button
                  type="button"
                  onClick={() => {
                    setEmail(demo.demo_emails[0]);
                    setPassword(demo.demo_password);
                  }}
                  className="rounded bg-white px-2 py-1 text-left hover:bg-blue-100"
                >
                  普通用户 User：{demo.demo_emails[0]} / {demo.demo_password}
                </button>
              )}
            </div>
          </div>
        )}

        {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
        <label className="mb-1 block text-sm font-medium text-slate-600">{t("email")}</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2"
        />
        <label className="mb-1 block text-sm font-medium text-slate-600">{t("password")}</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2"
        />
        <label className="mb-1 block text-sm font-medium text-slate-600">2FA Code (optional)</label>
        <input
          type="text"
          value={totpCode}
          onChange={(e) => setTotpCode(e.target.value)}
          className="mb-6 w-full rounded-lg border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {t("login")}
        </button>
        <p className="mt-4 text-center text-sm text-slate-500">
          No account?{" "}
          <Link to="/register" className="font-medium text-blue-600">
            {t("register")}
          </Link>
          {" · "}
          <button type="button" onClick={() => setShowForgot(!showForgot)} className="font-medium text-blue-600">
            Forgot password?
          </button>
        </p>

        {showForgot && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <label className="mb-1 block text-sm font-medium text-slate-600">Email for reset</label>
            <div className="flex gap-2">
              <input
                type="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
              />
              <button
                type="button"
                onClick={onForgot}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                Send
              </button>
            </div>
            {resetMessage && <div className="mt-2 break-all text-sm text-slate-600">{resetMessage}</div>}
            <Link to="/reset-password" className="mt-2 inline-block text-sm text-blue-600">
              Already have a reset token?
            </Link>
          </div>
        )}
      </form>
    </div>
  );
}
