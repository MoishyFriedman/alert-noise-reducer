import { useEffect, useState } from "react";
import { getIncidents, getStats } from "./api";
import type { Incident, Stats } from "./types";
import { NoiseReductionBanner } from "./components/NoiseReductionBanner";
import { IncidentTable } from "./components/IncidentTable";

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getIncidents()])
      .then(([s, i]) => {
        setStats(s);
        setIncidents(i);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Alert Noise Reducer</h1>
        <p className="subtitle">Raw alerts correlated into incidents</p>
      </header>

      {error && (
        <div className="error-banner">
          Failed to load from the API — is the backend running? ({error})
        </div>
      )}

      {stats && <NoiseReductionBanner stats={stats} />}

      {incidents ? (
        <IncidentTable incidents={incidents} />
      ) : (
        !error && <p className="loading">Loading incidents…</p>
      )}
    </div>
  );
}
