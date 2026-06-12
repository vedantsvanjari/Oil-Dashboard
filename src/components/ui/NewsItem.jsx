import React from 'react';
import { format } from 'date-fns';
import { useTheme } from '../../theme/ThemeContext';

export default function NewsItem({ item }) {
  const { colors } = useTheme();

  const sentimentColor =
    item.sentiment === 'Bullish' ? colors.bullish :
    item.sentiment === 'Bearish' ? colors.bearish : colors.textMuted;

  const sentimentLabel = item.sentiment.toUpperCase();

  return (
    <div className="flex border-b py-4 px-5 transition-colors duration-150"
      style={{
        borderColor: colors.border,
        borderLeftWidth: '4px',
        borderLeftColor: sentimentColor,
      }}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5 mb-2">
          {item.pinned && <span className="text-sm">📌</span>}
          <span className="px-2 py-0.5 text-xs font-semibold rounded-md"
            style={{
              backgroundColor: sentimentColor + '18',
              color: sentimentColor,
              fontSize: '10px',
              letterSpacing: '0.05em',
            }}>
            {sentimentLabel}
          </span>
          <span className="px-2 py-0.5 text-xs rounded-md"
            style={{
              backgroundColor: colors.bgElevated,
              color: colors.textSecondary,
              fontSize: '10px',
            }}>
            {item.category}
          </span>
        </div>

        <div className="text-sm font-medium mb-2 leading-snug" style={{ color: colors.textPrimary }}>
          {item.headline}
        </div>

        <div className="flex items-center gap-3 mb-1.5">
          <span style={{ color: colors.textMuted, fontSize: '12px' }}>
            {item.source} · {format(item.timestamp, 'HH:mm')}
          </span>
        </div>

        {/* Confidence score bar */}
        <div className="flex items-center gap-2">
          <span style={{ color: colors.textMuted, fontSize: '11px' }}>CONFIDENCE</span>
          <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated, maxWidth: '100px' }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${item.confidence}%`,
                backgroundColor: sentimentColor,
              }}
            />
          </div>
          <span className="data-value" style={{ color: colors.textMuted, fontSize: '11px' }}>
            {item.confidence}%
          </span>
        </div>
      </div>
    </div>
  );
}
