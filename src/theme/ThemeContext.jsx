import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';

const ThemeContext = createContext();

const lightPalette = {
  // Backgrounds
  bgPrimary: '#f5f3ee',
  bgSurface: '#ffffff',
  bgElevated: '#f8f7f3',
  bgDeep: '#edeae3',

  // Borders
  border: '#dde1e8',
  borderSubtle: '#eaecf0',

  // Text
  textPrimary: '#1a1d26',
  textSecondary: '#5a6178',
  textMuted: '#8c93a8',
  textFaint: '#b0b7c9',

  // Semantic
  bullish: '#0d9f6f',
  bearish: '#dc2c2c',
  neutral: '#d48c06',
  cyan: '#0891b2',
  purple: '#7c3aed',

  // Charts
  gridLine: '#e2e6ee',
  axisText: '#7a839a',
  tooltipBg: '#ffffff',
  tooltipBorder: '#dde1e8',

  // Scrollbar
  scrollTrack: '#f0f2f5',
  scrollThumb: '#cdd2dc',
  scrollThumbHover: '#b0b7c9',

  // Special
  cardBg: '#ffffff',
  cardBorder: '#d8d3c8',
  inputBg: '#f0ede6',
  activeTabBg: '#e2e6ee',
  badgeBackground: (color) => color + '18',
  overlayBg: '#f7f5f0',
  heatmapCellBorder: '#f0ede6',
  inventoryBgFill: '#f0ede6',
};

const darkPalette = {
  // Backgrounds
  bgPrimary: '#0c0f18',
  bgSurface: '#141826',
  bgElevated: '#1c2236',
  bgDeep: '#0a0d14',

  // Borders
  border: '#232940',
  borderSubtle: '#1c2236',

  // Text
  textPrimary: '#e8eaf0',
  textSecondary: '#a0a8bf',
  textMuted: '#5c6480',
  textFaint: '#3a4158',

  // Semantic
  bullish: '#10b981',
  bearish: '#ef4444',
  neutral: '#f59e0b',
  cyan: '#06b6d4',
  purple: '#a855f7',

  // Charts
  gridLine: '#232940',
  axisText: '#5c6480',
  tooltipBg: '#1c2236',
  tooltipBorder: '#3a4158',

  // Scrollbar
  scrollTrack: '#0c0f18',
  scrollThumb: '#1c2236',
  scrollThumbHover: '#3a4158',

  // Special
  cardBg: '#181d30',
  cardBorder: '#2a3150',
  inputBg: '#0c0f18',
  activeTabBg: '#1c2236',
  badgeBackground: (color) => color + '18',
  overlayBg: '#111525',
  heatmapCellBorder: '#0c0f18',
  inventoryBgFill: '#0c0f18',
};

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('oil-dash-theme') || 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    localStorage.setItem('oil-dash-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));

  const colors = useMemo(() => (theme === 'light' ? lightPalette : darkPalette), [theme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, colors }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
