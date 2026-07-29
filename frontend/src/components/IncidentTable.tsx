import { useState } from "react";
import type { Incident } from "../types";
import { IncidentRow } from "./IncidentRow";

export function IncidentTable({ incidents }: { incidents: Incident[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (incidents.length === 0) {
    return <p className="empty">No incidents.</p>;
  }

  return (
    <table className="incident-table">
      <thead>
        <tr>
          <th>Severity</th>
          <th>Incident</th>
          <th>Alerts</th>
          <th>First seen</th>
          <th>Last seen</th>
          <th>Duration</th>
        </tr>
      </thead>
      <tbody>
        {incidents.map((inc) => (
          <IncidentRow
            key={inc.id}
            incident={inc}
            expanded={expandedId === inc.id}
            onToggle={() => setExpandedId(expandedId === inc.id ? null : inc.id)}
          />
        ))}
      </tbody>
    </table>
  );
}
