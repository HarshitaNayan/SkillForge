import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import NetworkBackground from "../components/NetworkBackground";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="-mx-5 -my-8">
      {/* ---------- Hero ---------- */}
      <section className="relative overflow-hidden border-b border-border">
        <NetworkBackground />
        <div className="relative z-10 max-w-6xl mx-auto px-5 pt-20 pb-24">
          <p className="sf-badge mb-5">Skills → Team → Claims &amp; Evidence → Judging → Ranking</p>
          <h1 className="font-display text-5xl md:text-6xl leading-[1.05] mb-6 max-w-2xl">
            Build the right team.
            <br />
            Prove what you built.
          </h1>
          <p className="text-muted text-lg mb-9 max-w-xl leading-relaxed">
            SkillForge matches participants by complementary skill, has teams state exactly what
            their project claims to implement with evidence behind each claim, and gives judges a
            reproducible, auditable scoring process — normalized so a harsh judge and a generous
            judge don't quietly decide the outcome.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/hackathons" className="sf-btn sf-btn-primary">Browse hackathons</Link>
            <Link to="/projects" className="sf-btn sf-btn-secondary">View the gallery</Link>
            {!user && <Link to="/register" className="sf-btn sf-btn-secondary">Get started</Link>}
          </div>
        </div>
      </section>

      {/* ---------- Pipeline ---------- */}
      <section className="border-b border-border">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <h2 className="font-display text-2xl mb-2">How a project moves through SkillForge</h2>
          <p className="text-muted text-sm mb-10 max-w-lg">
            One pipeline, six real stages. Each stage is a working part of the product, not a
            diagram of an idea.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border rounded-md overflow-hidden">
            {PIPELINE.map((step, i) => (
              <div key={step.title} className="bg-surface p-6">
                <span className="text-copper font-display text-sm">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="font-display text-lg mt-2 mb-1.5">{step.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="border-b border-border">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <h2 className="font-display text-2xl mb-10">What actually makes this different</h2>
          <div className="grid sm:grid-cols-2 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="sf-card p-6">
                <h3 className="font-display text-lg mb-2 text-ink">{f.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Honesty strip ---------- */}
      <section className="border-b border-border bg-surface">
        <div className="max-w-6xl mx-auto px-5 py-14">
          <h2 className="font-display text-xl mb-6">Built to be checked, not taken on faith</h2>
          <div className="grid sm:grid-cols-3 gap-6 text-sm">
            {FACTS.map((f) => (
              <div key={f.label}>
                <p className="font-display text-2xl text-copper mb-1">{f.stat}</p>
                <p className="text-muted">{f.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section>
        <div className="max-w-6xl mx-auto px-5 py-20 text-center">
          <h2 className="font-display text-3xl mb-4">Ready to see it in action?</h2>
          <p className="text-muted mb-8 max-w-md mx-auto">
            Browse the current hackathon and its published rankings, or register to form a team.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link to="/hackathons" className="sf-btn sf-btn-primary">Browse hackathons</Link>
            {!user && <Link to="/register" className="sf-btn sf-btn-secondary">Create an account</Link>}
          </div>
        </div>
      </section>
    </div>
  );
}

const PIPELINE = [
  { title: "Skills", body: "Participants list what they have (with proficiency) and what they're looking for." },
  { title: "Team formation", body: "Complementary-skill matching, with the reasoning shown — never a mystery score." },
  { title: "Claims & evidence", body: "Teams state exactly what they built, and attach evidence per claim." },
  { title: "Judging", body: "Assigned judges score against a weighted rubric. Conflicts of interest are enforced, not just asked about." },
  { title: "Normalization", body: "Judge-relative z-scoring corrects for harsh vs. generous grading before ranking." },
  { title: "Ranking & audit", body: "A published ranking, a replayable history, and a lab for what-if scenarios that never touch the official result." },
];

const FEATURES = [
  {
    title: "Explainable matching, not a black box",
    body: "Every teammate suggestion comes with the skills it covers, what's still missing, and a plain-language reason — never just a percentage.",
  },
  {
    title: "Claims don't grade themselves",
    body: "Evidence attached to a claim never auto-marks it \"verified.\" A judge always makes that call — the system won't do it for them.",
  },
  {
    title: "Judging integrity, enforced server-side",
    body: "Blind judging, conflict-of-interest recusal, and score locking are checked on every request — not just hidden in the interface.",
  },
  {
    title: "Ranking Lab, without risk to the real result",
    body: "Run what-if scenarios — remove a judge, change rubric weights — against real data. The official, published ranking never changes underneath it.",
  },
];

const FACTS = [
  { stat: "57", label: "real API routes — every button in this app calls one of them" },
  { stat: "16", label: "automated tests covering RBAC, conflicts of interest, and score locking" },
  { stat: "0", label: "hardcoded rankings, fake charts, or mock judging results" },
];

export function Hackathons() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/hackathons").then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted">Loading…</p>;
  if (!items.length) return <EmptyState title="No hackathons yet" body="Once an organizer creates one, it will show up here." />;

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl mb-4">Hackathons</h1>
      {items.map((h) => (
        <Link to={`/hackathons/${h.id}`} key={h.id} className="sf-card p-5 block hover:border-copper transition-colors">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg">{h.name}</h2>
            <span className="sf-badge">{h.status}</span>
          </div>
          {h.tagline && <p className="text-muted text-sm mt-1">{h.tagline}</p>}
          <p className="text-xs text-muted mt-3">Submission deadline: {new Date(h.submission_deadline).toLocaleString()}</p>
        </Link>
      ))}
    </div>
  );
}

export function HackathonDetail({ id }: { id: string }) {
  const [h, setH] = useState<any>(null);
  useEffect(() => { api.get(`/hackathons/${id}`).then(setH); }, [id]);
  if (!h) return <p className="text-muted">Loading…</p>;
  return (
    <div className="max-w-2xl">
      <span className="sf-badge">{h.status}</span>
      <h1 className="font-display text-3xl mt-3 mb-2">{h.name}</h1>
      {h.tagline && <p className="text-copper mb-4">{h.tagline}</p>}
      {h.description && <p className="text-muted mb-6 whitespace-pre-wrap">{h.description}</p>}
      <div className="sf-card p-5 grid grid-cols-2 gap-4 text-sm">
        <div><span className="sf-label">Submission deadline</span>{new Date(h.submission_deadline).toLocaleString()}</div>
        <div><span className="sf-label">Team size</span>{h.min_team_size}–{h.max_team_size} members</div>
        <div><span className="sf-label">Blind judging</span>{h.blind_judging ? "Enabled" : "Disabled"}</div>
      </div>
      {h.rules && (
        <div className="mt-6">
          <h3 className="font-display text-lg mb-2">Rules</h3>
          <p className="text-muted text-sm whitespace-pre-wrap">{h.rules}</p>
        </div>
      )}
      <div className="mt-6">
        <Link to={`/projects?hackathon_id=${h.id}`} className="sf-btn sf-btn-secondary">View submitted projects</Link>
      </div>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="sf-card p-10 text-center max-w-md mx-auto">
      <p className="font-display text-lg mb-1">{title}</p>
      <p className="text-muted text-sm">{body}</p>
    </div>
  );
}