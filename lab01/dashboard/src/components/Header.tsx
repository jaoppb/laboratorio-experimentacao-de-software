import React from 'react';
import { Moon, Sun, RotateCcw, Activity, Layers, Database } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { fmt } from '../utils/formatters';

interface HeaderProps {
  totalRows: number;
  filteredCount: number;
  computeTimeMs: number;
  onResetFilters: () => void;
  isFiltered: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  totalRows,
  filteredCount,
  computeTimeMs,
  onResetFilters,
  isFiltered,
}) => {
  const { isDark, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200 dark:border-github-border bg-white/80 dark:bg-github-card/80 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Title */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600/10 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-lg">
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1.5 1.75A.75.75 0 0 1 2.25 1h11.5a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75H2.25a.75.75 0 0 1-.75-.75Zm1.5.75v11h10v-11Z" />
              <path d="M4.5 11.5a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 .75.75v1.25h-2.5Zm3.25-3a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 .75.75v4.25h-2.5Zm3.25-2.5a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 .75.75v6.75h-2.5Z" />
            </svg>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
            <span className="text-xs sm:text-sm text-gray-500 dark:text-github-muted font-medium">
              jaoppb / lab01 /
            </span>
            <h1 className="text-sm sm:text-base font-bold text-gray-900 dark:text-white tracking-tight">
              Interactive Analytics Dashboard
            </h1>
          </div>
        </div>

        {/* Status Badges & Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Worker compute indicator */}
          <div className="hidden md:flex items-center gap-2 text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-github-darker border border-gray-200 dark:border-github-border text-gray-600 dark:text-github-muted">
            <Database className="w-3.5 h-3.5 text-blue-500" />
            <span>
              <b>{fmt(filteredCount)}</b> / {fmt(totalRows)} repos
            </span>
            {computeTimeMs > 0 && (
              <>
                <span className="text-gray-300 dark:text-gray-700">|</span>
                <Activity className="w-3.5 h-3.5 text-emerald-500" />
                <span>{computeTimeMs} ms</span>
              </>
            )}
          </div>

          {/* Reset Filters button */}
          {isFiltered && (
            <button
              onClick={onResetFilters}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 dark:bg-amber-400/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition"
              title="Limpar todos os filtros"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Limpar Filtros</span>
            </button>
          )}

          {/* Dark / Light Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-gray-600 dark:text-github-muted hover:bg-gray-100 dark:hover:bg-github-dark border border-gray-200 dark:border-github-border transition"
            aria-label="Alternar tema claro/escuro"
            title={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-gray-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
