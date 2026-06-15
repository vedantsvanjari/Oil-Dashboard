import { useState, useEffect } from 'react';

export function useLiveTicker() {
  const [tickerItems, setTickerItems] = useState([]);
  const [benchmarks, setBenchmarks] = useState({
    brent: null,
    wti: null,
    m1m12: null,
    crack: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTickerData() {
      setLoading(true);
      setError(null);
      try {
        const [pricesRes, spreadRes, crackRes] = await Promise.all([
          fetch('/api/prices/live'),
          fetch('/api/spreads/latest'), // Wait, M1-M12 is statistics? Let's use spreads/brent-wti for ticker or spreads/latest? The backend has spreads/latest returning M1/M2 WTI. Let's fetch /api/spreads/latest and /api/crack/latest
          fetch('/api/crack/latest')
        ]);
        
        let pricesData = {};
        if (pricesRes.ok) pricesData = await pricesRes.json();
        
        let spreadData = {};
        if (spreadRes.ok) spreadData = await spreadRes.json();
        
        let crackData = {};
        if (crackRes.ok) crackData = await crackRes.json();

        // Build ticker items array
        const items = [];
        
        if (pricesData.brent != null && pricesData.brent !== 0) {
          items.push({ label: 'BRENT', value: pricesData.brent });
        }
        if (pricesData.wti != null && pricesData.wti !== 0) {
          items.push({ label: 'WTI', value: pricesData.wti });
        }
        if (pricesData.gasoline != null && pricesData.gasoline !== 0) {
          items.push({ label: 'RBOB', value: pricesData.gasoline });
        }
        if (pricesData.heating_oil != null && pricesData.heating_oil !== 0) {
          items.push({ label: 'HO', value: pricesData.heating_oil });
        }
        
        // Spread
        if (spreadData.spread != null) {
          items.push({ label: 'WTI M1-M2', value: spreadData.spread });
        }
        
        // Crack
        if (crackData.crack_spread != null) {
          const crackChange = crackData.crack_change_w_w;
          const hasCrackChange = crackChange != null;
          items.push({ 
            label: 'CRACK 3:2:1', 
            value: crackData.crack_spread, 
            ...(hasCrackChange && {
              change: crackChange, 
              changePercent: crackData.crack_spread !== 0 ? (crackChange / crackData.crack_spread) * 100 : 0 
            })
          });
        }

        setTickerItems(items);
        setBenchmarks({
          brent: pricesData.brent,
          wti: pricesData.wti,
          m1m12: spreadData.spread, // using spreads/latest which is M1-M2 for now
          crack: crackData.crack_spread,
          crackChange: crackData.crack_change_w_w || 0
        });

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    
    fetchTickerData();
    // Refresh every 60s
    const interval = setInterval(fetchTickerData, 60000);
    return () => clearInterval(interval);
  }, []);

  return { tickerItems, benchmarks, loading, error };
}
