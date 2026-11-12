import React from 'react';

type BadgeVariant =
  | 'green'
  | 'red'
  | 'blue'
  | 'amber'
  | 'slate'
  | 'cyan'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  pulse?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'slate',
  children,
  pulse = false,
  className = '',
}) => {
  // Normalize alias variants
  let resolvedVariant = variant;
  if (variant === 'success') resolvedVariant = 'green';
  if (variant === 'warning') resolvedVariant = 'amber';
  if (variant === 'danger') resolvedVariant = 'red';
  if (variant === 'info') resolvedVariant = 'cyan';

  const variantStyles: Record<string, string> = {
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    red: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    slate: 'bg-slate-800 text-slate-300 border-slate-700',
    cyan: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  };

  const pulseColors: Record<string, string> = {
    green: 'bg-emerald-400',
    red: 'bg-rose-400',
    blue: 'bg-blue-400',
    amber: 'bg-amber-400',
    slate: 'bg-slate-400',
    cyan: 'bg-sky-400',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        variantStyles[resolvedVariant] || variantStyles.slate
      } ${className}`}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              pulseColors[resolvedVariant] || pulseColors.slate
            }`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              pulseColors[resolvedVariant] || pulseColors.slate
            }`}
          />
        </span>
      )}
      {children}
    </span>
  );
};

export default Badge;
