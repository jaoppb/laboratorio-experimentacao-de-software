import React from 'react';
import { Sparkles } from 'lucide-react';

interface Top100ChipBarProps {
  topRepos: string[];
  selectedRepo: string;
  onSelectRepo: (repoName: string) => void;
}

export const Top100ChipBar: React.FC<Top100ChipBarProps> = ({
  topRepos,
  selectedRepo,
  onSelectRepo,
}) => {
  if (!topRepos.length) return null;

  return (
    <div className="pt-3 pb-1 flex items-center gap-1.5 overflow-x-auto text-xs no-scrollbar w-full border-b border-gray-100 dark:border-github-border/40">
      <span className="text-gray-400 dark:text-github-muted flex items-center gap-1 mr-1 font-medium shrink-0">
        <Sparkles className="w-3 h-3 text-purple-500" /> Top 100 Dinâmico:
      </span>
      {topRepos.map((repo, idx) => {
        const isSelected = selectedRepo === repo;
        return (
          <button
            key={repo}
            onClick={() => onSelectRepo(repo)}
            className={`px-2.5 py-1 rounded-md whitespace-nowrap font-mono text-[11px] transition border flex items-center gap-1 shrink-0 ${
              isSelected
                ? 'bg-purple-600 text-white border-purple-600 font-semibold shadow-sm'
                : 'bg-gray-100 dark:bg-github-darker border-gray-200 dark:border-github-border text-gray-700 dark:text-github-muted hover:border-purple-400'
            }`}
            title={`Rank #${idx + 1}: ${repo}`}
          >
            <span className="opacity-50 text-[9px] font-sans">#{idx + 1}</span>
            <span>{repo}</span>
          </button>
        );
      })}
    </div>
  );
};
