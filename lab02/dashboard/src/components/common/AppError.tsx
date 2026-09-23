import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

interface AppErrorProps {
  error: string;
  onRetry: () => void;
}

export const AppError: React.FC<AppErrorProps> = ({ error, onRetry }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-github-card border border-red-200 dark:border-red-900/40 rounded-2xl p-6 text-center shadow-lg space-y-4">
        <div className="mx-auto w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            Erro ao Carregar Experimento
          </h2>
          <p className="text-xs text-gray-600 dark:text-github-muted mt-1">{error}</p>
        </div>
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
        >
          <RotateCcw className="w-4 h-4" />
          Tentar Novamente
        </button>
      </div>
    </div>
  );
};
