import React from 'react';
import { useAnalyticsWorker, INITIAL_FILTERS } from './hooks/useAnalyticsWorker';
import { Header } from './components/Header';
import { AppHero } from './components/common/AppHero';
import { AppLoading } from './components/common/AppLoading';
import { AppError } from './components/common/AppError';
import { KPIGrid } from './components/KPIGrid';
import { CrossFilterBar } from './components/filters/CrossFilterBar';
import { BenchmarkInspector } from './components/benchmark/BenchmarkInspector';
import { CorrelationHeatmap } from './components/correlation/CorrelationHeatmap';
import { RQChartsGrid } from './components/rq/RQChartsGrid';

export const App: React.FC = () => {
  const {
    isLoading,
    progressMsg,
    error,
    totalRows,
    topRepos,
    languages,
    filters,
    updateFilters,
    stats,
    correlation,
    filteredCount,
    computeTimeMs,
    benchmark,
    inspectingRepoName,
    inspectRepo,
    suggestions,
    searchSuggestions,
  } = useAnalyticsWorker();

  const isFiltered =
    filters.ageMinYears !== INITIAL_FILTERS.ageMinYears ||
    filters.ageMaxYears !== INITIAL_FILTERS.ageMaxYears ||
    filters.minMergedPRs !== INITIAL_FILTERS.minMergedPRs ||
    filters.minReleases !== INITIAL_FILTERS.minReleases ||
    filters.maxDaysSinceUpdate !== INITIAL_FILTERS.maxDaysSinceUpdate ||
    filters.selectedLanguages.length > 0 ||
    filters.minClosedIssuesRatio !== INITIAL_FILTERS.minClosedIssuesRatio ||
    filters.searchQuery !== '';

  if (isLoading) return <AppLoading progressMsg={progressMsg} />;
  if (error) return <AppError error={error} />;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker text-gray-900 dark:text-github-text">
      <Header
        totalRows={totalRows}
        filteredCount={filteredCount}
        computeTimeMs={computeTimeMs}
        onResetFilters={() => updateFilters(INITIAL_FILTERS)}
        isFiltered={isFiltered}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <AppHero totalRows={totalRows} />

        <KPIGrid stats={stats} />

        <CrossFilterBar
          filters={filters}
          onUpdateFilters={updateFilters}
          languages={languages}
          filteredCount={filteredCount}
          totalRows={totalRows}
        />

        <BenchmarkInspector
          benchmark={benchmark}
          inspectingRepoName={inspectingRepoName}
          onInspectRepo={inspectRepo}
          suggestions={suggestions}
          onSearchSuggestions={searchSuggestions}
          topRepos={topRepos}
        />

        <CorrelationHeatmap correlation={correlation} />

        <section className="space-y-4">
          <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
            Análise Detalhada das 7 Questões de Pesquisa (RQs)
          </h2>
          <RQChartsGrid stats={stats} />
        </section>

        <footer className="mt-12 pt-6 border-t border-gray-200 dark:border-github-border text-xs text-gray-500 dark:text-github-muted space-y-2">
          <p>
            Fonte dos dados: Extração GraphQL sem dependências externas, convertida em Parquet por <code>scripts/csv_to_parquet.py</code>.
          </p>
          <p>
            Processamento 100% client-side via Web Worker com <a href="https://github.com/hyparam/hyparquet" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">hyparquet</a> e <a href="https://plotly.com/javascript/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Plotly.js</a>.
          </p>
        </footer>
      </main>
    </div>
  );
};
