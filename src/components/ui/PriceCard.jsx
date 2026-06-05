import React from 'react';
import { useTheme } from '../../theme/ThemeContext';

export default function PriceCard({ instrument, isSelected, onSelect }) {
  const { colors } = useTheme();
  const isPositive = instrument.change >= 0;
  const changeColor = isPositive ? colors.bullish : colors.bearish;
  const arrow = isPositive ? '▲' : '▼';

  return (
    <div
      onClick={() => onSelect(instrument.id)}
      className="cursor-pointer p-4 border rounded-xl transition-all duration-200 theme-card"
      style={{
        backgroundColor: isSelected ? colors.bgElevated : colors.cardBg,
        borderColor: isSelected ? colors.bullish : colors.cardBorder,
        borderWidth: '1px',
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-xs font-medium" style={{ color: colors.textPrimary }}>
            {instrument.name}
          </div>
          <div className="text-xs" style={{ color: colors.textMuted, fontSize: '10px' }}>
            {instrument.exchange}
          </div>
        </div>
        {isSelected && (
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colors.bullish }} />
        )}
      </div>

      <div className="data-value text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
        {instrument.price.toFixed(instrument.decimals)}
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="data-value text-xs font-medium" style={{ color: changeColor }}>
          {arrow} {isPositive ? '+' : ''}{instrument.change.toFixed(instrument.decimals)}
        </span>
        <span className="data-value text-xs" style={{ color: changeColor }}>
          ({isPositive ? '+' : ''}{instrument.changePercent.toFixed(2)}%)
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        <div className="flex justify-between">
          <span className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>High</span>
          <span className="data-value text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>
            {instrument.high.toFixed(instrument.decimals)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>Low</span>
          <span className="data-value text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>
            {instrument.low.toFixed(instrument.decimals)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>Vol</span>
          <span className="data-value text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>
            {(instrument.volume / 1000).toFixed(1)}K
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>OI</span>
          <span className="data-value text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>
            {(instrument.openInterest / 1000).toFixed(1)}K
          </span>
        </div>
      </div>
    </div>
  );
}
