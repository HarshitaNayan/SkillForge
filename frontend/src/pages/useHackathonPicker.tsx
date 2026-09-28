import React, { useEffect, useState } from "react";
import { api } from "../api/client";

export function useHackathonPicker() {
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [hackathonId, setHackathonId] = useState("");

  useEffect(() => {
    api.get("/hackathons").then((hs) => {
      setHackathons(hs);
      if (hs.length) setHackathonId(hs[0].id);
    });
  }, []);

  function HackathonPicker() {
    if (hackathons.length <= 1) return null;
    return (
      <select className="sf-input mb-4 max-w-xs" value={hackathonId} onChange={(e) => setHackathonId(e.target.value)}>
        {hackathons.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
      </select>
    );
  }

  return { hackathons, hackathonId, setHackathonId, HackathonPicker };
}
