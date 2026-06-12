import { useState, useEffect } from 'react';

export function useCorrelations() {
  const [data, setData] = useState({ product: null, spreads: null, macro: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [productRes, spreadsRes, macroRes] = await Promise.all([
          fetch('/api/correlations/product'),
          fetch('/api/correlations/spreads'),
          fetch('/api/correlations/macro')
        ]);
        
        if (!productRes.ok || !spreadsRes.ok || !macroRes.ok) {
          throw new Error('Failed to fetch correlation data');
        }
        
        const product = await productRes.json();
        const spreads = await spreadsRes.json();
        const macro = await macroRes.json();
        
        setData({
          product,
          spreads,
          macro
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
