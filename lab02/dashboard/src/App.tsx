import React from 'react';
import { useLab02Data } from './hooks/useLab02Data';
import { Header } from './components/Header';
import { AppHero } from './components/AppHero';
import { KPIGrid } from './components/KPIGrid';
import { CrossFilterBar } from './components/filters/CrossFilterBar';
import { RQ1TimeCard } from './components/rq/RQ1TimeCard';
import { RQ2SuccessCard } from './components/rq/RQ2SuccessCard';
import { RQ3StructureCard } from './components/rq/RQ3StructureCard';
import { TrialInspector } from './components/inspector/TrialInspector';
import { RawDataTable } from './components/table/RawDataTable';
import { AppLoading } from './components/common/AppLoading';
import { AppError } from './components/common/AppError';

export const App: React.FC = () => {
  const {
    isLoading,
    error,
    allTrials,
    filteredTrials,
    stats,
    filters,
    updateFilters,
    resetFilters,
    isFiltered,
    selectedTrial,
    setSelectedTrialId,
    participantsList,
    katasList,
    reload,
  } = useLab02Data();

  if (isLoading) return <AppLoading />;
  if (error) return <AppError error={error} onRetry={reload} />;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker text-gray-900 dark:text-github-text transition-colors">
      <Header
        totalTrials={allTrials.length}
        filteredCount={filteredTrials.length}
        isFiltered={isFiltered}
        onResetFilters={resetFilters}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <AppHero totalTrials={allTrials.length} />

        <KPIGrid stats={stats} />

        <CrossFilterBar
          filters={filters}
          onUpdateFilters={updateFilters}
          onResetFilters={resetFilters}
          filteredCount={filteredTrials.length}
          totalTrials={allTrials.length}
          participants={participantsList}
          katas={katasList}
        />

        {/* Research Questions Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
              Questões de Pesquisa (RQs) do Experimento
            </h2>
            <span className="text-xs text-gray-500 dark:text-github-muted">
              {filteredTrials.length} trials considerados no cálculo atual
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <RQ1TimeCard stats={stats} trials={filteredTrials} />
            <RQ2SuccessCard stats={stats} trials={filteredTrials} />
          </div>

          <RQ3StructureCard stats={stats} />
        </section>

        {/* Drill-down Trial Inspector */}
        <TrialInspector
          trials={allTrials}
          selectedTrial={selectedTrial}
          onSelectTrial={setSelectedTrialId}
        />

        {/* Raw Data Table */}
        <RawDataTable
          trials={filteredTrials}
          onSelectTrial={setSelectedTrialId}
          selectedTrialId={selectedTrial?.trial_id || ''}
        />

        <footer className="mt-12 pt-6 border-t border-gray-200 dark:border-github-border text-xs text-gray-500 dark:text-github-muted space-y-2 text-center sm:text-left">
          <p>
            Fonte dos dados: <code>lab02/dados/trials.csv</code> e <code>lab02/dados/metrics.csv</code> gerados pelos runners de cronometragem e Radon/jscpd.
          </p>
          <p>
            Dashboard construído com React 18, Vite 6, TypeScript, Tailwind CSS e Plotly.js.
          </p>
        </footer>
      </main>
    </div>
  );
};
