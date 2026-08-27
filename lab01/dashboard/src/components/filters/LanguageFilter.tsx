import React from 'react';
import { Code2 } from 'lucide-react';
import { fmt } from '../../utils/formatters';

interface LanguageFilterProps {
  languages: { name: string; count: number }[];
  selectedLanguages: string[];
  onToggleLanguage: (lang: string) => void;
  onClearLanguages: () => void;
}

export const LanguageFilter: React.FC<LanguageFilterProps> = ({
  languages,
  selectedLanguages,
  onToggleLanguage,
  onClearLanguages,
}) => {
  const topLanguages = languages.slice(0, 10);

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-medium text-gray-700 dark:text-github-text">
        <span className="flex items-center gap-1.5">
          <Code2 className="w-3.5 h-3.5 text-indigo-500" /> Filtrar Linguagens
        </span>
        {selectedLanguages.length > 0 && (
          <button
            onClick={onClearLanguages}
            className="text-[11px] text-indigo-500 hover:underline"
          >
            Limpar ({selectedLanguages.length})
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
        {topLanguages.map((l) => {
          const selected = selectedLanguages.includes(l.name);
          return (
            <button
              key={l.name}
              onClick={() => onToggleLanguage(l.name)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition border ${
                selected
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-gray-50 dark:bg-github-darker border-gray-200 dark:border-github-border text-gray-700 dark:text-github-muted hover:border-gray-400'
              }`}
            >
              {l.name} <span className="opacity-60 text-[10px]">({fmt(l.count)})</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
