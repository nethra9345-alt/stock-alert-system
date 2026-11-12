import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  text?: string;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message,
  text,
  className = '',
}) => {
  const displayMsg = text || message || 'Loading live market data...';
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-slate-400 ${className}`}>
      <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
      <p className="text-sm font-medium">{displayMsg}</p>
    </div>
  );
};

export default LoadingSpinner;
