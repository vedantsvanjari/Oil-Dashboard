import { create } from 'zustand';

const useDashboardStore = create((set) => ({
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab }),

  selectedInstrument: 'brent',
  setSelectedInstrument: (id) => set({ selectedInstrument: id }),

  priceTimeRange: '1Y',
  setPriceTimeRange: (range) => set({ priceTimeRange: range }),

  priceIndicators: { vwap: true, ema20: false, ema50: false, bb: false },
  toggleIndicator: (key) =>
    set((state) => ({
      priceIndicators: {
        ...state.priceIndicators,
        [key]: !state.priceIndicators[key],
      },
    })),

  selectedSpreadChart: 'm1m2',
  setSelectedSpreadChart: (id) => set({ selectedSpreadChart: id }),

  spreadTimeRange: '1Y',
  setSpreadTimeRange: (range) => set({ spreadTimeRange: range }),

  inventoryTab: 'crude',
  setInventoryTab: (tab) => set({ inventoryTab: tab }),

  newsCategory: 'All',
  setNewsCategory: (cat) => set({ newsCategory: cat }),

  newsSearch: '',
  setNewsSearch: (q) => set({ newsSearch: q }),

  selectedRegime: 'physical',
  setSelectedRegime: (id) => set({ selectedRegime: id }),

  // Overview: which fundamental signals are active in the sentiment engine
  sentimentSignals: {
    curveStructure: true,
    eiaInventory: true,
    opecCompliance: true,
    usdDxy: true,
    crackSpreads: true,
    geopoliticalRisk: true,
    rigCount: true,
    positioning: true,
    newsSentiment: true,
  },
  toggleSentimentSignal: (key) =>
    set((state) => ({
      sentimentSignals: {
        ...state.sentimentSignals,
        [key]: !state.sentimentSignals[key],
      },
    })),
  setAllSentimentSignals: (enabled) =>
    set((state) => {
      const updated = {};
      Object.keys(state.sentimentSignals).forEach((k) => { updated[k] = enabled; });
      return { sentimentSignals: updated };
    }),

  // Server-side Sentiment Engine Data
  sentimentData: null,
  isSentimentLoading: false,
  sentimentError: null,
  fetchSentimentData: async () => {
    set({ isSentimentLoading: true, sentimentError: null });
    try {
      const response = await fetch('/api/sentiment');
      if (!response.ok) throw new Error('Failed to fetch sentiment data');
      const data = await response.json();
      set({ sentimentData: data, isSentimentLoading: false });
    } catch (err) {
      set({ sentimentError: err.message, isSentimentLoading: false });
    }
  },
}));

export default useDashboardStore;
