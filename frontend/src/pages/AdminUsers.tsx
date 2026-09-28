import React, { useEffect, useState } from "react";
import { api } from "../api/client";

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  useEffect(() => { api.get("/users").then(setUsers); }, []);

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl mb-6">Users</h1>
      <div className="space-y-1">
        {users.map((u) => (
          <div key={u.id} className="sf-card px-4 py-2.5 flex items-center justify-between text-sm">
            <span>{u.full_name} <span className="text-muted">({u.email})</span></span>
            <span className="sf-badge">{u.role}{u.is_demo ? " · demo" : ""}</span>
          </div>
        ))}
        {!users.length && <p className="text-muted text-sm">No users found (only organizers/admins can list all users).</p>}
      </div>
    </div>
  );
}
