import { addDays, subDays, subHours, subMinutes, format, nextWednesday, setHours, setMinutes } from 'date-fns';

// ─── HELPERS ───────────────────────────────────────────────
function seededRandom(seed) {
  let s = seed;
  return function () {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function generatePricePath(startPrice, days, volatility, seed) {
  const rng = seededRandom(seed);
  const data = [];
  let price = startPrice;
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const date = subDays(now, i);
    const change = (rng() - 0.48) * volatility;
    price = Math.max(price * 0.7, price + change);
    const high = price + rng() * volatility * 0.5;
    const low = price - rng() * volatility * 0.5;
    const open = price + (rng() - 0.5) * volatility * 0.3;
    const close = price;
    const volume = Math.floor(100000 + rng() * 300000);
    data.push({
      date: format(date, 'yyyy-MM-dd'),
      timestamp: date.getTime(),
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume,
    });
  }
  return data;
}

function generateIntradayData(basePrice, seed) {
  const rng = seededRandom(seed);
  const data = [];
  let price = basePrice - 0.5;
  const now = new Date();
  const marketOpen = new Date(now);
  marketOpen.setHours(9, 30, 0, 0);
  for (let i = 0; i < 78; i++) {
    const time = new Date(marketOpen.getTime() + i * 5 * 60000);
    const change = (rng() - 0.48) * 0.15;
    price += change;
    const high = price + rng() * 0.08;
    const low = price - rng() * 0.08;
    const volume = Math.floor(2000 + rng() * 8000);
    data.push({
      date: format(time, 'HH:mm'),
      timestamp: time.getTime(),
      open: +(price - change).toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +price.toFixed(2),
      volume,
    });
  }
  return data;
}

function computeIndicators(priceData) {
  const closes = priceData.map((d) => d.close);
  const result = priceData.map((d, i) => {
    const entry = { ...d };

    // EMA 20
    if (i >= 19) {
      const slice = closes.slice(i - 19, i + 1);
      entry.ema20 = +(slice.reduce((a, b) => a + b, 0) / 20).toFixed(2);
    }
    // EMA 50
    if (i >= 49) {
      const slice = closes.slice(i - 49, i + 1);
      entry.ema50 = +(slice.reduce((a, b) => a + b, 0) / 50).toFixed(2);
    }
    // VWAP (simple approx)
    if (i >= 0) {
      const lookback = Math.min(i + 1, 20);
      const slice = priceData.slice(i - lookback + 1, i + 1);
      const totalVol = slice.reduce((a, s) => a + s.volume, 0);
      const vwap = totalVol > 0
        ? slice.reduce((a, s) => a + s.close * s.volume, 0) / totalVol
        : d.close;
      entry.vwap = +vwap.toFixed(2);
    }
    // Bollinger Bands (20-period)
    if (i >= 19) {
      const slice = closes.slice(i - 19, i + 1);
      const mean = slice.reduce((a, b) => a + b, 0) / 20;
      const stdDev = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / 20);
      entry.bbUpper = +(mean + 2 * stdDev).toFixed(2);
      entry.bbLower = +(mean - 2 * stdDev).toFixed(2);
      entry.bbMiddle = +mean.toFixed(2);
    }
    // RSI (14-period)
    if (i >= 14) {
      let gains = 0;
      let losses = 0;
      for (let j = i - 13; j <= i; j++) {
        const diff = closes[j] - closes[j - 1];
        if (diff > 0) gains += diff;
        else losses -= diff;
      }
      const avgGain = gains / 14;
      const avgLoss = losses / 14;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      entry.rsi = +(100 - 100 / (1 + rs)).toFixed(1);
    }
    return entry;
  });
  return result;
}

function generateSpreadSeries(baseValue, days, vol, seed) {
  const rng = seededRandom(seed);
  const data = [];
  let value = baseValue;
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const date = subDays(now, i);
    const change = (rng() - 0.5) * vol;
    value += change;
    data.push({
      date: format(date, 'yyyy-MM-dd'),
      timestamp: date.getTime(),
      value: +value.toFixed(3),
    });
  }
  // Add MA20
  return data.map((d, i, arr) => {
    if (i >= 19) {
      const slice = arr.slice(i - 19, i + 1);
      d.ma20 = +(slice.reduce((a, b) => a + b.value, 0) / 20).toFixed(3);
      const mean = d.ma20;
      const stdDev = Math.sqrt(slice.reduce((a, b) => a + (b.value - mean) ** 2, 0) / 20);
      d.std1Upper = +(mean + stdDev).toFixed(3);
      d.std1Lower = +(mean - stdDev).toFixed(3);
      d.std2Upper = +(mean + 2 * stdDev).toFixed(3);
      d.std2Lower = +(mean - 2 * stdDev).toFixed(3);
    }
    return d;
  });
}

// ─── PRICE DATA ────────────────────────────────────────────
const brentDaily = computeIndicators(generatePricePath(82.40, 252, 0.8, 42));
const wtiDaily = computeIndicators(generatePricePath(78.15, 252, 0.75, 87));
const gasoilDaily = computeIndicators(generatePricePath(720.50, 252, 5.0, 123));
const heatingOilDaily = computeIndicators(generatePricePath(2.344, 252, 0.02, 199));
const rbobDaily = computeIndicators(generatePricePath(2.582, 252, 0.02, 257));

const brentIntraday = computeIndicators(generateIntradayData(82.40, 43));
const wtiIntraday = computeIndicators(generateIntradayData(78.15, 88));
const gasoilIntraday = computeIndicators(generateIntradayData(720.50, 124));
const heatingOilIntraday = computeIndicators(generateIntradayData(2.344, 200));
const rbobIntraday = computeIndicators(generateIntradayData(2.582, 258));

export const instruments = [
  {
    id: 'brent',
    name: 'Brent Crude',
    exchange: 'ICE',
    price: 82.40,
    change: 0.32,
    changePercent: 0.39,
    high: 83.10,
    low: 81.80,
    volume: 182440,
    openInterest: 312100,
    unit: '$/bbl',
    decimals: 2,
    dailyData: brentDaily,
    intradayData: brentIntraday,
  },
  {
    id: 'wti',
    name: 'WTI Crude',
    exchange: 'NYMEX',
    price: 78.15,
    change: 0.28,
    changePercent: 0.36,
    high: 78.90,
    low: 77.60,
    volume: 312880,
    openInterest: 480200,
    unit: '$/bbl',
    decimals: 2,
    dailyData: wtiDaily,
    intradayData: wtiIntraday,
  },
  {
    id: 'gasoil',
    name: 'Gasoil',
    exchange: 'ICE',
    price: 720.50,
    change: 5.20,
    changePercent: 0.73,
    high: 725.00,
    low: 716.00,
    volume: 82100,
    openInterest: 210400,
    unit: '$/mt',
    decimals: 2,
    dailyData: gasoilDaily,
    intradayData: gasoilIntraday,
  },
  {
    id: 'heatingOil',
    name: 'Heating Oil',
    exchange: 'NYMEX',
    price: 2.3440,
    change: 0.018,
    changePercent: 0.77,
    high: 2.360,
    low: 2.320,
    volume: 55320,
    openInterest: 140200,
    unit: '$/gal',
    decimals: 4,
    dailyData: heatingOilDaily,
    intradayData: heatingOilIntraday,
  },
  {
    id: 'rbob',
    name: 'RBOB Gasoline',
    exchange: 'NYMEX',
    price: 2.5820,
    change: 0.018,
    changePercent: 0.70,
    high: 2.596,
    low: 2.564,
    volume: 72440,
    openInterest: 98200,
    unit: '$/gal',
    decimals: 4,
    dailyData: rbobDaily,
    intradayData: rbobIntraday,
  },
];

// ─── TICKER TAPE ───────────────────────────────────────────
export const tickerItems = [
  { label: 'Brent', value: 82.40, change: +0.32, changePercent: +0.39 },
  { label: 'WTI', value: 78.15, change: +0.28, changePercent: +0.36 },
  { label: 'M1-M2', value: 0.45, change: +0.03, changePercent: +7.14 },
  { label: '3:2:1 Crack', value: 18.40, change: +0.60, changePercent: +3.37 },
  { label: 'DXY', value: 104.20, change: -0.18, changePercent: -0.17 },
  { label: 'US 10Y', value: 4.45, change: -0.02, changePercent: -0.45 },
  { label: 'Gasoil', value: 720.50, change: +5.20, changePercent: +0.73 },
  { label: 'RBOB', value: 2.582, change: +0.018, changePercent: +0.70 },
];

// ─── SPREADS ───────────────────────────────────────────────
const m1m2Series = generateSpreadSeries(0.45, 756, 0.08, 301);
const m2m3Series = generateSpreadSeries(0.31, 756, 0.06, 302);
const m3m4Series = generateSpreadSeries(0.22, 756, 0.05, 303);
const m1m12Series = generateSpreadSeries(2.80, 756, 0.3, 304);
const wtiBrentSeries = generateSpreadSeries(-4.25, 756, 0.2, 305);
const crackSeries = generateSpreadSeries(18.40, 756, 1.5, 306);

export const spreads = [
  {
    id: 'm1m2',
    name: 'Brent M1-M2',
    value: 0.45,
    structure: 'BACKWARDATION',
    dayChange: +0.03,
    ma20: 0.38,
    zScore: 0.82,
    percentile: 72,
    series: m1m2Series,
  },
  {
    id: 'm2m3',
    name: 'Brent M2-M3',
    value: 0.31,
    structure: 'BACKWARDATION',
    dayChange: +0.02,
    ma20: 0.25,
    zScore: 0.74,
    percentile: 68,
    series: m2m3Series,
  },
  {
    id: 'm3m4',
    name: 'Brent M3-M4',
    value: 0.22,
    structure: 'BACKWARDATION',
    dayChange: +0.01,
    ma20: 0.18,
    zScore: 0.52,
    percentile: 61,
    series: m3m4Series,
  },
  {
    id: 'm1m12',
    name: 'Brent M1-M12',
    value: 2.80,
    structure: 'BACKWARDATION',
    dayChange: +0.08,
    ma20: 2.65,
    zScore: 1.20,
    percentile: 78,
    series: m1m12Series,
  },
];

export const wtiBrentSpread = {
  id: 'wtiBrent',
  name: 'WTI-Brent Spread',
  value: -4.25,
  dayChange: -0.05,
  ma20: -4.10,
  zScore: -0.42,
  percentile: 44,
  series: wtiBrentSeries,
};

export const crackSpread = {
  id: 'crack',
  name: '3:2:1 Crack Spread',
  value: 18.40,
  dayChange: +0.60,
  ma20: 17.20,
  zScore: 0.68,
  percentile: 65,
  interpretation:
    '$10-$20 = Normal refining margin. >$25 = Exceptional. Current level is healthy but within normal range.',
  series: crackSeries,
};

// ─── EIA / PHYSICAL ────────────────────────────────────────
function getNextEIARelease() {
  const now = new Date();
  let wed = nextWednesday(now);
  wed = setHours(wed, 10);
  wed = setMinutes(wed, 30);
  if (wed.getTime() < now.getTime()) {
    wed = nextWednesday(addDays(wed, 1));
    wed = setHours(wed, 10);
    wed = setMinutes(wed, 30);
  }
  return wed;
}

function generateInventoryHistory(baseValue, weeks, vol, seed) {
  const rng = seededRandom(seed);
  const data = [];
  let value = baseValue;
  const now = new Date();
  for (let i = weeks - 1; i >= 0; i--) {
    const date = subDays(now, i * 7);
    const change = (rng() - 0.5) * vol;
    value += change;
    data.push({
      date: format(date, 'yyyy-MM-dd'),
      value: +value.toFixed(1),
      fiveYearAvg: +(value + (rng() - 0.4) * vol * 3).toFixed(1),
      fiveYearMin: +(value - vol * 4 - rng() * vol * 2).toFixed(1),
      fiveYearMax: +(value + vol * 6 + rng() * vol * 2).toFixed(1),
    });
  }
  return data;
}

export const eiaData = {
  nextRelease: getNextEIARelease(),
  crude: {
    label: 'US Crude Stocks',
    value: 430.2,
    unit: 'mn bbl',
    weekChange: -2.4,
    consensus: -1.8,
    surprise: -0.6,
    signal: 'BULLISH',
    history: generateInventoryHistory(430, 52, 3.0, 401),
  },
  cushing: {
    label: 'Cushing Stocks',
    value: 24.8,
    unit: 'mn bbl',
    weekChange: -0.8,
    interpretation: 'Cushing draws tightening WTI delivery hub, supports backwardation.',
    history: generateInventoryHistory(25, 52, 1.0, 402),
  },
  gasoline: {
    label: 'Gasoline Stocks',
    value: 228.4,
    unit: 'mn bbl',
    weekChange: -1.2,
    interpretation: 'Gasoline draws ahead of summer driving season, supports RBOB cracks.',
    history: generateInventoryHistory(228, 52, 2.5, 403),
  },
  refineryUtil: {
    label: 'Refinery Utilization',
    value: 91.2,
    unit: '%',
    weekChange: +0.4,
    interpretation: 'Rising utilization signals strong product demand and crude consumption.',
  },
};

export const freightData = {
  bdti: {
    label: 'BDTI (Dirty Tanker)',
    value: 1142,
    weekChange: +22,
    weekChangePercent: +2.0,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      day: i,
      value: 1100 + Math.sin(i * 0.5) * 30 + (i * 1.5),
    })),
    interpretation: 'Dirty tanker rates rising, reflecting tighter vessel availability.',
  },
  bcti: {
    label: 'BCTI (Clean Tanker)',
    value: 742,
    weekChange: -8,
    weekChangePercent: -1.1,
    sparkline: Array.from({ length: 20 }, (_, i) => ({
      day: i,
      value: 760 - Math.sin(i * 0.4) * 20 - (i * 0.8),
    })),
    interpretation: 'Clean tanker rates easing as CPP supply normalizes.',
  },
};

export const physicalIndicators = {
  rigCount: {
    totalUS: 588,
    permian: 312,
    weekChange: -3,
    yearChange: -42,
    yearChangePercent: -6.7,
    signal: 'BEARISH',
    interpretation: 'Falling rig count signals reduced future US production growth.',
  },
  floatingStorage: {
    value: 68.2,
    unit: 'mn bbl',
    trend: 'falling',
    weekChange: -3.4,
    signal: 'BULLISH',
    interpretation: 'Declining floating storage indicates physical demand absorbing excess.',
  },
};

// ─── NEWS ──────────────────────────────────────────────────
const now = new Date();

export const newsItems = [
  {
    id: 1,
    headline: 'OPEC+ Agrees to Extend Production Cuts Through Q3 2025',
    source: 'Reuters',
    category: 'OPEC',
    sentiment: 'bullish',
    timestamp: subHours(now, 1),
    impactScore: 9,
    pinned: true,
    summary:
      'The OPEC+ alliance confirmed voluntary output cuts of 2.2 mb/d will remain through September, with Saudi Arabia maintaining its additional 1 mb/d unilateral reduction.',
  },
  {
    id: 2,
    headline: 'Red Sea Shipping Disruptions Force Suez Canal Diversions',
    source: 'Bloomberg',
    category: 'Geopolitics',
    sentiment: 'bullish',
    timestamp: subHours(now, 2),
    impactScore: 8,
    pinned: true,
    summary:
      'Houthi attacks continue to force tankers around the Cape of Good Hope, adding 10-14 days to Europe-bound crude deliveries and tightening Atlantic basin supplies.',
  },
  {
    id: 3,
    headline: 'EIA Reports Larger-Than-Expected Crude Draw of 2.4 Million Barrels',
    source: 'EIA',
    category: 'Inventories',
    sentiment: 'bullish',
    timestamp: subHours(now, 3),
    impactScore: 7,
    pinned: false,
    summary:
      'US commercial crude stocks fell by 2.4 mn bbl last week vs consensus of -1.8 mn, marking the fourth consecutive weekly draw.',
  },
  {
    id: 4,
    headline: 'China Crude Imports Rise 8% YoY in Latest Customs Data',
    source: 'Reuters',
    category: 'Macro',
    sentiment: 'bullish',
    timestamp: subHours(now, 4),
    impactScore: 7,
    pinned: false,
    summary:
      'China imported 11.8 mn bpd of crude oil in the latest month, up from 10.9 mn bpd a year ago, driven by independent refinery demand and strategic reserve purchases.',
  },
  {
    id: 5,
    headline: 'US Dollar Index Slips Below 104.50 on Dovish Fed Signals',
    source: 'Bloomberg',
    category: 'Macro',
    sentiment: 'bullish',
    timestamp: subHours(now, 5),
    impactScore: 6,
    pinned: false,
    summary:
      'DXY fell 0.18 points as Fed officials hinted at potential rate cuts in September, weakening the dollar and supporting crude price benchmarks.',
  },
  {
    id: 6,
    headline: 'Iranian Oil Exports Reach 1.8 mb/d Despite Sanctions',
    source: 'OilPrice',
    category: 'Geopolitics',
    sentiment: 'bearish',
    timestamp: subHours(now, 6),
    impactScore: 6,
    pinned: false,
    summary:
      'Tanker tracking data shows Iranian crude exports at their highest in 5 years, with most volumes going to Chinese independent refiners via ship-to-ship transfers.',
  },
  {
    id: 7,
    headline: 'Gasoline Demand Hits Seasonal High Ahead of Memorial Day',
    source: 'EIA',
    category: 'Inventories',
    sentiment: 'bullish',
    timestamp: subHours(now, 7),
    impactScore: 5,
    pinned: false,
    summary:
      'US gasoline demand reached 9.3 mn bpd in the latest week, the highest seasonal level since 2019, supporting RBOB crack spreads.',
  },
  {
    id: 8,
    headline: 'Permian Basin Rig Count Falls by 3 to 312',
    source: 'OilPrice',
    category: 'Refineries',
    sentiment: 'bearish',
    timestamp: subHours(now, 8),
    impactScore: 5,
    pinned: false,
    summary:
      'Baker Hughes data shows the Permian rig count declining for the fourth consecutive week, signaling capital discipline among US shale producers.',
  },
  {
    id: 9,
    headline: 'VLCC Rates Surge 15% on Atlantic Basin Tightness',
    source: 'Reuters',
    category: 'Tankers',
    sentiment: 'bullish',
    timestamp: subHours(now, 9),
    impactScore: 6,
    pinned: false,
    summary:
      'VLCC rates on the WAF-East route jumped to WS 62 as vessel availability tightened due to Red Sea rerouting and Nigerian loading delays.',
  },
  {
    id: 10,
    headline: 'IEA Raises 2025 Global Oil Demand Forecast by 200 kb/d',
    source: 'IEA',
    category: 'Macro',
    sentiment: 'bullish',
    timestamp: subHours(now, 10),
    impactScore: 7,
    pinned: false,
    summary:
      'The International Energy Agency revised its 2025 demand growth estimate to 1.3 mn bpd, citing stronger-than-expected jet fuel and petrochemical feedstock demand.',
  },
  {
    id: 11,
    headline: 'Russian Urals Crude Discount Narrows to $3/bbl vs Brent',
    source: 'Bloomberg',
    category: 'Geopolitics',
    sentiment: 'neutral',
    timestamp: subHours(now, 11),
    impactScore: 4,
    pinned: false,
    summary:
      'Urals discount to Dated Brent narrowed from $5 to $3 as Indian and Chinese refiners compete for Russian barrels amid tighter supply.',
  },
  {
    id: 12,
    headline: 'PBF Energy Reports Unexpected Refinery Outage at Delaware City',
    source: 'Reuters',
    category: 'Refineries',
    sentiment: 'bullish',
    timestamp: subHours(now, 13),
    impactScore: 5,
    pinned: false,
    summary:
      'PBF Energy shut a 120 kb/d crude unit at its Delaware City refinery due to equipment failure, expected to last 2-3 weeks, tightening PADD 1 product supply.',
  },
  {
    id: 13,
    headline: 'CFTC Data Shows Managed Money Net Long Positions Increase',
    source: 'Bloomberg',
    category: 'Macro',
    sentiment: 'bullish',
    timestamp: subHours(now, 15),
    impactScore: 5,
    pinned: false,
    summary:
      'Hedge funds and commodity trading advisors added 28,000 contracts to WTI net long positions, the largest weekly increase in 3 months.',
  },
  {
    id: 14,
    headline: 'Libya Oil Output Drops to 900 kb/d Amid Political Tensions',
    source: 'OilPrice',
    category: 'Geopolitics',
    sentiment: 'bullish',
    timestamp: subHours(now, 18),
    impactScore: 7,
    pinned: false,
    summary:
      'Libyan oil production fell by 200 kb/d as rival government factions dispute control of the central bank and oil revenue distribution.',
  },
  {
    id: 15,
    headline: 'India Refinery Throughput Reaches Record 5.8 mn bpd',
    source: 'Reuters',
    category: 'Refineries',
    sentiment: 'neutral',
    timestamp: subHours(now, 20),
    impactScore: 4,
    pinned: false,
    summary:
      'Indian refinery runs hit an all-time high driven by strong domestic fuel demand and competitive export margins, boosting crude import appetite.',
  },
];

// ─── OPEC ──────────────────────────────────────────────────
export const opecData = {
  nextMeeting: new Date('2025-06-01T10:00:00Z'),
  productionTarget: 27.2,
  estimatedActual: 27.45,
  compliancePercent: 99.1,
  secretaryStatement:
    '"We remain committed to market stability. Our proactive approach ensures supply-demand equilibrium while supporting fair prices for both producers and consumers." — Haitham Al Ghais, OPEC Secretary General',
  members: [
    { country: 'Saudi Arabia', flag: '🇸🇦', target: 9.0, actual: 9.0, compliance: 100.0 },
    { country: 'Russia', flag: '🇷🇺', target: 9.0, actual: 9.1, compliance: 98.9 },
    { country: 'Iraq', flag: '🇮🇶', target: 4.2, actual: 4.35, compliance: 96.4 },
    { country: 'UAE', flag: '🇦🇪', target: 3.2, actual: 3.2, compliance: 100.0 },
  ],
};

export const scheduledReleases = [
  {
    name: 'EIA Weekly Petroleum Status',
    source: 'EIA',
    date: getNextEIARelease(),
  },
  {
    name: 'CFTC Commitments of Traders',
    source: 'CFTC',
    date: (() => {
      const d = new Date();
      const day = d.getDay();
      const daysUntilFriday = (5 - day + 7) % 7 || 7;
      const friday = addDays(d, daysUntilFriday);
      return setHours(setMinutes(friday, 30), 15);
    })(),
  },
  {
    name: 'OPEC Monthly Oil Market Report',
    source: 'OPEC',
    date: (() => {
      const d = new Date();
      const nextMonth = new Date(d.getFullYear(), d.getMonth() + 1, 12, 12, 0, 0);
      return nextMonth;
    })(),
  },
];

// ─── REGIME ────────────────────────────────────────────────
export const regimeData = {
  current: 'PHYSICAL TIGHTNESS',
  confidence: 82,
  since: subDays(new Date(), 18),
  durationDays: 18,
  explanation:
    'Physical market indicators dominate the current price regime. Calendar spreads are in strong backwardation, inventory draws have persisted for 4 consecutive weeks, and floating storage is declining. These signal genuine physical tightness rather than macro-driven or supply-shock dynamics.',
  signals: {
    dxyBrentCorrelation: -0.31,
    m1m2ZScore: 0.82,
    drawStreak: 4,
    crackDeviation: '+1.2 from 20D MA',
  },
  allRegimes: [
    { id: 'macro', label: 'MACRO DRIVEN', color: '#a855f7', description: 'Price driven by USD, rates, and risk sentiment' },
    { id: 'supply', label: 'SUPPLY SHOCK', color: '#f97316', description: 'Sudden supply disruption or OPEC action driving prices' },
    { id: 'demand', label: 'DEMAND SHOCK', color: '#06b6d4', description: 'Demand destruction or recovery dominating fundamentals' },
    { id: 'physical', label: 'PHYSICAL TIGHTNESS', color: '#10b981', description: 'Inventory draws, backwardation, and physical premiums leading' },
    { id: 'refining', label: 'REFINING DRIVEN', color: '#f59e0b', description: 'Crack spreads and product markets driving crude direction' },
  ],
};

// ─── KEY METRICS ───────────────────────────────────────────
export const keyMetrics = [
  { label: 'Brent', value: '82.40', unit: '$/bbl', change: '+0.32', changePercent: '+0.39%', percentile: 68, signal: 'BULL' },
  { label: 'WTI', value: '78.15', unit: '$/bbl', change: '+0.28', changePercent: '+0.36%', percentile: 65, signal: 'BULL' },
  { label: 'Crack Spread', value: '18.40', unit: '$/bbl', change: '+0.60', changePercent: '+3.37%', percentile: 65, signal: 'BULL' },
  { label: 'M1-M2', value: '+0.45', unit: '$/bbl', change: '+0.03', changePercent: '+7.14%', percentile: 72, signal: 'BULL' },
  { label: 'M1-M12', value: '+2.80', unit: '$/bbl', change: '+0.08', changePercent: '+2.94%', percentile: 78, signal: 'BULL' },
  { label: 'WTI-Brent', value: '-4.25', unit: '$/bbl', change: '-0.05', changePercent: '-1.19%', percentile: 44, signal: 'NEUT' },
  { label: 'DXY', value: '104.20', unit: '', change: '-0.18', changePercent: '-0.17%', percentile: 58, signal: 'BULL' },
  { label: 'US 10Y', value: '4.45', unit: '%', change: '-0.02', changePercent: '-0.45%', percentile: 72, signal: 'NEUT' },
  { label: 'Inv. Surprise', value: '-0.6', unit: 'mn bbl', change: '', changePercent: '', percentile: 74, signal: 'BULL' },
  { label: 'Rig Count', value: '588', unit: '', change: '-3', changePercent: '-0.51%', percentile: 38, signal: 'BEAR' },
];

// ─── CORRELATION MATRIX ────────────────────────────────────
export const correlationLabels = ['Brent', 'WTI', 'RBOB', 'Crack', 'WTI-Br', 'DXY', '10Y', 'Inventory'];
export const correlationMatrix = [
  [1.00,  0.98,  0.91,  0.72, -0.42, -0.68, -0.31, -0.58],
  [0.98,  1.00,  0.89,  0.70, -0.38, -0.65, -0.28, -0.55],
  [0.91,  0.89,  1.00,  0.84, -0.31, -0.52, -0.22, -0.48],
  [0.72,  0.70,  0.84,  1.00, -0.18, -0.41, -0.14, -0.38],
  [-0.42, -0.38, -0.31, -0.18,  1.00,  0.28,  0.11,  0.22],
  [-0.68, -0.65, -0.52, -0.41,  0.28,  1.00,  0.62, -0.41],
  [-0.31, -0.28, -0.22, -0.14,  0.11,  0.62,  1.00, -0.18],
  [-0.58, -0.55, -0.48, -0.38,  0.22, -0.41, -0.18,  1.00],
];

// ─── SPREAD CORRELATION MATRIX (for Overview) ─────────────
export const spreadCorrelationLabels = ['M1-M2', 'M2-M3', 'M3-M4', 'M1-M12', 'WTI-Brent', 'Crack'];
export const spreadCorrelationMatrix = [
  [ 1.00,  0.92,  0.81,  0.74, -0.28,  0.35],
  [ 0.92,  1.00,  0.88,  0.69, -0.22,  0.31],
  [ 0.81,  0.88,  1.00,  0.62, -0.18,  0.27],
  [ 0.74,  0.69,  0.62,  1.00, -0.35,  0.48],
  [-0.28, -0.22, -0.18, -0.35,  1.00, -0.15],
  [ 0.35,  0.31,  0.27,  0.48, -0.15,  1.00],
];

// ─── PRODUCT CORRELATION MATRIX (for Overview) ─────────────
export const productCorrelationLabels = ['Brent', 'WTI', 'RBOB', 'Gasoil', 'HeatOil', 'DXY'];
export const productCorrelationMatrix = [
  [ 1.00,  0.98,  0.91,  0.94,  0.89, -0.68],
  [ 0.98,  1.00,  0.89,  0.92,  0.87, -0.65],
  [ 0.91,  0.89,  1.00,  0.82,  0.85, -0.52],
  [ 0.94,  0.92,  0.82,  1.00,  0.90, -0.61],
  [ 0.89,  0.87,  0.85,  0.90,  1.00, -0.55],
  [-0.68, -0.65, -0.52, -0.61, -0.55,  1.00],
];

// ─── SENTIMENT / FUNDAMENTAL ANALYSIS (for Overview) ───────
export const sentimentAnalysis = {
  overall: 'BULLISH',
  score: 72, // 0-100, 50 = neutral
  priceDirection: 'Higher prices likely in the short-to-medium term',
  summary: 'The oil market is exhibiting broad-based bullish signals. Physical tightness dominates: calendar spreads are firmly in backwardation, US crude inventories have drawn for 4 consecutive weeks, and floating storage is declining. OPEC+ maintains high compliance with production cuts. The weakening US dollar provides additional tailwind. The main risk is Iranian supply growth, but Red Sea disruptions and falling US rig counts offset this.',
  signals: [
    {
      storeKey: 'curveStructure',
      name: 'Curve Structure',
      value: 'Backwardation',
      detail: 'M1-M12 at +$2.80 — physical tightness confirmed',
      signal: 'BULL',
      weight: 20,
      score: 85,
      bullishReason: 'Strong backwardation signals physical tightness and near-term supply deficit. Producers hedging at a premium reflects genuine demand pull.',
      bearishReason: 'If contango develops, it would signal oversupply and incentivize storage builds.',
      marketImpact: 'Backwardation discourages floating storage and accelerates physical drawdowns, supporting spot prices.',
    },
    {
      storeKey: 'eiaInventory',
      name: 'EIA Inventory',
      value: '-2.4 mn bbl',
      detail: 'Draw vs -1.8 consensus, 4th consecutive draw week',
      signal: 'BULL',
      weight: 18,
      score: 78,
      bullishReason: 'Consecutive draws indicate demand outpacing supply. The -0.6 mn bbl surprise vs consensus amplifies the signal.',
      bearishReason: 'If draws reverse to builds, it signals weakening demand or increased imports.',
      marketImpact: 'Cushing hub draws are particularly significant — depleting delivery point stocks directly supports WTI pricing and backwardation.',
    },
    {
      storeKey: 'opecCompliance',
      name: 'OPEC+ Compliance',
      value: '99.1%',
      detail: 'Near-full compliance; cuts extended through Q3',
      signal: 'BULL',
      weight: 15,
      score: 82,
      bullishReason: 'High compliance means supply discipline is holding. Saudi voluntary cuts add an extra 1 mb/d of tightness.',
      bearishReason: 'Iraq and Russia show slight overproduction — if cheating accelerates, effective cuts diminish.',
      marketImpact: 'OPEC+ credibility on cuts directly influences speculative positioning and term-structure shape.',
    },
    {
      storeKey: 'usdDxy',
      name: 'USD / DXY',
      value: '104.20 (−0.18)',
      detail: 'Falling dollar supports crude benchmarks',
      signal: 'BULL',
      weight: 12,
      score: 65,
      bullishReason: 'Weakening dollar makes oil cheaper for non-USD buyers, boosting global demand at the margin.',
      bearishReason: 'A strengthening dollar (hawkish Fed) compresses commodity prices across the board.',
      marketImpact: 'DXY-Brent correlation at -0.68 means the dollar is a significant macro driver right now.',
    },
    {
      storeKey: 'crackSpreads',
      name: 'Crack Spreads',
      value: '$18.40/bbl',
      detail: 'Healthy refining margins signal product demand',
      signal: 'BULL',
      weight: 10,
      score: 68,
      bullishReason: 'Strong crack spreads incentivize refiners to run at high utilization, pulling more crude barrels off the market.',
      bearishReason: 'Crack compression would signal product oversupply or demand destruction at the consumer level.',
      marketImpact: 'Current 3:2:1 at $18.40 is within the normal $10-$20 range but trending higher — watch for >$25 which signals exceptional tightness.',
    },
    {
      storeKey: 'geopoliticalRisk',
      name: 'Geopolitical Risk',
      value: 'Elevated',
      detail: 'Red Sea disruptions + Libya output drops',
      signal: 'BULL',
      weight: 10,
      score: 75,
      bullishReason: 'Houthi attacks rerouting tankers add 10-14 days transit time, tightening Atlantic basin. Libya output at 900 kb/d, down 200 kb/d.',
      bearishReason: 'Geopolitical premiums can evaporate quickly on ceasefire or de-escalation headlines.',
      marketImpact: 'Supply-side geopolitical risk is most impactful when it coincides with already-tight physical markets — as now.',
    },
    {
      storeKey: 'rigCount',
      name: 'Rig Count Trend',
      value: '588 (−3 WoW)',
      detail: 'Falling rigs = less future US supply growth',
      signal: 'BULL',
      weight: 8,
      score: 62,
      bullishReason: 'Declining rig count means US shale production growth is decelerating. YoY down 42 rigs (−6.7%), signaling capital discipline.',
      bearishReason: 'Shale productivity gains can offset rig declines — fewer rigs doesn\'t always mean less output.',
      marketImpact: 'Medium-term signal: rig count changes take 4-6 months to flow through to production. Current trend supportive for H2 prices.',
    },
    {
      storeKey: 'positioning',
      name: 'Positioning (CFTC)',
      value: 'Net Long +28K',
      detail: 'Managed money adding length — risk appetite rising',
      signal: 'BULL',
      weight: 7,
      score: 70,
      bullishReason: 'CTAs and hedge funds adding net long positions signals bullish conviction among systematic and discretionary traders.',
      bearishReason: 'Extreme net long positioning increases vulnerability to a liquidation-driven sell-off.',
      marketImpact: 'Current positioning is elevated but not extreme — room for further length before crowding becomes a risk.',
    },
    {
      storeKey: 'newsSentiment',
      name: 'News Sentiment',
      value: '11 Bull / 2 Bear',
      detail: '73% of headlines carry bullish sentiment across 15 items (last 24h)',
      signal: 'BULL',
      weight: 10,
      score: 73,
      bullishReason: 'Overwhelming bullish flow: OPEC+ cut extensions, EIA draws, IEA demand upgrade, Red Sea supply disruptions, and CFTC long positioning all dominate headlines.',
      bearishReason: 'Iranian export growth and falling rig count represent minority bearish narratives that could gain traction.',
      marketImpact: 'News sentiment acts as a sentiment amplifier — when headlines align with physical fundamentals, price moves tend to be more sustained and conviction-driven.',
    },
  ],
  risks: [
    'Iranian exports at 5-year highs (1.8 mb/d) despite sanctions',
    'China economic slowdown could weigh on demand growth',
    'Potential OPEC+ overproduction from Iraq and Russia',
    'US SPR refilling could pause if prices rise too quickly',
  ],
  catalysts: [
    'Next EIA release — continued draws would confirm tightening',
    'OPEC+ meeting June 1 — any cut extension bullish',
    'Fed rate decision — dovish tilt weakens USD further',
    'Summer driving season demand peak approaching',
  ],
};

// ─── NAV TABS ──────────────────────────────────────────────
export const navTabs = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'prices', label: 'PRICES' },
  { id: 'spreads', label: 'SPREADS' },
  { id: 'physical', label: 'PHYSICAL' },
  { id: 'news', label: 'NEWS' },
];
