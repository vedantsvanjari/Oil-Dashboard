# 🛢️ Oil Market Intelligence Dashboard

An institutional-grade oil market intelligence dashboard built with React, providing real-time price monitoring, spread analytics, physical market fundamentals, and AI-driven sentiment analysis — all in a single unified interface.

## ✨ Features

### 📊 Overview
- **Key Benchmarks** — Live prices for Brent, WTI, Crack Spreads, and DXY with change indicators
- **Sentiment Engine** — Weighted composite score (0–100) derived from 9 configurable fundamental signals with dynamic market behavior narratives
- **Active Regime Detection** — Market regime classification (Physical Tightness, Contango, etc.) with confidence scoring
- **OPEC+ Snapshot** — Production targets, actual output, compliance rates, and next-meeting countdown
- **Correlation Heatmaps** — 30-day spread and product correlation matrices with interactive hover details
- **Price Outlook** — Key support/resistance levels, directional bias, and OPEC member compliance breakdown

### 💰 Prices
- Interactive price charts with configurable time ranges (1M, 3M, 6M, 1Y, 5Y)
- Technical indicators: VWAP, EMA-20, EMA-50, Bollinger Bands
- Instrument selection across Brent, WTI, Dubai, and refined products

### 📈 Spreads
- Calendar spread monitoring (M1-M2, M1-M6, M1-M12)
- Crack spread and WTI-Brent basis tracking
- Statistical overlays with moving averages, z-scores, and percentile rankings

### 🏭 Physical Market
- EIA weekly inventory data (Crude, Gasoline, Distillates)
- Inventory charts with 5-year range bands and seasonal comparisons
- Refinery utilization rates and Cushing hub stocks

### 📰 News & Analysis
- Categorized news feed (OPEC, Supply, Demand, Geopolitical, Macro)
- Full-text search across headlines
- Sentiment-tagged articles with source attribution and timestamps

### 🎨 Theming
- Light and dark mode with smooth CSS transitions
- Persistent theme preference via localStorage
- Fully scoped color palettes for both themes

---

## 🛠️ Tech Stack

| Layer         | Technology                                                      |
| ------------- | --------------------------------------------------------------- |
| Framework     | [React 18](https://react.dev/) (JSX)                            |
| Build Tool    | [Vite 6](https://vite.dev/)                                     |
| Styling       | [Tailwind CSS 4](https://tailwindcss.com/) + custom CSS         |
| Charts        | [Recharts 2](https://recharts.org/)                             |
| State         | [Zustand 5](https://zustand.docs.pmnd.rs/)                      |
| Date Utility  | [date-fns 4](https://date-fns.org/)                             |
| Fonts         | IBM Plex Sans · JetBrains Mono (Google Fonts)                   |

---

## 📁 Project Structure

```
Dashboard/
├── index.html                  # Entry HTML with meta tags & font preloads
├── vite.config.js              # Vite + React + Tailwind plugin config
├── package.json
├── public/
│   └── vite.svg                # Favicon
└── src/
    ├── main.jsx                # React root + ThemeProvider mount
    ├── App.jsx                 # Tab-based routing & layout shell
    ├── index.css               # Global styles, theme vars, animations
    ├── theme/
    │   └── ThemeContext.jsx     # Light/dark palette + theme toggle provider
    ├── stores/
    │   └── dashboardStore.js   # Zustand store (tabs, filters, indicators)
    ├── data/
    │   └── mockData.js         # Comprehensive mock dataset (~33 KB)
    ├── components/
    │   ├── layout/
    │   │   ├── TopBar.jsx      # Navigation tabs + theme toggle
    │   │   ├── TickerTape.jsx  # Scrolling price ticker
    │   │   └── StatusBar.jsx   # Footer status bar
    │   ├── sections/
    │   │   ├── OverviewSection.jsx   # Main dashboard overview
    │   │   ├── PricesSection.jsx     # Price charts & indicators
    │   │   ├── SpreadsSection.jsx    # Spread analytics
    │   │   ├── PhysicalSection.jsx   # Inventory & physical data
    │   │   ├── NewsSection.jsx       # News feed & search
    │   │   └── RegimeSection.jsx     # Market regime analysis
    │   ├── charts/
    │   │   ├── PriceChart.jsx        # Composable price chart
    │   │   ├── SpreadChart.jsx       # Spread time-series chart
    │   │   ├── InventoryChart.jsx    # Inventory vs. 5yr range
    │   │   └── CorrelationHeatmap.jsx # Interactive heatmap
    │   └── ui/
    │       ├── PriceCard.jsx         # Instrument price card
    │       ├── SpreadCard.jsx        # Spread summary card
    │       ├── MetricTile.jsx        # KPI metric tile
    │       ├── NewsItem.jsx          # News article card
    │       ├── RegimeBadge.jsx       # Regime indicator badge
    │       └── CountdownTimer.jsx    # Live countdown component
    └──
```

---

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18
- npm ≥ 9 (ships with Node)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Dashboard

# Install dependencies
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Production Build

```bash
npm run build
npm run preview   # Preview the production build locally
```

---

## 🏗️ Architecture

### State Management

The app uses **Zustand** for lightweight, hook-based global state. The single store ([dashboardStore.js](src/stores/dashboardStore.js)) manages:

- Active navigation tab
- Selected instruments and time ranges
- Technical indicator toggles (VWAP, EMA, Bollinger)
- Spread chart selection
- Inventory category tabs
- News filtering and search
- Sentiment engine signal configuration

### Theming

A custom React Context ([ThemeContext.jsx](src/theme/ThemeContext.jsx)) provides:

- Two complete color palettes (light & dark) with semantic tokens
- `useTheme()` hook returning `{ theme, toggleTheme, colors }`
- CSS custom properties synced via `data-theme` attribute for scrollbar and chart styling
- Theme preference persisted to `localStorage`

### Data Layer

Currently uses a comprehensive mock dataset ([mockData.js](src/data/mockData.js)) containing:

- Historical price series for multiple crude benchmarks
- Calendar and crack spread time-series with statistical bands
- EIA inventory data with seasonal comparisons
- OPEC+ production and compliance data
- Sentiment analysis signals with weights, scores, and narratives
- Correlation matrices for spreads and refined products
- Curated news articles with sentiment tags

> **Note**: The mock data layer is designed to be swapped with live API integrations (e.g., Bloomberg, Refinitiv, EIA API) without changing component logic.

---

## 📜 License

This project is private and not licensed for public distribution.
