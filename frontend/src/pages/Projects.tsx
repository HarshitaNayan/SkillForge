import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { EmptyState } from "./Home";

export default function ProjectsGallery() {
  const [params] = useSearchParams();
  const hackathonId = params.get("hackathon_id") || undefined;
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const qs = new URLSearchParams();
    if (hackathonId) qs.set("hackathon_id", hackathonId);
    if (q) qs.set("q", q);
    api.get(`/projects?${qs.toString()}`).then(setItems).finally(() => setLoading(false));
  }

  useEffect(load, [hackathonId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <h1 className="font-display text-2xl">Project gallery</h1>
        <form onSubmit={(e) => { e.preventDefault(); load(); }} className="flex gap-2">
          <input className="sf-input" placeholder="Search projects…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="sf-btn sf-btn-secondary">Search</button>
        </form>
      </div>
      {loading ? (
        <p className="text-muted">Loading…</p>
      ) : !items.length ? (
        <EmptyState title="No submitted projects yet" body="Once teams submit, their projects will appear here for anyone to browse." />
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {items.map((p) => (
            <Link to={`/projects/${p.id}`} key={p.id} className="sf-card p-5 block hover:border-copper transition-colors">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg">{p.name}</h2>
                <span className="sf-badge">{p.status}</span>
              </div>
              {p.short_description && <p className="text-muted text-sm mt-2">{p.short_description}</p>}
              {p.technologies && <p className="text-xs text-copper mt-3">{p.technologies}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProjectDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [project, setProject] = useState<any>(null);
  const [votes, setVotes] = useState(0);
  const [comments, setComments] = useState<any[]>([]);
  const [commentText, setCommentText] = useState("");
  const [voteError, setVoteError] = useState<string | null>(null);

  function load() {
    if (!id) return;
    api.get(`/projects/${id}`).then(setProject);
    api.get(`/community/projects/${id}/votes`).then((r) => setVotes(r.vote_count));
    api.get(`/community/projects/${id}/comments`).then(setComments);
  }

  useEffect(load, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function vote() {
    setVoteError(null);
    try {
      const r = await api.post(`/community/projects/${id}/vote`);
      setVotes(r.vote_count);
    } catch (e) {
      setVoteError(e instanceof ApiError ? e.message : "Could not vote");
    }
  }

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!commentText.trim()) return;
    await api.post(`/community/projects/${id}/comments?content=${encodeURIComponent(commentText)}`);
    setCommentText("");
    load();
  }

  if (!project) return <p className="text-muted">Loading…</p>;

  return (
    <div className="max-w-2xl">
      <span className="sf-badge">{project.status}</span>
      <h1 className="font-display text-3xl mt-3 mb-2">{project.name}</h1>
      {project.short_description && <p className="text-copper mb-4">{project.short_description}</p>}
      {project.detailed_description && <p className="text-muted mb-4 whitespace-pre-wrap">{project.detailed_description}</p>}
      <div className="flex gap-3 mb-6 text-sm">
        {project.repo_url && <a href={project.repo_url} target="_blank" rel="noreferrer" className="sf-btn sf-btn-secondary">Repository</a>}
        {project.demo_url && <a href={project.demo_url} target="_blank" rel="noreferrer" className="sf-btn sf-btn-secondary">Live demo</a>}
      </div>

      <h3 className="font-display text-lg mb-3">Claims &amp; evidence</h3>
      <div className="space-y-3 mb-8">
        {project.claims?.length ? project.claims.map((c: any) => (
          <div key={c.id} className="sf-card p-4">
            <p className="font-medium">{c.title}</p>
            {c.description && <p className="text-muted text-sm mt-1">{c.description}</p>}
            <div className="mt-2 flex flex-wrap gap-2">
              {c.evidence.length ? c.evidence.map((e: any) => (
                <span key={e.id} className="sf-badge">{e.type.replace(/_/g, " ")}</span>
              )) : <span className="text-xs text-muted">No evidence attached yet.</span>}
            </div>
          </div>
        )) : <p className="text-muted text-sm">No claims declared yet.</p>}
      </div>

      <div className="flex items-center gap-3 mb-8">
        <button className="sf-btn sf-btn-secondary" onClick={vote} disabled={!user}>
          Vote ({votes})
        </button>
        {!user && <span className="text-xs text-muted">Log in to vote</span>}
        {voteError && <span className="text-xs text-wine">{voteError}</span>}
      </div>

      <h3 className="font-display text-lg mb-3">Comments</h3>
      <div className="space-y-3 mb-4">
        {comments.map((c) => (
          <div key={c.id} className="sf-card p-3 text-sm">
            <p className="text-copper text-xs mb-1">{c.author}</p>
            <p>{c.content}</p>
          </div>
        ))}
        {!comments.length && <p className="text-muted text-sm">No comments yet.</p>}
      </div>
      {user && (
        <form onSubmit={submitComment} className="flex gap-2">
          <input className="sf-input" placeholder="Add a comment…" value={commentText} onChange={(e) => setCommentText(e.target.value)} />
          <button className="sf-btn sf-btn-primary">Post</button>
        </form>
      )}
    </div>
  );
}
