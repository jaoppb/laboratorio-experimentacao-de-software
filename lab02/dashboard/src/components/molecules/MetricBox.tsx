import React from 'react';

interface MetricBoxProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  valueColorClass?: string;
  className?: string;
}

export const MetricBox: React.FC<MetricBoxProps> = ({
  icon,
  label,
  value,
  subtitle,
  valueColorClass = 'text-gray-900 dark:text-white',
  className = '',
}) => {
  return (
    <div
      className={`p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl ${className}`}
    >
      <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
        {icon}
        <span>{label}</span>
      </div>
      <div className={`text-lg font-bold ${valueColorClass}`}>{value}</div>
      {subtitle && (
        <div className="text-[10px] text-gray-400 dark:text-github-muted mt-0.5 font-medium">
          {subtitle}
        </div>
      )}
    </div>
  );
};
