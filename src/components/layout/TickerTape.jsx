import React from 'react';
import { tickerItems } from '../../data/mockData';
import { useTheme } from '../../theme/ThemeContext';

function TickerItem({ item, colors }) {
  const isPositive = item.change >= 0;
  const color = isPositive ? colors.bullish : colors.bearish;
  const arrow = isPositive ? '▲' : '▼';

  return (
    <span className="inline-flex items-center gap-2 px-4 whitespace-nowrap">
      <span className="text-xs font-medium" style={{ color: colors.textMuted }}>{item.label}</span>
      <span className="data-value text-xs font-semibold" style={{ color: colors.textPrimary }}>
        {item.value.toFixed(item.value < 10 ? 3 : 2)}
      </span>
      <span className="data-value text-xs" style={{ color }}>
        {arrow} {isPositive ? '+' : ''}{item.change.toFixed(item.change < 1 ? 3 : 2)} ({isPositive ? '+' : ''}{item.changePercent.toFixed(2)}%)
      </span>
    </span>
  );
}

export default function TickerTape() {
  const { colors } = useTheme();
  const items = [...tickerItems, ...tickerItems];

  return (
    <div className="h-10 flex items-center overflow-hidden border-b"
      style={{ backgroundColor: colors.bgDeep, borderColor: colors.border }}>
      <div className="ticker-animate flex items-center" style={{ width: 'max-content' }}>
        {items.map((item, i) => (
          <TickerItem key={`${item.label}-${i}`} item={item} colors={colors} />
        ))}
      </div>
    </div>
  );
}
