import React from 'react';
import { useLiveTicker } from '../../hooks/useLiveTicker';
import { useTheme } from '../../theme/ThemeContext';

function TickerItem({ item, colors }) {
  const hasChange = item.change !== undefined && item.change !== null && item.change !== 0;
  const isPositive = hasChange ? item.change > 0 : item.value >= 0;
  const color = isPositive ? colors.bullish : colors.bearish;
  const arrow = isPositive ? '▲' : '▼';

  return (
    <div className="flex items-center whitespace-nowrap">
      <div className="flex items-center gap-3 px-8">
        <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: colors.textMuted }}>
          {item.label}
        </span>
        <span className="data-value text-[13px] font-bold" style={{ color: color }}>
          {item.value.toFixed(item.value < 10 ? 3 : 2)}
        </span>
        {hasChange && (
          <span className="flex items-center gap-1.5 data-value text-[12px] font-semibold" style={{ color }}>
            <span className="text-[10px]">{arrow}</span>
            <span>{isPositive ? '+' : ''}{item.change.toFixed(item.change < 1 && item.change > -1 ? 3 : 2)}</span>
            <span style={{ opacity: 0.8 }}>({isPositive ? '+' : ''}{item.changePercent.toFixed(2)}%)</span>
          </span>
        )}
      </div>
      <div className="h-4 w-px" style={{ backgroundColor: colors.borderSubtle || colors.border }}></div>
    </div>
  );
}

export default function TickerTape() {
  const { colors } = useTheme();
  const { tickerItems } = useLiveTicker();
  const items = tickerItems.length ? [...tickerItems, ...tickerItems, ...tickerItems] : [];

  return (
    <div className="h-10 flex items-center overflow-hidden border-b"
      style={{ backgroundColor: colors.bgDeep, borderColor: colors.border }}>
      {items.length > 0 ? (
        <div className="ticker-animate flex items-center" style={{ width: 'max-content' }}>
          {items.map((item, i) => (
            <TickerItem key={`${item.label}-${i}`} item={item} colors={colors} />
          ))}
        </div>
      ) : (
        <div className="flex w-full items-center justify-center text-xs" style={{ color: colors.textMuted }}>
          Loading market data...
        </div>
      )}
    </div>
  );
}
