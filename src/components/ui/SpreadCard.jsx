import React from 'react';
import { useTheme } from '../../theme/ThemeContext';

function getZScoreColor(z, colors) {
  const abs = Math.abs(z);
  if (abs >= 2) return z > 0 ? colors.bullish : colors.bearish;
  if (abs >= 1) return colors.neutral;
  return colors.textSecondary;
}

export default function SpreadCard({ spread, showStructure = true }) {
  const { colors } = useTheme();
  const isPositive = spread.dayChange >= 0;
  const changeColor = isPositive ? colors.bullish : colors.bearish;
  const structureColor = spread.structure === 'BACKWARDATION' ? colors.bullish : colors.bearish;

  return (
    <div className="p-4 border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: colors.textPrimary }}>{spread.name}</span>
        {showStructure && spread.structure && (
          <span className="px-1.5 py-0.5 text-xs font-semibold rounded-sm"
            style={{
              backgroundColor: structureColor + '18',
              color: structureColor,
              fontSize: '9px',
              letterSpacing: '0.05em',
            }}>
            {spread.structure}
          </span>
        )}
      </div>

      <div className="data-value text-xl font-bold mb-2" style={{ color: colors.textPrimary }}>
        {spread.value >= 0 ? '+' : ''}{spread.value.toFixed(2)}
        <span className="text-xs ml-1" style={{ color: colors.textMuted }}>$/bbl</span>
      </div>

      <div className="flex items-center gap-1.5 mb-2">
        <span className="data-value text-xs" style={{ color: changeColor }}>
          {isPositive ? '+' : ''}{spread.dayChange.toFixed(2)}
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between">
          <span style={{ color: colors.textMuted, fontSize: '12px' }}>20D MA</span>
          <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
            {spread.ma20 >= 0 ? '+' : ''}{spread.ma20.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: colors.textMuted, fontSize: '12px' }}>Z-Score (52w)</span>
          <span className="data-value font-medium" style={{ color: getZScoreColor(spread.zScore, colors), fontSize: '12px' }}>
            {spread.zScore >= 0 ? '+' : ''}{spread.zScore.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span style={{ color: colors.textMuted, fontSize: '12px' }}>Percentile</span>
          <span className="px-2 py-0.5 data-value font-medium rounded-md"
            style={{
              backgroundColor: colors.bgElevated,
              color: spread.percentile >= 70 ? colors.bullish : spread.percentile <= 30 ? colors.bearish : colors.neutral,
              fontSize: '12px',
            }}>
            {spread.percentile}%
          </span>
        </div>
      </div>
    </div>
  );
}
