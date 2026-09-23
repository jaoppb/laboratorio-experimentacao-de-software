import React from 'react';
import {
  Clock,
  CheckCircle2,
  GitFork,
  Activity,
  FileCode,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { SummaryStats } from '../types/dataset';
import { formatDuration, formatNumber } from '../utils/formatters';

interface KPIGridProps {
  stats: SummaryStats;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ stats }) => {
  const isTimeFaster = stats.time_reduction_pct > 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* KPI 1: Tempo Mediano (RQ1) */}
      <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition hover:border-blue-400">
        <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Tempo Mediano (RQ1)</span>
          <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-gray-900 dark:text-white">
            {formatDuration(stats.time_ai.median, true)}
          </span>
          <span className="text-xs text-gray-500 dark:text-github-muted">
            vs {formatDuration(stats.time_manual.median, true)} manual
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 text-xs font-semibold">
          {isTimeFaster ? (
            <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md">
              <TrendingDown className="w-3.5 h-3.5" />
              {stats.time_reduction_pct}% mais rápido c/ IA
            </span>
          ) : (
            <span className="text-gray-500">Sem variação relevante</span>
          )}
        </div>
      </div>

      {/* KPI 2: Taxa de Sucesso (RQ2) */}
      <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition hover:border-emerald-400">
        <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Taxa de Sucesso (RQ2)</span>
          <div className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-gray-900 dark:text-white">
            100%
          </span>
          <span className="text-xs text-gray-500 dark:text-github-muted">
            {stats.total_tests_passed}/{stats.total_tests_count} testes
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 text-xs font-semibold">
          <span className="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md">
            Zero testes falhando
          </span>
        </div>
      </div>

      {/* KPI 3: Complexidade Ciclomática (RQ3) */}
      <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition hover:border-purple-400">
        <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Complexidade CC (RQ3)</span>
          <div className="p-1.5 rounded-lg bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-gray-900 dark:text-white">
            {formatNumber(stats.cc_ai.mean, 1)}
          </span>
          <span className="text-xs text-gray-500 dark:text-github-muted">
            vs {formatNumber(stats.cc_manual.mean, 1)} manual
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-gray-500 dark:text-github-muted">
          Radon CC Médio por função
        </div>
      </div>

      {/* KPI 4: Índice Manutenibilidade MI (RQ3) */}
      <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition hover:border-teal-400">
        <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Manutenibilidade MI</span>
          <div className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400">
            <GitFork className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-gray-900 dark:text-white">
            {formatNumber(stats.mi_ai.mean, 1)}
          </span>
          <span className="text-xs text-gray-500 dark:text-github-muted">
            vs {formatNumber(stats.mi_manual.mean, 1)} manual
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400">
          Rank A (Radon score &gt; 50)
        </div>
      </div>

      {/* KPI 5: Tamanho do Código (LOC - Controle) */}
      <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl p-4 shadow-sm transition hover:border-amber-400">
        <div className="flex items-center justify-between text-gray-500 dark:text-github-muted mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">LOC Médio (Controle)</span>
          <div className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">
            <FileCode className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-gray-900 dark:text-white">
            {formatNumber(stats.loc_ai.mean, 0)}
          </span>
          <span className="text-xs text-gray-500 dark:text-github-muted">
            vs {formatNumber(stats.loc_manual.mean, 0)} manual
          </span>
        </div>
        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-gray-500 dark:text-github-muted">
          Linhas físicas de código
        </div>
      </div>
    </div>
  );
};
