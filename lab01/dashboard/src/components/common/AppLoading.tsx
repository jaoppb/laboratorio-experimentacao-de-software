import React from 'react';
import { Loader2 } from 'lucide-react';

interface AppLoadingProps {
  progressMsg: string;
}

export const AppLoading: React.FC<AppLoadingProps> = ({ progressMsg }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-github-darker flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full p-8 rounded-2xl bg-white dark:bg-github-card border border-gray-200 dark:border-github-border shadow-xl text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center animate-pulse">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">
          Carregando Analytics Engine
        </h2>
        <p className="text-xs text-gray-500 dark:text-github-muted mt-2">
          {progressMsg}
        </p>
        <div className="w-full bg-gray-200 dark:bg-github-darker rounded-full h-1.5 mt-6 overflow-hidden">
          <div className="bg-blue-600 h-1.5 rounded-full w-2/3 animate-[pulse_1.5s_ease-in-out_infinite]" />
        </div>
      </div>
    </div>
  );
};
