import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerJudges() {
  const { hackathons, hackathonId, HackathonPicker } = useHackathonPicker();
  const [judges, setJudges] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [selectedJudge, setSelectedJudge] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!hackathonId) return;
    api.get("/users?role=judge").then(setJudges);
    api.get(`/projects?hackathon_id=${hackathonId}`).then(setProjects);
    api.get(`/judging/assignments?hackathon_id=${hackathonId}`).then(setAssignments);
    api.get(`/judging/conflicts?hackathon_id=${hackathonId}`).then(setConflicts);
  }
  useEffect(load, [hackathonId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function assign() {
    setError(null);
    try {
      await api.post("/judging/assignments", { hackathon_id: hackathonId, judge_id: selectedJudge, project_id: selectedProject });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not assign");
    }
  }

  async function assignAllToAll() {
    setError(null);
    try {
      for (const j of judges) {
        for (const p of projects) {
          await api.post("/judging/assignments", { hackathon_id: hackathonId, judge_id: j.id, project_id: p.id }).catch(() => {});
        }
      }
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not bulk-assign");
    }
  }

  async function unassign(assignmentId: string) {
    await api.del(`/judging/assignments/${assignmentId}`).catch((e) => setError(e instanceof ApiError ? e.message : "Could not remove"));
    load();
  }

  async function declareConflict() {
    setError(null);
    try {
      await api.post("/judging/conflicts", { hackathon_id: hackathonId, judge_id: selectedJudge, project_id: selectedProject, reason: "Organizer-recorded conflict" });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not record conflict");
    }
  }

  function name(list: any[], id: string) { return list.find((x) => x.id === id)?.full_name || list.find((x) => x.id === id)?.name || id.slice(0, 8); }

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-4">Judges &amp; assignments</h1>
      <HackathonPicker />

      <div className="sf-card p-5 mb-6">
        <h3 className="font-display text-lg mb-3">Assign a judge to a project</h3>
        <div className="flex gap-2 flex-wrap items-center">
          <select className="sf-input flex-1 min-w-[10rem]" value={selectedJudge} onChange={(e) => setSelectedJudge(e.target.value)}>
            <option value="">Select judge…</option>
            {judges.map((j) => <option key={j.id} value={j.id}>{j.full_name}</option>)}
          </select>
          <select className="sf-input flex-1 min-w-[10rem]" value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)}>
            <option value="">Select project…</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button className="sf-btn sf-btn-secondary" onClick={assign} disabled={!selectedJudge || !selectedProject}>Assign</button>
          <button className="sf-btn sf-btn-secondary" onClick={declareConflict} disabled={!selectedJudge || !selectedProject}>Record COI</button>
        </div>
        <button className="sf-btn sf-btn-primary mt-3" onClick={assignAllToAll} disabled={!judges.length || !projects.length}>
          Assign every judge to every submitted project
        </button>
        {error && <p className="text-sm text-wine mt-3">{error}</p>}
      </div>

      <div className="grid sm:grid-cols-2 gap-6">
        <div>
          <h3 className="font-display text-lg mb-3">Assignment coverage</h3>
          <div className="space-y-2">
            {assignments.map((a) => (
              <div key={a.id} className="sf-card p-3 flex items-center justify-between text-sm">
                <span>{name(judges, a.judge_id)} → {name(projects, a.project_id)}</span>
                <button className="text-xs text-muted hover:text-wine" onClick={() => unassign(a.id)}>Remove</button>
              </div>
            ))}
            {!assignments.length && <p className="text-muted text-sm">No assignments yet.</p>}
          </div>
        </div>
        <div>
          <h3 className="font-display text-lg mb-3">Declared conflicts of interest</h3>
          <div className="space-y-2">
            {conflicts.map((c) => (
              <div key={c.id} className="sf-card p-3 text-sm">
                <p>{name(judges, c.judge_id)} — {name(projects, c.project_id)}</p>
                {c.reason && <p className="text-xs text-muted mt-1">{c.reason}</p>}
              </div>
            ))}
            {!conflicts.length && <p className="text-muted text-sm">None declared.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
