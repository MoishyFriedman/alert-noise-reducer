import type { Alert } from "../types";
import { fmtTime } from "../format";
import { SeverityBadge } from "./SeverityBadge";

export function AlertDrilldown({
  alerts,
  loading,
  error,
}: {
  alerts: Alert[] | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <div className="drilldown drilldown-status">Loading alerts…</div>;
  if (error) return <div className="drilldown drilldown-status drilldown-error">{error}</div>;
  if (!alerts) return null;

  return (
    <div className="drilldown">
      <table className="drilldown-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Host</th>
            <th>Service</th>
            <th>Severity</th>
            <th>Message</th>
            <th>Tags</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td className="mono">{fmtTime(alert.timestamp)}</td>
              <td className="mono">{alert.host}</td>
              <td>{alert.service}</td>
              <td>
                <SeverityBadge severity={alert.severity} />
              </td>
              <td>{alert.message}</td>
              <td className="tags">
                {alert.tags.map((t) => (
                  <span className="tag" key={t}>
                    {t}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
