import React from 'react';

export const CorrelationLegend: React.FC = () => {
  return (
    <div className="mt-4 pt-3 border-t border-gray-100 dark:border-github-border/60 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-gray-600 dark:text-github-muted">
      <div className="flex items-start gap-2">
        <span className="w-3 h-3 rounded-full bg-blue-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-gray-800 dark:text-gray-200">
            Correlação Positiva (&rho; &gt; 0):
          </span>{' '}
          Quando uma métrica sobe, a outra tende a subir monotonicamente (ex: Idade e PRs Mesclados).
        </div>
      </div>
      <div className="flex items-start gap-2">
        <span className="w-3 h-3 rounded-full bg-red-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-gray-800 dark:text-gray-200">
            Correlação Negativa (&rho; &lt; 0):
          </span>{' '}
          Quando uma métrica sobe, a outra decresce (ex: Dias sem update e atividade).
        </div>
      </div>
      <div className="flex items-start gap-2">
        <span className="w-3 h-3 rounded-full bg-gray-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-gray-800 dark:text-gray-200">
            Neutralidade (&rho; &approx; 0):
          </span>{' '}
          Ausência de relação monotônica entre os postos das variáveis.
        </div>
      </div>
    </div>
  );
};
