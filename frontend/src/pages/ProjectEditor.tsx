import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

const EVIDENCE_TYPES = [
  "repository", "demo", "documentation", "architecture_diagram", "screenshot", "test_result", "explanation",
];

export function NewProject() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [hackathonId, setHackathonId] = useState("");
  const [team, setTeam] = useState<any>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/hackathons").then(async (hs) => {
      if (!hs.length) return;
      setHackathonId(hs[0].id);
      const teams = await api.get(`/teams?hackathon_id=${hs[0].id}`);
      const mine = teams.find((t: any) => t.members.some((m: any) => m.user_id === user?.id));
      setTeam(mine || null);
    });
  }, [user]);

  async function create() {
    setError(null);
    try {
      const p = await api.post("/projects", { team_id: team.id, hackathon_id: hackathonId, name });
      navigate(`/projects/${p.id}/edit`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create project");
    }
  }

  if (!team) return <p className="text-muted">You need to be on a team before starting a project. <a href="/team" className="text-copper">Go to Team →</a></p>;

  return (
    <div className="max-w-md sf-card p-6">
      <h1 className="font-display text-xl mb-4">Start a project for {team.name}</h1>
      <label className="sf-label">Project name</label>
      <input className="sf-input mb-4" value={name} onChange={(e) => setName(e.target.value)} />
      {error && <p className="text-sm text-wine mb-3">{error}</p>}
      <button className="sf-btn sf-btn-primary" onClick={create} disabled={!name.trim()}>Create draft</button>
    </div>
  );
}

export function ProjectEditor() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [claimTitle, setClaimTitle] = useState("");
  const [evidenceDrafts, setEvidenceDrafts] = useState<Record<string, { type: string; content: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function load() {
    if (!id) return;
    api.get(`/projects/${id}`).then((p) => { setProject(p); setForm(p); });
  }
  useEffect(load, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const locked = project?.status === "locked";

  async function saveDraft() {
    setError(null);
    setSaved(false);
    try {
      const p = await api.patch(`/projects/${id}`, {
        name: form.name, short_description: form.short_description, detailed_description: form.detailed_description,
        technologies: form.technologies, repo_url: form.repo_url, demo_url: form.demo_url,
      });
      setProject(p);
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save");
    }
  }

  async function submit() {
    setError(null);
    try {
      const p = await api.post(`/projects/${id}/submit`);
      setProject(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not submit");
    }
  }

  async function addClaim() {
    if (!claimTitle.trim()) return;
    setError(null);
    try {
      await api.post(`/projects/${id}/claims`, { title: claimTitle });
      setClaimTitle("");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add claim");
    }
  }

  async function deleteClaim(claimId: string) {
    await api.del(`/projects/${id}/claims/${claimId}`).catch((e) => setError(e instanceof ApiError ? e.message : "Could not delete"));
    load();
  }

  async function addEvidence(claimId: string) {
    const draft = evidenceDrafts[claimId];
    if (!draft?.content?.trim()) return;
    setError(null);
    try {
      await api.post(`/projects/${id}/claims/${claimId}/evidence`, { type: draft.type || "repository", content: draft.content });
      setEvidenceDrafts({ ...evidenceDrafts, [claimId]: { type: "repository", content: "" } });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add evidence");
    }
  }

  async function deleteEvidence(claimId: string, evidenceId: string) {
    await api.del(`/projects/${id}/claims/${claimId}/evidence/${evidenceId}`).catch(() => {});
    load();
  }

  if (!project) return <p className="text-muted">Loading…</p>;

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="font-display text-2xl">{project.name}</h1>
        <span className="sf-badge">{project.status}</span>
      </div>

      {locked && <p className="text-sm text-wine bg-winedark/20 border border-winedark rounded px-3 py-2 mb-6">This project is locked — the submission deadline has passed and it can no longer be edited.</p>}
      {error && <p className="text-sm text-wine bg-winedark/20 border border-winedark rounded px-3 py-2 mb-4">{error}</p>}

      <section className="sf-card p-5 mb-6 space-y-3">
        <div>
          <label className="sf-label">Name</label>
          <input className="sf-input" disabled={locked} value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Short description</label>
          <input className="sf-input" disabled={locked} value={form.short_description || ""} onChange={(e) => setForm({ ...form, short_description: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Detailed description</label>
          <textarea className="sf-input" rows={4} disabled={locked} value={form.detailed_description || ""} onChange={(e) => setForm({ ...form, detailed_description: e.target.value })} />
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="sf-label">Technologies</label>
            <input className="sf-input" disabled={locked} value={form.technologies || ""} onChange={(e) => setForm({ ...form, technologies: e.target.value })} />
          </div>
          <div>
            <label className="sf-label">Repository URL</label>
            <input className="sf-input" disabled={locked} value={form.repo_url || ""} onChange={(e) => setForm({ ...form, repo_url: e.target.value })} />
          </div>
          <div>
            <label className="sf-label">Demo URL</label>
            <input className="sf-input" disabled={locked} value={form.demo_url || ""} onChange={(e) => setForm({ ...form, demo_url: e.target.value })} />
          </div>
        </div>
        <div className="flex gap-2 pt-2">
          <button className="sf-btn sf-btn-secondary" onClick={saveDraft} disabled={locked}>Save draft</button>
          {project.status === "draft" && <button className="sf-btn sf-btn-primary" onClick={submit}>Submit project</button>}
          {saved && <span className="text-xs text-copper self-center">Saved.</span>}
        </div>
      </section>

      <h3 className="font-display text-lg mb-3">Claims &amp; evidence</h3>
      <p className="text-xs text-muted mb-4">Declare exactly what your project implements. Judges decide whether the evidence actually backs each claim.</p>
      <div className="space-y-4 mb-6">
        {project.claims.map((c: any) => (
          <div key={c.id} className="sf-card p-4">
            <div className="flex items-center justify-between">
              <p className="font-medium">{c.title}</p>
              {!locked && <button className="text-xs text-muted hover:text-wine" onClick={() => deleteClaim(c.id)}>Delete claim</button>}
            </div>
            <div className="mt-2 space-y-1">
              {c.evidence.map((e: any) => (
                <div key={e.id} className="flex items-center justify-between text-sm bg-surface2 rounded px-3 py-1.5">
                  <span><span className="sf-badge mr-2">{e.type.replace(/_/g, " ")}</span>{e.content}</span>
                  {!locked && <button className="text-xs text-muted hover:text-wine" onClick={() => deleteEvidence(c.id, e.id)}>×</button>}
                </div>
              ))}
              {!c.evidence.length && <p className="text-xs text-muted">No evidence attached yet. Add evidence to support this claim.</p>}
            </div>
            {!locked && (
              <div className="flex gap-2 mt-3">
                <select className="sf-input w-40" value={evidenceDrafts[c.id]?.type || "repository"}
                        onChange={(e) => setEvidenceDrafts({ ...evidenceDrafts, [c.id]: { type: e.target.value, content: evidenceDrafts[c.id]?.content || "" } })}>
                  {EVIDENCE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
                <input className="sf-input" placeholder="URL or explanation" value={evidenceDrafts[c.id]?.content || ""}
                       onChange={(e) => setEvidenceDrafts({ ...evidenceDrafts, [c.id]: { type: evidenceDrafts[c.id]?.type || "repository", content: e.target.value } })} />
                <button className="sf-btn sf-btn-secondary" onClick={() => addEvidence(c.id)}>Add</button>
              </div>
            )}
          </div>
        ))}
        {!project.claims.length && <p className="text-muted text-sm">No claims yet.</p>}
      </div>
      {!locked && (
        <div className="flex gap-2">
          <input className="sf-input" placeholder="New claim title, e.g. Authentication" value={claimTitle} onChange={(e) => setClaimTitle(e.target.value)} />
          <button className="sf-btn sf-btn-primary" onClick={addClaim}>Add claim</button>
        </div>
      )}
    </div>
  );
}
