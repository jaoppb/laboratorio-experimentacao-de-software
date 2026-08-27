import React from 'react';
import { Sparkles } from 'lucide-react';
import { FilterState } from '../../types/dataset';
import { INITIAL_FILTERS } from '../../hooks/useAnalyticsWorker';

interface FilterPresetsProps {
  filters: FilterState;
  onApplyPreset: (preset: Partial<FilterState>) => void;
}

export const FilterPresets: React.FC<FilterPresetsProps> = ({
  filters,
  onApplyPreset,
}) => {
  const isDefault =
    filters.ageMinYears === 0 &&
    filters.ageMaxYears === 20 &&
    filters.minMergedPRs === 0 &&
    filters.minReleases === 0 &&
    filters.maxDaysSinceUpdate === 3650 &&
    filters.selectedLanguages.length === 0 &&
    filters.minClosedIssuesRatio === 0;

  const presets: { label: string; preset: Partial<FilterState> }[] = [
    { label: '🔥 Ativos Recentes (<7 dias)', preset: { maxDaysSinceUpdate: 7 } },
    { label: '⚡ Alto Throughput (>500 PRs)', preset: { minMergedPRs: 500 } },
    { label: '🏷️ Releases Frequentes (>10)', preset: { minReleases: 10 } },
    { label: '🏛️ Veteranos (>8 anos)', preset: { ageMinYears: 8 } },
    { label: '✅ Alta Resolução (>85% Issues Fechadas)', preset: { minClosedIssuesRatio: 0.85 } },
  ];

  return (
    <div className="pt-3 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
      <span className="text-gray-400 dark:text-github-muted flex items-center gap-1 mr-1 font-medium shrink-0">
        <Sparkles className="w-3 h-3 text-amber-500" /> Presets:
      </span>
      <button
        onClick={() => onApplyPreset(INITIAL_FILTERS)}
        className={`px-2.5 py-1 rounded-full whitespace-nowrap transition border ${
          isDefault
            ? 'bg-blue-600 text-white border-blue-600 font-semibold'
            : 'bg-gray-100 dark:bg-github-darker border-gray-200 dark:border-github-border text-gray-700 dark:text-github-muted hover:border-gray-400'
        }`}
      >
        Todos (100k)
      </button>
      {presets.map((p) => (
        <button
          key={p.label}
          onClick={() => onApplyPreset({ ...INITIAL_FILTERS, ...p.preset })}
          className="px-2.5 py-1 rounded-full whitespace-nowrap bg-gray-100 dark:bg-github-darker border border-gray-200 dark:border-github-border text-gray-700 dark:text-github-muted hover:border-blue-500 hover:text-blue-500 transition"
        >
          {p.label}
        </button>
      ))}
    </div>
  );
};
