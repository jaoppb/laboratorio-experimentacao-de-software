import React from 'react';
import { HelpCircle, GitPullRequest, ArrowRightLeft, Database } from 'lucide-react';
import { DashboardBundle } from '../../types/dataset';
import { formatHours, formatNumber } from '../../utils/formatters';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { Badge } from '../atoms/Badge';

interface Section1CenarioProps {
  bundle: DashboardBundle;
}

export const Section1Cenario: React.FC<Section1CenarioProps> = ({ bundle }) => {
  const p = bundle.parametros;
  const texto = bundle.textos.secao_1;

  return (
    <RQCardWrapper
      id="cenario"
      pillLabel="Seção 1"
      pillVariant="primary"
      title="1. Cenário: Contexto Experimental e Formulação de Hipóteses"
      subtitle="Definição da pergunta de pesquisa, formulação estatística bicaudal e caracterização amostral"
    >
      <div className="space-y-4">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        {/* Informative grid with research question, hypotheses, and parameters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* Pergunta de Pesquisa */}
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border space-y-2">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-semibold text-xs uppercase tracking-wider">
              <HelpCircle className="w-4 h-4" />
              Pergunta de Pesquisa
            </div>
            <p className="text-xs sm:text-sm text-gray-700 dark:text-github-text font-medium leading-relaxed">
              O tempo até o merge de PRs no repositório <code>tailwindlabs/tailwindcss</code> difere significativamente com a adoção do bot CodeRabbit?
            </p>
          </div>

          {/* Hipóteses Estatísticas */}
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border space-y-2">
            <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-semibold text-xs uppercase tracking-wider">
              <ArrowRightLeft className="w-4 h-4" />
              Hipóteses Formais (Bicaudais)
            </div>
            <div className="text-xs space-y-1 text-gray-700 dark:text-github-text">
              <div>
                <span className="font-bold text-gray-900 dark:text-white">H₀:</span> Distribuições idênticas (Welch: μ_com = μ_sem; MW: P(X &gt; Y) = 0,5)
              </div>
              <div>
                <span className="font-bold text-gray-900 dark:text-white">H₁:</span> Distribuições diferem em qualquer sentido (bicaudal, α = 0,05)
              </div>
            </div>
          </div>

          {/* Parâmetros Lognormais Estimados */}
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border space-y-2">
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-xs uppercase tracking-wider">
              <Database className="w-4 h-4" />
              Parâmetros Estimados (MLE)
            </div>
            <div className="text-xs space-y-1 text-gray-700 dark:text-github-text">
              <div className="flex justify-between items-center">
                <span>com_bot:</span>
                <span className="font-mono font-medium">
                  n={p.com_bot.n}, Med={formatHours(p.com_bot.mediana)}, σ_log={formatNumber(p.com_bot.sigma_log)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>sem_bot:</span>
                <span className="font-mono font-medium">
                  n={p.sem_bot.n}, Med={formatHours(p.sem_bot.mediana)}, σ_log={formatNumber(p.sem_bot.sigma_log)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </RQCardWrapper>
  );
};
