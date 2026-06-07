import React from 'react';
import useLivePriceStore from '../../stores/livePriceStore';
import useDashboardStore from '../../stores/dashboardStore';
import PriceCard from '../ui/PriceCard';
import PriceChart from '../charts/PriceChart';
import { useTheme } from '../../theme/ThemeContext';

export default function PricesSection() {
  const { selectedInstrument, setSelectedInstrument } = useDashboardStore();
  const { colors } = useTheme();
  const { instruments } = useLivePriceStore();

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="section-header" style={{ fontSize: '14px' }}>INSTRUMENT OVERVIEW</div>

      {/* Instrument cards grid */}
      <div className="grid grid-cols-5 gap-16">
        {instruments.map((inst) => (
          <PriceCard
            key={inst.id}
            instrument={inst}
            isSelected={selectedInstrument === inst.id}
            onSelect={setSelectedInstrument}
          />
        ))}
      </div>

      {/* Chart area */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="flex items-center justify-between mb-4">
          <div className="section-header" style={{ fontSize: '14px' }}>
            {instruments.find((i) => i.id === selectedInstrument)?.name || 'Brent Crude'} — PRICE CHART
          </div>
        </div>
        <PriceChart />
      </div>
    </div>
  );
}
