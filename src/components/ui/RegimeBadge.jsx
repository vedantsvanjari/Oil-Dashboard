import React from 'react';
import { useTheme } from '../../theme/ThemeContext';

export default function RegimeBadge({ regime, isActive, onClick }) {
  const { colors } = useTheme();

  return (
    <button
      onClick={() => onClick(regime.id)}
      className="flex flex-col items-center gap-1 p-2 border rounded-lg transition-all duration-200 cursor-pointer theme-card"
      style={{
        backgroundColor: isActive ? regime.color + '15' : colors.cardBg,
        borderColor: isActive ? regime.color : colors.cardBorder,
        minWidth: '130px',
      }}
    >
      <div
        className="w-2.5 h-2.5 rounded-full"
        style={{
          backgroundColor: regime.color,
          boxShadow: isActive ? `0 0 8px ${regime.color}60` : 'none',
        }}
      />
      <span className="text-xs font-semibold text-center leading-tight"
        style={{
          color: isActive ? regime.color : colors.textMuted,
          fontSize: '10px',
          letterSpacing: '0.05em',
        }}>
        {regime.label}
      </span>
    </button>
  );
}
