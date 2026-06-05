import React from 'react';
import { format } from 'date-fns';
import { regimeData, keyMetrics } from '../../data/mockData';
import useDashboardStore from '../../stores/dashboardStore';
import RegimeBadge from '../ui/RegimeBadge';
import MetricTile from '../ui/MetricTile';
import CorrelationHeatmap from '../charts/CorrelationHeatmap';
import { useTheme } from '../../theme/ThemeContext';

export default function RegimeSection() {
  const { selectedRegime, setSelectedRegime } = useDashboardStore();
  const { colors } = useTheme();

  const currentRegime = regimeData.allRegimes.find((r) => r.id === selectedRegime) || regimeData.allRegimes[3];
  const activeRegime = regimeData.allRegimes[3]; // PHYSICAL TIGHTNESS is active

  return (
    <div className="p-4 space-y-4">
      {/* Regime Engine */}
      <div className="border p-4 rounded-lg theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4">REGIME ENGINE</div>

        {/* Active regime display */}
        <div className="flex items-center gap-4 mb-4">
          <div className="px-4 py-2 rounded-md border"
            style={{
              backgroundColor: activeRegime.color + '15',
              borderColor: activeRegime.color,
            }}>
            <div className="data-value text-lg font-bold" style={{ color: activeRegime.color }}>
              {activeRegime.label}
            </div>
          </div>
          <div className="space-y-0.5">
            <div className="flex items-center gap-3">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>Confidence</span>
              <span className="data-value font-semibold" style={{ color: colors.textPrimary, fontSize: '13px' }}>
                {regimeData.confidence}%
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>Since</span>
              <span className="data-value" style={{ color: colors.textSecondary, fontSize: '11px' }}>
                {format(regimeData.since, 'MMM d, yyyy')} ({regimeData.durationDays}d)
              </span>
            </div>
          </div>
        </div>

        {/* Regime buttons */}
        <div className="flex items-center gap-2 mb-4">
          {regimeData.allRegimes.map((r) => (
            <RegimeBadge
              key={r.id}
              regime={r}
              isActive={r.id === 'physical'}
              onClick={setSelectedRegime}
            />
          ))}
        </div>

        {/* Explanation */}
        <div className="p-3 mb-4 border rounded-md" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
          <div className="section-header mb-1">WHY THIS REGIME?</div>
          <div className="text-xs leading-relaxed" style={{ color: colors.textSecondary }}>
            {regimeData.explanation}
          </div>
        </div>

        {/* Key signals */}
        <div className="grid grid-cols-4 gap-3">
          <div className="p-2 border rounded-md" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div style={{ color: colors.textMuted, fontSize: '9px', marginBottom: '4px' }}>DXY-BRENT CORR</div>
            <div className="data-value text-sm font-bold" style={{ color: colors.bearish }}>
              {regimeData.signals.dxyBrentCorrelation.toFixed(2)}
            </div>
          </div>
          <div className="p-2 border rounded-md" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div style={{ color: colors.textMuted, fontSize: '9px', marginBottom: '4px' }}>M1-M2 Z-SCORE</div>
            <div className="data-value text-sm font-bold" style={{ color: colors.bullish }}>
              +{regimeData.signals.m1m2ZScore.toFixed(2)}
            </div>
          </div>
          <div className="p-2 border rounded-md" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div style={{ color: colors.textMuted, fontSize: '9px', marginBottom: '4px' }}>DRAW STREAK</div>
            <div className="data-value text-sm font-bold" style={{ color: colors.bullish }}>
              {regimeData.signals.drawStreak} weeks
            </div>
          </div>
          <div className="p-2 border rounded-md" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div style={{ color: colors.textMuted, fontSize: '9px', marginBottom: '4px' }}>CRACK DEVIATION</div>
            <div className="data-value text-sm font-bold" style={{ color: colors.neutral }}>
              {regimeData.signals.crackDeviation}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="border p-4 rounded-lg theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-3">KEY METRICS</div>
        <div className="flex flex-wrap gap-2 justify-center">
          {keyMetrics.map((m, i) => (
            <MetricTile key={i} metric={m} />
          ))}
        </div>
      </div>

      {/* Correlation Heatmap */}
      <div className="border p-4 rounded-lg theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <CorrelationHeatmap />
      </div>
    </div>
  );
}
