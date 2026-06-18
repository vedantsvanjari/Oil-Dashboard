import React from 'react';
import { useTheme } from '../../theme/ThemeContext';
import {
  mockRegimeIntelligenceState,
  mockRegimeScores,
  mockMarketState,
  mockSignalMonitor,
  mockRegimeStats,
} from '../../data/mockData';

export default function RegimeIntelligenceSection() {
  const { colors } = useTheme();

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>

      {/* ═══════════ ROW 1: Regime Hero — matches KEY BENCHMARKS card ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4">REGIME INTELLIGENCE</div>
        <div className="grid grid-cols-4 gap-16">

          {/* Current Regime */}
          <div className="p-4 border rounded-lg col-span-2" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em', marginBottom: '8px' }}>CURRENT REGIME</div>
            <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
              {mockRegimeIntelligenceState.currentRegime}
            </div>
            <div className="mt-3" style={{ color: colors.textMuted, fontSize: '11px' }}>
              Last updated: {mockRegimeIntelligenceState.lastUpdated}
            </div>
          </div>

          {/* Confidence */}
          <div className="p-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>CONFIDENCE</span>
              <span className="px-1.5 py-0.5 rounded-sm" style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '9px', fontWeight: 600 }}>
                HIGH
              </span>
            </div>
            <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
              {mockRegimeIntelligenceState.confidence}%
            </div>
            <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
              <div className="h-full rounded-full" style={{ width: `${mockRegimeIntelligenceState.confidence}%`, backgroundColor: colors.bullish }} />
            </div>
          </div>

          {/* Regime Score */}
          <div className="p-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>REGIME SCORE</span>
            </div>
            <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
              {mockRegimeIntelligenceState.regimeScore}
            </div>
            <div className="mt-1 data-value text-sm" style={{ color: colors.textMuted }}>/ 100</div>
          </div>
        </div>
      </div>

      {/* ═══════════ ROW 2: Score Breakdown — matches ROW 1b grid cards ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4">SCORE BREAKDOWN</div>
        <div className="grid grid-cols-5 gap-6">
          {mockRegimeScores.map((item) => {
            const isUp = item.direction === 'up';
            const isDown = item.direction === 'down';
            const dirColor = isUp ? colors.bullish : isDown ? colors.bearish : colors.neutral;
            const icon = isUp ? '▲' : isDown ? '▼' : '→';

            return (
              <div key={item.name} className="p-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
                <div className="flex items-center justify-between mb-2">
                  <span style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>
                    {item.name.toUpperCase()}
                  </span>
                </div>
                <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>{item.score}</div>
                <div className="data-value text-sm mt-1" style={{ color: dirColor }}>
                  {icon} {item.contribution}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══════════ ROW 3: Market State + Regime Statistics — matches 3-col grid ═══════════ */}
      <div className="grid grid-cols-3 gap-10">

        {/* Market State — 2 columns wide */}
        <div className="col-span-2 border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">CURRENT MARKET STATE</div>
          <div className="grid grid-cols-3 gap-4">
            {mockMarketState.map((state) => {
              const isRich = state.classification.includes('Rich');
              const isCheap = state.classification.includes('Cheap');
              const badgeColor = isRich ? colors.bearish : isCheap ? colors.bullish : colors.neutral;

              return (
                <div key={state.instrument} className="p-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
                  <div className="flex items-center justify-between mb-2">
                    <span style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>
                      {state.instrument}
                    </span>
                    <span className="px-1.5 py-0.5 rounded-sm" style={{ backgroundColor: badgeColor + '18', color: badgeColor, fontSize: '9px', fontWeight: 600 }}>
                      {isCheap ? 'CHEAP' : isRich ? 'RICH' : 'FAIR'}
                    </span>
                  </div>
                  <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
                    {state.value > 0 ? '+' : ''}{state.value}
                  </div>
                  <div className="data-value text-sm mt-1" style={{ color: colors.textMuted }}>P{state.percentile} — {state.classification}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Regime Statistics — 1 column */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">REGIME STATISTICS</div>
          <div className="grid grid-cols-1 gap-4">
            {[
              { label: 'BEST STRUCTURE', value: mockRegimeStats.bestStructure, color: colors.textPrimary },
              { label: 'BEST HORIZON', value: mockRegimeStats.bestHorizon, color: colors.textPrimary },
              { label: 'HISTORICAL WIN RATE', value: mockRegimeStats.historicalWinRate, color: colors.bullish },
              { label: 'MEDIAN RETURN', value: mockRegimeStats.historicalMedianReturn, color: colors.textPrimary },
            ].map((kpi) => (
              <div key={kpi.label} className="flex items-center justify-between">
                <span style={{ color: colors.textMuted, fontSize: '12px', fontWeight: 600 }}>{kpi.label}</span>
                <div className="data-value font-bold" style={{ color: kpi.color }}>{kpi.value}</div>
              </div>
            ))}
            <div className="pt-4 border-t" style={{ borderColor: colors.borderSubtle }}>
              <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>ECONOMIC EDGE SCORE</div>
              <div className="data-value text-2xl font-bold mt-1" style={{ color: '#8b5cf6' }}>{mockRegimeStats.economicEdgeScore}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════ ROW 4: Signal Monitor — matches sentiment signal table style ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-6">SIGNAL MONITOR</div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${colors.borderSubtle}` }}>
              {['INSTRUMENT', 'HORIZON', 'DRIFT', 'RELATIVE VALUE', 'CONFIDENCE', 'ACTION'].map((h, i) => (
                <th key={h} className="section-header pb-3"
                  style={{ textAlign: i >= 4 ? 'right' : 'left', fontSize: '10px', paddingLeft: i === 0 ? 0 : '16px', paddingRight: i === 5 ? 0 : '16px' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mockSignalMonitor.map((row, idx) => {
              const isBuy = row.recommendation.includes('Buy');
              const isSell = row.recommendation.includes('Sell');
              const actionColor = isBuy ? colors.bullish : isSell ? colors.bearish : colors.neutral;
              const driftColor = row.drift === 'Bullish' ? colors.bullish : row.drift === 'Bearish' ? colors.bearish : colors.textMuted;

              return (
                <tr key={idx} style={{ borderBottom: idx < mockSignalMonitor.length - 1 ? `1px solid ${colors.borderSubtle}` : 'none' }}>
                  <td className="data-value font-bold py-4" style={{ color: colors.textPrimary }}>{row.instrument}</td>
                  <td className="data-value py-4" style={{ color: colors.textSecondary, paddingLeft: '16px' }}>{row.horizon}</td>
                  <td className="py-4" style={{ paddingLeft: '16px' }}>
                    <span className="data-value" style={{ color: driftColor, fontSize: '12px', fontWeight: 700 }}>
                      {row.drift === 'Bullish' ? '▲' : row.drift === 'Bearish' ? '▼' : '→'} {row.drift.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-4" style={{ paddingLeft: '16px' }}>
                    <span className="px-2 py-1 rounded-md data-value"
                      style={{ backgroundColor: colors.bgElevated, color: colors.textSecondary, fontSize: '10px', fontWeight: 600 }}>
                      {row.rv.toUpperCase()}
                    </span>
                  </td>
                  <td className="data-value py-4 text-right" style={{ color: colors.textPrimary, fontWeight: 700 }}>{row.confidence}</td>
                  <td className="py-4 text-right" style={{ paddingLeft: '16px' }}>
                    <span className="px-2 py-1 rounded-md data-value"
                      style={{ backgroundColor: actionColor + '18', color: actionColor, fontSize: '10px', fontWeight: 700 }}>
                      {row.recommendation.toUpperCase()}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
}
