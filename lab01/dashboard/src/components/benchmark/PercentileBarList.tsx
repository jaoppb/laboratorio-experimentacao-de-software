import React from 'react';
import { PercentileResult } from '../../types/dataset';
import { fmtDec } from '../../utils/formatters';

interface PercentileBarListProps {
  percentiles: PercentileResult[];
}

export const PercentileBarList: React.FC<PercentileBarListProps> = ({ percentiles }) => {
  return (
    <div className="space-y-3">
      {percentiles.map((p) => {
        const isHigh = p.percentile >= 75;
        const isTop = p.percentile >= 90;

        return (
          <div
            key={p.metric}
            className="p-2.5 rounded-lg bg-gray-50/70 dark:bg-github-card border border-gray-100 dark:border-github-border/60 hover:border-blue-500/40 transition"
          >
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="font-semibold text-gray-800 dark:text-github-text">
                {p.label}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-gray-600 dark:text-github-muted">
                  {p.formattedValue}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    isTop
                      ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300'
                      : isHigh
                      ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300'
                      : 'bg-gray-200 dark:bg-github-darker text-gray-700 dark:text-github-muted'
                  }`}
                >
                  {p.tier} ({fmtDec(p.percentile, 1)}%)
                </span>
              </div>
            </div>

            {/* Progress Bar Container */}
            <div className="w-full h-2 rounded-full bg-gray-200 dark:bg-github-darker overflow-hidden relative">
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-gray-400 dark:bg-gray-600 z-10"
                style={{ left: '50%' }}
                title="Mediana Geral (P50)"
              />
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isTop
                    ? 'bg-gradient-to-r from-purple-500 to-amber-500'
                    : isHigh
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.max(2, p.percentile)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
