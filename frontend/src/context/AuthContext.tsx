import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setToken, getStoredToken } from "../api/client";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "participant" | "judge" | "organizer" | "admin";
  institution?: string | null;
  is_demo?: boolean;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, full_name: string, role: string, institution?: string) => Promise<User>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api.get("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const data = await api.post("/auth/login", { email, password });
    setToken(data.access_token);
    setUser(data.user);
    return data.user as User;
  }

  async function register(email: string, password: string, full_name: string, role: string, institution?: string) {
    const data = await api.post("/auth/register", { email, password, full_name, role, institution });
    setToken(data.access_token);
    setUser(data.user);
    return data.user as User;
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}