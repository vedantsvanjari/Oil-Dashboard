import React from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { freightData, physicalIndicators } from '../../data/mockData';
import CountdownTimer from '../ui/CountdownTimer';
import InventoryChart from '../charts/InventoryChart';
import RefineryChart from '../charts/RefineryChart';
import { useTheme } from '../../theme/ThemeContext';
import { useInventoryData } from '../../hooks/useInventoryData';
import { useRefineryData } from '../../hooks/useRefineryData';
import { getNextEIARelease } from '../../utils/dates';

function StatCard({ label, value, unit, weekChange, interpretation, signal, colors }) {
  const changeColor = weekChange >= 0 ? colors.bullish : colors.bearish;
  const signalColor =
    signal === 'BULLISH' ? colors.bullish :
      signal === 'BEARISH' ? colors.bearish : colors.neutral;

  return (
    <div className="p-5 border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
      <div className="section-header mb-3">{label}</div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
          {typeof value === 'number' ? value.toFixed(1) : value}
        </span>
        <span className="text-sm" style={{ color: colors.textMuted }}>{unit}</span>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <span className="data-value text-sm" style={{ color: changeColor }}>
          WoW: {weekChange >= 0 ? '+' : ''}{weekChange.toFixed(1)}
        </span>
        {signal && (
          <span className="px-2 py-1 text-xs font-semibold rounded-md"
            style={{
              backgroundColor: signalColor + '18',
              color: signalColor,
              fontSize: '11px',
            }}>
            {signal}
          </span>
        )}
      </div>
      {interpretation && (
        <div className="text-sm leading-relaxed" style={{ color: colors.textMuted }}>
          {interpretation}
        </div>
      )}
    </div>
  );
}

function Sparkline({ data, color }) {
  return (
    <div style={{ height: 36, width: 120 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function PhysicalSection() {
  const { colors } = useTheme();
  const { bdti, bcti } = freightData;
  const { rigCount, floatingStorage } = physicalIndicators;
  
  const { latestData, historyData, loading, error } = useInventoryData();
  const refinery = useRefineryData();

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* EIA Inventory Panel */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="flex items-center justify-between mb-5">
          <div className="section-header" style={{ fontSize: '14px' }}>EIA WEEKLY PETROLEUM STATUS</div>
          <CountdownTimer targetDate={getNextEIARelease()} label="NEXT RELEASE" />
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center p-10" style={{ color: colors.textMuted }}>
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mb-4" style={{ borderColor: colors.neutral, borderTopColor: 'transparent' }}></div>
            <p>Loading EIA data...</p>
          </div>
        ) : error ? (
          <div className="p-5 border rounded-lg text-center" style={{ backgroundColor: colors.bearish + '11', borderColor: colors.bearish }}>
            <p style={{ color: colors.bearish }}>Failed to load inventory data: {error}</p>
          </div>
        ) : latestData && (
          <>
            {/* Main crude stats */}
            <div className="p-5 border mb-5 rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>US Crude Stocks</span>
                <span className="px-2 py-1 text-xs font-semibold rounded-md"
                  style={{
                    backgroundColor: (latestData.crude.weekChange < 0 ? colors.bullish : colors.bearish) + '18',
                    color: latestData.crude.weekChange < 0 ? colors.bullish : colors.bearish,
                    fontSize: '11px',
                  }}>
                  {latestData.crude.weekChange < 0 ? 'BULLISH (DRAW)' : 'BEARISH (BUILD)'}
                </span>
              </div>
              <div className="flex items-baseline gap-4 mb-3">
                <span className="data-value text-3xl font-bold" style={{ color: colors.textPrimary }}>
                  {(latestData.crude.value / 1000).toFixed(1)}
                </span>
                <span className="text-sm" style={{ color: colors.textMuted }}>mn bbl</span>
              </div>
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>WoW Change</span>
                  <div className="data-value text-base font-medium" style={{ color: latestData.crude.weekChange < 0 ? colors.bullish : colors.bearish }}>
                    {latestData.crude.weekChange > 0 ? '+' : ''}{(latestData.crude.weekChange / 1000).toFixed(1)} mn bbl
                  </div>
                </div>
                <div>
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Consensus</span>
                  <div className="data-value text-base" style={{ color: colors.textSecondary }}>
                    -1.8 mn bbl
                  </div>
                </div>
                <div>
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Surprise</span>
                  <div className="data-value text-base font-medium" style={{ color: (latestData.crude.weekChange / 1000 + 1.8) < 0 ? colors.bullish : colors.bearish }}>
                    {(((latestData.crude.weekChange / 1000) + 1.8) > 0 ? '+' : '') + ((latestData.crude.weekChange / 1000) + 1.8).toFixed(1)} mn bbl
                  </div>
                </div>
              </div>
            </div>

            {/* Sub-cards */}
            <div className="grid grid-cols-3 gap-4">
              <StatCard 
                label="Gasoline Stocks" 
                value={latestData.gasoline.value / 1000} 
                unit="mn bbl" 
                weekChange={latestData.gasoline.weekChange / 1000} 
                interpretation="Gasoline inventories tracking real-time demand." 
                colors={colors} 
              />
              <StatCard 
                label="Distillate Stocks" 
                value={latestData.distillate.value / 1000} 
                unit="mn bbl" 
                weekChange={latestData.distillate.weekChange / 1000} 
                interpretation="Distillate levels reflect industrial and freight activity." 
                colors={colors} 
              />
              <StatCard 
                label="SPR" 
                value={latestData.spr.value / 1000} 
                unit="mn bbl" 
                weekChange={latestData.spr.weekChange / 1000} 
                interpretation="Strategic Petroleum Reserve inventory levels." 
                colors={colors} 
              />
            </div>
          </>
        )}
      </div>

      {/* Inventory History Chart */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4" style={{ fontSize: '14px' }}>INVENTORY HISTORY VS 5-YEAR RANGE</div>
        {!loading && !error && historyData && (
          <InventoryChart historyData={historyData} />
        )}
      </div>

      {/* Refinery Operations Panel */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-5" style={{ fontSize: '14px' }}>U.S. REFINERY OPERATIONS</div>

        {refinery.loading ? (
          <div className="flex flex-col items-center justify-center p-10" style={{ color: colors.textMuted }}>
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mb-4" style={{ borderColor: colors.neutral, borderTopColor: 'transparent' }}></div>
            <p>Loading EIA refinery data...</p>
          </div>
        ) : refinery.error ? (
          <div className="p-5 border rounded-lg text-center" style={{ backgroundColor: colors.bearish + '11', borderColor: colors.bearish }}>
            <p style={{ color: colors.bearish }}>Failed to load refinery data: {refinery.error}</p>
          </div>
        ) : refinery.latestData && (
          <>
            <div className="grid grid-cols-4 gap-4 mb-6">
              <StatCard 
                label="Refinery Utilization" 
                value={refinery.latestData.refinery_utilization.value} 
                unit="%" 
                weekChange={refinery.latestData.refinery_utilization.weekChange} 
                signal={refinery.latestData.refinery_utilization.weekChange > 0 ? 'BULLISH' : 'BEARISH'}
                colors={colors} 
              />
              <StatCard 
                label="Gross Inputs" 
                value={refinery.latestData.gross_inputs.value / 1000} 
                unit="mn bpd" 
                weekChange={refinery.latestData.gross_inputs.weekChange / 1000} 
                signal={refinery.latestData.gross_inputs.weekChange > 0 ? 'BULLISH' : 'BEARISH'}
                colors={colors} 
              />
              <StatCard 
                label="Gasoline Production" 
                value={refinery.latestData.gasoline_production.value / 1000} 
                unit="mn bpd" 
                weekChange={refinery.latestData.gasoline_production.weekChange / 1000} 
                signal={refinery.latestData.gasoline_production.weekChange > 0 ? 'BULLISH' : 'BEARISH'}
                colors={colors} 
              />
              <StatCard 
                label="Distillate Production" 
                value={refinery.latestData.distillate_production.value / 1000} 
                unit="mn bpd" 
                weekChange={refinery.latestData.distillate_production.weekChange / 1000} 
                signal={refinery.latestData.distillate_production.weekChange > 0 ? 'BULLISH' : 'BEARISH'}
                colors={colors} 
              />
            </div>

            <div className="section-header mb-4" style={{ fontSize: '14px' }}>REFINERY HISTORY VS 5-YEAR RANGE</div>
            {refinery.historyData && (
              <RefineryChart historyData={refinery.historyData} />
            )}
          </>
        )}
      </div>

      {/* Two-column: Freight + Physical Indicators */}
      <div className="grid grid-cols-2 gap-16">
        {/* Freight Rates */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-5" style={{ fontSize: '14px' }}>FREIGHT RATES</div>

          {[bdti, bcti].map((freight) => {
            const color = freight.weekChange >= 0 ? colors.bullish : colors.bearish;
            return (
              <div key={freight.label} className="mb-5 pb-5 border-b" style={{ borderColor: colors.borderSubtle }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>{freight.label}</span>
                  <Sparkline data={freight.sparkline} color={color} />
                </div>
                <div className="flex items-baseline gap-3">
                  <span className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>
                    {freight.value}
                  </span>
                  <span className="data-value text-sm" style={{ color }}>
                    {freight.weekChange >= 0 ? '+' : ''}{freight.weekChange} ({freight.weekChange >= 0 ? '+' : ''}{freight.weekChangePercent.toFixed(1)}%)
                  </span>
                </div>
                <div className="text-sm mt-2" style={{ color: colors.textMuted }}>
                  {freight.interpretation}
                </div>
              </div>
            );
          })}
        </div>

        {/* Physical Indicators */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-5" style={{ fontSize: '14px' }}>PHYSICAL INDICATORS</div>

          {/* Rig Count */}
          <div className="mb-5 pb-5 border-b" style={{ borderColor: colors.borderSubtle }}>
            <div className="text-sm font-medium mb-2" style={{ color: colors.textPrimary }}>Baker Hughes Rig Count</div>
            <div className="grid grid-cols-2 gap-4 mb-3">
              <div>
                <span style={{ color: colors.textMuted, fontSize: '12px' }}>Total US</span>
                <div className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>
                  {rigCount.totalUS}
                </div>
              </div>
              <div>
                <span style={{ color: colors.textMuted, fontSize: '12px' }}>Permian</span>
                <div className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>
                  {rigCount.permian}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4 mb-2">
              <span className="data-value text-sm" style={{ color: colors.bearish }}>
                WoW: {rigCount.weekChange}
              </span>
              <span className="data-value text-sm" style={{ color: colors.bearish }}>
                YoY: {rigCount.yearChange} ({rigCount.yearChangePercent}%)
              </span>
              <span className="px-2 py-1 text-xs font-semibold rounded-md"
                style={{ backgroundColor: colors.bearish + '18', color: colors.bearish, fontSize: '11px' }}>
                {rigCount.signal}
              </span>
            </div>
            <div className="text-sm" style={{ color: colors.textMuted }}>
              {rigCount.interpretation}
            </div>
          </div>

          {/* Floating Storage */}
          <div>
            <div className="text-sm font-medium mb-2" style={{ color: colors.textPrimary }}>Floating Storage</div>
            <div className="flex items-baseline gap-3 mb-2">
              <span className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>
                {floatingStorage.value}
              </span>
              <span className="text-sm" style={{ color: colors.textMuted }}>{floatingStorage.unit}</span>
              <span style={{ color: colors.bullish, fontSize: '16px' }}>
                {floatingStorage.trend === 'falling' ? '↓' : '↑'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="data-value text-sm" style={{ color: colors.bullish }}>
                WoW: {floatingStorage.weekChange.toFixed(1)}
              </span>
              <span className="px-2 py-1 text-xs font-semibold rounded-md"
                style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '11px' }}>
                {floatingStorage.signal}
              </span>
            </div>
            <div className="text-sm mt-2" style={{ color: colors.textMuted }}>
              {floatingStorage.interpretation}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

