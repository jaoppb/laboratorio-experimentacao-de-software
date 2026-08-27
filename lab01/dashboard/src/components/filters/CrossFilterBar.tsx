import React, { useState } from 'react';
import { SlidersHorizontal, ChevronDown, ChevronUp, Calendar, GitPullRequest, Tag, Clock, CheckCircle2 } from 'lucide-react';
import { FilterState } from '../../types/dataset';
import { FilterPresets } from './FilterPresets';
import { FilterSlider } from './FilterSlider';
import { LanguageFilter } from './LanguageFilter';
import { fmt } from '../../utils/formatters';

interface CrossFilterBarProps {
  filters: FilterState;
  onUpdateFilters: (newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => void;
  languages: { name: string; count: number }[];
  filteredCount: number;
  totalRows: number;
}

export const CrossFilterBar: React.FC<CrossFilterBarProps> = ({
  filters,
  onUpdateFilters,
  languages,
  filteredCount,
  totalRows,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const filterPct = totalRows > 0 ? ((filteredCount / totalRows) * 100).toFixed(1) : '100';

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 transition-all">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-gray-100 dark:border-github-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <SlidersHorizontal className="w-4 h-4" />
          </div>
          <span className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white">Multi-Dimension Cross Filtering</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium">
            {fmt(filteredCount)} repos ({filterPct}%)
          </span>
        </div>
        <button onClick={() => setIsExpanded(!isExpanded)} className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-github-muted hover:text-gray-900 dark:hover:text-white transition">
          <span>{isExpanded ? 'Recolher Filtros' : 'Expandir Filtros'}</span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      <FilterPresets filters={filters} onApplyPreset={(preset) => onUpdateFilters(preset)} />

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-github-border/60 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-medium text-gray-700 dark:text-github-text">
              <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 text-blue-500" /> Idade</span>
              <span className="text-blue-600 dark:text-blue-400 font-semibold">{filters.ageMinYears} – {filters.ageMaxYears === 20 ? '20+ anos' : `${filters.ageMaxYears} anos`}</span>
            </div>
            <div className="flex items-center gap-2">
              <input type="range" min="0" max="20" step="1" value={filters.ageMinYears} onChange={(e) => onUpdateFilters({ ageMinYears: Math.min(Number(e.target.value), filters.ageMaxYears - 1) })} className="w-full h-1.5 bg-gray-200 dark:bg-github-darker rounded-lg appearance-none cursor-pointer accent-blue-600" />
              <input type="range" min="0" max="20" step="1" value={filters.ageMaxYears} onChange={(e) => onUpdateFilters({ ageMaxYears: Math.max(Number(e.target.value), filters.ageMinYears + 1) })} className="w-full h-1.5 bg-gray-200 dark:bg-github-darker rounded-lg appearance-none cursor-pointer accent-blue-600" />
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 dark:text-github-muted"><span>0 anos</span><span>20 anos</span></div>
          </div>

          <FilterSlider icon={<GitPullRequest className="w-3.5 h-3.5 text-purple-500" />} label="Mín. PRs Mesclados" displayValue={<span className="text-purple-600 dark:text-purple-400">&ge; {fmt(filters.minMergedPRs)}</span>} min={0} max={2000} step={25} value={filters.minMergedPRs} onChange={(v) => onUpdateFilters({ minMergedPRs: v })} accentColorClass="accent-purple-600" hints={['0', '500', '1.000', '2.000+']} />
          <FilterSlider icon={<Tag className="w-3.5 h-3.5 text-emerald-500" />} label="Mín. Releases" displayValue={<span className="text-emerald-600 dark:text-emerald-400">&ge; {filters.minReleases}</span>} min={0} max={100} step={2} value={filters.minReleases} onChange={(v) => onUpdateFilters({ minReleases: v })} accentColorClass="accent-emerald-600" hints={['0', '25', '50', '100+']} />
          <FilterSlider icon={<Clock className="w-3.5 h-3.5 text-amber-500" />} label="Dias Máx. s/ Update" displayValue={<span className="text-amber-600 dark:text-amber-400">&le; {filters.maxDaysSinceUpdate >= 3650 ? 'Sem limite' : `${filters.maxDaysSinceUpdate}d`}</span>} min={1} max={3650} step={30} value={filters.maxDaysSinceUpdate} onChange={(v) => onUpdateFilters({ maxDaysSinceUpdate: v })} accentColorClass="accent-amber-500" hints={['1 dia', '90d', '1 ano', 'Sem limite']} />
          <FilterSlider icon={<CheckCircle2 className="w-3.5 h-3.5 text-teal-500" />} label="Mín. Taxa Fechamento" displayValue={<span className="text-teal-600 dark:text-teal-400">&ge; {(filters.minClosedIssuesRatio * 100).toFixed(0)}%</span>} min={0} max={1} step={0.05} value={filters.minClosedIssuesRatio} onChange={(v) => onUpdateFilters({ minClosedIssuesRatio: v })} accentColorClass="accent-teal-500" hints={['0%', '50%', '75%', '100%']} />

          <LanguageFilter languages={languages} selectedLanguages={filters.selectedLanguages} onToggleLanguage={(l) => onUpdateFilters((p) => ({ ...p, selectedLanguages: p.selectedLanguages.includes(l) ? p.selectedLanguages.filter((x) => x !== l) : [...p.selectedLanguages, l] }))} onClearLanguages={() => onUpdateFilters({ selectedLanguages: [] })} />
        </div>
      )}
    </div>
  );
};
