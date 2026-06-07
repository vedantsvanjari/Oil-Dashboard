import { create } from 'zustand';
import { instruments as mockInstruments, tickerItems as mockTickerItems } from '../data/mockData';

const useLivePriceStore = create(() => ({
  instruments: mockInstruments,
  tickerItems: mockTickerItems,
  isConnected: true, // Mock connection as true
}));

export default useLivePriceStore;
