import React, { useState, useMemo } from 'react';
import { format } from 'date-fns';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  instruments,
  spreads,
  crackSpread,
  wtiBrentSpread,
  opecData,
  regimeData,
  sentimentAnalysis,
  spreadCorrelationLabels,
  spreadCorrelationMatrix,
  productCorrelationLabels,
  productCorrelationMatrix,
  scheduledReleases,
} from '../../data/mockData';
import { getNextEIARelease } from '../../utils/dates';
import useDashboardStore from '../../stores/dashboardStore';
import useLivePriceStore from '../../stores/livePriceStore';
import CountdownTimer from '../ui/CountdownTimer';
import { useTheme } from '../../theme/ThemeContext';
import { useMacroData } from '../../hooks/useMacroData';
import { useCorrelations } from '../../hooks/useCorrelations';
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
  const { data: corrData, loading: corrLoading, error: corrError } = useCorrelations();
  const { sentimentSignals, toggleSentimentSignal, setAllSentimentSignals } = useDashboardStore();
  const { theme, colors } = useTheme();
  const { instruments } = useLivePriceStore();
  const isDark = theme === 'dark';
  const [expandedSignal, setExpandedSignal] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  const brent = instruments.find(i => i.id === 'brent');
  const wti = instruments.find(i => i.id === 'wti');

  const m1m12 = spreads[3];
  const m1m12Chart = m1m12.series.slice(-66);

  // Dynamic sentiment calculation based on enabled signals
  const { computedScore, computedLabel, enabledSignals, activeCount, totalCount } = useMemo(() => {
    const all = sentimentAnalysis.signals;
    const enabled = all.filter((s) => sentimentSignals[s.storeKey]);
    const totalWeight = enabled.reduce((sum, s) => sum + s.weight, 0);
    const weightedScore = totalWeight > 0
      ? enabled.reduce((sum, s) => sum + s.score * s.weight, 0) / totalWeight
      : 50;
    const score = Math.round(weightedScore);
    let label = 'NEUTRAL';
    if (score >= 75) label = 'STRONGLY BULLISH';
    else if (score >= 62) label = 'BULLISH';
    else if (score >= 55) label = 'SLIGHTLY BULLISH';
    else if (score >= 45) label = 'NEUTRAL';
    else if (score >= 38) label = 'SLIGHTLY BEARISH';
    else if (score >= 25) label = 'BEARISH';
    else label = 'STRONGLY BEARISH';
    return { computedScore: score, computedLabel: label, enabledSignals: enabled, activeCount: enabled.length, totalCount: all.length };
  }, [sentimentSignals]);

  const sentimentColor =
    computedScore >= 62 ? colors.bullish :
      computedScore >= 45 ? colors.neutral : colors.bearish;

  // Generate dynamic market behavior text based on active signals
  const marketBehavior = useMemo(() => {
    const parts = [];
    const activeKeys = Object.entries(sentimentSignals).filter(([, v]) => v).map(([k]) => k);

    if (activeKeys.includes('curveStructure') && activeKeys.includes('eiaInventory')) {
      parts.push('Physical fundamentals are the primary driver — backwardation and inventory draws confirm genuine tightness in the spot market.');
    } else if (activeKeys.includes('curveStructure')) {
      parts.push('Term-structure analysis shows backwardation, indicating physical tightness.');
    } else if (activeKeys.includes('eiaInventory')) {
      parts.push('US inventory data points to persistent crude draws, reducing available supply.');
    }

    if (activeKeys.includes('opecCompliance')) {
      parts.push('OPEC+ supply discipline remains intact with near-full compliance, constraining available barrels.');
    }

    if (activeKeys.includes('usdDxy') && activeKeys.includes('positioning')) {
      parts.push('Macro tailwinds are present: a weakening dollar supports USD-denominated commodities, while managed money net longs show rising speculative conviction.');
    } else if (activeKeys.includes('usdDxy')) {
      parts.push('The weakening US dollar provides a macro tailwind for crude benchmarks.');
    }

    if (activeKeys.includes('crackSpreads')) {
      parts.push('Healthy refining margins are pulling crude off the market as refiners run at elevated throughput rates.');
    }

    if (activeKeys.includes('geopoliticalRisk')) {
      parts.push('Geopolitical risk premium is elevated due to Red Sea disruptions and Libyan supply losses, adding $2-3/bbl of risk premium.');
    }

    if (activeKeys.includes('rigCount')) {
      parts.push('Declining US rig counts signal decelerating shale supply growth, removing the bearish overhang of unlimited US production response.');
    }

    if (parts.length === 0) {
      parts.push('No fundamental signals are currently selected. Enable metrics below to generate a market behavior analysis.');
    }

    // Price direction
    if (computedScore >= 62) {
      parts.push('Net assessment: the weight of evidence supports higher prices in the near to medium term. Brent likely to test $83-85 resistance zone.');
    } else if (computedScore >= 45) {
      parts.push('Net assessment: mixed signals suggest range-bound trading. Watch for catalysts to break out of current range.');
    } else {
      parts.push('Net assessment: bearish weight building. Brent likely to test $78-80 support levels.');
    }

    return parts.join(' ');
  }, [sentimentSignals, computedScore]);

  return (
    <div className="px-6 py-8 space-y-16" style={{ maxWidth: 1400, margin: '0 auto' }}>

      {/* ═══════════ ROW 1: Key Benchmarks ═══════════ */}
      <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="section-header mb-4">KEY BENCHMARKS</div>
        <div className="grid grid-cols-4 gap-16">
          {[
            { label: 'Brent', val: brent ? brent.price.toFixed(2) : '82.40', chg: brent ? `${brent.change > 0 ? '+' : ''}${brent.change.toFixed(2)}` : '+0.32', pct: brent ? `${brent.changePercent > 0 ? '+' : ''}${brent.changePercent.toFixed(2)}%` : '+0.39%', unit: '$/bbl' },
            { label: 'WTI', val: wti ? wti.price.toFixed(2) : '78.15', chg: wti ? `${wti.change > 0 ? '+' : ''}${wti.change.toFixed(2)}` : '+0.28', pct: wti ? `${wti.changePercent > 0 ? '+' : ''}${wti.changePercent.toFixed(2)}%` : '+0.36%', unit: '$/bbl' },
            { label: 'M1-M12', val: '+2.80', chg: '+0.08', pct: '', unit: '$/bbl', extraLabel: 'BACKWD' },
            { label: 'Crack 3:2:1', val: '18.40', chg: '+0.60', pct: '+3.37%', unit: '$/bbl' },
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
            { label: 'US Crude', val: '-2.4', unit: 'mn bbl', badge: 'DRAW', badgeColor: colors.bullish },
            { label: 'Cushing', val: '-0.8', unit: 'mn bbl', badge: 'DRAW', badgeColor: colors.bullish },
            { label: 'OPEC Compl.', val: '99.1%', unit: '', badge: 'HIGH', badgeColor: colors.bullish },
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
          <div className="px-4 py-3 rounded-lg border mb-4" style={{ backgroundColor: colors.bullish + '12', borderColor: colors.bullish }}>
            <div className="data-value text-sm font-bold" style={{ color: colors.bullish }}>PHYSICAL TIGHTNESS</div>
          </div>
          <div className="flex items-center gap-3 mb-2">
            <span style={{ color: colors.textMuted, fontSize: '12px' }}>Confidence</span>
            <span className="data-value text-base font-semibold" style={{ color: colors.textPrimary }}>82%</span>
          </div>
          <div className="w-full h-2.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
            <div className="h-full rounded-full" style={{ width: '82%', backgroundColor: colors.bullish }} />
          </div>
        </div>
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="section-header mb-4">OPEC+ SNAPSHOT</div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>TARGET</div>
              <div className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>27.2</div>
              <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
            </div>
            <div>
              <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>ACTUAL</div>
              <div className="data-value text-xl font-bold" style={{ color: colors.textPrimary }}>27.45</div>
              <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
            </div>
          </div>
          <div className="flex items-center justify-between pt-3 border-t" style={{ borderColor: colors.borderSubtle }}>
            <span style={{ color: colors.textMuted, fontSize: '12px' }}>Next Meeting</span>
            <CountdownTimer targetDate={opecData.nextMeeting} />
          </div>
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
              {sentimentAnalysis.signals.map((sig) => {
                const isEnabled = sentimentSignals[sig.storeKey];
                const c = sig.signal === 'BULL' ? colors.bullish : sig.signal === 'BEAR' ? colors.bearish : colors.neutral;
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
                        Weight: {sig.weight}% · Score: {sig.score}
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
              {sentimentAnalysis.signals.map((sig) => {
                const isEnabled = sentimentSignals[sig.storeKey];
                const isExpanded = expandedSignal === sig.storeKey;
                const c = sig.signal === 'BULL' ? colors.bullish : sig.signal === 'BEAR' ? colors.bearish : colors.neutral;

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
                          {sig.signal} {sig.signal === 'BULL' ? '▲' : sig.signal === 'BEAR' ? '▼' : '→'}
                        </span>
                      </div>
                    </div>

                    {/* Score bar */}
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: colors.bgElevated }}>
                        <div className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${sig.score}%`, backgroundColor: c, opacity: 0.8 }} />
                      </div>
                      <span className="data-value" style={{ color: c, fontSize: '12px', minWidth: '28px', textAlign: 'right' }}>{sig.score}</span>
                    </div>

                    <div className="text-xs" style={{ color: colors.textMuted, fontSize: '11px' }}>{sig.detail}</div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="mt-3 pt-3 border-t space-y-2" style={{ borderColor: colors.borderSubtle }}>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.bullish, fontSize: '11px' }}>Bullish case: </span>
                          <span className="text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>{sig.bullishReason}</span>
                        </div>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.bearish, fontSize: '11px' }}>Bearish risk: </span>
                          <span className="text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>{sig.bearishReason}</span>
                        </div>
                        <div>
                          <span className="text-xs font-medium" style={{ color: colors.neutral, fontSize: '11px' }}>Market impact: </span>
                          <span className="text-xs" style={{ color: colors.textSecondary, fontSize: '11px' }}>{sig.marketImpact}</span>
                        </div>
                        <div className="flex items-center gap-2 pt-1">
                          <span style={{ color: colors.textFaint, fontSize: '10px' }}>Weight in model: {sig.weight}%</span>
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
          <div className="flex items-center gap-3">
            <span className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>+{m1m12.value.toFixed(2)}</span>
            <span className="px-2 py-1 rounded-md text-xs font-semibold"
              style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '11px' }}>
              BACKWARDATION
            </span>
          </div>
        </div>
        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={m1m12Chart} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
              <XAxis dataKey="date"
                tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                tickLine={false} axisLine={{ stroke: colors.gridLine }} interval="preserveStartEnd" />
              <YAxis orientation="right" domain={['auto', 'auto']}
                tick={{ fill: colors.axisText, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                tickLine={false} axisLine={{ stroke: colors.gridLine }} />
              <Tooltip content={<ChartTooltip colors={colors} />} />
              <ReferenceLine y={0} stroke={colors.textMuted} strokeDasharray="3 3" />
              <Area type="monotone" dataKey="std1Upper" stroke="none" fill={colors.textMuted} fillOpacity={0.06} name="+1σ" />
              <Area type="monotone" dataKey="std1Lower" stroke="none" fill={colors.textMuted} fillOpacity={0.06} name="-1σ" />
              <Line type="monotone" dataKey="value" stroke={colors.neutral} strokeWidth={2} dot={false} name="M1-M12" />
              <Line type="monotone" dataKey="ma20" stroke={colors.textMuted} strokeWidth={1} strokeDasharray="4 4" dot={false} name="20D MA" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-6 mt-4 pt-4 border-t" style={{ borderColor: colors.borderSubtle }}>
          {[
            { label: 'Current', value: `+${m1m12.value.toFixed(2)}` },
            { label: '20D MA', value: `+${m1m12.ma20.toFixed(2)}` },
            { label: 'Z-Score', value: `+${m1m12.zScore.toFixed(2)}`, color: colors.neutral },
            { label: 'Percentile', value: `${m1m12.percentile}%`, color: colors.bullish },
            { label: 'Day Chg', value: `+${m1m12.dayChange.toFixed(2)}`, color: colors.bullish },
          ].map((s) => (
            <div key={s.label}>
              <div style={{ color: colors.textMuted, fontSize: '11px' }}>{s.label}</div>
              <div className="data-value text-sm font-semibold" style={{ color: s.color || colors.textPrimary }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ═══════════ ROW 3b: EIA + Risks/Catalysts side-by-side ═══════════ */}
      <div className="grid grid-cols-2 gap-10">
        {/* EIA compact */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="flex items-center justify-between mb-4">
            <div className="section-header">EIA WEEKLY</div>
            <CountdownTimer targetDate={getNextEIARelease()} label="NEXT" />
          </div>
          <div className="p-4 border mb-4 rounded-lg" style={{ backgroundColor: colors.overlayBg, borderColor: colors.borderSubtle }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium" style={{ color: colors.textPrimary }}>US Crude</span>
              <span className="px-2 py-1 rounded-md" style={{ backgroundColor: colors.bullish + '18', color: colors.bullish, fontSize: '10px', fontWeight: 700 }}>BULLISH</span>
            </div>
            <div className="data-value text-2xl font-bold" style={{ color: colors.textPrimary }}>430.2 <span style={{ color: colors.textFaint, fontSize: '13px', fontWeight: 400 }}>mn bbl</span></div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              {[
                { l: 'DRAW', v: '-2.4' },
                { l: 'CONS.', v: '-1.8' },
                { l: 'SURP.', v: '-0.6' },
              ].map((x) => (
                <div key={x.l}>
                  <div style={{ color: colors.textMuted, fontSize: '10px', fontWeight: 600 }}>{x.l}</div>
                  <div className="data-value text-sm font-semibold" style={{ color: colors.bullish }}>{x.v}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="text-sm leading-relaxed" style={{ color: colors.textMuted, lineHeight: '1.5' }}>
            4th consecutive draw. Cushing −0.8 mn, Gasoline −1.2 mn. Refinery util at 91.2%.
          </div>
        </div>

        {/* Risks & Catalysts */}
        <div className="border p-6 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="mb-5">
            <div className="section-header mb-3" style={{ color: colors.bearish }}>KEY RISKS</div>
            {sentimentAnalysis.risks.map((r, i) => (
              <div key={i} className="flex items-start gap-2 mb-2">
                <span style={{ color: colors.bearish, fontSize: '10px', marginTop: '4px' }}>▼</span>
                <span className="text-sm leading-relaxed" style={{ color: colors.textSecondary, lineHeight: '1.5' }}>{r}</span>
              </div>
            ))}
          </div>
          <div>
            <div className="section-header mb-3" style={{ color: colors.bullish }}>CATALYSTS</div>
            {sentimentAnalysis.catalysts.map((c, i) => (
              <div key={i} className="flex items-start gap-2 mb-2">
                <span style={{ color: colors.bullish, fontSize: '10px', marginTop: '4px' }}>▲</span>
                <span className="text-sm leading-relaxed" style={{ color: colors.textSecondary, lineHeight: '1.5' }}>{c}</span>
              </div>
            ))}
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

          <div className="section-header mb-3">BRENT KEY LEVELS</div>
          <div className="space-y-2">
            {[
              { label: 'Resistance 2', val: '$85.00', note: '52-week high' },
              { label: 'Resistance 1', val: '$83.80', note: 'Swing high' },
              { label: 'Current', val: '$82.40', note: '', highlight: true },
              { label: 'Support 1', val: '$80.50', note: '20D EMA' },
              { label: 'Support 2', val: '$78.00', note: '50D EMA' },
            ].map((lvl) => (
              <div key={lvl.label} className="flex items-center justify-between py-1"
                style={{ borderLeft: lvl.highlight ? `3px solid ${colors.neutral}` : '3px solid transparent', paddingLeft: '10px' }}>
                <span style={{ color: lvl.highlight ? colors.neutral : colors.textMuted, fontSize: '12px', fontWeight: lvl.highlight ? 600 : 400 }}>{lvl.label}</span>
                <div className="flex items-center gap-3">
                  <span className="data-value text-sm font-medium" style={{ color: lvl.highlight ? colors.neutral : colors.textPrimary }}>{lvl.val}</span>
                  {lvl.note && <span style={{ color: colors.textFaint, fontSize: '10px' }}>{lvl.note}</span>}
                </div>
              </div>
            ))}
          </div>

          {/* OPEC mini table */}
          <div className="mt-4 pt-4 border-t" style={{ borderColor: colors.borderSubtle }}>
            <div className="section-header mb-2">OPEC COMPLIANCE</div>
            {opecData.members.map((m) => (
              <div key={m.country} className="flex items-center justify-between py-1">
                <span style={{ color: colors.textSecondary, fontSize: '11px' }}>{m.flag} {m.country}</span>
                <span className="data-value" style={{
                  color: m.compliance >= 100 ? colors.bullish : m.compliance >= 97 ? colors.neutral : colors.bearish,
                  fontSize: '11px',
                }}>{m.compliance.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
