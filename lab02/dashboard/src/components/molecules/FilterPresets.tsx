import React from 'react';
import { Button } from '../atoms/Button';

export interface PresetItem {
  label: string;
  apply: () => void;
}

interface FilterPresetsProps {
  presets: PresetItem[];
  className?: string;
}

export const FilterPresets: React.FC<FilterPresetsProps> = ({
  presets,
  className = '',
}) => {
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      <span className="text-xs font-semibold text-gray-500 dark:text-github-muted mr-1">
        Presets:
      </span>
      {presets.map((p) => (
        <Button
          key={p.label}
          variant="outline"
          size="sm"
          onClick={p.apply}
          className="text-xs px-2.5 py-1"
        >
          {p.label}
        </Button>
      ))}
    </div>
  );
};
