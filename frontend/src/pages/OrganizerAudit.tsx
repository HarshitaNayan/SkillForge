import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useHackathonPicker } from "./useHackathonPicker";

export default function OrganizerAudit() {
  const { hackathons, hackathonId, HackathonPicker } = useHackathonPicker();
  const [events, setEvents] = useState<any[]>([]);
  const [replay, setReplay] = useState<any[]>([]);
  const [tab, setTab] = useState<"log" | "replay">("log");

  useEffect(() => {
    if (!hackathonId) return;
    api.get(`/audit?hackathon_id=${hackathonId}&limit=300`).then(setEvents);
    api.get(`/scoring/replay?hackathon_id=${hackathonId}`).then(setReplay);
  }, [hackathonId]);

  if (!hackathons.length) return <p className="text-muted">Create a hackathon first.</p>;

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl mb-4">Audit log</h1>
      <HackathonPicker />
      <div className="flex gap-2 mb-4">
        <button className={`sf-badge ${tab === "log" ? "border-copper text-copper" : ""}`} onClick={() => setTab("log")}>Full log</button>
        <button className={`sf-badge ${tab === "replay" ? "border-copper text-copper" : ""}`} onClick={() => setTab("replay")}>Ranking replay</button>
      </div>

      {tab === "log" ? (
        <div className="space-y-1">
          {events.map((e) => (
            <div key={e.id} className="text-xs sf-card px-3 py-2 flex justify-between">
              <span><span className="text-copper">{e.action}</span> · {e.resource_type} {e.resource_id?.slice(0, 8)}</span>
              <span className="text-muted">{new Date(e.timestamp).toLocaleString()}</span>
            </div>
          ))}
          {!events.length && <p className="text-muted text-sm">No audit events yet.</p>}
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-xs text-muted mb-2">The actual stored sequence of events that produced the current ranking — not a scripted animation.</p>
          {replay.map((e, i) => (
            <div key={i} className="text-xs sf-card px-3 py-2 flex justify-between">
              <span>{i + 1}. <span className="text-copper">{e.action}</span></span>
              <span className="text-muted">{new Date(e.timestamp).toLocaleString()}</span>
            </div>
          ))}
          {!replay.length && <p className="text-muted text-sm">No ranking events yet.</p>}
        </div>
      )}
    </div>
  );
}
