import React from 'react';
import { Loader2 } from 'lucide-react';

export const AppLoading: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker flex flex-col items-center justify-center p-4">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        <h2 className="text-base font-bold text-gray-900 dark:text-white">
          Carregando dados do Lab 04...
        </h2>
        <p className="text-xs text-gray-500 dark:text-github-muted">
          Processando simulações de Monte Carlo e dados empíricos
        </p>
      </div>
    </div>
  );
};
