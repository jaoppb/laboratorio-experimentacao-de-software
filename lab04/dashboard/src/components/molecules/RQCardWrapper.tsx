import React from 'react';
import { Badge, BadgeVariant } from '../atoms/Badge';

interface RQCardWrapperProps {
  id?: string;
  pillLabel: string;
  pillVariant?: BadgeVariant;
  title: string;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const RQCardWrapper: React.FC<RQCardWrapperProps> = ({
  id,
  pillLabel,
  pillVariant = 'primary',
  title,
  subtitle,
  action,
  children,
  className = '',
}) => {
  return (
    <section
      id={id}
      className={`bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-5 sm:p-6 flex flex-col justify-between transition-colors ${className}`}
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <Badge variant={pillVariant}>{pillLabel}</Badge>
          {action && <div>{action}</div>}
        </div>
        <h2 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">
          {title}
        </h2>
        {subtitle && (
          <div className="text-xs sm:text-sm text-gray-600 dark:text-github-muted mt-1 leading-relaxed">
            {subtitle}
          </div>
        )}
      </div>
      <div className="w-full mt-4">{children}</div>
    </section>
  );
};
