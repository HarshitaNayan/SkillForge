import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { EmptyState } from "./Home";

export function JudgeQueue() {
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [hackathonId, setHackathonId] = useState("");
  const [queue, setQueue] = useState<any[]>([]);

  useEffect(() => {
    api.get("/hackathons").then((hs) => {
      setHackathons(hs);
      if (hs.length) setHackathonId(hs[0].id);
    });
  }, []);

  useEffect(() => {
    if (hackathonId) api.get(`/judging/my-projects?hackathon_id=${hackathonId}`).then(setQueue);
  }, [hackathonId]);

  if (!hackathons.length) return <EmptyState title="No judging assignments yet" body="Once an organizer assigns you to a project, it will appear here." />;

  return (
    <div>
      <h1 className="font-display text-2xl mb-6">Your judging queue</h1>
      {!queue.length ? (
        <EmptyState title="No judging assignments yet" body="Once an organizer assigns you to a project, it will appear here." />
      ) : (
        <div className="space-y-3">
          {queue.map((item) => (
            <Link key={item.project_id} to={`/judge/projects/${item.project_id}`} className="sf-card p-4 flex items-center justify-between hover:border-copper block">
              <div>
                <p className="font-medium">{item.project_name}</p>
                <p className="text-sm text-muted">{item.short_description}</p>
                {item.team_name && <p className="text-xs text-copper mt-1">{item.team_name}</p>}
              </div>
              <span className="sf-badge">{item.evaluated ? "Evaluated" : "Pending"}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function JudgeEvaluate() {
  const { projectId } = useParams();
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [rubric, setRubric] = useState<any>(null);
  const [item, setItem] = useState<any>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.get("/hackathons").then(async (hs) => {
      setHackathons(hs);
      if (!hs.length) return;
      const hid = hs[0].id;
      const queue = await api.get(`/judging/my-projects?hackathon_id=${hid}`);
      const found = queue.find((q: any) => q.project_id === projectId);
      setItem(found);
      try {
        const r = await api.get(`/judging/rubrics/active?hackathon_id=${hid}`);
        setRubric(r);
        const initial: Record<string, number> = {};
        r.criteria.forEach((c: any) => { initial[c.id] = 5; });
        setScores(initial);
      } catch { /* no active rubric */ }
    });
  }, [projectId]);

  async function submit(final: boolean) {
    setError(null);
    try {
      const scoreList = Object.entries(scores).map(([criterion_id, score]) => ({ criterion_id, score }));
      await api.post("/judging/evaluations", { project_id: projectId, scores: scoreList, overall_comment: comment, submit_final: final });
      setDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not submit evaluation");
    }
  }

  if (!item || !rubric) return <p className="text-muted">Loading…</p>;
  if (done) return <div className="sf-card p-6"><p>Evaluation locked in. Thank you.</p><Link to="/judge" className="sf-btn sf-btn-secondary mt-4">Back to queue</Link></div>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl mb-1">{item.project_name}</h1>
      <p className="text-muted text-sm mb-6">{item.short_description}</p>

      <h3 className="font-display text-lg mb-3">Claims &amp; evidence</h3>
      <div className="space-y-3 mb-8">
        {item.claims.map((c: any) => (
          <div key={c.id} className="sf-card p-4">
            <p className="font-medium">{c.title}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {c.evidence.length ? c.evidence.map((e: any, i: number) => (
                <span key={i} className="sf-badge">{e.type.replace(/_/g, " ")}: {e.content}</span>
              )) : <span className="text-xs text-muted">No evidence provided.</span>}
            </div>
          </div>
        ))}
      </div>

      <h3 className="font-display text-lg mb-3">Score against: {rubric.name}</h3>
      <div className="sf-card p-5 space-y-4 mb-6">
        {rubric.criteria.map((c: any) => (
          <div key={c.id}>
            <div className="flex justify-between text-sm mb-1">
              <span>{c.name} <span className="text-muted">({c.weight_percent}%)</span></span>
              <span className="text-copper">{scores[c.id]}</span>
            </div>
            <input type="range" min={0} max={10} step={0.5} value={scores[c.id]}
                   onChange={(e) => setScores({ ...scores, [c.id]: Number(e.target.value) })} className="w-full" />
          </div>
        ))}
        <div>
          <label className="sf-label">Overall comment</label>
          <textarea className="sf-input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
      </div>
      {error && <p className="text-sm text-wine mb-4">{error}</p>}
      <div className="flex gap-2">
        <button className="sf-btn sf-btn-secondary" onClick={() => submit(false)}>Save draft</button>
        <button className="sf-btn sf-btn-primary" onClick={() => submit(true)}>Submit final (locks evaluation)</button>
      </div>
    </div>
  );
}

export function JudgeHistory() {
  const [evals, setEvals] = useState<any[]>([]);
  useEffect(() => { api.get("/judging/my-history").then(setEvals); }, []);
  return (
    <div>
      <h1 className="font-display text-2xl mb-6">Your judging history</h1>
      {!evals.length ? <EmptyState title="No evaluations yet" body="Evaluations you submit will show up here." /> : (
        <div className="space-y-3">
          {evals.map((e) => (
            <div key={e.id} className="sf-card p-4 flex justify-between items-center">
              <span className="text-sm">Project {e.project_id.slice(0, 8)}…</span>
              <span className="sf-badge">{e.locked ? "Locked" : "Draft"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
