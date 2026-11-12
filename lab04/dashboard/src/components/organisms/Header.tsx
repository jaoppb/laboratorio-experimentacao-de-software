import React from 'react';
import {
  RotateCcw,
  Sun,
  Moon,
  Github,
  Home,
  ExternalLink,
  GitPullRequest,
  Kanban,
  Globe,
} from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';

interface HeaderProps {
  isFiltered: boolean;
  onResetFilters: () => void;
  activeAlpha: number;
}

export const Header: React.FC<HeaderProps> = ({
  isFiltered,
  onResetFilters,
  activeAlpha,
}) => {
  const { toggleTheme, isDark } = useTheme();

  return (
    <header className="sticky top-0 z-40 bg-white/90 dark:bg-github-dark/90 backdrop-blur-md border-b border-gray-200 dark:border-github-border transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Branding & Status */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 shrink-0">
            <GitPullRequest className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Badge variant="primary" className="uppercase tracking-wider">
                Lab 04
              </Badge>
              <h1 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                Welch × Mann-Whitney em Dados Lognormais
              </h1>
            </div>
            <p className="text-xs text-gray-500 dark:text-github-muted truncate hidden sm:block">
              Simulação de Monte Carlo · P1 tailwindlabs/tailwindcss · α = {activeAlpha}
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

          {/* Navigation to Central Portal & Other Labs */}
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
            href="../lab02/"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-github-border rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Acessar Dashboard do Lab 02"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Lab 02</span>
          </a>

          {/* GitHub Repo */}
          <a
            href="https://github.com/jaoppb/laboratorio-experimentacao-de-software"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Repositório GitHub"
          >
            <Github className="w-4 h-4" />
          </a>

          {/* GitHub Projects */}
          <a
            href="https://github.com/users/jaoppb/projects/3/views/1"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="Quadro Kanban no GitHub Projects"
          >
            <Kanban className="w-4 h-4" />
          </a>

          {/* GitHub Pages */}
          <a
            href="https://jaoppb.github.io/laboratorio-experimentacao-de-software/lab04/"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-github-card transition"
            title="URL Publicada no GitHub Pages"
          >
            <Globe className="w-4 h-4" />
          </a>

          {/* Theme Toggle */}
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
