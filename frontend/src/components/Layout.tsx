import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const roleLinks: Record<string, { to: string; label: string }[]> = {
    participant: [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/skills", label: "Skills" },
      { to: "/team", label: "Team" },
    ],
    judge: [
      { to: "/judge", label: "Judging Queue" },
      { to: "/judge/history", label: "History" },
    ],
    organizer: [
      { to: "/organizer", label: "Hackathon" },
      { to: "/organizer/rubric", label: "Rubric" },
      { to: "/organizer/judges", label: "Judges" },
      { to: "/organizer/judging", label: "Observatory" },
      { to: "/organizer/rankings", label: "Rankings" },
      { to: "/organizer/ranking-lab", label: "Ranking Lab" },
      { to: "/organizer/audit", label: "Audit Log" },
    ],
    admin: [
      { to: "/admin/users", label: "Users" },
      { to: "/admin/audit", label: "Audit Log" },
    ],
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border sticky top-0 bg-bg/95 backdrop-blur z-10">
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <SkillForgeMark />
            <span className="font-display text-lg tracking-tight">SkillForge</span>
          </Link>
          <nav className="hidden md:flex items-center gap-5 text-sm text-muted">
            <Link to="/hackathons" className="hover:text-ink">Hackathons</Link>
            <Link to="/projects" className="hover:text-ink">Gallery</Link>
            {user && roleLinks[user.role]?.map((l) => (
              <Link key={l.to} to={l.to} className="hover:text-ink">{l.label}</Link>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            {user ? (
              <>
                <span className="text-muted hidden sm:inline">{user.full_name} <span className="sf-badge ml-1">{user.role}</span></span>
                <button className="sf-btn sf-btn-secondary" onClick={() => { logout(); navigate("/"); }}>Log out</button>
              </>
            ) : (
              <>
                <Link to="/login" className="sf-btn sf-btn-secondary">Log in</Link>
                <Link to="/register" className="sf-btn sf-btn-primary">Register</Link>
              </>
            )}
          </div>
        </div>
        {user && (
          <div className="md:hidden border-t border-border overflow-x-auto">
            <div className="flex gap-4 px-5 py-2 text-xs text-muted whitespace-nowrap">
              {roleLinks[user.role]?.map((l) => (
                <Link key={l.to} to={l.to} className="hover:text-ink">{l.label}</Link>
              ))}
            </div>
          </div>
        )}
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-5 py-8">{children}</main>
      <footer className="border-t border-border py-6 text-center text-xs text-muted">
        SkillForge — build the right team. Prove what you built.
      </footer>
    </div>
  );
}

function SkillForgeMark() {
  // Minimal mark: three nodes converging into one — skills joining a team.
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="5" cy="6" r="2.4" stroke="#B88952" strokeWidth="1.4" />
      <circle cx="19" cy="6" r="2.4" stroke="#B88952" strokeWidth="1.4" />
      <circle cx="12" cy="18" r="2.8" fill="#7A263A" />
      <path d="M6.8 8 L10.5 15.5 M17.2 8 L13.5 15.5" stroke="#B88952" strokeWidth="1.2" />
    </svg>
  );
}