import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerRubric() {
  const { hackathons, hackathonId, setHackathonId, HackathonPicker } = useHackathonPicker();
  const [criteria, setCriteria] = useState([
    { name: "Technical correctness", weight_percent: 40 },
    { name: "Innovation", weight_percent: 20 },
    { name: "Usability", weight_percent: 15 },
    { name: "Architecture", weight_percent: 15 },
    { name: "Documentation", weight_percent: 10 },
  ]);
  const [active, setActive] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!hackathonId) return;
    api.get(`/judging/rubrics/active?hackathon_id=${hackathonId}`).then(setActive).catch(() => setActive(null));
  }, [hackathonId]);

  const total = criteria.reduce((s, c) => s + Number(c.weight_percent || 0), 0);

  function update(i: number, field: string, value: string) {
    const next = [...criteria];
    (next[i] as any)[field] = field === "weight_percent" ? Number(value) : value;
    setCriteria(next);
  }

  async function save() {
    setError(null);
    setSaved(false);
    try {
      const r = await api.post("/judging/rubrics", { hackathon_id: hackathonId, name: "Standard Rubric", criteria });
      setActive(r);
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save rubric");
    }
  }

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl mb-4">Judging rubric</h1>
      <HackathonPicker />
      {active && (
        <p className="text-xs text-copper mb-4">
          Active rubric: {active.name} ({active.criteria.length} criteria). Saving below replaces it with a new active rubric.
        </p>
      )}
      <div className="sf-card p-5 space-y-3">
        {criteria.map((c, i) => (
          <div key={i} className="flex gap-3 items-center">
            <input className="sf-input flex-1" value={c.name} onChange={(e) => update(i, "name", e.target.value)} />
            <input className="sf-input w-24" type="number" value={c.weight_percent} onChange={(e) => update(i, "weight_percent", e.target.value)} />
            <span className="text-muted text-sm">%</span>
            <button className="text-xs text-muted hover:text-wine" onClick={() => setCriteria(criteria.filter((_, j) => j !== i))}>Remove</button>
          </div>
        ))}
        <button className="sf-btn sf-btn-secondary" onClick={() => setCriteria([...criteria, { name: "", weight_percent: 0 }])}>+ Add criterion</button>
        <p className={`text-sm ${total === 100 ? "text-copper" : "text-wine"}`}>Total weight: {total}% {total !== 100 && "(must equal 100%)"}</p>
        {error && <p className="text-sm text-wine">{error}</p>}
        {saved && <p className="text-sm text-copper">Rubric saved and active.</p>}
        <button className="sf-btn sf-btn-primary" onClick={save} disabled={total !== 100 || !hackathonId}>Save rubric</button>
      </div>
    </div>
  );
}
