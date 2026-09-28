import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { EmptyState } from "./Home";

export default function Dashboard() {
  const { user } = useAuth();
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [myTeam, setMyTeam] = useState<any>(null);
  const [myProject, setMyProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/hackathons").then(async (hs) => {
      setHackathons(hs);
      if (hs.length) {
        const teams = await api.get(`/teams?hackathon_id=${hs[0].id}`);
        const mine = teams.find((t: any) => t.members.some((m: any) => m.user_id === user?.id));
        setMyTeam(mine || null);
        if (mine) {
          const own = await api.get(`/projects/by-team/${mine.id}`).catch(() => null);
          setMyProject(own);
        }
      }
      setLoading(false);
    });
  }, [user]);

  if (loading) return <p className="text-muted">Loading…</p>;

  return (
    <div>
      <h1 className="font-display text-2xl mb-6">Welcome, {user?.full_name}</h1>
      {!hackathons.length ? (
        <EmptyState title="No hackathons open yet" body="Check back once an organizer publishes one." />
      ) : (
        <div className="grid sm:grid-cols-2 gap-5">
          <div className="sf-card p-5">
            <h3 className="font-display text-lg mb-2">Your team</h3>
            {myTeam ? (
              <>
                <p className="text-copper">{myTeam.name}</p>
                <p className="text-sm text-muted mt-1">{myTeam.members.length} member(s)</p>
                <Link to="/team" className="sf-btn sf-btn-secondary mt-3">Manage team</Link>
              </>
            ) : (
              <>
                <p className="text-muted text-sm mb-3">No team yet. Build your team — find participants with complementary skills.</p>
                <Link to="/team" className="sf-btn sf-btn-primary">Create or join a team</Link>
              </>
            )}
          </div>
          <div className="sf-card p-5">
            <h3 className="font-display text-lg mb-2">Your project</h3>
            {myProject ? (
              <>
                <p className="text-copper">{myProject.name}</p>
                <p className="text-sm text-muted mt-1">Status: {myProject.status}</p>
                <Link to={`/projects/${myProject.id}/edit`} className="sf-btn sf-btn-secondary mt-3">Open project</Link>
              </>
            ) : myTeam ? (
              <>
                <p className="text-muted text-sm mb-3">No project yet for this team.</p>
                <Link to="/projects/new" className="sf-btn sf-btn-primary">Start a project</Link>
              </>
            ) : (
              <p className="text-muted text-sm">Join a team first, then start a project.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
