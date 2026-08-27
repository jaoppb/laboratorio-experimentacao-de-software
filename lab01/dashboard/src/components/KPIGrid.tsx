import React from 'react';
import {
  Calendar,
  GitPullRequest,
  Tag,
  Clock,
  Code2,
  CheckCircle2,
} from 'lucide-react';
import { RQStats } from '../types/dataset';
import { fmt, fmtDec, fmtPct } from '../utils/formatters';

interface KPIGridProps {
  stats: RQStats | null;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ stats }) => {
  if (!stats) return null;

  const topLanguage =
    stats.rq05.labels.length > 0 && stats.rq05.labels[0] !== '(sem linguagem)'
      ? stats.rq05.labels[0]
      : stats.rq05.labels[1] || 'N/A';

  const kpis = [
    {
      icon: <Calendar className="w-4 h-4 text-blue-500" />,
      label: 'RQ01 · Idade Mediana',
      value: `${fmtDec(stats.rq01.median_years, 1)} anos`,
      sub: `Média: ${fmtDec(stats.rq01.mean_years, 1)} anos | Máx: ${fmtDec(stats.rq01.max_years, 1)} anos`,
      color: 'border-blue-500/20 bg-blue-500/5',
    },
    {
      icon: <GitPullRequest className="w-4 h-4 text-purple-500" />,
      label: 'RQ02 · Mediana PRs Mesclados',
      value: fmt(stats.rq02.median),
      sub: `Média: ${fmt(Math.round(stats.rq02.mean))} | P90: ${fmt(stats.rq02.q_values[3])}`,
      color: 'border-purple-500/20 bg-purple-500/5',
    },
    {
      icon: <Tag className="w-4 h-4 text-emerald-500" />,
      label: 'RQ03 · Sem Releases',
      value: fmtPct(stats.rq03.zero_pct, 1),
      sub: `Mediana: ${fmt(stats.rq03.median)} | Média: ${fmtDec(stats.rq03.mean, 1)} releases`,
      color: 'border-emerald-500/20 bg-emerald-500/5',
    },
    {
      icon: <Clock className="w-4 h-4 text-amber-500" />,
      label: 'RQ04 · Mediana Dias s/ Update',
      value: `${fmt(stats.rq04.median)} dias`,
      sub: `Média: ${fmtDec(stats.rq04.mean, 1)} dias | Máx: ${fmt(stats.rq04.max)} dias`,
      color: 'border-amber-500/20 bg-amber-500/5',
    },
    {
      icon: <Code2 className="w-4 h-4 text-indigo-500" />,
      label: 'RQ05 · Linguagem Líder',
      value: topLanguage,
      sub: `${fmt(stats.rq05.counts[0])} repositórios (${fmtPct((stats.rq05.counts[0] / Math.max(1, stats.n_filtered)) * 100, 1)})`,
      color: 'border-indigo-500/20 bg-indigo-500/5',
    },
    {
      icon: <CheckCircle2 className="w-4 h-4 text-teal-500" />,
      label: 'RQ06 · Mediana Issues Fechadas',
      value: fmtPct(stats.rq06.median * 100, 1),
      sub: `Média: ${fmtPct(stats.rq06.mean * 100, 1)} | Sem issues: ${fmtPct(stats.rq06.missing_pct, 1)}`,
      color: 'border-teal-500/20 bg-teal-500/5',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
      {kpis.map((k, i) => (
        <div
          key={i}
          className={`p-4 rounded-xl border ${k.color} dark:bg-github-card/90 dark:border-github-border transition-all hover:scale-[1.01]`}
        >
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 dark:text-github-muted mb-1">
            {k.icon}
            <span className="truncate">{k.label}</span>
          </div>
          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white tracking-tight">
            {k.value}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-github-muted mt-1 truncate">
            {k.sub}
          </div>
        </div>
      ))}
    </div>
  );
};
