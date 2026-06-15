import { useState, useEffect } from 'react';

export function useOpecData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        // Sole data source: /api/opec/production
        // Returns 420 monthly rows (1993-present + short-term EIA forecasts)
        // backed by PostgreSQL — no country-level data needed.
        const response = await fetch('/api/opec/production');
        if (!response.ok) {
          throw new Error('Failed to fetch OPEC production data');
        }
        const productionData = await response.json();

        // ── Build raw history array ──────────────────────────────────────
        // Normalise to {period: "YYYY-MM", value: <float>} so the existing
        // AreaChart (dataKey="value") and tooltip keep working without changes.
        const rawHistory = (productionData?.history ?? []).map((row) => ({
          period: row.month,       // "YYYY-MM"
          value: row.production,   // mb/d float
        }));

        // ── Filter out future EIA forecast months ────────────────────────
        // Compute the current calendar month as "YYYY-MM" from the local clock
        // and discard any record beyond it. YYYY-MM strings are zero-padded so
        // lexicographic comparison is safe.
        const now = new Date();
        const currentMonth =
          `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

        const history = rawHistory.filter((row) => row.period <= currentMonth);

        // ── Derive KPIs from filtered history only ───────────────────────
        const latestEntry = history.length > 0 ? history[history.length - 1] : null;
        const latestProduction = latestEntry != null
          ? parseFloat(latestEntry.value.toFixed(2))
          : null;

        let trend = 0;
        if (history.length >= 2) {
          trend = parseFloat(
            (history[history.length - 1].value - history[history.length - 2].value).toFixed(3)
          );
        }

        setData({
          totalProduction: {
            latest: latestProduction,
            trend,
            history,    // filtered — no future months
          },
          // Debug metadata (not rendered)
          _meta: {
            rawCount: rawHistory.length,
            filteredCount: history.length,
            currentMonth,
            latestDisplayedMonth: latestEntry?.period ?? null,
          },
        });
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    // Refresh every 15 minutes
    const interval = setInterval(fetchData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error };
}
