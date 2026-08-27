import React from 'react';
import { ArrowUpDown } from 'lucide-react';

interface RQCardWrapperProps {
  pillLabel: string;
  pillColorClass?: string;
  title: string;
  subtitle: React.ReactNode;
  scale?: 'linear' | 'log';
  onToggleScale?: () => void;
  children: React.ReactNode;
  className?: string;
}

export const RQCardWrapper: React.FC<RQCardWrapperProps> = ({
  pillLabel,
  pillColorClass = 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
  title,
  subtitle,
  scale,
  onToggleScale,
  children,
  className = '',
}) => {
  return (
    <div className={`bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 flex flex-col justify-between transition ${className}`}>
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${pillColorClass}`}>
            {pillLabel}
          </span>
          {scale && onToggleScale && (
            <button
              onClick={onToggleScale}
              className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border border-gray-200 dark:border-github-border hover:bg-gray-100 dark:hover:bg-github-darker transition text-gray-700 dark:text-github-muted"
              title="Alternar entre escala linear e logarítmica"
            >
              <ArrowUpDown className="w-3 h-3 text-blue-500" />
              <span>Escala: <b>{scale.toUpperCase()}</b></span>
            </button>
          )}
        </div>
        <h3 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white">
          {title}
        </h3>
        <div className="text-xs text-gray-500 dark:text-github-muted mt-0.5">
          {subtitle}
        </div>
      </div>
      <div className="w-full mt-3">
        {children}
      </div>
    </div>
  );
};
