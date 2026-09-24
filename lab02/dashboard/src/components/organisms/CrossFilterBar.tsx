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
} from 'lucide-react';
import { FilterState } from '../../types/dataset';
import { KATA_INFO } from '../../utils/formatters';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Input } from '../atoms/Input';
import { FilterSelect } from '../molecules/FilterSelect';
import { FilterPresets, PresetItem } from '../molecules/FilterPresets';

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

  const presets: PresetItem[] = [
    { label: 'Todos', apply: () => onResetFilters() },
    { label: 'Apenas IA', apply: () => onUpdateFilters({ treatment: 'ai', ai_model: 'all' }) },
    { label: 'Apenas Manual', apply: () => onUpdateFilters({ treatment: 'manual', ai_model: 'all' }) },
    { label: 'Gabriel', apply: () => onUpdateFilters({ participant: 'gabriel' }) },
    { label: 'João', apply: () => onUpdateFilters({ participant: 'joao' }) },
    { label: 'Marcela', apply: () => onUpdateFilters({ participant: 'marcela' }) },
    { label: 'Gemini 3.8', apply: () => onUpdateFilters({ ai_model: 'gemini-flash-3.8', treatment: 'ai' }) },
    { label: 'Claude 5', apply: () => onUpdateFilters({ ai_model: 'claude-sonnet-5', treatment: 'ai' }) },
    { label: 'GPT-4o', apply: () => onUpdateFilters({ ai_model: 'gpt-4o', treatment: 'ai' }) },
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
          <Badge variant="primary">
            {filteredCount} de {totalTrials} trials ({filterPct}%)
          </Badge>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          icon={isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        >
          {isExpanded ? 'Recolher Filtros' : 'Expandir Filtros'}
        </Button>
      </div>

      {/* Quick Presets */}
      <FilterPresets presets={presets} className="pt-3" />

      {/* Expanded Filter Controls */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-github-border/60 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <FilterSelect
            label="Participante"
            icon={<User className="w-3.5 h-3.5 text-blue-500" />}
            value={filters.participant}
            onChange={(val) => onUpdateFilters({ participant: val })}
            options={[
              { value: 'all', label: 'Todos os Participantes' },
              ...participants.map((p) => ({ value: p, label: p })),
            ]}
          />

          <FilterSelect
            label="Tratamento"
            icon={<Cpu className="w-3.5 h-3.5 text-purple-500" />}
            value={filters.treatment}
            onChange={(val) =>
              onUpdateFilters({
                treatment: val as 'all' | 'ai' | 'manual',
                ai_model: val === 'manual' ? 'manual' : filters.ai_model,
              })
            }
            options={[
              { value: 'all', label: 'Todos (Com IA + Manual)' },
              { value: 'ai', label: 'Com Assistente de IA' },
              { value: 'manual', label: 'Manual (Sem IA)' },
            ]}
          />

          <FilterSelect
            label="Modelo de IA"
            icon={<Bot className="w-3.5 h-3.5 text-emerald-500" />}
            value={filters.ai_model}
            onChange={(val) =>
              onUpdateFilters({
                ai_model: val,
                treatment:
                  val === 'manual'
                    ? 'manual'
                    : val !== 'all'
                    ? 'ai'
                    : filters.treatment,
              })
            }
            options={[
              { value: 'all', label: 'Todos os Modelos / Modos' },
              { value: 'gemini-flash-3.8', label: 'Gemini 3.8 Flash (Gabriel)' },
              { value: 'claude-sonnet-5', label: 'Claude Sonnet 5 (João)' },
              { value: 'gpt-4o', label: 'GPT-4o (Marcela)' },
              { value: 'manual', label: 'N/A (Apenas Manual)' },
            ]}
          />

          <FilterSelect
            label="Kata"
            icon={<Layers className="w-3.5 h-3.5 text-amber-500" />}
            value={filters.kata}
            onChange={(val) => onUpdateFilters({ kata: val })}
            options={[
              { value: 'all', label: 'Todos os Katas (6 problemas)' },
              ...katas.map((k) => ({ value: k, label: KATA_INFO[k]?.pretty || k })),
            ]}
          />

          <div className="space-y-1.5">
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text">
              <Search className="w-3.5 h-3.5 text-blue-500" />
              <span>Buscar Trial</span>
            </label>
            <Input
              value={filters.searchQuery}
              onChange={(val) => onUpdateFilters({ searchQuery: val })}
              icon={<Search className="w-3.5 h-3.5 text-gray-400" />}
              placeholder="Ex: trial-gabriel-01..."
            />
          </div>
        </div>
      )}
    </div>
  );
};
