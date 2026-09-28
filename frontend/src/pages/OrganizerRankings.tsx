import React, { useEffect, useState } from "react";
import { api, ApiError, getStoredToken } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerRankings() {
  const { hackathons, hackathonId, HackathonPicker } = useHackathonPicker();
  const [official, setOfficial] = useState<any[]>([]);
  const [method, setMethod] = useState("z_score");
  const [runResult, setRunResult] = useState<any>(null);
  const [why, setWhy] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);

  function loadOfficial() {
    if (hackathonId) api.get(`/scoring/rank/official?hackathon_id=${hackathonId}`).then(setOfficial);
  }
  useEffect(loadOfficial, [hackathonId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function runAndPublish() {
    setError(null);
    try {
      const run = await api.post("/scoring/normalize", { hackathon_id: hackathonId, method });
      setRunResult(run);
      await api.post(`/scoring/rank/${run.run_id}?hackathon_id=${hackathonId}&publish=true`);
      loadOfficial();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not run normalization — make sure there is at least one locked evaluation");
    }
  }

  async function loadWhy(projectId: string) {
    const r = await api.get(`/scoring/why/${projectId}?hackathon_id=${hackathonId}`);
    setWhy({ ...why, [projectId]: r });
  }

  function exportCsv() {
    const token = getStoredToken();
    fetch(`/api/export/rankings.csv?hackathon_id=${hackathonId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "skillforge_rankings.csv";
        a.click();
      });
  }

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-4">Rankings</h1>
      <HackathonPicker />

      <div className="sf-card p-5 mb-6 flex flex-wrap items-center gap-3">
        <label className="sf-label m-0">Normalization method</label>
        <select className="sf-input w-48" value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="z_score">z-score (judge-relative)</option>
          <option value="min_max">min-max (judge-relative)</option>
          <option value="none">none (raw average)</option>
        </select>
        <button className="sf-btn sf-btn-primary" onClick={runAndPublish}>Run normalization &amp; publish</button>
        <button className="sf-btn sf-btn-secondary" onClick={exportCsv} disabled={!official.length}>Export CSV</button>
      </div>
      {error && <p className="text-sm text-wine mb-4">{error}</p>}
      {runResult && <p className="text-xs text-copper mb-4">Normalization run {runResult.run_id.slice(0, 8)}… computed over {runResult.scores.length} project(s).</p>}

      <h3 className="font-display text-lg mb-3">Official ranking</h3>
      {!official.length ? (
        <p className="text-muted text-sm">No official ranking published yet.</p>
      ) : (
        <div className="space-y-3">
          {official.map((r) => (
            <div key={r.project_id} className="sf-card p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">#{r.rank} {r.project_name}</span>
                <span className="sf-badge">{r.final_score}</span>
              </div>
              <button className="text-xs text-copper mt-2" onClick={() => loadWhy(r.project_id)}>Why this score?</button>
              {why[r.project_id] && (
                <div className="mt-3 text-sm bg-surface2 rounded p-3 space-y-1">
                  <p>Evaluations: {why[r.project_id].num_evaluations} · method: {why[r.project_id].normalization_method}</p>
                  <p>Weighted raw score: {why[r.project_id].weighted_raw_score} → normalized: {why[r.project_id].normalized_score} → final: {why[r.project_id].final_score}</p>
                  <div className="pt-1">
                    {why[r.project_id].criterion_breakdown.map((c: any) => (
                      <p key={c.criterion} className="text-xs text-muted">{c.criterion} ({c.weight_percent}%): avg {c.average_score} across {c.num_scores} judge(s)</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
