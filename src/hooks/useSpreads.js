import { useState, useEffect } from 'react';

export function useSpreads() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const pairs = [
          { c: 'wti', c1: 'M1', c2: 'M2' },
          { c: 'wti', c1: 'M1', c2: 'M6' },
          { c: 'wti', c1: 'M1', c2: 'M12' },
          { c: 'brent', c1: 'M1', c2: 'M2' },
          { c: 'brent', c1: 'M1', c2: 'M6' },
          { c: 'brent', c1: 'M1', c2: 'M12' }
        ];

        const results = await Promise.all(
          pairs.map(async ({ c, c1, c2 }) => {
            const key = `${c}_${c1}-${c2}`;
            try {
              const [latestRes, statsRes, histRes] = await Promise.all([
                fetch(`/api/spreads/latest?commodity=${c}&contract1=${c1}&contract2=${c2}`),
                fetch(`/api/spreads/statistics?commodity=${c}&contract1=${c1}&contract2=${c2}`),
                fetch(`/api/spreads/history?commodity=${c}&contract1=${c1}&contract2=${c2}&days=180`)
              ]);
              const latest = latestRes.ok ? await latestRes.json() : null;
              const stats = statsRes.ok ? await statsRes.json() : null;
              const hist = histRes.ok ? await histRes.json() : null;
              return { key, latest, stats, hist: hist ? hist.history : [] };
            } catch(e) {
              return { key, latest: null, stats: null, hist: [] };
            }
          })
        );
        
        const latestMap = {};
        const historyMap = {};
        
        results.forEach(r => {
           if (r.latest) {
               latestMap[r.key] = {
                   ...r.latest,
                   statistics: r.stats || {}
               };
           }
           if (r.hist) {
               historyMap[r.key] = r.hist;
           }
        });
        
        setData({ latest: latestMap, history: historyMap });
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
