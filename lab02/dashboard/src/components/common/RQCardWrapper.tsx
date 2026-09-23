import React from 'react';

interface RQCardWrapperProps {
  pillLabel: string;
  pillColorClass?: string;
  title: string;
  subtitle: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const RQCardWrapper: React.FC<RQCardWrapperProps> = ({
  pillLabel,
  pillColorClass = 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
  title,
  subtitle,
  action,
  children,
  className = '',
}) => {
  return (
    <div
      className={`bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 flex flex-col justify-between transition ${className}`}
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${pillColorClass}`}>
            {pillLabel}
          </span>
          {action && <div>{action}</div>}
        </div>
        <h3 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white">
          {title}
        </h3>
        <div className="text-xs text-gray-500 dark:text-github-muted mt-0.5">
          {subtitle}
        </div>
      </div>
      <div className="w-full mt-3">{children}</div>
    </div>
  );
};
