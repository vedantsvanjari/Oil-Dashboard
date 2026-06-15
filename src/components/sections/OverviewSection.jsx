import React, { useState, useMemo, useEffect } from 'react';
import { format } from 'date-fns';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { getNextEIARelease } from '../../utils/dates';
import useDashboardStore from '../../stores/dashboardStore';
import CountdownTimer from '../ui/CountdownTimer';
import { useTheme } from '../../theme/ThemeContext';
import { useMacroData } from '../../hooks/useMacroData';
import { useOpecData } from '../../hooks/useOpecData';
import { useCorrelations } from '../../hooks/useCorrelations';
import { useLiveTicker } from '../../hooks/useLiveTicker';
import { useSpreads } from '../../hooks/useSpreads';
import { useInventoryData } from '../../hooks/useInventoryData';
import CorrelationHeatmap from '../charts/CorrelationHeatmap';


// ─── Helpers ─────────────────────────────────────────────────
function getCorrelationColor(value, isDark) {
  if (value >= 0) {
    const t = Math.abs(value);
    if (isDark) {
      return `rgb(${Math.round(30 - t * 20)}, ${Math.round(40 - t * 10)}, ${Math.round(60 + t * 140)})`;
    } else {
      // Light mode — brighter blues
      return `rgb(${Math.round(210 - t * 130)}, ${Math.round(220 - t * 100)}, ${Math.round(240 - t * 20)})`;
    }
  } else {
    const t = Math.abs(value);
    if (isDark) {
      return `rgb(${Math.round(60 + t * 140)}, ${Math.round(40 - t * 20)}, ${Math.round(40 - t * 20)})`;
    } else {
      return `rgb(${Math.round(240 - t * 20)}, ${Math.round(210 - t * 130)}, ${Math.round(210 - t * 130)})`;
    }
  }
}

function ChartTooltip({ active, payload, label, colors }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="px-3 py-2 text-xs border rounded-lg"
      style={{ backgroundColor: colors.tooltipBg, borderColor: colors.tooltipBorder }}>
      <div className="data-value mb-1.5" style={{ color: colors.textMuted, fontSize: '11px' }}>{label}</div>
      {payload.filter(p => p.value != null).map((p, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
          <span style={{ color: colors.textMuted, fontSize: '11px' }}>{p.name}:</span>
          <span className="data-value" style={{ color: colors.textPrimary, fontSize: '11px' }}>
            {typeof p.value === 'number' ? p.value.toFixed(3) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Mini Heatmap ────────────────────────────────────────────
function MiniHeatmap({ title, labels, matrix, colors, isDark }) {
  const [hover, setHover] = useState(null);
  return (
    <div>
      <div className="section-header mb-3">{title}</div>
      <div className="overflow-x-auto">
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: 70 }} />
              {labels.map((l) => (
                <th key={l} className="text-center px-1 py-1.5"
                  style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, fontFamily: "'IBM Plex Sans', sans-serif" }}>
                  {l}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <td className="pr-2 py-1 text-right"
                  style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, fontFamily: "'IBM Plex Sans', sans-serif" }}>
                  {labels[i]}
                </td>
                {row.map((val, j) => (
                  <td key={j} className="text-center cursor-default"
                    style={{
                      backgroundColor: getCorrelationColor(val, isDark),
                      padding: '6px 4px',
                      borderWidth: '1px',
                      borderColor: colors.heatmapCellBorder,
                    }}
                    onMouseEnter={() => setHover({ r: i, c: j, val })}
                    onMouseLeave={() => setHover(null)}
                  >
                    <span className="data-value" style={{ color: isDark ? '#fff' : '#1a1d26', fontSize: '10px' }}>
                      {val.toFixed(2)}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hover && (
        <div className="mt-2 text-xs" style={{ color: colors.textMuted }}>
          <span style={{ color: colors.textSecondary }}>{labels[hover.r]}</span>
          {' × '}
          <span style={{ color: colors.textSecondary }}>{labels[hover.c]}</span>
          {': '}
          <span className="data-value" style={{ color: colors.textPrimary }}>{hover.val.toFixed(2)}</span>
          {' — '}
          {Math.abs(hover.val) >= 0.8 ? 'Very Strong' :
            Math.abs(hover.val) >= 0.6 ? 'Strong' :
              Math.abs(hover.val) >= 0.4 ? 'Moderate' :
                Math.abs(hover.val) >= 0.2 ? 'Weak' : 'Negligible'}
          {hover.val >= 0 ? ' Positive' : ' Inverse'}
        </div>
      )}
      <div className="flex items-center justify-center gap-2 mt-3">
        <span className="data-value" style={{ color: colors.bearish, fontSize: '9px' }}>−1</span>
        <div className="flex h-2 rounded-sm overflow-hidden" style={{ width: 120 }}>
          {Array.from({ length: 16 }, (_, i) => (
            <div key={i} style={{ flex: 1, backgroundColor: getCorrelationColor(-1 + (i / 15) * 2, isDark) }} />
          ))}
        </div>
        <span className="data-value" style={{ color: '#3b82f6', fontSize: '9px' }}>+1</span>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────
export default function OverviewSection() {
  const { data: macroData, loading: macroLoading, error: macroError } = useMacroData();
  const { data: opecData, loading: opecLoading, error: opecError } = useOpecData();
  const { data: corrData, loading: corrLoading, error: corrError } = useCorrelations();
  const { sentimentSignals, toggleSentimentSignal, setAllSentimentSignals, sentimentData, isSentimentLoading, fetchSentimentData } = useDashboardStore();
  
  useEffect(() => {
    fetchSentimentData();
  }, [fetchSentimentData]);

  const { theme, colors } = useTheme();
  const isDark = theme === 'dark';
  const [expandedSignal, setExpandedSignal] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  const { benchmarks } = useLiveTicker();
  const { data: spreadsData, loading: spreadsLoading } = useSpreads();
  const { latestData: invLatest } = useInventoryData();

  const brentPrice = benchmarks.brent;
  const wtiPrice = benchmarks.wti;
  const crackValue = benchmarks.crack;
  const crackChange = benchmarks.crackChange;

  const brentSpreadData = spreadsData?.latest?.['brent_M1-M12'] || {};
  const brentSpreadHistory = spreadsData?.history?.['brent_M1-M12']?.slice(-66) || [];
  const brentSpreadVal = brentSpreadData?.spread || null;
  const brentSpreadStats = brentSpreadData?.statistics || {};

  // Dynamic sentiment calculation based on backend payload
  const { computedScore, computedLabel, enabledSignals, activeCount, totalCount, narrativeText } = useMemo(() => {
    if (!sentimentData) {
      return { computedScore: 50, computedLabel: 'LOADING', enabledSignals: [], activeCount: 0, totalCount: 0, narrativeText: 'Loading sentiment data...' };
    }
    
    const all = sentimentData.metrics;
    const enabled = all.filter((s) => sentimentSignals[s.storeKey]);
    
    // We recalculate the score dynamically based on toggled signals
    const baseScore = 50;
    const toggledContributions = enabled.reduce((sum, s) => sum + (s.contribution || 0), 0);
    const score = Math.max(0, Math.min(100, baseScore + toggledContributions));
    
    let label = 'NEUTRAL';
    if (score >= 65) label = 'BULLISH';
    else if (score <= 35) label = 'BEARISH';
    
    // If all signals are active, use backend narrative, otherwise fallback to mixed
    const text = (enabled.length === all.length - 1) // -1 for Rig Count
      ? sentimentData.narrative 
      : 'Custom signal combination active. Net directional bias updated dynamically.';

    return { 
      computedScore: score, 
      computedLabel: label, 
      enabledSignals: enabled, 
      activeCount: enabled.length, 
      totalCount: all.length,
      narrativeText: text
    };
  }, [sentimentSignals, sentimentData]);

  const sentimentColor =
    computedScore >= 55 ? colors.bullish :
      computedScore >= 45 ? colors.neutral : colors.bearish;

  const marketBehavior = narrativeText;

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>

      {/* ═══════════ ROW 1: Key Benchmarks ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4">KEY BENCHMARKS</div>
        <div className="grid grid-cols-4 gap-16">
          {[
            { label: 'Brent', val: brentPrice != null ? brentPrice.toFixed(2) : 'N/A', chg: 'N/A', pct: '', unit: '$/bbl' },
            { label: 'WTI', val: wtiPrice != null ? wtiPrice.toFixed(2) : 'N/A', chg: 'N/A', pct: '', unit: '$/bbl' },
            { label: 'M1-M12', val: brentSpreadVal != null ? `${brentSpreadVal > 0 ? '+' : ''}${brentSpreadVal.toFixed(2)}` : 'N/A', chg: '', pct: '', unit: '$/bbl', extraLabel: brentSpreadVal > 0 ? 'BACKWD' : brentSpreadVal < 0 ? 'CONTAN' : '' },
            { label: 'Crack 3:2:1', val: crackValue != null ? crackValue.toFixed(2) : 'N/A', chg: crackChange != null ? `${crackChange > 0 ? '+' : ''}${crackChange.toFixed(2)}` : '', pct: '', unit: '$/bbl' },
          ].map((b) => {
            const isUp = b.chg.startsWith('+');
            return (
              <div key={b.label} className="p-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
                <div className="flex items-center justify-between mb-2">
                  <span style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>{b.label}</span>
                  {b.extraLabel && (
                    <span className="px-1.5 py-0.5 rounded-sm" style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '9px', fontWeight: 600 }}>
                      {b.extraLabel}
                    </span>
                  )}
                </div>
                <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
                  {b.val}
                  {b.unit && <span className="text-sm ml-1" style={{ color: colors.textFaint, fontWeight: 400 }}>{b.unit}</span>}
                </div>
                <div className="data-value text-sm mt-1" style={{ color: isUp ? colors.bullish : colors.bearish }}>
                  {b.chg} {b.pct}
                </div>
              </div>
            );
          })}
        </div>
        {/* Quick fundamental row */}
        <div className="grid grid-cols-4 gap-16 mt-4">
          {[
            { 
              label: 'US Crude', 
              val: invLatest?.crude?.weekChange != null ? `${invLatest.crude.weekChange > 0 ? '+' : ''}${invLatest.crude.weekChange}` : 'N/A', 
              unit: 'mn bbl', 
              badge: invLatest?.crude?.weekChange < 0 ? 'DRAW' : invLatest?.crude?.weekChange > 0 ? 'BUILD' : 'FLAT', 
              badgeColor: invLatest?.crude?.weekChange < 0 ? colors.bullish : colors.bearish 
            },
          ].map((f) => (
            <div key={f.label} className="flex items-center justify-between p-3 border rounded-lg"
              style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px' }}>{f.label}</div>
                <div className="data-value text-base font-bold" style={{ color: colors.textPrimary }}>{f.val} <span style={{ color: colors.textFaint, fontWeight: 400, fontSize: '12px' }}>{f.unit}</span></div>
              </div>
              <span className="px-2 py-1 rounded-md data-value" style={{ backgroundColor: f.badgeColor + '18', color: f.badgeColor, fontSize: '10px', fontWeight: 600 }}>
                {f.badge}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ═══════════ ROW 1b: Regime + OPEC + Macro ═══════════ */}
      <div className="grid grid-cols-3 gap-10">
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">ACTIVE REGIME</div>
          <div className="px-4 py-3 rounded-lg border mb-4" style={{ backgroundColor: sentimentColor + '12', borderColor: sentimentColor }}>
            <div className="data-value text-sm font-bold uppercase" style={{ color: sentimentColor }}>{sentimentData?.regime || 'NEUTRAL'}</div>
          </div>
          <div className="flex items-center gap-3 mb-2">
            <span style={{ color: colors.textMuted, fontSize: '12px' }}>Confidence</span>
            <span className="data-value text-base font-semibold" style={{ color: colors.textPrimary }}>{sentimentData?.confidence || 50}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${sentimentData?.confidence || 50}%`, backgroundColor: sentimentColor }} />
          </div>
        </div>
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">OPEC+ SNAPSHOT</div>
          {opecLoading ? (
            <div style={{ color: colors.textMuted, fontSize: '11px' }} className="mb-4">Loading...</div>
          ) : opecError ? (
            <div style={{ color: colors.bearish, fontSize: '11px' }} className="mb-4">Error</div>
          ) : (() => {
            const hist    = opecData?.totalProduction?.history || [];
            const latest  = opecData?.totalProduction?.latest;
            const prevVal = hist.length >= 2 ? hist[hist.length - 2].value : null;
            const change  = latest != null && prevVal != null
              ? parseFloat((latest - prevVal).toFixed(2))
              : null;
            const changeColor = change == null
              ? colors.textMuted
              : change > 0 ? colors.bullish : change < 0 ? colors.bearish : colors.textMuted;
            // Format "YYYY-MM" → "Jan 2026" inline
            const prevPeriod = hist.length >= 2 ? hist[hist.length - 2].period : null;
            const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const prevLabel = prevPeriod
              ? (() => { const [y,m] = prevPeriod.split('-'); return `${MONTHS[parseInt(m,10)-1]} ${y}`; })()
              : null;
            return (
              <div className="grid grid-cols-3 gap-3 mb-4">
                {/* Latest */}
                <div>
                  <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>LATEST</div>
                  <div className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>
                    {latest != null ? latest.toFixed(2) : 'N/A'}
                  </div>
                  <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
                </div>
                {/* Prev Month */}
                <div>
                  <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>PREV MONTH</div>
                  <div className="data-value text-lg font-bold" style={{ color: colors.textSecondary }}>
                    {prevVal != null ? prevVal.toFixed(2) : 'N/A'}
                  </div>
                  <div style={{ color: colors.textMuted, fontSize: '11px' }}>{prevLabel || 'mb/d'}</div>
                </div>
                {/* Monthly Change */}
                <div>
                  <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>MONTHLY CHG</div>
                  <div className="data-value text-lg font-bold" style={{ color: changeColor }}>
                    {change != null ? `${change > 0 ? '+' : ''}${change.toFixed(2)}` : 'N/A'}
                  </div>
                  <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
                </div>
              </div>
            );
          })()}
        </div>
        <div className="border p-6 rounded-xl theme-card flex flex-col" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">MACRO SNAPSHOT</div>
          {macroLoading ? (
            <div className="flex-1 flex items-center justify-center data-value" style={{ color: colors.textMuted }}>Loading...</div>
          ) : macroError ? (
            <div className="flex-1 flex items-center justify-center data-value" style={{ color: colors.bearish }}>Error loading data</div>
          ) : macroData ? (
            <div className="grid grid-cols-1 gap-4">
              {[
                { label: 'DXY', val: macroData.dxy.value.toFixed(2), chg: macroData.dxy.change, unit: '' },
                { label: 'US 10Y', val: macroData.us10y.value.toFixed(2), chg: macroData.us10y.change, unit: '%' },
                { label: 'Yield Curve', val: macroData.yield_curve.value.toFixed(2), chg: macroData.yield_curve.change, unit: '%' },
              ].map((m) => {
                const isUp = m.chg >= 0;
                return (
                  <div key={m.label} className="flex items-center justify-between">
                    <span style={{ color: colors.textMuted, fontSize: '12px', fontWeight: 600 }}>{m.label}</span>
                    <div className="text-right">
                      <div className="data-value font-bold" style={{ color: colors.textPrimary }}>{m.val}<span style={{ fontSize: '11px', color: colors.textFaint, fontWeight: 400 }}>{m.unit}</span></div>
                      <div className="data-value text-xs" style={{ color: isUp ? colors.bullish : colors.bearish }}>
                        {isUp ? '+' : ''}{m.chg.toFixed(2)}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : null}
        </div>
      </div>

      {/* ═══════════ ROW 2: SENTIMENT ENGINE ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        {/* Header with settings toggle */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="section-header" style={{ fontSize: '14px' }}>SENTIMENT ENGINE</div>
            <span className="data-value text-sm" style={{ color: colors.textMuted }}>
              {activeCount}/{totalCount} signals active
            </span>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm transition-colors duration-150 cursor-pointer"
            style={{
              backgroundColor: showSettings ? colors.bgElevated : 'transparent',
              borderColor: showSettings ? colors.border : colors.borderSubtle,
              color: showSettings ? colors.textPrimary : colors.textMuted,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
            Configure Metrics
          </button>
        </div>

        {/* Settings panel (collapsible) */}
        {showSettings && (
          <div className="mb-6 p-5 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm" style={{ color: colors.textSecondary }}>
                Select which fundamentals feed into the sentiment score. The weighted average recalculates in real-time.
              </span>
              <div className="flex items-center gap-3">
                <button onClick={() => setAllSentimentSignals(true)}
                  className="px-3 py-1 text-xs rounded-md cursor-pointer" style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '11px' }}>
                  Enable All
                </button>
                <button onClick={() => setAllSentimentSignals(false)}
                  className="px-3 py-1 text-xs rounded-md cursor-pointer" style={{ backgroundColor: colors.bearish + '18', color: colors.bearish, fontSize: '11px' }}>
                  Disable All
                </button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {(sentimentData?.metrics || []).map((sig) => {
                const isEnabled = sentimentSignals[sig.storeKey];
                const c = sig.signal === 'Bullish' ? colors.bullish : sig.signal === 'Bearish' ? colors.bearish : colors.neutral;
                return (
                  <button
                    key={sig.storeKey}
                    onClick={() => toggleSentimentSignal(sig.storeKey)}
                    className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-all duration-200"
                    style={{
                      backgroundColor: isEnabled ? colors.bgElevated : colors.overlayBg,
                      borderColor: isEnabled ? c + '60' : colors.borderSubtle,
                      opacity: isEnabled ? 1 : 0.4,
                    }}
                  >
                    <div className="w-4 h-4 rounded-sm border flex items-center justify-center"
                      style={{
                        borderColor: isEnabled ? c : colors.textFaint,
                        backgroundColor: isEnabled ? c : 'transparent',
                      }}>
                      {isEnabled && (
                        <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2">
                          <path d="M2 6l3 3 5-5" />
                        </svg>
                      )}
                    </div>
                    <div className="text-left">
                      <div className="text-sm font-medium" style={{ color: isEnabled ? colors.textPrimary : colors.textMuted }}>
                        {sig.name}
                      </div>
                      <div style={{ color: colors.textFaint, fontSize: '10px' }}>
                        Value: {sig.value} · Contrib: {sig.contribution > 0 ? '+' : ''}{sig.contribution}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Main sentiment display */}
        <div className="grid gap-16" style={{ gridTemplateColumns: '240px 1fr' }}>

          {/* Left: Big gauge */}
          <div className="flex flex-col items-center justify-center">
            <div className="relative mb-4" style={{ width: 180, height: 180 }}>
              <svg width="180" height="180" viewBox="0 0 180 180">
                <circle cx="90" cy="90" r="74" fill="none" stroke={colors.bgElevated} strokeWidth="10" />
                <circle cx="90" cy="90" r="74" fill="none"
                  stroke={sentimentColor}
                  strokeWidth="10"
                  strokeDasharray={`${(computedScore / 100) * 465} 465`}
                  strokeLinecap="round"
                  transform="rotate(-90 90 90)"
                  style={{ transition: 'stroke-dasharray 0.6s ease, stroke 0.3s ease' }}
                />
                <circle cx="90" cy="90" r="58" fill="none" stroke={colors.border} strokeWidth="1" strokeOpacity="0.4" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="data-value font-bold" style={{ color: sentimentColor, fontSize: '42px', lineHeight: 1 }}>
                  {computedScore}
                </span>
                <span style={{ color: colors.textMuted, fontSize: '12px', marginTop: '4px' }}>/ 100</span>
              </div>
            </div>
            <div className="text-center">
              <div className="data-value text-base font-bold tracking-wider" style={{ color: sentimentColor }}>
                {computedLabel}
              </div>
              <div className="text-sm mt-1.5" style={{ color: colors.textMuted }}>
                Based on {activeCount} active metric{activeCount !== 1 ? 's' : ''}
              </div>
            </div>

            {/* Direction indicator */}
            <div className="mt-4 px-4 py-3 border rounded-lg w-full" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
              <div style={{ color: colors.textMuted, fontSize: '11px', marginBottom: '6px', fontWeight: 600, letterSpacing: '0.05em' }}>PRICE DIRECTION</div>
              <div className="flex items-center gap-3">
                <span style={{ color: sentimentColor, fontSize: '20px' }}>
                  {computedScore >= 55 ? '▲' : computedScore >= 45 ? '→' : '▼'}
                </span>
                <span className="text-sm" style={{ color: colors.textPrimary, lineHeight: '1.4' }}>
                  {computedScore >= 62 ? 'Higher prices likely' : computedScore >= 45 ? 'Range-bound' : 'Lower prices likely'}
                </span>
              </div>
            </div>
          </div>

          {/* Right: Market behavior text + signal details */}
          <div>
            {/* Dynamic market behavior analysis */}
            <div className="p-5 mb-4 border rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
              <div className="section-header mb-3">HOW THE MARKET BEHAVES</div>
              <p className="text-sm leading-relaxed" style={{ color: colors.textSecondary, lineHeight: '1.7' }}>
                {marketBehavior}
              </p>
            </div>

            {/* Signal cards grid */}
            <div className="grid grid-cols-2 gap-4">
              {(sentimentData?.metrics || []).map((sig) => {
                const isEnabled = sentimentSignals[sig.storeKey];
                const isExpanded = expandedSignal === sig.storeKey;
                const c = sig.signal === 'Bullish' ? colors.bullish : sig.signal === 'Bearish' ? colors.bearish : colors.neutral;

                if (!isEnabled) return null;

                return (
                  <div key={sig.storeKey}
                    className="p-4 border rounded-lg cursor-pointer transition-all duration-200"
                    style={{
                      backgroundColor: isExpanded ? colors.overlayBg : colors.cardBg,
                      borderColor: isExpanded ? c + '40' : colors.borderSubtle,
                    }}
                    onClick={() => setExpandedSignal(isExpanded ? null : sig.storeKey)}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c }} />
                        <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>{sig.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="data-value font-semibold" style={{ color: colors.textSecondary, fontSize: '12px' }}>{sig.value}</span>
                        <span className="data-value font-bold" style={{ color: c, fontSize: '12px' }}>
                          {sig.signal.toUpperCase()} {sig.signal === 'Bullish' ? '▲' : sig.signal === 'Bearish' ? '▼' : '→'}
                        </span>
                      </div>
                    </div>

                    {/* Contribution bar */}
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
                        <div className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.abs(sig.contribution) * 5)}%`, backgroundColor: c, opacity: 0.8 }} />
                      </div>
                      <span className="data-value" style={{ color: c, fontSize: '12px', minWidth: '28px', textAlign: 'right' }}>
                        {sig.contribution > 0 ? '+' : ''}{sig.contribution} pts
                      </span>
                    </div>

                    <div className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>Source: {sig.source}</div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: colors.borderSubtle }}>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.textPrimary, fontSize: '11px' }}>Backend Endpoint: </span>
                          <span className="text-xs data-value" style={{ color: colors.textSecondary, fontSize: '11px' }}>{sig.source}</span>
                        </div>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.textPrimary, fontSize: '11px' }}>Calculated Value: </span>
                          <span className="text-xs data-value" style={{ color: colors.textSecondary, fontSize: '11px' }}>{sig.value}</span>
                        </div>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.textPrimary, fontSize: '11px' }}>Directional Signal: </span>
                          <span className="text-xs" style={{ color: c, fontSize: '11px' }}>{sig.signal} ({sig.contribution > 0 ? '+' : ''}{sig.contribution} score impact)</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Disabled signals notice */}
            {activeCount < totalCount && (
              <div className="mt-3 text-sm" style={{ color: colors.textFaint }}>
                {totalCount - activeCount} signal{totalCount - activeCount !== 1 ? 's' : ''} disabled —{' '}
                <button onClick={() => setShowSettings(true)} className="cursor-pointer underline" style={{ color: colors.textMuted }}>
                  configure metrics
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════ ROW 3: M1-M12 Chart ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="flex items-center justify-between mb-4">
          <div className="section-header">BRENT M1-M12 CALENDAR SPREAD — 3M</div>
          {brentSpreadVal != null && (
            <div className="flex items-center gap-3">
              <span className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>{brentSpreadVal > 0 ? '+' : ''}{brentSpreadVal.toFixed(2)}</span>
              <span className="px-2 py-1 rounded-md text-xs font-semibold"
                style={{ backgroundColor: brentSpreadVal > 0 ? colors.bullish + '18' : colors.bearish + '18', color: brentSpreadVal > 0 ? colors.bullish : colors.bearish, fontSize: '11px' }}>
                {brentSpreadVal > 0 ? 'BACKWARDATION' : 'CONTANGO'}
              </span>
            </div>
          )}
        </div>
        <div style={{ height: 320 }}>
          {spreadsLoading ? (
            <div className="w-full h-full flex items-center justify-center text-sm" style={{ color: colors.textMuted }}>Loading chart data...</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={brentSpreadHistory} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
                <XAxis dataKey="timestamp"
                  tickFormatter={(val) => val ? format(new Date(val), 'MMM d') : ''}
                  tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                  tickLine={false} axisLine={{ stroke: colors.gridLine }} interval="preserveStartEnd" />
                <YAxis orientation="right" domain={['auto', 'auto']}
                  tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                  tickLine={false} axisLine={{ stroke: colors.gridLine }} />
                <Tooltip content={<ChartTooltip colors={colors} />} />
                <ReferenceLine y={0} stroke={colors.textMuted} strokeDasharray="3 3" />
                <Line type="monotone" dataKey="spread" stroke={colors.neutral} strokeWidth={2} dot={false} name="M1-M12" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="flex items-center gap-6 mt-4 pt-4 border-t" style={{ borderColor: colors.borderSubtle }}>
          {[
            { label: 'Current', value: brentSpreadVal != null ? `${brentSpreadVal > 0 ? '+' : ''}${brentSpreadVal.toFixed(2)}` : 'N/A' },
            { label: 'Z-Score', value: brentSpreadStats.z_score != null ? `${brentSpreadStats.z_score > 0 ? '+' : ''}${brentSpreadStats.z_score.toFixed(2)}` : 'N/A', color: colors.neutral },
            { label: 'Percentile', value: brentSpreadStats.percentile != null ? `${brentSpreadStats.percentile.toFixed(1)}%` : 'N/A', color: colors.bullish },
          ].map((s) => (
            <div key={s.label}>
              <div style={{ color: colors.textMuted, fontSize: '11px' }}>{s.label}</div>
              <div className="data-value text-sm font-semibold" style={{ color: s.color || colors.textPrimary }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ═══════════ ROW 3b: EIA + Risks/Catalysts side-by-side ═══════════ */}
      <div className="grid grid-cols-1 gap-10">
        {/* EIA compact */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-4">
            <div className="section-header">EIA WEEKLY</div>
            <CountdownTimer targetDate={getNextEIARelease()} label="NEXT" />
          </div>
          <div className="p-4 border mb-4 rounded-lg max-w-sm" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>US Crude</span>
              {invLatest?.crude?.weekChange != null && (
                <span className="px-2 py-1 rounded-md" style={{ backgroundColor: invLatest.crude.weekChange < 0 ? colors.bullish + '18' : colors.bearish + '18', color: invLatest.crude.weekChange < 0 ? colors.bullish : colors.bearish, fontSize: '10px', fontWeight: 700 }}>
                  {invLatest.crude.weekChange < 0 ? 'BULLISH' : invLatest.crude.weekChange > 0 ? 'BEARISH' : 'NEUTRAL'}
                </span>
              )}
            </div>
            <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>
              {invLatest?.crude?.value != null ? invLatest.crude.value.toFixed(1) : 'N/A'} <span style={{ color: colors.textFaint, fontSize: '13px', fontWeight: 400 }}>mn bbl</span>
            </div>
            {invLatest?.crude?.weekChange != null && (
              <div className="mt-3">
                <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600 }}>{invLatest.crude.weekChange < 0 ? 'DRAW' : 'BUILD'}</div>
                <div className="data-value text-sm font-semibold" style={{ color: invLatest.crude.weekChange < 0 ? colors.bullish : colors.bearish }}>
                  {invLatest.crude.weekChange > 0 ? '+' : ''}{invLatest.crude.weekChange}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════ ROW 4: Correlations + Outlook ═══════════ */}
      <div className="grid gap-16" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <CorrelationHeatmap 
            title="PRODUCT CORRELATION (30D)"
            labels={corrData?.product?.labels}
            matrix={corrData?.product?.matrix}
            loading={corrLoading}
            error={corrError}
          />
        </div>
        <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <CorrelationHeatmap 
            title="MACRO CORRELATION (30D)"
            labels={corrData?.macro?.labels}
            matrix={corrData?.macro?.matrix}
            loading={corrLoading}
            error={corrError}
          />
        </div>

        {/* Price outlook */}
        <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">PRICE OUTLOOK</div>
          <div className="p-4 mb-4 border rounded-lg" style={{ backgroundColor: sentimentColor + '08', borderColor: sentimentColor + '30' }}>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: sentimentColor + '20' }}>
                <span style={{ color: sentimentColor, fontSize: '16px' }}>
                  {computedScore >= 55 ? '▲' : computedScore >= 45 ? '→' : '▼'}
                </span>
              </div>
              <div>
                <div className="text-sm font-bold" style={{ color: sentimentColor }}>{computedLabel}</div>
                <div style={{ color: colors.textMuted, fontSize: '11px' }}>Score: {computedScore}/100</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
