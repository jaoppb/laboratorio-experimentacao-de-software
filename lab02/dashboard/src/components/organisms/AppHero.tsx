import React from 'react';
import { Sparkles } from 'lucide-react';
import { Badge } from '../atoms/Badge';

interface AppHeroProps {
  totalTrials: number;
}

export const AppHero: React.FC<AppHeroProps> = ({ totalTrials }) => {
  return (
    <div className="bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-transparent border border-blue-200/60 dark:border-blue-500/20 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2 max-w-3xl">
          <Badge variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
            Experimento Controlado · Crossover Within-Subject
          </Badge>
          <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            Impacto de Assistentes de IA na Resolução de Katas de Programação
          </h2>
          <p className="text-xs sm:text-sm text-gray-600 dark:text-github-muted leading-relaxed">
            Avaliação comparativa da resolução de 6 problemas da <b>XIII Maratona Mineira de Programação (2026)</b> por desenvolvedores humanos em dois tratamentos: com assistente de IA habilitado (<b>Gemini 3.8 Flash</b> e <b>Claude Sonnet 5</b>) vs. desenvolvimento manual sem IA.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 shrink-0">
          <div className="bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-blue-600 dark:text-blue-400">{totalTrials}</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">Trials Registrados</div>
          </div>
          <div className="bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-purple-600 dark:text-purple-400">6</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">Katas Avaliados</div>
          </div>
          <div className="col-span-2 sm:col-span-1 bg-white/80 dark:bg-github-card/80 backdrop-blur border border-gray-200 dark:border-github-border rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">100%</div>
            <div className="text-[11px] text-gray-500 dark:text-github-muted font-medium">Testes Passando</div>
          </div>
        </div>
      </div>
    </div>
  );
};
