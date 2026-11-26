import { useState } from "react";
import { ApiClientError } from "../api/errors";
import { useAuth, validateAuthInputs } from "../context/AuthContext";

interface AuthPanelProps {
  onSuccess?: () => void;
  title?: string;
  subtitle?: string;
}

export function AuthPanel({
  onSuccess,
  title = "Sign in to your Option Form",
  subtitle = "Save up to 100 college choices, reorder priorities, and print your CAP preference list.",
}: AuthPanelProps) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const validationError = validateAuthInputs(username, password, mode);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(username, password);
        onSuccess?.();
      } else {
        await register(username, password);
        setMode("login");
        setPassword("");
        setNotice("Account created. Sign in with your new username and password.");
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Couldn't complete your request right now. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-[6px] border border-rule-strong bg-surface p-5 sm:p-6">
      <h2 className="font-display text-[20px] font-semibold text-ink">{title}</h2>
      <p className="mt-1 text-[13.5px] leading-relaxed text-ink-secondary">{subtitle}</p>

      <div role="tablist" aria-label="Account mode" className="mt-4 grid grid-cols-2 border-b border-rule">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "login"}
          onClick={() => {
            setMode("login");
            setError(null);
            setNotice(null);
          }}
          className={`min-h-[42px] border-b-2 text-[13.5px] font-medium transition-colors ${
            mode === "login"
              ? "border-accent text-accent"
              : "border-transparent text-ink-secondary hover:text-ink"
          }`}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "register"}
          onClick={() => {
            setMode("register");
            setError(null);
            setNotice(null);
          }}
          className={`min-h-[42px] border-b-2 text-[13.5px] font-medium transition-colors ${
            mode === "register"
              ? "border-accent text-accent"
              : "border-transparent text-ink-secondary hover:text-ink"
          }`}
        >
          Create account
        </button>
      </div>

      {notice && (
        <div
          role="status"
          className="mt-3 rounded-[4px] border border-safe/30 bg-safe-tint px-3 py-2 text-[13px] text-safe"
        >
          {notice}
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-[4px] border border-danger/30 bg-danger-tint px-3 py-2 text-[13px] text-danger"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 space-y-3.5" noValidate>
        <div>
          <label
            htmlFor={`auth-username-${mode}`}
            className="mb-1.5 block text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase"
          >
            Username
          </label>
          <input
            id={`auth-username-${mode}`}
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            placeholder="e.g. aarav_cet2026"
            className="min-h-[44px] w-full rounded-[6px] border border-rule-strong bg-surface px-3 py-2 text-[14px] text-ink placeholder:text-ink-muted"
          />
          {mode === "register" && (
            <p className="mt-1 text-[12px] text-ink-muted">
              3–50 characters: letters, digits, dot (.), underscore (_), or hyphen (-).
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor={`auth-password-${mode}`}
            className="mb-1.5 block text-[11.5px] font-semibold tracking-[0.04em] text-ink-muted uppercase"
          >
            Password
          </label>
          <input
            id={`auth-password-${mode}`}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={mode === "register" ? "At least 8 characters" : "Enter password"}
            className="min-h-[44px] w-full rounded-[6px] border border-rule-strong bg-surface px-3 py-2 text-[14px] text-ink placeholder:text-ink-muted"
          />
          {mode === "register" && (
            <p className="mt-1 text-[12px] text-ink-muted">8–128 characters.</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="min-h-[44px] w-full rounded-[4px] bg-accent px-4 py-2 text-[14px] font-semibold text-accent-ink transition-colors hover:bg-accent-hover disabled:opacity-60"
        >
          {isSubmitting
            ? mode === "login"
              ? "Signing in…"
              : "Creating account…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>
    </div>
  );
}
