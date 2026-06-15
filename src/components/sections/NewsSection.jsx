import React, { useMemo, useEffect } from 'react';
import { format } from 'date-fns';
import { opecData, scheduledReleases } from '../../data/mockData';
import useDashboardStore from '../../stores/dashboardStore';
import useNewsStore from '../../stores/newsStore';
import { useOpecData } from '../../hooks/useOpecData';
import NewsItem from '../ui/NewsItem';
import CountdownTimer from '../ui/CountdownTimer';
import { useTheme } from '../../theme/ThemeContext';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

// ── OPEC chart helpers ────────────────────────────────────────────────────
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function formatOpecMonth(period) {
  if (!period || typeof period !== 'string') return period || '';
  const [year, mon] = period.split('-');
  const idx = parseInt(mon, 10) - 1;
  return `${MONTH_NAMES[idx] || mon} ${year}`;
}

function OpecTooltip({ active, payload, colors }) {
  if (!active || !payload || !payload.length) return null;
  const { payload: data } = payload[0];
  return (
    <div style={{
      backgroundColor: colors?.tooltipBg || '#1a1d26',
      borderColor: colors?.tooltipBorder || '#2a2d3a',
      border: '1px solid',
      borderRadius: 6,
      padding: '6px 10px',
      fontSize: '11px',
    }}>
      <div style={{ color: colors?.textMuted || '#9ca3af', marginBottom: 3 }}>
        {formatOpecMonth(data?.period)}
      </div>
      <div style={{ color: colors?.textPrimary || '#e5e7eb', fontWeight: 600 }}>
        Production: {typeof data?.value === 'number' ? data.value.toFixed(2) : 'N/A'} mb/d
      </div>
    </div>
  );
}

const categories = ['All', 'OPEC', 'Geopolitics', 'Inventories', 'Tankers', 'Refineries', 'Macro'];

export default function NewsSection() {
  const { newsCategory, setNewsCategory, newsSearch, setNewsSearch } = useDashboardStore();
  const { newsItems, aggregateSentiment, isLoadingNews, newsError, fetchNews } = useNewsStore();
  const { data: opecData, loading: opecLoading, error: opecError } = useOpecData();
  const { colors } = useTheme();

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  const filteredNews = useMemo(() => {
    let items = [...newsItems];
    // Sort: pinned first, then by timestamp
    items.sort((a, b) => {
      if (a.pinned !== b.pinned) return b.pinned ? 1 : -1;
      return b.timestamp - a.timestamp;
    });
    if (newsCategory !== 'All') {
      items = items.filter((n) => n.category === newsCategory);
    }
    if (newsSearch.trim()) {
      const q = newsSearch.toLowerCase();
      items = items.filter(
        (n) =>
          n.headline.toLowerCase().includes(q) ||
          n.source.toLowerCase().includes(q) ||
          n.summary.toLowerCase().includes(q)
      );
    }
    return items;
  }, [newsItems, newsCategory, newsSearch]);

  return (
    <div className="px-6 py-8" style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div className="grid gap-16" style={{ gridTemplateColumns: '1fr 380px' }}>
        {/* Left: News Feed */}
        <div className="border rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
          <div className="p-5 border-b" style={{ borderColor: colors.borderSubtle }}>
            <div className="section-header mb-4" style={{ fontSize: '14px' }}>NEWS FEED</div>

            {/* Filter bar */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1.5">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setNewsCategory(cat)}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors duration-150"
                    style={{
                      backgroundColor: newsCategory === cat ? colors.activeTabBg : 'transparent',
                      color: newsCategory === cat ? colors.textPrimary : colors.textMuted,
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
              <input
                type="text"
                placeholder="Search headlines..."
                value={newsSearch}
                onChange={(e) => setNewsSearch(e.target.value)}
                className="px-3 py-2 text-sm border rounded-lg outline-none"
                style={{
                  backgroundColor: colors.inputBg,
                  borderColor: colors.borderSubtle,
                  color: colors.textPrimary,
                  width: 220,
                }}
              />
            </div>
          </div>

          {/* News list */}
          <div className="custom-scroll" style={{ maxHeight: 800 }}>
            {isLoadingNews && (
              <div className="p-8 text-center text-sm" style={{ color: colors.textPrimary }}>
                Loading news...
              </div>
            )}
            {newsError && !isLoadingNews && (
              <div className="p-8 text-center text-sm" style={{ color: colors.bearish }}>
                {newsError}
              </div>
            )}
            {!isLoadingNews && !newsError && filteredNews.map((item) => (
              <NewsItem key={item.id} item={item} />
            ))}
            {!isLoadingNews && !newsError && filteredNews.length === 0 && (
              <div className="p-8 text-center text-sm" style={{ color: colors.textMuted }}>
                No news items match your filters.
              </div>
            )}
          </div>
        </div>

        {/* Right: Summary Cards */}
        <div className="space-y-5">
          {/* Overall News Sentiment */}
          <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
            <div className="section-header mb-4" style={{ fontSize: '14px' }}>OVERALL NEWS SENTIMENT</div>
            
            {isLoadingNews ? (
              <div className="text-sm" style={{ color: colors.textMuted }}>Loading sentiment...</div>
            ) : aggregateSentiment ? (
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="data-value text-2xl font-bold" 
                      style={{ 
                        color: aggregateSentiment.market_sentiment === 'Bullish' ? colors.bullish : 
                               aggregateSentiment.market_sentiment === 'Bearish' ? colors.bearish : colors.neutral 
                      }}>
                      {aggregateSentiment.market_sentiment.toUpperCase()}
                    </div>
                    <div style={{ color: colors.textSecondary, fontSize: '12px' }}>
                      {aggregateSentiment.confidence}% Confidence
                    </div>
                  </div>
                  <div className="w-12 h-12 rounded-full border-4 flex items-center justify-center"
                    style={{
                      borderColor: aggregateSentiment.market_sentiment === 'Bullish' ? colors.bullish : 
                                   aggregateSentiment.market_sentiment === 'Bearish' ? colors.bearish : colors.neutral,
                      backgroundColor: colors.bgElevated
                    }}>
                    <span style={{ 
                      color: aggregateSentiment.market_sentiment === 'Bullish' ? colors.bullish : 
                             aggregateSentiment.market_sentiment === 'Bearish' ? colors.bearish : colors.neutral,
                      fontSize: '18px' 
                    }}>
                      {aggregateSentiment.market_sentiment === 'Bullish' ? '▲' : 
                       aggregateSentiment.market_sentiment === 'Bearish' ? '▼' : '→'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-3 border-t" style={{ borderColor: colors.borderSubtle }}>
                  <div className="text-center">
                    <div className="data-value text-lg font-bold" style={{ color: colors.bullish }}>{aggregateSentiment.bullish}</div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>BULLISH</div>
                  </div>
                  <div className="text-center">
                    <div className="data-value text-lg font-bold" style={{ color: colors.bearish }}>{aggregateSentiment.bearish}</div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>BEARISH</div>
                  </div>
                  <div className="text-center">
                    <div className="data-value text-lg font-bold" style={{ color: colors.neutral }}>{aggregateSentiment.neutral}</div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>NEUTRAL</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-sm" style={{ color: colors.textMuted }}>Sentiment not available</div>
            )}
          </div>

          {/* OPEC Tracker */}
          <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
            <div className="section-header mb-4" style={{ fontSize: '14px' }}>OPEC+ TRACKER</div>



            {/* Production KPIs: Latest / Prev Month / Monthly Change */}
            {opecLoading ? (
              <div className="text-sm mb-5" style={{ color: colors.textMuted }}>Loading...</div>
            ) : opecError ? (
              <div className="text-sm mb-5" style={{ color: colors.bearish }}>Error loading data</div>
            ) : (() => {
              const hist = opecData?.totalProduction?.history || [];
              const latest   = opecData?.totalProduction?.latest;
              const prevVal  = hist.length >= 2 ? hist[hist.length - 2].value : null;
              const prevMonth = hist.length >= 2 ? formatOpecMonth(hist[hist.length - 2].period) : null;
              const change   = latest != null && prevVal != null
                ? parseFloat((latest - prevVal).toFixed(2))
                : null;
              const changeColor = change == null
                ? colors.textMuted
                : change > 0 ? colors.bullish : change < 0 ? colors.bearish : colors.textMuted;
              return (
                <div className="grid grid-cols-3 gap-4 mb-5">
                  {/* Latest Production */}
                  <div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>LATEST</div>
                    <div className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>
                      {latest != null ? latest.toFixed(2) : 'N/A'}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
                  </div>
                  {/* Previous Month */}
                  <div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>PREV MONTH</div>
                    <div className="data-value text-lg font-bold" style={{ color: colors.textSecondary }}>
                      {prevVal != null ? prevVal.toFixed(2) : 'N/A'}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: '11px' }}>
                      {prevMonth || 'mb/d'}
                    </div>
                  </div>
                  {/* Monthly Change */}
                  <div>
                    <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>MONTHLY CHG</div>
                    <div className="data-value text-lg font-bold" style={{ color: changeColor }}>
                      {change != null ? `${change > 0 ? '+' : ''}${change.toFixed(2)}` : 'N/A'}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
                  </div>
                </div>
              );
            })()}

            {/* Historical Chart */}
            {!opecLoading && !opecError && opecData?.totalProduction?.history && (
              <div className="mb-5" style={{ height: 120 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={opecData.totalProduction.history} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorOpec" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={colors.neutral} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={colors.neutral} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Tooltip content={<OpecTooltip colors={colors} />} />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Area type="monotone" dataKey="value" stroke={colors.neutral} fillOpacity={1} fill="url(#colorOpec)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

          </div>

          {/* Scheduled Releases */}
          <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
            <div className="section-header mb-4" style={{ fontSize: '14px' }}>SCHEDULED DATA RELEASES</div>
            {scheduledReleases.map((release) => (
              <div
                key={release.name}
                className="flex items-center justify-between py-3 border-b"
                style={{ borderColor: colors.borderSubtle }}
              >
                <div>
                  <div className="text-sm font-medium" style={{ color: colors.textPrimary }}>
                    {release.name}
                  </div>
                  <div style={{ color: colors.textMuted, fontSize: '12px' }}>
                    {release.source} · {format(release.date, 'MMM d, HH:mm')}
                  </div>
                </div>
                <CountdownTimer targetDate={release.date} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
