import type { Alert, Incident, Stats } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const getStats = () => getJSON<Stats>("/api/stats");
export const getIncidents = () => getJSON<Incident[]>("/api/incidents");
export const getIncidentAlerts = (incidentId: string) =>
  getJSON<Alert[]>(`/api/incidents/${encodeURIComponent(incidentId)}/alerts`);
