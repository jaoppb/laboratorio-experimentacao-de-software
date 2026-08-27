import React, { useState, useRef, useEffect } from 'react';
import { ListFilter, Flame, Check } from 'lucide-react';

interface Top100DropdownProps {
  topRepos: string[];
  selectedRepo: string;
  onSelectRepo: (repoName: string) => void;
}

export const Top100Dropdown: React.FC<Top100DropdownProps> = ({
  topRepos,
  selectedRepo,
  onSelectRepo,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!topRepos.length) return null;

  return (
    <div className="relative shrink-0" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/40 hover:bg-purple-100 dark:hover:bg-purple-900/40 transition whitespace-nowrap"
        title="Ver lista completa dos 100 repositórios de topo da amostra"
      >
        <ListFilter className="w-3.5 h-3.5" />
        <span>Top 100 ({topRepos.length})</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-80 bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-lg shadow-xl z-50 max-h-80 overflow-y-auto">
          <div className="sticky top-0 px-3 py-2 bg-gray-50 dark:bg-github-darker border-b border-gray-100 dark:border-github-border text-xs font-bold text-gray-700 dark:text-github-text flex items-center justify-between">
            <span className="flex items-center gap-1"><Flame className="w-3.5 h-3.5 text-amber-500" /> Top 100 da Amostra</span>
            <span className="text-[10px] text-gray-400">100 repos</span>
          </div>
          {topRepos.map((repo, idx) => {
            const isSelected = selectedRepo === repo;
            return (
              <button
                key={repo}
                onClick={() => { onSelectRepo(repo); setIsOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs font-mono flex items-center justify-between transition border-b border-gray-50 dark:border-github-border/30 last:border-0 ${
                  isSelected ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-900 dark:text-purple-200 font-bold' : 'hover:bg-gray-100 dark:hover:bg-github-darker text-gray-800 dark:text-gray-300'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="text-[10px] text-gray-400 w-6 font-sans">#{idx + 1}</span>
                  <span className="truncate">{repo}</span>
                </div>
                {isSelected && <Check className="w-3.5 h-3.5 text-purple-500 shrink-0 ml-1" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
