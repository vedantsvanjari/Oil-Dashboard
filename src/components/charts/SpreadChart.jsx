import React, { useMemo } from 'react';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import useDashboardStore from '../../stores/dashboardStore';
import { useTheme } from '../../theme/ThemeContext';

function filterByRange(data, range) {
  if (!data || data.length === 0) return data;
  switch (range) {
    case '1M': return data.slice(-22);
    case '3M': return data.slice(-66);
    case '1Y': return data.slice(-252);
    case '3Y': return data;
    default: return data;
  }
}

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
            {typeof p.value === 'number' ? p.value.toFixed(3) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SpreadChart({ chartData, activeTab, onTabChange }) {
  const { colors } = useTheme();
  const { spreadTimeRange, setSpreadTimeRange } = useDashboardStore();

  const filteredData = useMemo(() => {
    return filterByRange(chartData || [], spreadTimeRange);
  }, [chartData, spreadTimeRange]);

  const tabs = [
    { id: 'm1m2', label: 'WTI M1-M2' },
    { id: 'm1m6', label: 'WTI M1-M6' },
    { id: 'm1m12', label: 'WTI M1-M12' },
    { id: 'brent_m1m2', label: 'Brent M1-M2' },
    { id: 'brent_m1m6', label: 'Brent M1-M6' },
    { id: 'brent_m1m12', label: 'Brent M1-M12' },
    { id: 'wtiBrent', label: 'WTI-Brent' },
    { id: 'crack', label: 'Crack 3:2:1' },
  ];

  const timeRanges = ['1M', '3M', '1Y', '3Y'];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => onTabChange && onTabChange(t.id)}
              className="px-2.5 py-1 text-xs font-medium rounded-md transition-colors duration-150"
              style={{
                backgroundColor: activeTab === t.id ? colors.activeTabBg : 'transparent',
                color: activeTab === t.id ? colors.textPrimary : colors.textMuted,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {timeRanges.map((r) => (
            <button
              key={r}
              onClick={() => setSpreadTimeRange(r)}
              className="px-2 py-1 text-xs font-medium rounded-md transition-colors duration-150"
              style={{
                backgroundColor: spreadTimeRange === r ? colors.activeTabBg : 'transparent',
                color: spreadTimeRange === r ? colors.textPrimary : colors.textMuted,
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 380 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filteredData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
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
              tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
              tickLine={false}
              axisLine={{ stroke: colors.gridLine }}
            />
            <Tooltip content={<CustomTooltip colors={colors} />} />
            <ReferenceLine y={0} stroke={colors.textMuted} strokeDasharray="3 3" />

            {/* ±1 and ±2 std dev bands */}
            <Area type="monotone" dataKey="std2Upper" stroke="none" fill={colors.textMuted} fillOpacity={0.05} name="+2σ" />
            <Area type="monotone" dataKey="std2Lower" stroke="none" fill={colors.textMuted} fillOpacity={0.05} name="-2σ" />
            <Area type="monotone" dataKey="std1Upper" stroke="none" fill={colors.textMuted} fillOpacity={0.08} name="+1σ" />
            <Area type="monotone" dataKey="std1Lower" stroke="none" fill={colors.textMuted} fillOpacity={0.08} name="-1σ" />

            {/* Spread value line */}
            <Line type="monotone" dataKey="value" stroke={colors.neutral} strokeWidth={1.5} dot={false} name="Spread" />

            {/* 20-day MA */}
            <Line
              type="monotone"
              dataKey="ma20"
              stroke={colors.textMuted}
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name="20D MA"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
