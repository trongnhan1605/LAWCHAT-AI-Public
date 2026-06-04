import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { UI_TEXT, resolveStoredLocale } from "../locales";
import { useAuthStore } from "../store/auth.store";
import { resolveUserHomePath } from "../types/auth";

export default function LoginPage() {
  const ui = UI_TEXT[resolveStoredLocale()];
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const isLoading = useAuthStore((state) => state.isLoading);
  const user = useAuthStore((state) => state.user);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      await login({ email: email.trim().toLowerCase(), password });
      const nextUser = useAuthStore.getState().user ?? user;
      navigate(nextUser ? resolveUserHomePath(nextUser.role) : "/customer/workspace", { replace: true });
    } catch {
      setError(ui.authLoginError);
    }
  };

  return (
    <main className="auth-shell">
      <form className="auth-card" onSubmit={handleSubmit}>
        <p className="eyebrow">LawChat-AI</p>
        <h1>{ui.authLoginTitle}</h1>
        <p className="auth-copy">{ui.authLoginDescription}</p>

        {error ? <div className="error-banner">{error}</div> : null}

        <label>
          {ui.authEmailLabel}
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>

        <label>
          {ui.authPasswordLabel}
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>

        <button className="primary-button" type="submit" disabled={isLoading}>
          {isLoading ? ui.authSigningInButton : ui.authSignInButton}
        </button>

        <p className="auth-footer">
          {ui.authNoAccountText} <Link to="/register">{ui.authCreateAccountLink}</Link>
        </p>
      </form>
    </main>
  );
}
