import { useState } from "react";
import { supabase } from "../lib/supabase";

export default function Login() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (err) setError(err.message);
  };

  return (
    <div className="login-shell">
      <div className="login-card">

        {/* Branding */}
        <div className="login-brand">
          <img
            src="/tech9labs_logo.png"
            alt="Tech9Labs"
            className="login-logo"
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
          <div>
            <div className="login-title">Pre Screening Assistant</div>
            <div className="login-sub">AI-powered resume screening — Tech9Labs</div>
          </div>
        </div>

        <div className="login-divider" />

        <form onSubmit={handleLogin} className="login-form">
          <div className="login-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              placeholder="you@tech9labs.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="email"
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="login-error">{error}</div>
          )}

          <button
            type="submit"
            className="btn-primary login-btn"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="login-footer">
          Contact your administrator to get access.
        </div>
      </div>
    </div>
  );
}
