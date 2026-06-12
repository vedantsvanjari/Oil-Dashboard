import { useState, useEffect } from 'react';

export function useCrackSpread() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [latestRes, statsRes, historyRes] = await Promise.all([
          fetch('/api/crack/latest'),
          fetch('/api/crack/statistics'),
          fetch('/api/crack/history?days=180')
        ]);
        
        if (!latestRes.ok) {
          throw new Error('Failed to fetch crack spread data');
        }
        
        const latest = await latestRes.json();
        const stats = statsRes.ok ? await statsRes.json() : null;
        const historyData = historyRes.ok ? await historyRes.json() : null;
        
        latest.statistics = stats || {};
        
        let day_change = 0;
        if (historyData && historyData.history && historyData.history.length >= 2) {
             const h = historyData.history;
             day_change = h[h.length - 1].crack_spread - h[h.length - 2].crack_spread;
        }
        latest.statistics.day_change = day_change;

        setData({ latest, history: historyData ? historyData.history : [] });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return { data, loading, error };
}
