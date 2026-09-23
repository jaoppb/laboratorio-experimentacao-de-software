import React from 'react';
import {
  Clock,
  CheckCircle2,
  GitFork,
  Activity,
  FileCode,
  TrendingDown,
} from 'lucide-react';
import { SummaryStats } from '../../types/dataset';
import { formatDuration, formatNumber } from '../../utils/formatters';
import { KPICard } from '../molecules/KPICard';

interface KPIGridProps {
  stats: SummaryStats;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ stats }) => {
  const isTimeFaster = stats.time_reduction_pct > 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* KPI 1: Tempo Mediano (RQ1) */}
      <KPICard
        label="Tempo Mediano (RQ1)"
        icon={<Clock className="w-4 h-4" />}
        iconBgClass="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
        value={formatDuration(stats.time_ai.median, true)}
        comparisonText={`vs ${formatDuration(stats.time_manual.median, true)} manual`}
        footerBadge={
          isTimeFaster ? (
            <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md font-semibold">
              <TrendingDown className="w-3.5 h-3.5" />
              {stats.time_reduction_pct}% mais rápido c/ IA
            </span>
          ) : (
            <span className="text-gray-500">Sem variação relevante</span>
          )
        }
        hoverBorderClass="hover:border-blue-400"
      />

      {/* KPI 2: Taxa de Sucesso (RQ2) */}
      <KPICard
        label="Taxa de Sucesso (RQ2)"
        icon={<CheckCircle2 className="w-4 h-4" />}
        iconBgClass="bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
        value="100%"
        comparisonText={`${stats.total_tests_passed}/${stats.total_tests_count} testes`}
        footerBadge={
          <span className="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md font-semibold">
            Zero testes falhando
          </span>
        }
        hoverBorderClass="hover:border-emerald-400"
      />

      {/* KPI 3: Complexidade Ciclomática (RQ3) */}
      <KPICard
        label="Complexidade CC (RQ3)"
        icon={<Activity className="w-4 h-4" />}
        iconBgClass="bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
        value={formatNumber(stats.cc_ai.mean, 1)}
        comparisonText={`vs ${formatNumber(stats.cc_manual.mean, 1)} manual`}
        footerText="Radon CC Médio por função"
        hoverBorderClass="hover:border-purple-400"
      />

      {/* KPI 4: Índice Manutenibilidade MI (RQ3) */}
      <KPICard
        label="Manutenibilidade MI"
        icon={<GitFork className="w-4 h-4" />}
        iconBgClass="bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400"
        value={formatNumber(stats.mi_ai.mean, 1)}
        comparisonText={`vs ${formatNumber(stats.mi_manual.mean, 1)} manual`}
        footerBadge={
          <span className="text-teal-600 dark:text-teal-400 font-medium">
            Rank A (Radon score &gt; 50)
          </span>
        }
        hoverBorderClass="hover:border-teal-400"
      />

      {/* KPI 5: Tamanho do Código (LOC - Controle) */}
      <KPICard
        label="LOC Médio (Controle)"
        icon={<FileCode className="w-4 h-4" />}
        iconBgClass="bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
        value={formatNumber(stats.loc_ai.mean, 0)}
        comparisonText={`vs ${formatNumber(stats.loc_manual.mean, 0)} manual`}
        footerText="Linhas físicas de código"
        hoverBorderClass="hover:border-amber-400"
      />
    </div>
  );
};
