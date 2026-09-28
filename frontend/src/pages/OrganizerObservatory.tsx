import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerObservatory() {
  const { hackathons, hackathonId, HackathonPicker } = useHackathonPicker();
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (hackathonId) api.get(`/scoring/observatory?hackathon_id=${hackathonId}`).then(setStats);
  }, [hackathonId]);

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;
  if (!stats) return <p className="text-muted">Loading…</p>;

  const stat = (label: string, value: any) => (
    <div className="sf-card p-4">
      <p className="text-2xl font-display">{value}</p>
      <p className="text-xs text-muted mt-1">{label}</p>
    </div>
  );

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-4">Judging observatory</h1>
      <HackathonPicker />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {stat("Submissions", stats.total_submissions)}
        {stat("Assignments", stats.total_assignments)}
        {stat("Evaluations locked", stats.completed_evaluations)}
        {stat("Pending", stats.pending_evaluations)}
      </div>
      <p className="text-sm text-muted mb-8">
        Assignment coverage: {stats.assignment_coverage_percent}%
        {stats.normalization_last_run && ` — normalization last run ${new Date(stats.normalization_last_run).toLocaleString()} (${stats.normalization_method})`}
      </p>

      <h3 className="font-display text-lg mb-3">Judge score distributions</h3>
      <div className="space-y-2">
        {stats.judge_score_distributions.map((j: any) => (
          <div key={j.judge_id} className="sf-card p-4 flex items-center justify-between text-sm">
            <span>{j.judge_name}</span>
            <span className="text-muted">n={j.count} · avg {j.average} · range {j.min}–{j.max}</span>
          </div>
        ))}
        {!stats.judge_score_distributions.length && <p className="text-muted text-sm">No locked evaluations yet.</p>}
      </div>
    </div>
  );
}
