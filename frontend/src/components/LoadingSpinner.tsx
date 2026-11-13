import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  text?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message,
  text,
  className = '',
  size = 'md',
}) => {
  const displayMsg = text || message || (size === 'sm' ? '' : 'Loading live market data...');

  const sizeClass =
    size === 'sm'
      ? 'p-2'
      : size === 'lg'
      ? 'p-16'
      : 'p-12';

  const iconClass =
    size === 'sm'
      ? 'w-4 h-4 mb-0'
      : size === 'lg'
      ? 'w-10 h-10 mb-4'
      : 'w-8 h-8 mb-3';

  return (
    <div className={`flex flex-col items-center justify-center text-slate-400 ${sizeClass} ${className}`}>
      <Loader2 className={`${iconClass} text-sky-400 animate-spin`} />
      {displayMsg && <p className="text-sm font-medium">{displayMsg}</p>}
    </div>
  );
};

export default LoadingSpinner;
