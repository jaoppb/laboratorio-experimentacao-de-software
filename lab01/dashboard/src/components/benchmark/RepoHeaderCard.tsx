import React from 'react';
import { ExternalLink } from 'lucide-react';
import { RepoRow } from '../../types/dataset';
import { fmtDec } from '../../utils/formatters';

interface RepoHeaderCardProps {
  repo: RepoRow;
  rankScore: number;
}

export const RepoHeaderCard: React.FC<RepoHeaderCardProps> = ({ repo, rankScore }) => {
  return (
    <div className="p-4 rounded-xl bg-gray-50 dark:bg-github-darker border border-gray-200 dark:border-github-border flex flex-wrap items-center justify-between gap-3">
      <div>
        <div className="flex items-center gap-2">
          <a
            href={`https://github.com/${repo.repo}`}
            target="_blank"
            rel="noreferrer"
            className="font-bold text-base sm:text-lg font-mono text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1.5"
          >
            <span>{repo.repo}</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          {repo.primary_language && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
              {repo.primary_language}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 dark:text-github-muted mt-1">
          Criado em {repo.created_at ? new Date(repo.created_at).toLocaleDateString('pt-BR') : `${fmtDec(repo.age_days / 365.25, 1)} anos atrás`}
        </div>
      </div>

      <div className="text-right">
        <div className="text-[10px] uppercase font-bold tracking-wider text-gray-400 dark:text-github-muted">
          Score de Maturidade
        </div>
        <div className="text-xl sm:text-2xl font-black text-purple-600 dark:text-purple-400">
          {rankScore} <span className="text-xs font-normal text-gray-400">/ 100</span>
        </div>
      </div>
    </div>
  );
};
