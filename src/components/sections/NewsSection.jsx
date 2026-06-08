import React, { useMemo, useEffect } from 'react';
import { format } from 'date-fns';
import { opecData, scheduledReleases } from '../../data/mockData';
import useDashboardStore from '../../stores/dashboardStore';
import useNewsStore from '../../stores/newsStore';
import NewsItem from '../ui/NewsItem';
import CountdownTimer from '../ui/CountdownTimer';
import { useTheme } from '../../theme/ThemeContext';

const categories = ['All', 'OPEC', 'Geopolitics', 'Inventories', 'Tankers', 'Refineries', 'Macro'];

export default function NewsSection() {
  const { newsCategory, setNewsCategory, newsSearch, setNewsSearch } = useDashboardStore();
  const { newsItems, isLoadingNews, newsError, fetchNews } = useNewsStore();
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
              <CountdownTimer targetDate={opecData.nextMeeting} />
            </div>

            {/* Production overview */}
            <div className="grid grid-cols-3 gap-4 mb-5">
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>TARGET</div>
                <div className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>
                  {opecData.productionTarget.toFixed(1)}
                </div>
                <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
              </div>
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>ACTUAL</div>
                <div className="data-value text-lg font-bold" style={{ color: colors.textPrimary }}>
                  {opecData.estimatedActual.toFixed(2)}
                </div>
                <div style={{ color: colors.textMuted, fontSize: '11px' }}>mb/d</div>
              </div>
              <div>
                <div style={{ color: colors.textMuted, fontSize: '11px', fontWeight: 600 }}>COMPLIANCE</div>
                <div className="data-value text-lg font-bold" style={{ color: colors.bullish }}>
                  {opecData.compliancePercent.toFixed(1)}%
                </div>
              </div>
            </div>

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
                {opecData.members.map((m) => (
                  <tr key={m.country} style={{ borderBottom: `1px solid ${colors.borderSubtle}` }}>
                    <td className="py-2" style={{ color: colors.textPrimary }}>
                      {m.flag} {m.country}
                    </td>
                    <td className="text-right data-value py-2" style={{ color: colors.textSecondary }}>
                      {m.target.toFixed(1)}
                    </td>
                    <td className="text-right data-value py-2" style={{ color: colors.textPrimary }}>
                      {m.actual.toFixed(2)}
                    </td>
                    <td className="text-right py-2">
                      <span className="data-value font-medium"
                        style={{ color: m.compliance >= 100 ? colors.bullish : m.compliance >= 97 ? colors.neutral : colors.bearish }}>
                        {m.compliance.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Secretary General statement */}
            <div className="p-3 border-l-2 rounded-r-lg" style={{ borderColor: colors.neutral, backgroundColor: colors.overlayBg }}>
              <div className="text-sm italic leading-relaxed" style={{ color: colors.textSecondary }}>
                {opecData.secretaryStatement}
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
