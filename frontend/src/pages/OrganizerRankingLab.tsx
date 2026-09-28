import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerRankingLab() {
  const { hackathons, hackathonId, HackathonPicker } = useHackathonPicker();
  const [judges, setJudges] = useState<any[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [excludeJudges, setExcludeJudges] = useState<string[]>([]);
  const [method, setMethod] = useState("z_score");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hackathonId) return;
    api.get("/users?role=judge").then(setJudges);
    api.get(`/judging/assignments?hackathon_id=${hackathonId}`).then(setAssignments);
  }, [hackathonId]);

  const judgesWithAssignments = judges.filter((j) => assignments.some((a) => a.judge_id === j.id));

  function toggleJudge(id: string) {
    setExcludeJudges((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  async function run() {
    setError(null);
    try {
      const r = await api.post("/scoring/simulate", {
        hackathon_id: hackathonId, name: name || "Untitled simulation",
        exclude_judge_ids: excludeJudges, method,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not run simulation");
    }
  }

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-1">Ranking Lab</h1>
      <p className="text-muted text-sm mb-4">
        Run what-if scenarios against real stored evaluations. Simulations never change the official, published ranking.
      </p>
      <HackathonPicker />

      <div className="sf-card p-5 mb-6 space-y-3">
        <div>
          <label className="sf-label">Simulation name</label>
          <input className="sf-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Remove Judge X" />
        </div>
        <div>
          <label className="sf-label">Exclude judges</label>
          <div className="flex flex-wrap gap-2">
            {judgesWithAssignments.map((j) => (
              <button key={j.id} className={`sf-badge ${excludeJudges.includes(j.id) ? "border-wine text-wine" : ""}`}
                      onClick={() => toggleJudge(j.id)}>{j.full_name}</button>
            ))}
            {!judgesWithAssignments.length && <p className="text-muted text-xs">No assigned judges yet.</p>}
          </div>
        </div>
        <div>
          <label className="sf-label">Normalization method</label>
          <select className="sf-input w-48" value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="z_score">z-score</option>
            <option value="min_max">min-max</option>
            <option value="none">none (raw)</option>
          </select>
        </div>
        {error && <p className="text-sm text-wine">{error}</p>}
        <button className="sf-btn sf-btn-primary" onClick={run}>Run simulation</button>
      </div>

      {result && (
        <div>
          <p className="text-copper text-sm mb-4">{result.diff_summary}</p>
          <div className="grid sm:grid-cols-2 gap-6">
            <div>
              <h3 className="font-display text-lg mb-3">Official ranking</h3>
              <div className="space-y-2">
                {result.official_ranking.map((r: any) => (
                  <div key={r.project_id} className="sf-card p-3 text-sm flex justify-between">
                    <span>#{r.rank} {r.project_name}</span><span>{r.final_score}</span>
                  </div>
                ))}
                {!result.official_ranking.length && <p className="text-muted text-xs">No official ranking published yet.</p>}
              </div>
            </div>
            <div>
              <h3 className="font-display text-lg mb-3">Simulated ranking</h3>
              <div className="space-y-2">
                {result.simulated_ranking.map((r: any) => (
                  <div key={r.project_id} className={`sf-card p-3 text-sm flex justify-between ${r.official_rank !== r.rank ? "border-copper" : ""}`}>
                    <span>#{r.rank} {r.project_name}</span>
                    <span>{r.final_score} {r.official_rank && r.official_rank !== r.rank && <span className="text-xs text-muted">(was #{r.official_rank})</span>}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
