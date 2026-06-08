import React, { useMemo, useEffect } from 'react';
import {
  ComposedChart, Area, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, LineChart, BarChart,
} from 'recharts';
import useDashboardStore from '../../stores/dashboardStore';
import useLivePriceStore from '../../stores/livePriceStore';
import { useTheme } from '../../theme/ThemeContext';

function filterByRange(data, range) {
  if (!data || data.length === 0) return data;
  const len = data.length;
  switch (range) {
    case '1D': return data; // intraday
    case '5D': return data.slice(-5);
    case '1M': return data.slice(-22);
    case '3M': return data.slice(-66);
    case '1Y': return data;
    default: return data;
  }
}

function CustomTooltip({ active, payload, label, colors }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="px-2 py-1.5 text-xs border rounded"
      style={{ backgroundColor: colors.tooltipBg, borderColor: colors.tooltipBorder }}>
      <div className="data-value mb-1" style={{ color: colors.textMuted, fontSize: '10px' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span style={{ color: colors.textMuted, fontSize: '10px' }}>{p.name}:</span>
          <span className="data-value" style={{ color: colors.textPrimary, fontSize: '10px' }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function PriceChart() {
  const { colors } = useTheme();
  const {
    selectedInstrument, priceTimeRange, setPriceTimeRange, priceIndicators, toggleIndicator,
  } = useDashboardStore();
  const { instruments, isLoadingHistory, historyError, fetchHistoricalData } = useLivePriceStore();

  const instrument = instruments.find((i) => i.id === selectedInstrument) || instruments[0];

  useEffect(() => {
    fetchHistoricalData(selectedInstrument);
  }, [selectedInstrument, fetchHistoricalData]);

  const chartData = useMemo(() => {
    if (priceTimeRange === '1D') {
      return instrument.intradayData || [];
    }
    return filterByRange(instrument.dailyData, priceTimeRange);
  }, [instrument, priceTimeRange]);

  const timeRanges = ['1D', '5D', '1M', '3M', '1Y'];
  const indicators = [
    { key: 'vwap', label: 'VWAP' },
    { key: 'ema20', label: 'EMA20' },
    { key: 'ema50', label: 'EMA50' },
    { key: 'bb', label: 'BB' },
  ];

  // Get last RSI and VWAP for indicator panel
  const lastPoint = chartData[chartData.length - 1] || {};
  const rsiValue = lastPoint.rsi || 50;
  const vwapValue = lastPoint.vwap || instrument.price;
  const vwapDev = instrument.price - vwapValue;

  // ATR approximation (average true range from last 14 bars)
  const atrBars = chartData.slice(-14);
  const atr = atrBars.length > 0
    ? (atrBars.reduce((sum, d) => sum + (d.high - d.low), 0) / atrBars.length)
    : 0;

  // Volume comparison
  const last30Vol = chartData.slice(-30);
  const avgVol = last30Vol.length > 0
    ? last30Vol.reduce((sum, d) => sum + d.volume, 0) / last30Vol.length
    : 0;
  const currentVol = lastPoint.volume || 0;
  const volRatio = avgVol > 0 ? ((currentVol / avgVol) * 100).toFixed(0) : 0;

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1">
          {timeRanges.map((r) => (
            <button
              key={r}
              onClick={() => setPriceTimeRange(r)}
              className="px-2 py-1 text-xs font-medium rounded-md transition-colors duration-150"
              style={{
                backgroundColor: priceTimeRange === r ? colors.activeTabBg : 'transparent',
                color: priceTimeRange === r ? colors.textPrimary : colors.textMuted,
              }}
            >
              {r}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {indicators.map((ind) => (
            <button
              key={ind.key}
              onClick={() => toggleIndicator(ind.key)}
              className="px-2 py-1 text-xs font-medium rounded-md transition-colors duration-150"
              style={{
                backgroundColor: priceIndicators[ind.key] ? colors.activeTabBg : 'transparent',
                color: priceIndicators[ind.key] ? colors.textPrimary : colors.textMuted,
                borderWidth: '1px',
                borderColor: priceIndicators[ind.key] ? colors.border : 'transparent',
              }}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-3">
        {/* Main chart area */}
        <div className="flex-1" style={{ minWidth: 0 }}>
          {/* Price chart */}
          <div style={{ height: 460, position: 'relative' }}>
            {isLoadingHistory && (
              <div className="absolute inset-0 flex items-center justify-center z-10" style={{ backgroundColor: colors.cardBg, opacity: 0.8 }}>
                <span style={{ color: colors.textPrimary, fontSize: '14px' }}>Loading historical data...</span>
              </div>
            )}
            {historyError && !isLoadingHistory && (
              <div className="absolute inset-0 flex items-center justify-center z-10" style={{ backgroundColor: colors.cardBg, opacity: 0.8 }}>
                <span style={{ color: colors.bearish, fontSize: '14px' }}>{historyError}</span>
              </div>
            )}
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
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

                {/* Bollinger Bands */}
                {priceIndicators.bb && (
                  <>
                    <Area type="monotone" dataKey="bbUpper" stroke="none" fill={colors.textMuted} fillOpacity={0.1} name="BB Upper" />
                    <Area type="monotone" dataKey="bbLower" stroke="none" fill={colors.textMuted} fillOpacity={0.1} name="BB Lower" />
                  </>
                )}

                {/* Price area */}
                <Area type="monotone" dataKey="close" stroke={colors.neutral} strokeWidth={1.5} fill={colors.neutral} fillOpacity={0.08} name="Price" />

                {/* Indicators */}
                {priceIndicators.vwap && (
                  <Line type="monotone" dataKey="vwap" stroke={colors.cyan} strokeWidth={1} dot={false} name="VWAP" />
                )}
                {priceIndicators.ema20 && (
                  <Line type="monotone" dataKey="ema20" stroke={colors.purple} strokeWidth={1} dot={false} name="EMA20" />
                )}
                {priceIndicators.ema50 && (
                  <Line type="monotone" dataKey="ema50" stroke={colors.bullish} strokeWidth={1} dot={false} name="EMA50" />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* RSI sub-chart */}
          <div style={{ height: 100 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
                <XAxis dataKey="date" hide />
                <YAxis
                  orientation="right"
                  domain={[0, 100]}
                  ticks={[30, 50, 70]}
                  tick={{ fill: colors.axisText, fontSize: 9, fontFamily: "'JetBrains Mono', monospace" }}
                  tickLine={false}
                  axisLine={{ stroke: colors.gridLine }}
                />
                <ReferenceLine y={70} stroke={colors.bearish} strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={30} stroke={colors.bullish} strokeDasharray="3 3" strokeOpacity={0.5} />
                <Line type="monotone" dataKey="rsi" stroke={colors.neutral} strokeWidth={1} dot={false} name="RSI" />
                <Tooltip content={<CustomTooltip colors={colors} />} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Volume sub-chart */}
          <div style={{ height: 80 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip colors={colors} />} />
                <Bar
                  dataKey="volume"
                  name="Volume"
                  fill={colors.textMuted}
                  radius={[1, 1, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Indicator panel */}
        <div className="w-56 p-4 border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-3">INDICATORS</div>

          {/* RSI */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>RSI(14)</span>
              <span className="data-value font-semibold"
                style={{
                  color: rsiValue > 70 ? colors.bearish : rsiValue < 30 ? colors.bullish : colors.textSecondary,
                  fontSize: '12px',
                }}>
                {rsiValue.toFixed(1)}
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${rsiValue}%`,
                  backgroundColor: rsiValue > 70 ? colors.bearish : rsiValue < 30 ? colors.bullish : colors.textMuted,
                }}
              />
            </div>
          </div>

          {/* ATR */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>ATR(14)</span>
              <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
                {atr.toFixed(instrument.decimals)} {instrument.unit}
              </span>
            </div>
          </div>

          {/* VWAP Deviation */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>VWAP Dev</span>
              <span className="data-value font-medium"
                style={{
                  color: vwapDev > 0 ? colors.bullish : vwapDev < 0 ? colors.bearish : colors.textMuted,
                  fontSize: '12px',
                }}>
                {vwapDev >= 0 ? '+' : ''}{vwapDev.toFixed(instrument.decimals)}
              </span>
            </div>
          </div>

          {/* Volume vs 30D Avg */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span style={{ color: colors.textMuted, fontSize: '10px' }}>Vol vs 30D</span>
              <span className="data-value font-medium"
                style={{
                  color: volRatio > 100 ? colors.bullish : colors.bearish,
                  fontSize: '12px',
                }}>
                {volRatio}%
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(Number(volRatio), 200) / 2}%`,
                  backgroundColor: volRatio > 100 ? colors.bullish : colors.bearish,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
