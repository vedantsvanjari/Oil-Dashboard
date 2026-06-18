import React, { useEffect } from 'react';
import { useTheme } from './theme/ThemeContext';
import useDashboardStore from './stores/dashboardStore';
import useLivePriceStore from './stores/livePriceStore';
import TopBar from './components/layout/TopBar';
import TickerTape from './components/layout/TickerTape';
import StatusBar from './components/layout/StatusBar';
import OverviewSection from './components/sections/OverviewSection';
import PricesSection from './components/sections/PricesSection';
import SpreadsSection from './components/sections/SpreadsSection';
import PhysicalSection from './components/sections/PhysicalSection';
import NewsSection from './components/sections/NewsSection';
import RegimeIntelligenceSection from './components/sections/RegimeIntelligenceSection';

function MainContent() {
  const activeTab = useDashboardStore((s) => s.activeTab);

  switch (activeTab) {
    case 'overview':
      return <OverviewSection />;
    case 'prices':
      return <PricesSection />;
    case 'spreads':
      return <SpreadsSection />;
    case 'physical':
      return <PhysicalSection />;
    case 'news':
      return <NewsSection />;
    case 'regimeIntelligence':
      return <RegimeIntelligenceSection />;
    default:
      return <OverviewSection />;
  }
}

export default function App() {
  const { colors } = useTheme();
  const fetchLivePrices = useLivePriceStore((s) => s.fetchLivePrices);

  // Poll live prices so the instrument list + connection status reflect reality.
  useEffect(() => {
    fetchLivePrices();
    const interval = setInterval(fetchLivePrices, 60000);
    return () => clearInterval(interval);
  }, [fetchLivePrices]);

  return (
    <div className="flex flex-col min-h-full" style={{ backgroundColor: colors.bgPrimary }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 50 }}>
        <TopBar />
        <TickerTape />
      </div>
      <div className="flex-1">
        <MainContent />
      </div>
      <StatusBar />
    </div>
  );
}
