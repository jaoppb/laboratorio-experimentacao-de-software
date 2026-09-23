import React from 'react';

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (val: T) => void;
  activeColorClass?: string;
  className?: string;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  activeColorClass = 'text-blue-600 dark:text-blue-400',
  className = '',
}: SegmentedControlProps<T>) {
  return (
    <div
      className={`inline-flex rounded-lg border border-gray-200 dark:border-github-border overflow-hidden bg-gray-50 dark:bg-github-dark p-0.5 ${className}`}
    >
      {options.map((opt) => {
        const isActive = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`px-2 py-1 text-[11px] font-semibold rounded-md transition-all ${
              isActive
                ? `bg-white dark:bg-github-card ${activeColorClass} shadow-sm`
                : 'text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
