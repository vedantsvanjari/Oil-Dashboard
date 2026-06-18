import { create } from 'zustand';
import { computeIndicators } from '../data/mockData';

// Static instrument catalog (display config only — NOT market data). Live prices and
// historical/intraday series are fetched from the backend and merged onto these
// entries. Only instruments the backend can actually serve are listed here.
//   backendSymbol -> the key/symbol used by /api/prices/* endpoints.
const INSTRUMENT_CATALOG = [
  { id: 'brent',      name: 'Brent Crude',   exchange: 'ICE',   unit: '$/bbl', decimals: 2, backendSymbol: 'brent' },
  { id: 'wti',        name: 'WTI Crude',     exchange: 'NYMEX', unit: '$/bbl', decimals: 2, backendSymbol: 'wti' },
  { id: 'rbob',       name: 'RBOB Gasoline', exchange: 'NYMEX', unit: '$/gal', decimals: 4, backendSymbol: 'gasoline' },
  { id: 'heatingOil', name: 'Heating Oil',   exchange: 'NYMEX', unit: '$/gal', decimals: 4, backendSymbol: 'heating_oil' },
];

// Build a fully-shaped instrument object so downstream components (PriceCard, etc.)
// never read undefined numeric fields. Fields the backend does not yet provide
// (change, high, low, volume, openInterest) default to 0 rather than fake values.
function buildInstrument(meta, livePrice, previous) {
  return {
    ...meta,
    price: typeof livePrice === 'number' ? livePrice : (previous?.price ?? 0),
    change: previous?.change ?? 0,
    changePercent: previous?.changePercent ?? 0,
    high: previous?.high ?? 0,
    low: previous?.low ?? 0,
    volume: previous?.volume ?? 0,
    openInterest: previous?.openInterest ?? 0,
    // Series are populated lazily by fetchHistoricalData / fetchIntradayData.
    dailyData: previous?.dailyData ?? [],
    intradayData: previous?.intradayData ?? [],
  };
}

const useLivePriceStore = create((set, get) => ({
  instruments: [],
  isConnected: false,
  isLoadingPrices: false,
  connectionError: null,

  isLoadingHistory: false,
  historyError: null,

  // Fetch latest live prices and (re)build the instrument list. Drives isConnected
  // off the real API result instead of a hardcoded flag.
  fetchLivePrices: async () => {
    set({ isLoadingPrices: true, connectionError: null });
    try {
      const response = await fetch('/api/prices/live');
      if (!response.ok) throw new Error(`Live prices request failed (${response.status})`);
      const data = await response.json();

      const prev = get().instruments;
      const instruments = INSTRUMENT_CATALOG.map((meta) => {
        const previous = prev.find((p) => p.id === meta.id);
        return buildInstrument(meta, data?.[meta.backendSymbol], previous);
      });

      set({ instruments, isConnected: true, isLoadingPrices: false, connectionError: null });
    } catch (err) {
      // Keep whatever instruments we already have; just flag the connection as down.
      set({ isConnected: false, isLoadingPrices: false, connectionError: err.message });
    }
  },

  fetchHistoricalData: async (instrumentId) => {
    const meta = INSTRUMENT_CATALOG.find((m) => m.id === instrumentId);
    if (!meta) {
      set({ historyError: `No historical data available for ${instrumentId}`, isLoadingHistory: false });
      return;
    }

    set({ isLoadingHistory: true, historyError: null });

    try {
      const response = await fetch(`/api/prices/history/${meta.backendSymbol}`);
      if (!response.ok) throw new Error('Failed to fetch historical data');
      const data = await response.json();

      const formattedData = data.map((d) => ({
        ...d,
        volume: 0,
        timestamp: new Date(d.date).getTime(),
      }));

      const enrichedData = computeIndicators(formattedData);

      set((state) => ({
        instruments: state.instruments.map((inst) =>
          inst.id === instrumentId ? { ...inst, dailyData: enrichedData } : inst
        ),
        isLoadingHistory: false,
      }));
    } catch (err) {
      set({ historyError: err.message, isLoadingHistory: false });
    }
  },

  // Pull persisted 15-minute intraday bars (from the backend ingestion task) to give
  // the 1D / 5D charts a dense series instead of sparse end-of-day points.
  fetchIntradayData: async (instrumentId) => {
    const meta = INSTRUMENT_CATALOG.find((m) => m.id === instrumentId);
    if (!meta) return;

    try {
      const response = await fetch(`/api/prices/intraday/${meta.backendSymbol}?days=5`);
      if (!response.ok) throw new Error('Failed to fetch intraday data');
      const data = await response.json();

      const formattedData = data.map((d) => ({
        ...d,
        volume: d.volume ?? 0,
        timestamp: new Date(d.timestamp).getTime(),
      }));

      const enrichedData = computeIndicators(formattedData);

      set((state) => ({
        instruments: state.instruments.map((inst) =>
          inst.id === instrumentId ? { ...inst, intradayData: enrichedData } : inst
        ),
      }));
    } catch {
      // Intraday is best-effort; the chart falls back to whatever it already has.
    }
  },
}));

export default useLivePriceStore;
