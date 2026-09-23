import React from 'react';

interface KPICardProps {
  label: string;
  icon: React.ReactNode;
  iconBgClass?: string;
  value: React.ReactNode;
  comparisonText?: React.ReactNode;
  footerBadge?: React.ReactNode;
  footerText?: React.ReactNode;
  hoverBorderClass?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  icon,
  iconBgClass = 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  value,
  comparisonText,
  footerBadge,
  footerText,
  hoverBorderClass = 'hover:border-blue-400',
}) => {
  return (
    <div
      className={`bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition-all ${hoverBorderClass}`}
    >
      <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        <div className={`p-1.5 rounded-lg ${iconBgClass}`}>{icon}</div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-black text-gray-900 dark:text-white">{value}</span>
        {comparisonText && (
          <span className="text-xs text-gray-500 dark:text-github-muted truncate">
            {comparisonText}
          </span>
        )}
      </div>
      <div className="mt-2.5 flex items-center gap-1.5 text-xs">
        {footerBadge}
        {footerText && (
          <span className="text-gray-500 dark:text-github-muted">{footerText}</span>
        )}
      </div>
    </div>
  );
};
