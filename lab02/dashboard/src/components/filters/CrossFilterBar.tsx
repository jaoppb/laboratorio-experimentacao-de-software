import React, { useState } from 'react';
import {
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  User,
  Cpu,
  Layers,
  Bot,
  Search,
  RotateCcw,
} from 'lucide-react';
import { FilterState } from '../../types/dataset';
import { KATA_INFO } from '../../utils/formatters';

interface CrossFilterBarProps {
  filters: FilterState;
  onUpdateFilters: (newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => void;
  onResetFilters: () => void;
  filteredCount: number;
  totalTrials: number;
  participants: string[];
  katas: string[];
}

export const CrossFilterBar: React.FC<CrossFilterBarProps> = ({
  filters,
  onUpdateFilters,
  onResetFilters,
  filteredCount,
  totalTrials,
  participants,
  katas,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const filterPct = totalTrials > 0 ? ((filteredCount / totalTrials) * 100).toFixed(0) : '100';

  const presets = [
    { label: 'Todos', apply: () => onResetFilters() },
    { label: 'Apenas IA', apply: () => onUpdateFilters({ treatment: 'ai', ai_model: 'all' }) },
    { label: 'Apenas Manual', apply: () => onUpdateFilters({ treatment: 'manual', ai_model: 'all' }) },
    { label: 'Gabriel', apply: () => onUpdateFilters({ participant: 'gabriel' }) },
    { label: 'João', apply: () => onUpdateFilters({ participant: 'joao' }) },
    { label: 'Gemini 3.8', apply: () => onUpdateFilters({ ai_model: 'gemini-flash-3.8', treatment: 'ai' }) },
    { label: 'Claude 5', apply: () => onUpdateFilters({ ai_model: 'claude-sonnet-5', treatment: 'ai' }) },
  ];

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 transition-all">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-gray-100 dark:border-github-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <SlidersHorizontal className="w-4 h-4" />
          </div>
          <span className="font-bold text-sm sm:text-base text-gray-900 dark:text-white">
            Filtros Cruzados Multi-Dimensão
          </span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-semibold">
            {filteredCount} de {totalTrials} trials ({filterPct}%)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-github-muted hover:text-gray-900 dark:hover:text-white transition"
          >
            <span>{isExpanded ? 'Recolher Filtros' : 'Expandir Filtros'}</span>
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Quick Preset Buttons */}
      <div className="flex flex-wrap items-center gap-1.5 pt-3">
        <span className="text-xs font-semibold text-gray-500 dark:text-github-muted mr-1">
          Presets:
        </span>
        {presets.map((p) => (
          <button
            key={p.label}
            onClick={p.apply}
            className="text-xs px-2.5 py-1 rounded-lg border border-gray-200 dark:border-github-border bg-gray-50 dark:bg-github-dark hover:bg-gray-100 dark:hover:bg-github-border/50 text-gray-700 dark:text-github-text font-medium transition"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Expanded Filter Selectors */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-github-border/60 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Participante */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text mb-1.5">
              <User className="w-3.5 h-3.5 text-blue-500" /> Participante
            </label>
            <select
              value={filters.participant}
              onChange={(e) => onUpdateFilters({ participant: e.target.value })}
              className="w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg px-2.5 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 capitalize"
            >
              <option value="all">Todos os Participantes</option>
              {participants.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Tratamento */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text mb-1.5">
              <Cpu className="w-3.5 h-3.5 text-purple-500" /> Tratamento
            </label>
            <select
              value={filters.treatment}
              onChange={(e) =>
                onUpdateFilters({
                  treatment: e.target.value as 'all' | 'ai' | 'manual',
                  // Reset ai_model if selecting manual
                  ai_model: e.target.value === 'manual' ? 'manual' : filters.ai_model,
                })
              }
              className="w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg px-2.5 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">Todos (Com IA + Manual)</option>
              <option value="ai">Com Assistente de IA</option>
              <option value="manual">Manual (Sem IA)</option>
            </select>
          </div>

          {/* Modelo de IA */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text mb-1.5">
              <Bot className="w-3.5 h-3.5 text-emerald-500" /> Modelo de IA
            </label>
            <select
              value={filters.ai_model}
              onChange={(e) =>
                onUpdateFilters({
                  ai_model: e.target.value,
                  // If picking a specific AI model, ensure treatment is ai
                  treatment:
                    e.target.value === 'manual'
                      ? 'manual'
                      : e.target.value !== 'all'
                      ? 'ai'
                      : filters.treatment,
                })
              }
              className="w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg px-2.5 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">Todos os Modelos / Modos</option>
              <option value="gemini-flash-3.8">Gemini 3.8 Flash (Gabriel)</option>
              <option value="claude-sonnet-5">Claude Sonnet 5 (João)</option>
              <option value="manual">N/A (Apenas Manual)</option>
            </select>
          </div>

          {/* Kata */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text mb-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-500" /> Kata
            </label>
            <select
              value={filters.kata}
              onChange={(e) => onUpdateFilters({ kata: e.target.value })}
              className="w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg px-2.5 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">Todos os Katas (6 problemas)</option>
              {katas.map((k) => (
                <option key={k} value={k}>
                  {KATA_INFO[k]?.pretty || k}
                </option>
              ))}
            </select>
          </div>

          {/* Search Query */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text mb-1.5">
              <Search className="w-3.5 h-3.5 text-blue-500" /> Buscar Trial
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Ex: trial-gabriel-01..."
                value={filters.searchQuery}
                onChange={(e) => onUpdateFilters({ searchQuery: e.target.value })}
                className="w-full text-xs bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg pl-8 pr-2.5 py-2 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
