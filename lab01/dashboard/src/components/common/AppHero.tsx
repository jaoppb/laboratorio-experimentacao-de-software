import React from 'react';
import { fmt } from '../../utils/formatters';

interface AppHeroProps {
  totalRows: number;
}

export const AppHero: React.FC<AppHeroProps> = ({ totalRows }) => {
  return (
    <section className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-2xl p-5 sm:p-7 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/40">
          Laboratório de Experimentação de Software · Lab01
        </span>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40">
          Web Worker Engine (WASM/JS)
        </span>
      </div>

      <h2 className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white tracking-tight">
        Características de Repositórios Populares no GitHub
      </h2>
      <p className="text-xs sm:text-sm text-gray-600 dark:text-github-muted mt-2 leading-relaxed max-w-4xl">
        Análise interativa das 7 questões de pesquisa sobre os repositórios mais populares do GitHub. Todas as estatísticas, medianas, percentis e matriz de correlação de Spearman são calculadas <b>ao vivo no navegador</b> via Web Worker a partir de <code>unified_sample.parquet</code> (<b>{fmt(totalRows)}</b> repositórios).
      </p>
    </section>
  );
};
