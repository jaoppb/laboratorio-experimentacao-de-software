import React from 'react';
import { Sparkles, GitBranch, Cpu, Database } from 'lucide-react';
import { Badge } from '../atoms/Badge';

export const AppHero: React.FC = () => {
  return (
    <div className="bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-transparent border border-blue-200/60 dark:border-blue-500/20 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
              Testes de Hipótese por Simulação · Par P1
            </Badge>
            <Badge variant="purple" icon={<Cpu className="w-3.5 h-3.5" />}>
              Monte Carlo (R = 10.000)
            </Badge>
            <Badge variant="success" icon={<GitBranch className="w-3.5 h-3.5" />}>
              tailwindlabs/tailwindcss
            </Badge>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            Welch × Mann-Whitney em Dados de Processo de Software com Cauda Pesada
          </h2>
          <p className="text-xs sm:text-sm text-gray-600 dark:text-github-muted leading-relaxed">
            Investigação empírica e por simulação sobre o tempo até o merge de pull requests no repositório <b>tailwindlabs/tailwindcss</b>, comparando a eficácia e robustez do <b>teste t de Welch (paramétrico)</b> contra o <b>teste U de Mann-Whitney (não paramétrico)</b> sob distribuição lognormal com assimetria severa e outliers.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 shrink-0">
          <div className="bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-blue-600 dark:text-blue-400">60</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">PRs Reais Coletados</div>
          </div>
          <div className="bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-purple-600 dark:text-purple-400">10.000</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">Repetições / Cenário</div>
          </div>
          <div className="col-span-2 sm:col-span-1 bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">6</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">Situações Simuladas</div>
          </div>
        </div>
      </div>
    </div>
  );
};
