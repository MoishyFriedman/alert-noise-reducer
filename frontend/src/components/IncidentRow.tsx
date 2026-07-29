import { useEffect, useState } from "react";
import type { Alert, Incident } from "../types";
import { getIncidentAlerts } from "../api";
import { fmtDuration, fmtTime } from "../format";
import { SeverityBadge } from "./SeverityBadge";
import { AlertDrilldown } from "./AlertDrilldown";

export function IncidentRow({
  incident,
  expanded,
  onToggle,
}: {
  incident: Incident;
  expanded: boolean;
  onToggle: () => void;
}) {

  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!expanded || alerts !== null || loading) return;
    setLoading(true);
    setError(null);
    getIncidentAlerts(incident.id)
      .then(setAlerts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [expanded, alerts, loading, incident.id]);

  return (
    <>
      <tr className={`incident-row ${expanded ? "expanded" : ""}`} onClick={onToggle}>
        <td>
          <SeverityBadge severity={incident.max_severity} />
        </td>
        <td className="incident-title">
          <span className="caret">{expanded ? "▾" : "▸"}</span>
          {incident.title}
          {incident.correlation === "cascade" && (
            <span className="chip chip-cascade">⛓ cascade · {incident.dependency}</span>
          )}
        </td>
        <td className="mono">
          {incident.alert_count}
          <span className="breakdown">
            {incident.crit_count > 0 && ` ${incident.crit_count} 🔴`}
            {incident.warn_count > 0 && ` ${incident.warn_count} 🟠`}
            {incident.info_count > 0 && ` ${incident.info_count} ⚪`}
          </span>
        </td>
        <td className="mono">{fmtTime(incident.first_seen)}</td>
        <td className="mono">{fmtTime(incident.last_seen)}</td>
        <td className="mono">{fmtDuration(incident.duration_s)}</td>
      </tr>
      {expanded && (
        <tr className="drilldown-row">
          <td colSpan={6}>
            <AlertDrilldown alerts={alerts} loading={loading} error={error} />
          </td>
        </tr>
      )}
    </>
  );
}
