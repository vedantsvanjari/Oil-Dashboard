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

const categories = ['All', 'OPEC', 'Geopolitics', 'Inventories', 'Tankers', 'Refineries', 'Macro'];

export default function NewsSection() {
  const { newsCategory, setNewsCategory, newsSearch, setNewsSearch } = useDashboardStore();
  const { newsItems, isLoadingNews, newsError, fetchNews } = useNewsStore();
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

        {/* Right: OPEC Tracker + Scheduled Releases */}
        <div className="space-y-5">
          {/* OPEC Tracker */}
          <div className="border p-5 rounded-xl theme-card" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
            <div className="section-header mb-4" style={{ fontSize: '14px' }}>OPEC+ TRACKER</div>

            {/* Next meeting */}
            <div className="flex items-center justify-between mb-4 pb-3 border-b" style={{ borderColor: colors.borderSubtle }}>
              <span className="text-sm" style={{ color: colors.textSecondary }}>Next Meeting</span>
              <span className="text-sm" style={{ color: colors.textMuted }}>Data source not implemented</span>
            </div>

            {/* Production overview */}
            <div className="grid grid-cols-3 gap-4 mb-5">
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>TARGET</div>
                <div className="data-value text-lg font-bold" style={{ color: colors.textMuted }}>
                  N/A
                </div>
              </div>
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>ACTUAL</div>
                {opecLoading ? (
                  <div className="text-sm" style={{ color: colors.textMuted }}>Loading...</div>
                ) : opecError ? (
                  <div className="text-sm" style={{ color: colors.bearish }}>Error</div>
                ) : (
                  <>
                    <div className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>
                      {opecData?.totalProduction?.latest?.toFixed(2) || 'N/A'}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: '11px' }}>
                      mb/d {opecData?.totalProduction?.trend ? (
                        <span style={{ color: opecData.totalProduction.trend > 0 ? colors.bullish : colors.bearish }}>
                          ({opecData.totalProduction.trend > 0 ? '+' : ''}{opecData.totalProduction.trend.toFixed(2)})
                        </span>
                      ) : ''}
                    </div>
                  </>
                )}
              </div>
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>COMPLIANCE</div>
                <div className="data-value text-lg font-bold" style={{ color: colors.textMuted }}>
                  N/A
                </div>
              </div>
            </div>

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
                    <Tooltip 
                      contentStyle={{ backgroundColor: colors.tooltipBg, borderColor: colors.tooltipBorder, fontSize: '11px' }}
                      itemStyle={{ color: colors.textPrimary }}
                      labelStyle={{ color: colors.textMuted }}
                    />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Area type="monotone" dataKey="value" stroke={colors.neutral} fillOpacity={1} fill="url(#colorOpec)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Member table */}
            <table className="w-full mb-4" style={{ fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.borderSubtle}` }}>
                  <th className="text-left py-2 font-medium" style={{ color: colors.textMuted }}>Member</th>
                  <th className="text-right py-2 font-medium" style={{ color: colors.textMuted }}>Target</th>
                  <th className="text-right py-2 font-medium" style={{ color: colors.textMuted }}>Actual</th>
                  <th className="text-right py-2 font-medium" style={{ color: colors.textMuted }}>Cmpl.</th>
                </tr>
              </thead>
              <tbody>
                {opecLoading ? (
                  <tr><td colSpan="4" className="py-4 text-center text-sm" style={{ color: colors.textMuted }}>Loading members...</td></tr>
                ) : opecError ? (
                  <tr><td colSpan="4" className="py-4 text-center text-sm" style={{ color: colors.bearish }}>Failed to load data</td></tr>
                ) : opecData?.members?.map((m) => (
                  <tr key={m.country} style={{ borderBottom: `1px solid ${colors.borderSubtle}` }}>
                    <td className="py-2" style={{ color: colors.textPrimary }}>
                      {m.flag} {m.country}
                    </td>
                    <td className="text-right data-value py-2" style={{ color: colors.textMuted }}>
                      N/A
                    </td>
                    <td className="text-right data-value py-2" style={{ color: colors.textPrimary }}>
                      {m.actual.toFixed(2)}
                    </td>
                    <td className="text-right py-2 text-xs" style={{ color: colors.textMuted }}>
                      N/A
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Secretary General statement */}
            <div className="p-3 border-l-2 rounded-r-lg" style={{ borderColor: colors.neutral, backgroundColor: colors.overlayBg }}>
              <div className="text-sm italic leading-relaxed" style={{ color: colors.textMuted }}>
                Data source not implemented
              </div>
            </div>
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
