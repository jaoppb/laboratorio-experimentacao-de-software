import React from 'react';
import { CheckCircle, AlertTriangle, Lightbulb, ShieldAlert } from 'lucide-react';
import { DashboardBundle } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { Badge } from '../atoms/Badge';

interface Section7ConclusaoProps {
  bundle: DashboardBundle;
}

export const Section7Conclusao: React.FC<Section7ConclusaoProps> = ({ bundle }) => {
  const texto = bundle.textos.secao_7;

  return (
    <RQCardWrapper
      id="conclusao"
      pillLabel="Seção 7"
      pillVariant="success"
      title="7. Conclusão: Síntese Experimental, Recomendações e Limitações"
      subtitle="Confronto entre a hipótese pré-experimental e os achados das simulações de Monte Carlo"
    >
      <div className="space-y-5">
        {/* Parágrafo canônico avaliado pelos testes */}
        <p
          id="conclusao-texto"
          className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed"
        >
          {texto}
        </p>

        {/* Blocos Estruturados com Destaques Visuais */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* 1. Expectativa Inicial × Resultado Empírico */}
          <div className="p-4 rounded-xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/50 space-y-2">
            <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-bold text-xs uppercase tracking-wider">
              <CheckCircle className="w-4 h-4" />
              Expectativa × Resultado
            </div>
            <p className="text-xs sm:text-sm text-gray-700 dark:text-github-text leading-relaxed">
              Antes de simular, esperava-se que o Welch mantivesse algum poder pelo TCL com n = 30. A simulação provou que o Welch <b>perde quase todo o poder sob assimetria severa</b> (3,4% vs. 32,5% do Mann-Whitney em com_bot) e fica ultraconservador (0,7% de erro tipo I).
            </p>
          </div>

          {/* 2. Recomendação Prática */}
          <div className="p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 space-y-2">
            <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-bold text-xs uppercase tracking-wider">
              <Lightbulb className="w-4 h-4" />
              Recomendação Prática
            </div>
            <p className="text-xs sm:text-sm text-gray-700 dark:text-github-text leading-relaxed">
              <b>Recomendamos enfaticamente o Mann-Whitney</b> para comparar tempos de merge e métricas de processo de software com cauda longa. O teste não paramétrico preserva o erro tipo I perto de 5% e atinge poder substancialmente superior em todos os cenários.
            </p>
          </div>

          {/* 3. Limitação Metodológica */}
          <div className="p-4 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 space-y-2">
            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300 font-bold text-xs uppercase tracking-wider">
              <ShieldAlert className="w-4 h-4" />
              Limitação Metodológica
            </div>
            <p className="text-xs sm:text-sm text-gray-700 dark:text-github-text leading-relaxed">
              O estudo empírico é <b>observacional e não pareado</b>: os grupos <code>com_bot</code> e <code>sem_bot</code> pertencem a períodos históricos distintos. Fatores de confusão temporais (maturidade do projeto, evolução dos mantenedores) impedem inferir relação causal direta.
            </p>
          </div>
        </div>
      </div>
    </RQCardWrapper>
  );
};
