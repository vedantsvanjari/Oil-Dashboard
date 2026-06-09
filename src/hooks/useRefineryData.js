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

export function useRefineryData() {
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
          fetch('/api/refineries/latest'),
          fetch('/api/refineries/history')
        ]);
        
        if (!latestRes.ok || !historyRes.ok) {
          throw new Error('Failed to fetch refinery data');
        }
        
        const latest = await latestRes.json();
        const history = await historyRes.json();
        
        // Reverse history to be ascending for chart (oldest first)
        const ascHistory = [...history].reverse();
        
        // Map history to the shape the chart expects per metric
        const formattedHistory = {
          refinery_utilization: [],
          gross_inputs: [],
          gasoline_production: [],
          distillate_production: []
        };
        
        ascHistory.forEach(row => {
          ['refinery_utilization', 'gross_inputs', 'gasoline_production', 'distillate_production'].forEach(key => {
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
          refinery_utilization: { value: latest.refinery_utilization, weekChange: computeChange('refinery_utilization') },
          gross_inputs: { value: latest.gross_inputs, weekChange: computeChange('gross_inputs') },
          gasoline_production: { value: latest.gasoline_production, weekChange: computeChange('gasoline_production') },
          distillate_production: { value: latest.distillate_production, weekChange: computeChange('distillate_production') }
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
