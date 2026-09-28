import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", institution: "", role: "participant" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(form.email, form.password, form.full_name, form.role, form.institution || undefined);
      navigate(form.role === "judge" ? "/judge" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto sf-card p-8">
      <h1 className="font-display text-2xl mb-1">Create an account</h1>
      <p className="text-muted text-sm mb-6">
        Organizer and admin accounts aren't self-registerable — an organizer sets those up directly.
      </p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="sf-label">Full name</label>
          <input className="sf-input" required value={form.full_name}
                 onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Email</label>
          <input className="sf-input" type="email" required value={form.email}
                 onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Password</label>
          <input className="sf-input" type="password" required minLength={8} value={form.password}
                 onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Institution (optional)</label>
          <input className="sf-input" value={form.institution}
                 onChange={(e) => setForm({ ...form, institution: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">I am joining as</label>
          <select className="sf-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="participant">Participant</option>
            <option value="judge">Judge</option>
          </select>
        </div>
        {error && <p className="text-sm text-wine bg-winedark/20 border border-winedark rounded px-3 py-2">{error}</p>}
        <button className="sf-btn sf-btn-primary w-full justify-center" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-muted mt-5">
        Already have an account? <Link to="/login" className="text-copper">Log in</Link>
      </p>
    </div>
  );
}
