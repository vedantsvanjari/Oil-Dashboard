import { create } from 'zustand';
import { instruments as mockInstruments, tickerItems as mockTickerItems, computeIndicators } from '../data/mockData';

const useLivePriceStore = create((set, get) => ({
  instruments: mockInstruments,
  tickerItems: mockTickerItems,
  isConnected: true, // Mock connection as true
  
  isLoadingHistory: false,
  historyError: null,
  
  fetchHistoricalData: async (instrumentId) => {
    const symbolMap = {
      'brent': 'brent',
      'wti': 'wti',
      'rbob': 'gasoline',
      'heatingOil': 'heating_oil',
    };
    
    const backendSymbol = symbolMap[instrumentId];
    if (!backendSymbol) {
        set({ historyError: `No historical data available for ${instrumentId}`, isLoadingHistory: false });
        return;
    }

    set({ isLoadingHistory: true, historyError: null });
    
    try {
      const response = await fetch(`/api/prices/history/${backendSymbol}`);
      if (!response.ok) throw new Error('Failed to fetch historical data');
      const data = await response.json();
      
      const formattedData = data.map(d => ({
          ...d,
          volume: 0,
          timestamp: new Date(d.date).getTime()
      }));
      
      const enrichedData = computeIndicators(formattedData);
      
      set(state => {
        const updatedInstruments = state.instruments.map(inst => {
            if (inst.id === instrumentId) {
                return { ...inst, dailyData: enrichedData };
            }
            return inst;
        });
        return { instruments: updatedInstruments, isLoadingHistory: false };
      });
      
    } catch (err) {
        set({ historyError: err.message, isLoadingHistory: false });
    }
  }
}));

export default useLivePriceStore;
