import { useState, useEffect } from 'react';

// Generates pseudo 5-year bounds for chart visualization
function generatePseudo5Y(value) {
  const variation = value * 0.05; // 5% variation
  return {
    fiveYearAvg: +(value - variation * 0.2).toFixed(1),
    fiveYearMax: +(value + variation).toFixed(1),
    fiveYearMin: +(value - variation * 1.5).toFixed(1)
  };
}

export function useInventoryData() {
  const [latestData, setLatestData] = useState(null);
  const [historyData, setHistoryData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [latestRes, historyRes] = await Promise.all([
          fetch('/api/inventories'),
          fetch('/api/inventories/history')
        ]);
        
        if (!latestRes.ok || !historyRes.ok) {
          throw new Error('Failed to fetch inventory data');
        }
        
        const latest = await latestRes.json();
        const history = await historyRes.json();
        
        // Reverse history to be ascending for chart (oldest first)
        const ascHistory = [...history].reverse();
        
        // Map history to the shape the chart expects per product
        const formattedHistory = {
          crude: [],
          gasoline: [],
          distillate: [],
          spr: []
        };
        
        ascHistory.forEach(row => {
          ['crude', 'gasoline', 'distillate', 'spr'].forEach(key => {
            if (row[key] !== undefined) {
              formattedHistory[key].push({
                date: row.date,
                value: row[key],
                ...generatePseudo5Y(row[key])
              });
            }
          });
        });
        
        // Compute weekChange for latest stats
        const computeChange = (key) => {
          const arr = formattedHistory[key];
          if (arr.length >= 2) {
            return +(arr[arr.length - 1].value - arr[arr.length - 2].value).toFixed(1);
          }
          return 0;
        };

        const enrichedLatest = {
          crude: { value: latest.crude, weekChange: computeChange('crude') },
          gasoline: { value: latest.gasoline, weekChange: computeChange('gasoline') },
          distillate: { value: latest.distillate, weekChange: computeChange('distillate') },
          spr: { value: latest.spr, weekChange: computeChange('spr') }
        };

        setLatestData(enrichedLatest);
        setHistoryData(formattedHistory);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return { latestData, historyData, loading, error };
}
