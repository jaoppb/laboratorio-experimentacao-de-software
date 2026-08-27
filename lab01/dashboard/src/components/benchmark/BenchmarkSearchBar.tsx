import React, { useState, useRef, useEffect } from 'react';
import { Search, ExternalLink } from 'lucide-react';

interface BenchmarkSearchBarProps {
  onSelectRepo: (repoName: string) => void;
  suggestions: string[];
  onSearchSuggestions: (query: string) => void;
}

export const BenchmarkSearchBar: React.FC<BenchmarkSearchBarProps> = ({
  onSelectRepo,
  suggestions,
  onSearchSuggestions,
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
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

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearchTerm(val);
    if (val.trim().length >= 1) {
      onSearchSuggestions(val);
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  };

  const handleSelect = (repoName: string) => {
    onSelectRepo(repoName);
    setSearchTerm('');
    setIsOpen(false);
  };

  return (
    <div className="relative w-full sm:w-72 md:w-80 min-w-[200px]" ref={dropdownRef}>
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-github-muted" />
        <input
          type="text"
          value={searchTerm}
          onChange={handleInputChange}
          onFocus={() => {
            if (searchTerm.trim().length >= 1) {
              setIsOpen(true);
            } else {
              onSearchSuggestions('');
              setIsOpen(true);
            }
          }}
          placeholder="Buscar qualquer repositório (ex: facebook/react)..."
          className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm rounded-lg bg-gray-50 dark:bg-github-darker border border-gray-200 dark:border-github-border text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-github-muted focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto">
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-github-muted border-b border-gray-100 dark:border-github-border/40 bg-gray-50 dark:bg-github-darker">
            {searchTerm.trim() ? `Resultados da busca (${suggestions.length})` : 'Top Repositórios'}
          </div>
          {suggestions.map((repoName) => (
            <button
              key={repoName}
              onClick={() => handleSelect(repoName)}
              className="w-full text-left px-3 py-2 text-xs font-mono hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-800 dark:text-gray-200 flex items-center justify-between transition border-b border-gray-50 dark:border-github-border/30 last:border-0"
            >
              <span className="truncate">{repoName}</span>
              <ExternalLink className="w-3 h-3 text-gray-400 shrink-0 ml-2" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
