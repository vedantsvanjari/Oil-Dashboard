import React, { useState } from 'react';
import { spreads, wtiBrentSpread, crackSpread } from '../../data/mockData';
import SpreadCard from '../ui/SpreadCard';
import SpreadChart from '../charts/SpreadChart';
import { useTheme } from '../../theme/ThemeContext';

export default function SpreadsSection() {
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const { colors } = useTheme();

  return (
    <div className="px-6 py-8 space-y-14" style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="section-header" style={{ fontSize: '14px' }}>CALENDAR SPREADS</div>

      {/* Top row: 4 calendar spread cards */}
      <div className="grid grid-cols-4 gap-5">
        {spreads.map((s) => (
          <SpreadCard key={s.id} spread={s} />
        ))}
      </div>

      {/* Second row: WTI-Brent + Crack Spread */}
      <div className="grid grid-cols-2 gap-5">
        <div className="p-5 border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>{wtiBrentSpread.name}</span>
          </div>
          <div className="data-value text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
            {wtiBrentSpread.value.toFixed(2)}
            <span className="text-sm ml-1.5" style={{ color: colors.textMuted }}>$/bbl</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Day Chg</span>
              <span className="data-value" style={{ color: colors.bearish, fontSize: '12px' }}>
                {wtiBrentSpread.dayChange.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>20D MA</span>
              <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
                {wtiBrentSpread.ma20.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Z-Score</span>
              <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
                {wtiBrentSpread.zScore.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Percentile</span>
              <span className="data-value px-2 py-0.5 rounded-md"
                style={{ backgroundColor: colors.bgElevated, color: colors.neutral, fontSize: '12px' }}>
                {wtiBrentSpread.percentile}%
              </span>
            </div>
          </div>
        </div>

        <div className="p-5 border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>{crackSpread.name}</span>
          </div>
          <div className="data-value text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
            ${crackSpread.value.toFixed(2)}
            <span className="text-sm ml-1.5" style={{ color: colors.textMuted }}>$/bbl</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Day Chg</span>
              <span className="data-value" style={{ color: colors.bullish, fontSize: '12px' }}>
                +{crackSpread.dayChange.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>20D MA</span>
              <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
                ${crackSpread.ma20.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Z-Score</span>
              <span className="data-value" style={{ color: colors.neutral, fontSize: '12px' }}>
                +{crackSpread.zScore.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: colors.textMuted, fontSize: '12px' }}>Percentile</span>
              <span className="data-value px-2 py-0.5 rounded-md"
                style={{ backgroundColor: colors.bgElevated, color: colors.neutral, fontSize: '12px' }}>
                {crackSpread.percentile}%
              </span>
            </div>
          </div>
          <div className="mt-3 text-sm leading-relaxed" style={{ color: colors.textMuted }}>
            {crackSpread.interpretation}
          </div>
        </div>
      </div>

      {/* Spread chart */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4" style={{ fontSize: '14px' }}>SPREAD CHART</div>
        <SpreadChart />
      </div>

      {/* Glossary */}
      <div className="border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <button
          onClick={() => setGlossaryOpen(!glossaryOpen)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm cursor-pointer"
          style={{ color: colors.textMuted }}
        >
          <span className="section-header">GLOSSARY</span>
          <span style={{ fontSize: '12px' }}>{glossaryOpen ? '▲' : '▼'}</span>
        </button>
        <div className={`glossary-content ${glossaryOpen ? 'open' : ''}`}>
          <div className="px-5 pb-4 space-y-3">
            <div>
              <span className="text-sm font-medium" style={{ color: colors.bullish }}>Backwardation: </span>
              <span className="text-sm" style={{ color: colors.textSecondary }}>
                When near-month futures trade at a premium to deferred months. Indicates physical market tightness and strong near-term demand. Bullish signal.
              </span>
            </div>
            <div>
              <span className="text-sm font-medium" style={{ color: colors.bearish }}>Contango: </span>
              <span className="text-sm" style={{ color: colors.textSecondary }}>
                When deferred futures trade at a premium to near-month contracts. Indicates ample supply and weak near-term demand. Often associated with inventory builds. Bearish signal.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
