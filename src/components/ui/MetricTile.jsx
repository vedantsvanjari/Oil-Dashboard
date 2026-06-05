import React from 'react';
import { useTheme } from '../../theme/ThemeContext';

export default function MetricTile({ metric }) {
  const { colors } = useTheme();

  const signalColor =
    metric.signal === 'BULL' ? colors.bullish :
    metric.signal === 'BEAR' ? colors.bearish : colors.neutral;

  const signalIcon =
    metric.signal === 'BULL' ? '▲' :
    metric.signal === 'BEAR' ? '▼' : '→';

  const changeColor = metric.change
    ? (metric.change.startsWith('+') ? colors.bullish : metric.change.startsWith('-') ? colors.bearish : colors.textMuted)
    : colors.textMuted;

  return (
    <div className="p-2.5 border rounded-lg flex flex-col justify-between theme-card"
      style={{
        backgroundColor: colors.cardBg,
        borderColor: colors.cardBorder,
        width: '140px',
        height: '110px',
      }}>
      <div className="section-header truncate" style={{ fontSize: '9px' }}>
        {metric.label}
      </div>

      <div className="data-value text-base font-bold" style={{ color: colors.textPrimary }}>
        {metric.value}
        {metric.unit && (
          <span className="text-xs ml-0.5" style={{ color: colors.textMuted, fontWeight: 400 }}>
            {metric.unit}
          </span>
        )}
      </div>

      {metric.change && (
        <div className="data-value text-xs" style={{ color: changeColor }}>
          {metric.change} {metric.changePercent}
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="px-1 py-0.5 data-value rounded-sm"
          style={{
            backgroundColor: colors.bgElevated,
            color: metric.percentile >= 70 ? colors.bullish : metric.percentile <= 30 ? colors.bearish : colors.neutral,
            fontSize: '9px',
          }}>
          P{metric.percentile}
        </span>
        <span className="data-value font-semibold"
          style={{ color: signalColor, fontSize: '10px' }}>
          {metric.signal} {signalIcon}
        </span>
      </div>
    </div>
  );
}
