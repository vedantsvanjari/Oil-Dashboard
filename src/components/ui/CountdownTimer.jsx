import React, { useState, useEffect } from 'react';
import { differenceInSeconds } from 'date-fns';
import { useTheme } from '../../theme/ThemeContext';

export default function CountdownTimer({ targetDate, label }) {
  const { colors } = useTheme();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const diffSec = Math.max(0, differenceInSeconds(targetDate, now));
  const days = Math.floor(diffSec / 86400);
  const hours = Math.floor((diffSec % 86400) / 3600);
  const minutes = Math.floor((diffSec % 3600) / 60);
  const seconds = diffSec % 60;

  return (
    <div className="flex items-center gap-2">
      {label && <span className="section-header">{label}</span>}
      <div className="flex items-center gap-1 data-value text-xs" style={{ color: colors.neutral }}>
        {days > 0 && <span>{days}d</span>}
        <span>{String(hours).padStart(2, '0')}</span>
        <span style={{ color: colors.textMuted }}>:</span>
        <span>{String(minutes).padStart(2, '0')}</span>
        <span style={{ color: colors.textMuted }}>:</span>
        <span>{String(seconds).padStart(2, '0')}</span>
      </div>
    </div>
  );
}
