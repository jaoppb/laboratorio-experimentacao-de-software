import React from 'react';
import { Select, SelectOption } from '../atoms/Select';

interface FilterSelectProps {
  label: string;
  icon?: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}

export const FilterSelect: React.FC<FilterSelectProps> = ({
  label,
  icon,
  value,
  onChange,
  options,
  className = '',
}) => {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text">
        {icon}
        <span>{label}</span>
      </label>
      <Select value={value} onChange={onChange} options={options} />
    </div>
  );
};
