import React from 'react';

interface FilterSliderProps {
  icon: React.ReactNode;
  label: string;
  displayValue: React.ReactNode;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
  accentColorClass?: string;
  hints?: string[];
}

export const FilterSlider: React.FC<FilterSliderProps> = ({
  icon,
  label,
  displayValue,
  min,
  max,
  step,
  value,
  onChange,
  accentColorClass = 'accent-blue-600',
  hints,
}) => {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-medium text-gray-700 dark:text-github-text">
        <span className="flex items-center gap-1.5">
          {icon} {label}
        </span>
        <span className="font-semibold">{displayValue}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={`w-full h-1.5 bg-gray-200 dark:bg-github-darker rounded-lg appearance-none cursor-pointer ${accentColorClass}`}
      />
      {hints && hints.length > 0 && (
        <div className="flex justify-between text-[10px] text-gray-400 dark:text-github-muted">
          {hints.map((h, i) => (
            <span key={i}>{h}</span>
          ))}
        </div>
      )}
    </div>
  );
};
