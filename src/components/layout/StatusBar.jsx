import React, { useState, useEffect } from 'react';
import { format, differenceInSeconds } from 'date-fns';
import { getNextEIARelease } from '../../utils/dates';
import { useTheme } from '../../theme/ThemeContext';

export default function StatusBar() {
  const { colors } = useTheme();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const eiaRelease = getNextEIARelease();
  const diffSec = Math.max(0, differenceInSeconds(eiaRelease, now));
  const days = Math.floor(diffSec / 86400);
  const hours = Math.floor((diffSec % 86400) / 3600);
  const minutes = Math.floor((diffSec % 3600) / 60);
  const seconds = diffSec % 60;

  return (
    <div className="flex items-center justify-between h-10 px-6 border-t text-xs"
      style={{ backgroundColor: colors.bgSurface, borderColor: colors.border, color: colors.textMuted }}>
      <div className="flex items-center gap-4">
        <span>Last updated: {format(now, 'HH:mm:ss')} ET</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full pulse-dot" style={{ backgroundColor: colors.bullish }} />
          WS Connected
        </span>
      </div>
      <div className="data-value">
        Next EIA: {days}d {String(hours).padStart(2, '0')}:{String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </div>
    </div>
  );
}
