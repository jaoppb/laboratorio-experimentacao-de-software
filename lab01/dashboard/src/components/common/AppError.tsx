import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface AppErrorProps {
  error: string;
}

export const AppError: React.FC<AppErrorProps> = ({ error }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full p-8 rounded-2xl bg-white dark:bg-github-card border border-red-500/30 shadow-xl text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-red-500/10 text-red-600 dark:text-red-400 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">
          Erro ao Carregar Amostra
        </h2>
        <p className="text-xs text-red-500 dark:text-red-400 mt-2 font-mono break-words">
          {error}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition flex items-center gap-2 mx-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Tentar Novamente</span>
        </button>
      </div>
    </div>
  );
};
