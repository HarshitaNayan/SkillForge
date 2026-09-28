import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

const empty = {
  name: "", tagline: "", description: "", rules: "",
  submission_deadline: "", registration_deadline: "", start_date: "", end_date: "",
  min_team_size: 1, max_team_size: 4, blind_judging: true,
};

export default function OrganizerHackathon() {
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [form, setForm] = useState<any>(empty);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function load() {
    api.get("/hackathons").then((hs) => {
      setHackathons(hs);
      if (hs.length && !selected) { setSelected(hs[0]); setForm(toFormShape(hs[0])); }
    });
  }
  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  function toFormShape(h: any) {
    return {
      ...h,
      submission_deadline: h.submission_deadline?.slice(0, 16),
      registration_deadline: h.registration_deadline?.slice(0, 16) || "",
      start_date: h.start_date?.slice(0, 16) || "",
      end_date: h.end_date?.slice(0, 16) || "",
    };
  }

  async function createNew() {
    setError(null);
    try {
      const h = await api.post("/hackathons", {
        name: form.name, tagline: form.tagline, description: form.description, rules: form.rules,
        submission_deadline: form.submission_deadline, min_team_size: Number(form.min_team_size),
        max_team_size: Number(form.max_team_size), blind_judging: form.blind_judging,
      });
      setSelected(h);
      setForm(toFormShape(h));
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create hackathon");
    }
  }

  async function saveEdits() {
    if (!selected) return;
    setError(null);
    setSaved(false);
    try {
      const h = await api.patch(`/hackathons/${selected.id}`, {
        name: form.name, tagline: form.tagline, description: form.description, rules: form.rules,
        submission_deadline: form.submission_deadline || undefined,
        min_team_size: Number(form.min_team_size), max_team_size: Number(form.max_team_size),
        blind_judging: form.blind_judging,
      });
      setSelected(h);
      setForm(toFormShape(h));
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save");
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl mb-6">Hackathon settings</h1>

      {hackathons.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {hackathons.map((h) => (
            <button key={h.id} className={`sf-badge ${selected?.id === h.id ? "border-copper text-copper" : ""}`}
                    onClick={() => { setSelected(h); setForm(toFormShape(h)); }}>{h.name}</button>
          ))}
          <button className="sf-badge" onClick={() => { setSelected(null); setForm(empty); }}>+ New</button>
        </div>
      )}

      <div className="sf-card p-5 space-y-3">
        <div>
          <label className="sf-label">Name</label>
          <input className="sf-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Tagline</label>
          <input className="sf-input" value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Description</label>
          <textarea className="sf-input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div>
          <label className="sf-label">Rules</label>
          <textarea className="sf-input" rows={3} value={form.rules} onChange={(e) => setForm({ ...form, rules: e.target.value })} />
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="sf-label">Submission deadline</label>
            <input type="datetime-local" className="sf-input" value={form.submission_deadline}
                   onChange={(e) => setForm({ ...form, submission_deadline: e.target.value })} />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input type="checkbox" checked={form.blind_judging} onChange={(e) => setForm({ ...form, blind_judging: e.target.checked })} />
            <label className="text-sm">Blind judging</label>
          </div>
          <div>
            <label className="sf-label">Min team size</label>
            <input type="number" min={1} className="sf-input" value={form.min_team_size} onChange={(e) => setForm({ ...form, min_team_size: e.target.value })} />
          </div>
          <div>
            <label className="sf-label">Max team size</label>
            <input type="number" min={1} className="sf-input" value={form.max_team_size} onChange={(e) => setForm({ ...form, max_team_size: e.target.value })} />
          </div>
        </div>
        {error && <p className="text-sm text-wine">{error}</p>}
        {saved && <p className="text-sm text-copper">Saved.</p>}
        <div className="flex gap-2 pt-2">
          {selected ? (
            <button className="sf-btn sf-btn-primary" onClick={saveEdits} disabled={!form.name || !form.submission_deadline}>Save changes</button>
          ) : (
            <button className="sf-btn sf-btn-primary" onClick={createNew} disabled={!form.name || !form.submission_deadline}>Create hackathon</button>
          )}
        </div>
      </div>
    </div>
  );
}
