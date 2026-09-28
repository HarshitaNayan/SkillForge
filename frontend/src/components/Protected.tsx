import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Protected({ roles, children }: { roles?: string[]; children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="text-muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role) && user.role !== "admin") {
    return (
      <div className="sf-card p-6">
        <p className="text-ink">This area is for {roles.join(" / ")} accounts.</p>
        <p className="text-muted text-sm mt-1">
          You're signed in as a {user.role}. This is a frontend convenience only — the API independently
          rejects this request server-side too.
        </p>
      </div>
    );
  }
  return <>{children}</>;
}
