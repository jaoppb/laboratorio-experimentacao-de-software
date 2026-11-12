import React from 'react';
import {
  Users,
  Clock,
  Activity,
  Repeat,
  CheckCircle2,
} from 'lucide-react';
import { DashboardBundle } from '../../types/dataset';
import { formatHours, formatNumber } from '../../utils/formatters';
import { KPICard } from '../molecules/KPICard';

interface KPIGridProps {
  bundle: DashboardBundle;
  activeAlpha: number;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ bundle, activeAlpha }) => {
  const p = bundle.parametros;
  const reais = bundle.resultado_testes;
  const nTotal = reais.n.com_bot + reais.n.sem_bot;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* KPI 1: Tamanho Amostral */}
      <KPICard
        label="Amostra Real"
        icon={<Users className="w-4 h-4" />}
        iconBgClass="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
        value={`${nTotal} PRs`}
        comparisonText={`${reais.n.com_bot} com_bot / ${reais.n.sem_bot} sem_bot`}
        footerBadge={
          <span className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 font-medium">
            API GitHub (tailwindcss)
          </span>
        }
        hoverBorderClass="hover:border-blue-400"
      />

      {/* KPI 2: Mediana com_bot vs sem_bot */}
      <KPICard
        label="Mediana Real"
        icon={<Clock className="w-4 h-4" />}
        iconBgClass="bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
        value={formatHours(reais.medianas_horas.com_bot)}
        comparisonText={`vs ${formatHours(reais.medianas_horas.sem_bot)} sem bot`}
        footerBadge={
          <span className="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md font-semibold">
            Razão empírica: 2,78×
          </span>
        }
        hoverBorderClass="hover:border-emerald-400"
      />

      {/* KPI 3: Assimetria Lognormal (σ_log) */}
      <KPICard
        label="Assimetria (σ_log)"
        icon={<Activity className="w-4 h-4" />}
        iconBgClass="bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
        value={formatNumber(p.com_bot.sigma_log, 2)}
        comparisonText={`vs ${formatNumber(p.sem_bot.sigma_log, 2)} sem bot`}
        footerText="Cauda pesada extrema (lognormal)"
        hoverBorderClass="hover:border-purple-400"
      />

      {/* KPI 4: Repetições de Monte Carlo */}
      <KPICard
        label="Monte Carlo (R)"
        icon={<Repeat className="w-4 h-4" />}
        iconBgClass="bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
        value="10.000"
        comparisonText="repetições por cenário"
        footerBadge={
          <span className="text-amber-600 dark:text-amber-400 font-medium">
            Semente fixa 42 (Q1, Q2, Q3)
          </span>
        }
        hoverBorderClass="hover:border-amber-400"
      />

      {/* KPI 5: Nível de Significância */}
      <KPICard
        label="Nível α Ativo"
        icon={<CheckCircle2 className="w-4 h-4" />}
        iconBgClass="bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400"
        value={`α = ${activeAlpha}`}
        comparisonText="Bicaudal"
        footerBadge={
          <span className="text-teal-600 dark:text-teal-400 font-medium">
            Tolerância: {activeAlpha === 0.05 ? '5%' : '1%'}
          </span>
        }
        hoverBorderClass="hover:border-teal-400"
      />
    </div>
  );
};
