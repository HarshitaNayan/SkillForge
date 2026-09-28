import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export function roleHome(role: string) {
  if (role === "organizer" || role === "admin") return "/organizer";
  if (role === "judge") return "/judge";
  return "/dashboard";
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await login(email, password);
      navigate(roleHome(user.role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto sf-card p-8">
      <h1 className="font-display text-2xl mb-1">Log in</h1>
      <p className="text-muted text-sm mb-6">Demo accounts use password DemoPass123!</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="sf-label">Email</label>
          <input className="sf-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="sf-label">Password</label>
          <input className="sf-input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p className="text-sm text-wine bg-winedark/20 border border-winedark rounded px-3 py-2">{error}</p>}
        <button className="sf-btn sf-btn-primary w-full justify-center" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="text-sm text-muted mt-5">
        No account? <Link to="/register" className="text-copper">Register</Link>
      </p>
    </div>
  );
}