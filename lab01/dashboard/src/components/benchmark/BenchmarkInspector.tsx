import React from 'react';
import { Target } from 'lucide-react';
import { BenchmarkReport } from '../../types/dataset';
import { BenchmarkSearchBar } from './BenchmarkSearchBar';
import { Top100Dropdown } from './Top100Dropdown';
import { Top100ChipBar } from './Top100ChipBar';
import { RepoHeaderCard } from './RepoHeaderCard';
import { PercentileBarList } from './PercentileBarList';
import { BenchmarkRadarChart } from './BenchmarkRadarChart';

interface BenchmarkInspectorProps {
  benchmark: BenchmarkReport | null;
  inspectingRepoName: string;
  onInspectRepo: (repoName: string) => void;
  suggestions: string[];
  onSearchSuggestions: (query: string) => void;
  topRepos?: string[];
}

export const BenchmarkInspector: React.FC<BenchmarkInspectorProps> = ({
  benchmark,
  onInspectRepo,
  suggestions,
  onSearchSuggestions,
  topRepos = [],
}) => {
  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-6 transition-all space-y-4">
      {/* Header Row: Title & Search Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-gray-100 dark:border-github-border/60">
        <div className="shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Target className="w-4 h-4" />
            </div>
            <h2 className="font-bold text-base sm:text-lg text-gray-900 dark:text-white whitespace-nowrap">
              Single-Repo Benchmark Inspector
            </h2>
          </div>
          <p className="text-xs text-gray-500 dark:text-github-muted mt-1 max-w-lg">
            Pesquise qualquer um dos 100.000 repositórios para comparar seu percentil exato frente à amostra global.
          </p>
        </div>

        {/* Right side: Search bar & Top 100 dropdown button */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <BenchmarkSearchBar onSelectRepo={onInspectRepo} suggestions={suggestions} onSearchSuggestions={onSearchSuggestions} />
          <Top100Dropdown topRepos={topRepos} selectedRepo={benchmark?.repo.repo || ''} onSelectRepo={onInspectRepo} />
        </div>
      </div>

      {/* Row 2: Full-width Top 100 Horizontal Scroll Chip Bar */}
      <Top100ChipBar topRepos={topRepos} selectedRepo={benchmark?.repo.repo || ''} onSelectRepo={onInspectRepo} />

      {/* Row 3: Benchmark Report Content */}
      {benchmark ? (
        <div className="pt-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-7 space-y-4">
            <RepoHeaderCard repo={benchmark.repo} rankScore={benchmark.rankScore} />
            <PercentileBarList percentiles={benchmark.percentiles} />
          </div>
          <BenchmarkRadarChart radarData={benchmark.radarData} repoName={benchmark.repo.repo} />
        </div>
      ) : (
        <div className="py-12 text-center text-sm text-gray-500 dark:text-github-muted">
          Repositório não encontrado. Tente buscar por outro nome da amostra de 100k.
        </div>
      )}
    </div>
  );
};
