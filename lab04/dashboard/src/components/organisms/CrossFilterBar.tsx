import React, { useState } from 'react';
import {
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Layers,
  Scale,
  GitPullRequest,
  CheckCircle2,
} from 'lucide-react';
import { FilterState } from '../../types/dataset';
import { ROTULO_SITUACAO } from '../../utils/formatters';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { SegmentedControl } from '../atoms/SegmentedControl';
import { FilterSelect } from '../molecules/FilterSelect';
import { FilterPresets, PresetItem } from '../molecules/FilterPresets';

interface CrossFilterBarProps {
  filters: FilterState;
  onUpdateFilters: (newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => void;
  onResetFilters: () => void;
  isFiltered: boolean;
}

export const CrossFilterBar: React.FC<CrossFilterBarProps> = ({
  filters,
  onUpdateFilters,
  onResetFilters,
  isFiltered,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const presets: PresetItem[] = [
    { label: 'Padrão (α = 0,05)', apply: () => onResetFilters() },
    { label: 'Sensibilidade (α = 0,01)', apply: () => onUpdateFilters({ alpha: 0.01 }) },
    { label: 'Cenário com_bot', apply: () => onUpdateFilters({ selectedScenario: 'com_bot' }) },
    { label: 'Assimetria Extrema', apply: () => onUpdateFilters({ selectedScenario: 'assimetria_extrema' }) },
    { label: 'Apenas Welch', apply: () => onUpdateFilters({ selectedTest: 'welch' }) },
    { label: 'Apenas Mann-Whitney', apply: () => onUpdateFilters({ selectedTest: 'mannwhitney' }) },
  ];

  const scenarioOptions = [
    { value: 'all', label: 'Todas as Situações Simuladas' },
    { value: 'com_bot', label: ROTULO_SITUACAO['com_bot'] },
    { value: 'sem_bot', label: ROTULO_SITUACAO['sem_bot'] },
    { value: 'referencia', label: ROTULO_SITUACAO['referencia'] },
    { value: 'n_pequeno', label: ROTULO_SITUACAO['n_pequeno'] },
    { value: 'assimetria_extrema', label: ROTULO_SITUACAO['assimetria_extrema'] },
    { value: 'outliers', label: ROTULO_SITUACAO['outliers'] },
  ];

  const testOptions = [
    { value: 'all', label: 'Ambos os Testes (Welch + Mann-Whitney)' },
    { value: 'welch', label: 'Apenas t de Welch (Paramétrico)' },
    { value: 'mannwhitney', label: 'Apenas Mann-Whitney (Não Paramétrico)' },
  ];

  const grupoOptions = [
    { value: 'all', label: 'Todos os PRs Reais (com_bot + sem_bot)' },
    { value: 'com_bot', label: 'Apenas com_bot (CodeRabbit)' },
    { value: 'sem_bot', label: 'Apenas sem_bot (Controle)' },
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
            Painel de Filtros e Parâmetros Interativos
          </span>
          <Badge variant={filters.alpha === 0.05 ? 'primary' : 'warning'}>
            α = {filters.alpha} {filters.alpha === 0.01 && '(Sensibilidade)'}
          </Badge>
          {filters.selectedScenario !== 'all' && (
            <Badge variant="purple">{filters.selectedScenario}</Badge>
          )}
          {filters.selectedTest !== 'all' && (
            <Badge variant={filters.selectedTest === 'welch' ? 'welch' : 'mannwhitney'}>
              {filters.selectedTest}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isFiltered && (
            <Button
              variant="outline"
              size="sm"
              onClick={onResetFilters}
              className="text-amber-700 dark:text-amber-300"
            >
              Resetar
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            icon={isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          >
            {isExpanded ? 'Recolher' : 'Expandir'}
          </Button>
        </div>
      </div>

      {/* Quick Presets */}
      <FilterPresets presets={presets} className="pt-3" />

      {/* Expanded Filter Controls */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-github-border/60 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Seletor de Nível α */}
          <div className="space-y-1.5">
            <label className="flex items-center gap-1.5 text-xs font-bold text-gray-700 dark:text-github-text">
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
              <span>Nível de Significância (α)</span>
            </label>
            <SegmentedControl<'0.05' | '0.01'>
              value={String(filters.alpha) as '0.05' | '0.01'}
              onChange={(val) => onUpdateFilters({ alpha: val === '0.01' ? 0.01 : 0.05 })}
              options={[
                { value: '0.05', label: 'α = 0,05 (Padrão 5%)' },
                { value: '0.01', label: 'α = 0,01 (Estrito 1%)' },
              ]}
              className="w-full"
            />
          </div>

          {/* Filtro de Situações Simuladas */}
          <FilterSelect
            label="Situação Simulada (Q1, Q2, Q3)"
            icon={<Layers className="w-3.5 h-3.5 text-purple-500" />}
            value={filters.selectedScenario}
            onChange={(val) => onUpdateFilters({ selectedScenario: val })}
            options={scenarioOptions}
          />

          {/* Destaque por Teste */}
          <FilterSelect
            label="Destaque de Teste"
            icon={<Scale className="w-3.5 h-3.5 text-emerald-500" />}
            value={filters.selectedTest}
            onChange={(val) => onUpdateFilters({ selectedTest: val as any })}
            options={testOptions}
          />

          {/* Filtro de Dados Reais */}
          <FilterSelect
            label="Grupo de PRs Reais (Seção 6)"
            icon={<GitPullRequest className="w-3.5 h-3.5 text-teal-500" />}
            value={filters.grupoFilter}
            onChange={(val) => onUpdateFilters({ grupoFilter: val as any })}
            options={grupoOptions}
          />
        </div>
      )}
    </div>
  );
};
