import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { EmptyState } from "./Home";

export default function Team() {
  const { user } = useAuth();
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [hackathonId, setHackathonId] = useState<string>("");
  const [teams, setTeams] = useState<any[]>([]);
  const [myTeam, setMyTeam] = useState<any>(null);
  const [coverage, setCoverage] = useState<any>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [lookingFor, setLookingFor] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/hackathons").then((hs) => {
      setHackathons(hs);
      if (hs.length) setHackathonId(hs[0].id);
    });
  }, []);

  function loadTeams() {
    if (!hackathonId) return;
    api.get(`/teams?hackathon_id=${hackathonId}`).then((ts) => {
      setTeams(ts);
      const mine = ts.find((t: any) => t.members.some((m: any) => m.user_id === user?.id));
      setMyTeam(mine || null);
      if (mine) {
        api.get(`/teams/${mine.id}/coverage`).then(setCoverage);
        api.get(`/teams/${mine.id}/matches`).then(setMatches);
      } else {
        setCoverage(null);
        setMatches([]);
      }
    });
  }

  useEffect(loadTeams, [hackathonId, user]); // eslint-disable-line react-hooks/exhaustive-deps

  async function createTeam() {
    setError(null);
    try {
      await api.post("/teams", {
        hackathon_id: hackathonId, name: newTeamName,
        looking_for_skill_names: lookingFor.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setNewTeamName("");
      setLookingFor("");
      loadTeams();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create team");
    }
  }

  async function joinTeam(teamId: string) {
    setError(null);
    try {
      await api.post(`/teams/${teamId}/join`);
      loadTeams();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not join team");
    }
  }

  async function leaveTeam() {
    if (!myTeam) return;
    setError(null);
    try {
      await api.post(`/teams/${myTeam.id}/leave`);
      loadTeams();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not leave team");
    }
  }

  if (!hackathons.length) return <EmptyState title="No hackathons yet" body="Teams can be formed once a hackathon is open." />;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-6">Team</h1>
      {error && <p className="text-sm text-wine bg-winedark/20 border border-winedark rounded px-3 py-2 mb-4">{error}</p>}

      {myTeam ? (
        <div className="space-y-6">
          <section className="sf-card p-5">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg">{myTeam.name}</h3>
              <button className="sf-btn sf-btn-secondary" onClick={leaveTeam}>Leave team</button>
            </div>
            <p className="text-sm text-muted mt-2">Members: {myTeam.members.map((m: any) => m.full_name).join(", ")}</p>
            {myTeam.looking_for?.length > 0 && (
              <p className="text-sm text-copper mt-1">Looking for: {myTeam.looking_for.join(", ")}</p>
            )}
          </section>

          <section className="sf-card p-5">
            <h3 className="font-display text-lg mb-3">Team skill coverage</h3>
            {coverage && Object.keys(coverage.covered).length ? (
              <div className="space-y-2">
                {Object.entries(coverage.covered).map(([skill, d]: any) => (
                  <div key={skill} className="flex items-center gap-3">
                    <span className="w-32 text-sm">{skill}</span>
                    <div className="flex-1 h-2 bg-surface2 rounded">
                      <div className="h-2 bg-wine rounded" style={{ width: `${d.max_proficiency}%` }} />
                    </div>
                    <span className="text-xs text-muted">{d.members.map((m: any) => m.name).join(", ")}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted text-sm">No skills recorded yet across the team.</p>
            )}
            {coverage?.missing?.length > 0 && (
              <p className="text-sm text-wine mt-3">Still missing: {coverage.missing.join(", ")}</p>
            )}
          </section>

          <section className="sf-card p-5">
            <h3 className="font-display text-lg mb-3">Suggested teammates</h3>
            <p className="text-xs text-muted mb-3">
              Ranked by real skill-coverage math over your team's declared gaps — not a black-box AI score.
            </p>
            <div className="space-y-3">
              {matches.map((m) => (
                <div key={m.candidate_id} className="flex items-start justify-between border-b border-border pb-3 last:border-0">
                  <div>
                    <p className="font-medium">{m.candidate_name}</p>
                    <p className="text-xs text-muted mt-1">{m.reasoning}</p>
                  </div>
                  <span className="sf-badge">{m.coverage_score}</span>
                </div>
              ))}
              {!matches.length && <p className="text-muted text-sm">No unmatched participants right now.</p>}
            </div>
          </section>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-6">
          <section className="sf-card p-5">
            <h3 className="font-display text-lg mb-3">Create a team</h3>
            <label className="sf-label">Team name</label>
            <input className="sf-input mb-3" value={newTeamName} onChange={(e) => setNewTeamName(e.target.value)} />
            <label className="sf-label">Looking for (comma-separated)</label>
            <input className="sf-input mb-4" value={lookingFor} onChange={(e) => setLookingFor(e.target.value)} placeholder="Backend, DevOps" />
            <button className="sf-btn sf-btn-primary" onClick={createTeam} disabled={!newTeamName.trim()}>Create team</button>
          </section>
          <section>
            <h3 className="font-display text-lg mb-3">Or join an existing team</h3>
            <div className="space-y-3">
              {teams.map((t) => (
                <div key={t.id} className="sf-card p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{t.name}</p>
                    <p className="text-xs text-muted">{t.members.length} member(s)</p>
                  </div>
                  <button className="sf-btn sf-btn-secondary" onClick={() => joinTeam(t.id)}>Join</button>
                </div>
              ))}
              {!teams.length && <p className="text-muted text-sm">No teams yet — be the first to create one.</p>}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
