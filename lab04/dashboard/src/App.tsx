import React from 'react';
import { useLab04Data } from './hooks/useLab04Data';
import { AppLoading } from './components/common/AppLoading';
import { AppError } from './components/common/AppError';
import { Header } from './components/organisms/Header';
import { AppHero } from './components/organisms/AppHero';
import { KPIGrid } from './components/organisms/KPIGrid';
import { CrossFilterBar } from './components/organisms/CrossFilterBar';
import { Section1Cenario } from './components/organisms/Section1Cenario';
import { Section2DadosG1 } from './components/organisms/Section2DadosG1';
import { Section3TestesG2 } from './components/organisms/Section3TestesG2';
import { Section4ErroTipo1G3 } from './components/organisms/Section4ErroTipo1G3';
import { Section5PoderG4 } from './components/organisms/Section5PoderG4';
import { Section6DadosReais } from './components/organisms/Section6DadosReais';
import { Section7Conclusao } from './components/organisms/Section7Conclusao';

export function App() {
  const {
    isLoading,
    error,
    bundle,
    realPRs,
    exemploRows,
    filters,
    updateFilters,
    resetFilters,
    isFiltered,
    reload,
  } = useLab04Data();

  if (isLoading) {
    return <AppLoading />;
  }

  if (error || !bundle) {
    return <AppError error={error || 'Falha ao carregar artefatos do Lab 04.'} onRetry={reload} />;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker text-gray-900 dark:text-github-text transition-colors duration-200">
      {/* Sticky Header with navigation & theme switch */}
      <Header
        isFiltered={isFiltered}
        onResetFilters={resetFilters}
        activeAlpha={filters.alpha}
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <AppHero />

        {/* KPI Summary Grid */}
        <KPIGrid bundle={bundle} activeAlpha={filters.alpha} />

        {/* Interactive Multi-Dimension Filter Bar */}
        <CrossFilterBar
          filters={filters}
          onUpdateFilters={updateFilters}
          onResetFilters={resetFilters}
          isFiltered={isFiltered}
        />

        {/* Seção 1: Cenário */}
        <Section1Cenario bundle={bundle} />

        {/* Seção 2: Os dados (G1) */}
        <Section2DadosG1
          bundle={bundle}
          realPRs={realPRs}
          exemploRows={exemploRows}
        />

        {/* Seção 3: Como os testes funcionam (G2) */}
        <Section3TestesG2 bundle={bundle} activeAlpha={filters.alpha} />

        {/* Seção 4: Erro tipo I (G3) */}
        <Section4ErroTipo1G3 bundle={bundle} filters={filters} />

        {/* Seção 5: Poder (G4) */}
        <Section5PoderG4 bundle={bundle} filters={filters} />

        {/* Seção 6: Dados reais e Inspetor de PRs */}
        <Section6DadosReais
          bundle={bundle}
          realPRs={realPRs}
          grupoFilter={filters.grupoFilter}
          onGrupoFilterChange={(grupo) => updateFilters({ grupoFilter: grupo })}
          searchQuery={filters.searchQuery}
          onSearchChange={(query) => updateFilters({ searchQuery: query })}
        />

        {/* Seção 7: Conclusão */}
        <Section7Conclusao bundle={bundle} />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-github-border py-8 text-center text-xs text-gray-500 dark:text-github-muted bg-white dark:bg-github-dark mt-12 transition-colors">
        <div className="max-w-7xl mx-auto px-4 space-y-2">
          <p className="font-semibold text-gray-700 dark:text-github-text">
            Laboratório de Experimentação de Software · Lab 04 · Testes de Hipótese por Simulação
          </p>
          <p>
            Engenharia de Software · PUC Minas · Repositório tailwindlabs/tailwindcss
          </p>
          <div className="flex justify-center items-center gap-4 pt-2">
            <a
              href="https://github.com/jaoppb/laboratorio-experimentacao-de-software"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Código-Fonte
            </a>
            <span>·</span>
            <a
              href="https://github.com/users/jaoppb/projects/3/views/1"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Projetos GitHub
            </a>
            <span>·</span>
            <a
              href="../"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Portal Central
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
export default App;
