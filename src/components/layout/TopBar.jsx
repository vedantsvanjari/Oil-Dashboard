import React from 'react';
import { navTabs } from '../../data/mockData';
import useDashboardStore from '../../stores/dashboardStore';
import { useTheme } from '../../theme/ThemeContext';

export default function TopBar() {
  const { activeTab, setActiveTab } = useDashboardStore();
  const { theme, toggleTheme, colors } = useTheme();

  return (
    <div className="flex items-center justify-between h-14 px-6 border-b theme-card"
      style={{ backgroundColor: colors.bgSurface, borderColor: colors.border }}>
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #10b981, #06b6d4)' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <span className="font-semibold text-sm tracking-wide" style={{ color: colors.textPrimary }}>
          OIL INTELLIGENCE
        </span>
      </div>

      {/* Nav tabs — each tab is a clear bordered box */}
      <div className="flex items-center gap-1.5 p-1 rounded-lg"
        style={{ backgroundColor: colors.bgElevated }}>
        {navTabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="px-4 py-1.5 text-xs font-bold tracking-wider rounded-md transition-all duration-200 cursor-pointer"
              style={{
                backgroundColor: isActive ? colors.bgSurface : 'transparent',
                color: isActive ? colors.textPrimary : colors.textMuted,
                letterSpacing: '0.08em',
                boxShadow: isActive
                  ? (theme === 'light'
                    ? '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)'
                    : '0 1px 3px rgba(0,0,0,0.3)')
                  : 'none',
                border: isActive ? `1px solid ${colors.border}` : '1px solid transparent',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Right: theme toggle + user */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="relative w-12 h-6 rounded-full cursor-pointer transition-colors duration-300 flex items-center"
          style={{
            backgroundColor: theme === 'dark' ? '#232940' : '#dde1e8',
          }}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          <div
            className="absolute w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300"
            style={{
              left: theme === 'dark' ? '26px' : '2px',
              backgroundColor: theme === 'dark' ? '#141826' : '#ffffff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
            }}
          >
            {theme === 'light' ? (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5">
                <circle cx="12" cy="12" r="5" />
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
              </svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a0a8bf" strokeWidth="2.5">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
              </svg>
            )}
          </div>
        </button>

        <span className="text-xs" style={{ color: colors.textMuted }}>Desk: Energy Trading</span>
        <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold"
          style={{ backgroundColor: colors.activeTabBg, color: colors.textSecondary }}>
          JD
        </div>
      </div>
    </div>
  );
}
