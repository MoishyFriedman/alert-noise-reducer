import type { Stats } from "../types";

export function NoiseReductionBanner({ stats }: { stats: Stats }) {
  return (
    <div className="banner">
      <div className="banner-figure">
        <span className="banner-number">{stats.raw_alerts}</span>
        <span className="banner-label">raw alerts</span>
      </div>
      <span className="banner-arrow">&rarr;</span>
      <div className="banner-figure">
        <span className="banner-number">{stats.incidents}</span>
        <span className="banner-label">incidents</span>
      </div>
      <div className="banner-reduction">
        <span className="banner-pct">{stats.reduction_pct}%</span>
        <span className="banner-label">noise reduction</span>
      </div>
    </div>
  );
}
