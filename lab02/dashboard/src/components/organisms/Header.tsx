import React from 'react';
import { RotateCcw, Sun, Moon, Github, Home, ExternalLink, Cpu } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';

interface HeaderProps {
  totalTrials: number;
  filteredCount: number;
  isFiltered: boolean;
  onResetFilters: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  totalTrials,
  filteredCount,
  isFiltered,
  onResetFilters,
}) => {
  const { toggleTheme, isDark } = useTheme();

  return (
    <header className="sticky top-0 z-40 bg-white/90 dark:bg-github-dark/90 backdrop-blur-md border-b border-gray-200 dark:border-github-border transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Branding & Status */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 shrink-0">
            <Cpu className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Badge variant="primary" className="uppercase tracking-wider">
                Lab 02
              </Badge>
              <h1 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                Resolução de Katas: IA vs. Manual
              </h1>
            </div>
            <p className="text-xs text-gray-500 dark:text-github-muted truncate hidden sm:block">
              {filteredCount} de {totalTrials} trials exibidos · Experimento crossover within-subject
            </p>
          </div>
        </div>

        {/* Right: Actions & Navigation */}
        <div className="flex items-center gap-2 shrink-0">
          {isFiltered && (
            <Button
              variant="outline"
              size="sm"
              icon={<RotateCcw className="w-3.5 h-3.5" />}
              onClick={onResetFilters}
              className="text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800/60 hover:bg-amber-100"
            >
              <span className="hidden sm:inline">Resetar Filtros</span>
            </Button>
          )}

          <a
            href="../"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-github-border rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Voltar ao Portal Central"
          >
            <Home className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Portal</span>
          </a>

          <a
            href="../lab01/"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-github-border rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Acessar Dashboard do Lab 01"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Lab 01</span>
          </a>

          <a
            href="https://github.com/jaoppb/laboratorio-experimentacao-de-software"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Repositório no GitHub"
          >
            <Github className="w-4 h-4" />
          </a>

          <Button
            variant="icon"
            onClick={toggleTheme}
            title={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
};
