import React, { useEffect, useState } from "react";
import { api } from "../api/client";

type Row = { skill_name: string; kind: "have" | "want"; proficiency: number | null };

export default function Skills() {
  const [rows, setRows] = useState<Row[]>([]);
  const [newHaveName, setNewHaveName] = useState("");
  const [newHaveProf, setNewHaveProf] = useState(70);
  const [newWantName, setNewWantName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get("/users/me/skills").then(setRows);
  }, []);

  async function save(next: Row[]) {
    setSaving(true);
    setSaved(false);
    const payload = next.map((r) => ({ skill_name: r.skill_name, kind: r.kind, proficiency: r.proficiency }));
    const result = await api.put("/users/me/skills", payload);
    setRows(result);
    setSaving(false);
    setSaved(true);
  }

  const have = rows.filter((r) => r.kind === "have");
  const want = rows.filter((r) => r.kind === "want");

  function addHave() {
    if (!newHaveName.trim()) return;
    const next = [...rows.filter((r) => !(r.kind === "have" && r.skill_name === newHaveName)),
      { skill_name: newHaveName.trim(), kind: "have" as const, proficiency: newHaveProf }];
    setNewHaveName("");
    save(next);
  }

  function addWant() {
    if (!newWantName.trim()) return;
    const next = [...rows.filter((r) => !(r.kind === "want" && r.skill_name === newWantName)),
      { skill_name: newWantName.trim(), kind: "want" as const, proficiency: null }];
    setNewWantName("");
    save(next);
  }

  function remove(kind: "have" | "want", name: string) {
    save(rows.filter((r) => !(r.kind === kind && r.skill_name === name)));
  }

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl mb-1">Your skill profile</h1>
      <p className="text-muted text-sm mb-6">
        This drives complementary team matching — proficiency is only used to explain matches, never hidden scoring.
      </p>

      <section className="sf-card p-5 mb-6">
        <h3 className="font-display text-lg mb-3">Skills you have</h3>
        <div className="space-y-2 mb-4">
          {have.map((r) => (
            <div key={r.skill_name} className="flex items-center gap-3">
              <span className="w-32 text-sm">{r.skill_name}</span>
              <div className="flex-1 h-2 bg-surface2 rounded">
                <div className="h-2 bg-wine rounded" style={{ width: `${r.proficiency}%` }} />
              </div>
              <span className="text-xs text-muted w-10">{r.proficiency}%</span>
              <button className="text-xs text-muted hover:text-wine" onClick={() => remove("have", r.skill_name)}>Remove</button>
            </div>
          ))}
          {!have.length && <p className="text-muted text-sm">No skills added yet.</p>}
        </div>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="sf-label">Skill name</label>
            <input className="sf-input" value={newHaveName} onChange={(e) => setNewHaveName(e.target.value)} placeholder="e.g. Frontend" />
          </div>
          <div className="w-32">
            <label className="sf-label">Proficiency: {newHaveProf}%</label>
            <input type="range" min={0} max={100} value={newHaveProf} onChange={(e) => setNewHaveProf(Number(e.target.value))} className="w-full" />
          </div>
          <button className="sf-btn sf-btn-secondary" onClick={addHave}>Add</button>
        </div>
      </section>

      <section className="sf-card p-5">
        <h3 className="font-display text-lg mb-3">Skills you're looking to team up with</h3>
        <div className="flex flex-wrap gap-2 mb-4">
          {want.map((r) => (
            <span key={r.skill_name} className="sf-badge flex items-center gap-2">
              {r.skill_name}
              <button className="text-muted hover:text-wine" onClick={() => remove("want", r.skill_name)}>×</button>
            </span>
          ))}
          {!want.length && <p className="text-muted text-sm">None yet.</p>}
        </div>
        <div className="flex gap-2">
          <input className="sf-input" value={newWantName} onChange={(e) => setNewWantName(e.target.value)} placeholder="e.g. DevOps" />
          <button className="sf-btn sf-btn-secondary" onClick={addWant}>Add</button>
        </div>
      </section>
      {saving && <p className="text-xs text-muted mt-3">Saving…</p>}
      {saved && !saving && <p className="text-xs text-copper mt-3">Saved.</p>}
    </div>
  );
}
