import React, { useMemo } from 'react';
import {
  ComposedChart, Bar, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';
import useDashboardStore from '../../stores/dashboardStore';
import { useTheme } from '../../theme/ThemeContext';

function CustomTooltip({ active, payload, label, colors }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="px-2 py-1.5 text-xs border rounded"
      style={{ backgroundColor: colors.tooltipBg, borderColor: colors.tooltipBorder }}>
      <div className="data-value mb-1" style={{ color: colors.textMuted, fontSize: '10px' }}>{label}</div>
      {payload.filter(p => p.value != null).map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color || colors.neutral }} />
          <span style={{ color: colors.textMuted, fontSize: '10px' }}>{p.name}:</span>
          <span className="data-value" style={{ color: colors.textPrimary, fontSize: '10px' }}>
            {typeof p.value === 'number' ? (p.value / 1000).toFixed(1) : p.value} mn bbl
          </span>
        </div>
      ))}
    </div>
  );
}

// Custom bar component that colors based on comparison to 5Y avg
function CustomBar(props) {
  const { x, y, width, height, payload, bullishColor, bearishColor } = props;
  const isBullish = payload.value < payload.fiveYearAvg;
  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      fill={isBullish ? (bullishColor || '#10b981') : (bearishColor || '#ef4444')}
      fillOpacity={0.7}
      rx={1}
    />
  );
}

export default function InventoryChart({ historyData }) {
  const { colors } = useTheme();
  const { inventoryTab, setInventoryTab } = useDashboardStore();

  const tabs = [
    { id: 'crude', label: 'Crude' },
    { id: 'gasoline', label: 'Gasoline' },
    { id: 'distillate', label: 'Distillate' },
    { id: 'spr', label: 'SPR' },
  ];

  // If the store's tab doesn't match our new backend tabs, reset it to crude
  const safeTab = tabs.some(t => t.id === inventoryTab) ? inventoryTab : 'crude';

  const data = useMemo(() => {
    if (!historyData || !historyData[safeTab]) return [];
    return historyData[safeTab];
  }, [historyData, safeTab]);

  return (
    <div>
      <div className="flex items-center gap-1 mb-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setInventoryTab(t.id)}
            className="px-2.5 py-1 text-xs font-medium rounded-md transition-colors duration-150"
            style={{
              backgroundColor: safeTab === t.id ? colors.activeTabBg : 'transparent',
              color: safeTab === t.id ? colors.textPrimary : colors.textMuted,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
            <XAxis
              dataKey="date"
              tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
              tickLine={false}
              axisLine={{ stroke: colors.gridLine }}
              interval="preserveStartEnd"
            />
            <YAxis
              orientation="right"
              domain={['auto', 'auto']}
              tickFormatter={(val) => (val / 1000).toFixed(0)}
              tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
              tickLine={false}
              axisLine={{ stroke: colors.gridLine }}
            />
            <Tooltip content={<CustomTooltip colors={colors} />} />

            {/* 5-year seasonal range */}
            <Area
              type="monotone"
              dataKey="fiveYearMax"
              stroke="none"
              fill={colors.textMuted}
              fillOpacity={0.08}
              name="5Y Max"
            />
            <Area
              type="monotone"
              dataKey="fiveYearMin"
              stroke="none"
              fill={colors.inventoryBgFill}
              fillOpacity={1}
              name="5Y Min"
            />

            {/* 5-year average */}
            <Line
              type="monotone"
              dataKey="fiveYearAvg"
              stroke={colors.textMuted}
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name="5Y Avg"
            />

            {/* Inventory bars */}
            <Bar
              dataKey="value"
              name="Inventory"
              shape={<CustomBar bullishColor={colors.bullish} bearishColor={colors.bearish} />}
              barSize={6}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

