import React, { useState } from 'react';
import { correlationLabels, correlationMatrix } from '../../data/mockData';
import { useTheme } from '../../theme/ThemeContext';

function getCorrelationColor(value, isDark) {
  if (value >= 0) {
    const intensity = Math.abs(value);
    if (isDark) {
      const r = Math.round(30 - intensity * 20);
      const g = Math.round(40 - intensity * 10);
      const b = Math.round(60 + intensity * 140);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round(210 - intensity * 130);
      const g = Math.round(220 - intensity * 100);
      const b = Math.round(240 - intensity * 20);
      return `rgb(${r}, ${g}, ${b})`;
    }
  } else {
    const intensity = Math.abs(value);
    if (isDark) {
      const r = Math.round(60 + intensity * 140);
      const g = Math.round(40 - intensity * 20);
      const b = Math.round(40 - intensity * 20);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round(240 - intensity * 20);
      const g = Math.round(210 - intensity * 130);
      const b = Math.round(210 - intensity * 130);
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
}

function getInterpretation(value) {
  const abs = Math.abs(value);
  if (abs >= 0.8) return 'Very Strong';
  if (abs >= 0.6) return 'Strong';
  if (abs >= 0.4) return 'Moderate';
  if (abs >= 0.2) return 'Weak';
  return 'Very Weak';
}

export default function CorrelationHeatmap() {
  const { theme, colors } = useTheme();
  const isDark = theme === 'dark';
  const [tooltip, setTooltip] = useState(null);

  return (
    <div>
      <div className="section-header mb-3">CORRELATION MATRIX (30-DAY ROLLING)</div>

      <div className="overflow-x-auto">
        <table style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ width: 70 }} />
              {correlationLabels.map((label) => (
                <th
                  key={label}
                  className="text-center px-1 py-1.5"
                  style={{
                    color: colors.textMuted,
                    fontSize: '10px',
                    fontWeight: 500,
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    width: 64,
                  }}
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {correlationMatrix.map((row, i) => (
              <tr key={i}>
                <td
                  className="pr-2 py-1"
                  style={{
                    color: colors.textMuted,
                    fontSize: '10px',
                    fontWeight: 500,
                    textAlign: 'right',
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  {correlationLabels[i]}
                </td>
                {row.map((value, j) => (
                  <td
                    key={j}
                    className="text-center relative cursor-default"
                    style={{
                      backgroundColor: getCorrelationColor(value, isDark),
                      padding: '6px 4px',
                      borderWidth: '1px',
                      borderColor: colors.heatmapCellBorder,
                      minWidth: 56,
                    }}
                    onMouseEnter={() => setTooltip({ row: i, col: j, value })}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    <span
                      className="data-value font-medium"
                      style={{ color: isDark ? '#ffffff' : '#1a1d26', fontSize: '10px' }}
                    >
                      {value.toFixed(2)}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div className="mt-2 px-3 py-1.5 inline-flex items-center gap-2 border rounded-md"
          style={{ backgroundColor: colors.tooltipBg, borderColor: colors.tooltipBorder }}>
          <span className="text-xs" style={{ color: colors.textSecondary }}>
            {correlationLabels[tooltip.row]} × {correlationLabels[tooltip.col]}:
          </span>
          <span className="data-value text-xs font-semibold" style={{ color: colors.textPrimary }}>
            {tooltip.value.toFixed(2)}
          </span>
          <span className="text-xs" style={{ color: colors.textMuted }}>
            ({getInterpretation(tooltip.value)} {tooltip.value >= 0 ? 'Positive' : 'Negative'})
          </span>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-3">
        <span className="data-value" style={{ color: colors.bearish, fontSize: '10px' }}>−1.0</span>
        <div className="flex h-2.5 rounded-sm overflow-hidden" style={{ width: 200 }}>
          {Array.from({ length: 20 }, (_, i) => {
            const val = -1.0 + (i / 19) * 2.0;
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  backgroundColor: getCorrelationColor(val, isDark),
                }}
              />
            );
          })}
        </div>
        <span className="data-value" style={{ color: '#3b82f6', fontSize: '10px' }}>+1.0</span>
      </div>
    </div>
  );
}
