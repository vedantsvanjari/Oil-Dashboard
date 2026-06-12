import React, { useState, useMemo } from 'react';
import SpreadCard from '../ui/SpreadCard';
import SpreadChart from '../charts/SpreadChart';
import CorrelationHeatmap from '../charts/CorrelationHeatmap';
import { useTheme } from '../../theme/ThemeContext';
import { useSpreads } from '../../hooks/useSpreads';
import { useCrackSpread } from '../../hooks/useCrackSpread';
import { useBrentWtiSpread } from '../../hooks/useBrentWtiSpread';
import { useCorrelations } from '../../hooks/useCorrelations';

export default function SpreadsSection() {
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const { colors } = useTheme();
  
  const { data: brentWtiData, loading: brentWtiLoading, error: brentWtiError } = useBrentWtiSpread();
  const { data: spreadsData, loading: spreadsLoading, error: spreadsError } = useSpreads();
  const { data: crackData, loading: crackLoading, error: crackError } = useCrackSpread();
  const { data: corrData, loading: corrLoading, error: corrError } = useCorrelations();

  const [activeTab, setActiveTab] = useState('m1m2');

  const calendarSpreads = useMemo(() => {
    if (!spreadsData?.latest) return [];
    const latest = spreadsData.latest;
    const requiredKeys = ['wti_M1-M2', 'wti_M1-M6', 'wti_M1-M12', 'brent_M1-M2', 'brent_M1-M6', 'brent_M1-M12'];
    return requiredKeys.map(key => {
      const sp = latest[key];
      if (!sp) return null;
      return {
        id: key,
        name: `${sp.commodity.toUpperCase()} ${sp.contract1}-${sp.contract2}`,
        value: sp.spread || 0,
        dayChange: sp.statistics?.daily_change || 0,
        ma20: sp.statistics?.avg_30d || 0,
        zScore: sp.statistics?.z_score || 0,
        percentile: sp.statistics?.volatility || 0,
        structure: sp.spread > 0 ? 'BACKWARDATION' : 'CONTANGO'
      };
    }).filter(Boolean);
  }, [spreadsData]);

  const activeChartData = useMemo(() => {
    if (activeTab === 'wtiBrent' && brentWtiData?.history) {
      return brentWtiData.history.map(item => ({ ...item, value: item.spread }));
    }
    if (activeTab === 'crack' && crackData?.history) {
      return crackData.history.map(item => ({ ...item, value: item.crack_spread }));
    }
    
    // For calendar spreads
    if (spreadsData?.history) {
      let rawHistory = [];
      if (activeTab === 'm1m2') rawHistory = spreadsData.history['wti_M1-M2'] || [];
      if (activeTab === 'm1m6') rawHistory = spreadsData.history['wti_M1-M6'] || [];
      if (activeTab === 'm1m12') rawHistory = spreadsData.history['wti_M1-M12'] || [];
      if (activeTab === 'brent_m1m2') rawHistory = spreadsData.history['brent_M1-M2'] || [];
      if (activeTab === 'brent_m1m6') rawHistory = spreadsData.history['brent_M1-M6'] || [];
      if (activeTab === 'brent_m1m12') rawHistory = spreadsData.history['brent_M1-M12'] || [];
      
      return rawHistory.map(item => ({ ...item, value: item.spread }));
    }
    return [];
  }, [activeTab, spreadsData, brentWtiData, crackData]);

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="section-header" style={{ fontSize: '14px' }}>CALENDAR SPREAD DASHBOARD</div>

      {/* Top row: 6 calendar spread cards */}
      {spreadsLoading ? (
        <div className="flex items-center justify-center min-h-[120px] text-sm" style={{ color: colors.textMuted }}>Loading calendar spreads...</div>
      ) : spreadsError ? (
        <div className="flex items-center justify-center min-h-[120px] text-sm" style={{ color: colors.bearish }}>Error loading spreads: {spreadsError}</div>
      ) : (
        <div className="grid grid-cols-3 gap-8">
          {calendarSpreads.map((s) => (
            <SpreadCard key={s.id} spread={s} />
          ))}
        </div>
      )}

      {/* Second row: WTI-Brent + Crack Spread */}
      <div className="grid grid-cols-2 gap-16">
        <div className="p-5 border rounded-xl theme-card flex flex-col" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>Brent-WTI Spread</span>
          </div>
          {brentWtiLoading ? (
            <div className="flex-1 flex items-center justify-center data-value min-h-[120px]" style={{ color: colors.textMuted }}>Loading...</div>
          ) : brentWtiError ? (
            <div className="flex-1 flex items-center justify-center data-value min-h-[120px]" style={{ color: colors.bearish }}>Error loading data</div>
          ) : brentWtiData ? (
            <>
              <div className="data-value text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
                {brentWtiData.current_spread.toFixed(2)}
                <span className="text-sm ml-1.5" style={{ color: colors.textMuted }}>$/bbl</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Day Chg</span>
                  <span className="data-value" style={{ color: brentWtiData.daily_change >= 0 ? colors.bullish : colors.bearish, fontSize: '12px' }}>
                    {brentWtiData.daily_change > 0 ? '+' : ''}{brentWtiData.daily_change.toFixed(2)}
                  </span>
                </div>
              </div>
            </>
          ) : null}
        </div>

        <div className="p-5 border rounded-xl theme-card flex flex-col" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>Crack Spread 3:2:1</span>
          </div>
          {crackLoading ? (
             <div className="flex-1 flex items-center justify-center data-value min-h-[120px]" style={{ color: colors.textMuted }}>Loading...</div>
          ) : crackError ? (
             <div className="flex-1 flex items-center justify-center data-value min-h-[120px]" style={{ color: colors.bearish }}>Error loading crack spread</div>
          ) : crackData && crackData.latest ? (
            <>
              <div className="data-value text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
                ${(crackData.latest.crack_spread || 0).toFixed(2)}
                <span className="text-sm ml-1.5" style={{ color: colors.textMuted }}>$/bbl</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Day Chg</span>
                  <span className="data-value" style={{ color: (crackData.latest.statistics?.day_change || 0) >= 0 ? colors.bullish : colors.bearish, fontSize: '12px' }}>
                    {(crackData.latest.statistics?.day_change || 0) >= 0 ? '+' : ''}{(crackData.latest.statistics?.day_change || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>30D MA</span>
                  <span className="data-value" style={{ color: colors.textSecondary, fontSize: '12px' }}>
                    ${(crackData.latest.statistics?.avg_30d || 0).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Trend</span>
                  <span className="data-value" style={{ color: colors.neutral, fontSize: '12px', textTransform: 'capitalize' }}>
                    {crackData.latest.statistics?.trend || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: colors.textMuted, fontSize: '12px' }}>Volatility</span>
                  <span className="data-value px-2 py-0.5 rounded-md"
                    style={{ backgroundColor: colors.bgElevated, color: colors.neutral, fontSize: '12px' }}>
                    {(crackData.latest.statistics?.volatility || 0).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="mt-3 text-sm leading-relaxed" style={{ color: colors.textMuted }}>
                {crackData.latest.statistics?.trend === 'positive' ? 'Refining margins are widening, bullish for crude demand.' : 'Refining margins are narrowing, bearish for crude demand.'}
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Spread chart */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4" style={{ fontSize: '14px' }}>SPREAD HISTORY</div>
        <SpreadChart chartData={activeChartData} activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Spread Correlation Heatmap */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <CorrelationHeatmap 
          title="SPREAD CORRELATION (30D)"
          labels={corrData?.spreads?.labels}
          matrix={corrData?.spreads?.matrix}
          loading={corrLoading}
          error={corrError}
        />
      </div>

      {/* Glossary */}
      <div className="border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <button
          onClick={() => setGlossaryOpen(!glossaryOpen)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm cursor-pointer"
          style={{ color: colors.textMuted }}
        >
          <span className="section-header">GLOSSARY</span>
          <span style={{ fontSize: '12px' }}>{glossaryOpen ? '▲' : '▼'}</span>
        </button>
        <div className={`glossary-content ${glossaryOpen ? 'open' : ''}`}>
          <div className="px-5 pb-4 space-y-3">
            <div>
              <span className="text-sm font-medium" style={{ color: colors.bullish }}>Backwardation: </span>
              <span className="text-sm" style={{ color: colors.textSecondary }}>
                When near-month futures trade at a premium to deferred months. Indicates physical market tightness and strong near-term demand. Bullish signal.
              </span>
            </div>
            <div>
              <span className="text-sm font-medium" style={{ color: colors.bearish }}>Contango: </span>
              <span className="text-sm" style={{ color: colors.textSecondary }}>
                When deferred futures trade at a premium to near-month contracts. Indicates ample supply and weak near-term demand. Often associated with inventory builds. Bearish signal.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
