import { useState, useEffect } from 'react';

export function useMacroData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [latestRes, historyRes] = await Promise.all([
          fetch('/api/macro/latest'),
          fetch('/api/macro/history')
        ]);
        
        if (!latestRes.ok || !historyRes.ok) {
          throw new Error('Failed to fetch macro data');
        }
        
        const latest = await latestRes.json();
        const history = await historyRes.json();
        
        // history is descending order [latest, previous, ...]
        let dxyChange = 0;
        let us10yChange = 0;
        let yieldCurveChange = 0;
        
        // Find the most recent record before the latest date
        const prev = history.find(r => r.date < latest.date);
        
        if (prev) {
            dxyChange = latest.dxy - prev.dxy;
            us10yChange = latest.us10y - prev.us10y;
            yieldCurveChange = latest.yield_curve - prev.yield_curve;
        }

        setData({
            dxy: {
                value: latest.dxy,
                change: dxyChange
            },
            us10y: {
                value: latest.us10y,
                change: us10yChange
            },
            yield_curve: {
                value: latest.yield_curve,
                change: yieldCurveChange
            },
            timestamp: latest.timestamp
        });
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
