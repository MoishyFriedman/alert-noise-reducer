// Mirrors backend/app/schemas.py field-for-field.

export type Severity = "critical" | "warning" | "info";
export type SeverityTier = "info" | "actionable";
export type CorrelationKind = "base" | "cascade";

export interface Incident {
  id: string;
  title: string;
  host: string | null;
  service: string;
  severity_tier: SeverityTier;
  max_severity: Severity;
  alert_count: number;
  first_seen: string; // ISO
  last_seen: string; // ISO
  duration_s: number;
  crit_count: number;
  warn_count: number;
  info_count: number;
  correlation: CorrelationKind;
  dependency: string | null;
}

export interface Alert {
  id: string;
  timestamp: string; // ISO
  host: string;
  service: string;
  severity: Severity;
  message: string;
  tags: string[];
}

export interface Stats {
  raw_alerts: number;
  incidents: number;
  reduction_pct: number;
}
