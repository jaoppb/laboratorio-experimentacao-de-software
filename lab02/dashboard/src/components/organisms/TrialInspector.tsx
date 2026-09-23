import React from 'react';
import {
  Target,
  ExternalLink,
  Clock,
  CheckCircle2,
  FileCode,
  Activity,
  Layers,
} from 'lucide-react';
import { UnifiedTrial } from '../../types/dataset';
import { formatDuration, formatNumber } from '../../utils/formatters';
import { Select } from '../atoms/Select';
import { Button } from '../atoms/Button';
import { TrialBadges } from '../molecules/TrialBadges';
import { MetricBox } from '../molecules/MetricBox';

interface TrialInspectorProps {
  trials: UnifiedTrial[];
  selectedTrial: UnifiedTrial | null;
  onSelectTrial: (trialId: string) => void;
}

export const TrialInspector: React.FC<TrialInspectorProps> = ({
  trials,
  selectedTrial,
  onSelectTrial,
}) => {
  if (!selectedTrial) return null;

  const trialOptions = trials.map((t) => ({
    value: t.trial_id,
    label: `${t.trial_id} (${t.participant} · ${t.treatment === 'ai' ? t.ai_model || 'IA' : 'manual'} · ${t.kata_title})`,
  }));

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-6 transition-all space-y-5">
      {/* Top Header & Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-100 dark:border-github-border/60">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Target className="w-4 h-4" />
            </div>
            <h2 className="font-bold text-base sm:text-lg text-gray-900 dark:text-white">
              Trial Inspector (Drill-Down Individual)
            </h2>
          </div>
          <p className="text-xs text-gray-500 dark:text-github-muted mt-1">
            Selecione qualquer trial para inspecionar medições de tempo, testes e métricas estáticas Radon/jscpd com link direto ao código.
          </p>
        </div>

        {/* Dropdown selector */}
        <div className="flex items-center gap-2 min-w-[280px]">
          <label className="text-xs font-semibold text-gray-500 dark:text-github-muted whitespace-nowrap">
            Selecionar Trial:
          </label>
          <Select
            value={selectedTrial.trial_id}
            onChange={onSelectTrial}
            options={trialOptions}
          />
        </div>
      </div>

      {/* Trial Overview Badge Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-gray-50 dark:bg-github-dark/50 border border-gray-100 dark:border-github-border/40 rounded-xl">
        <TrialBadges trial={selectedTrial} />

        <a
          href={selectedTrial.github_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button
            variant="primary"
            size="sm"
            icon={<ExternalLink className="w-3.5 h-3.5" />}
          >
            Ver Solução no GitHub
          </Button>
        </a>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricBox
          icon={<Clock className="w-3.5 h-3.5 text-blue-500" />}
          label="Tempo Registrado"
          value={formatDuration(selectedTrial.time_seconds)}
          subtitle={`Status: ${selectedTrial.status}`}
        />

        <MetricBox
          icon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
          label="Testes Aceitação"
          value={`${selectedTrial.passed_tests}/${selectedTrial.total_tests}`}
          valueColorClass="text-emerald-600 dark:text-emerald-400"
          subtitle="100% dos testes passaram"
        />

        <MetricBox
          icon={<Activity className="w-3.5 h-3.5 text-purple-500" />}
          label="CC Média (Radon)"
          value={formatNumber(selectedTrial.cc_avg, 1)}
          subtitle={`Rank CC: ${selectedTrial.cc_rank} · Máx: ${selectedTrial.cc_max}`}
        />

        <MetricBox
          icon={<Layers className="w-3.5 h-3.5 text-teal-500" />}
          label="Índice MI"
          value={formatNumber(selectedTrial.mi, 1)}
          valueColorClass="text-teal-600 dark:text-teal-400"
          subtitle={`Rank MI: ${selectedTrial.mi_rank} (Excelente)`}
        />

        <MetricBox
          icon={<FileCode className="w-3.5 h-3.5 text-amber-500" />}
          label="Linhas (LOC)"
          value={selectedTrial.loc}
          subtitle={`SLOC: ${selectedTrial.sloc} · Funções: ${selectedTrial.functions_count}`}
        />

        <MetricBox
          icon={<Layers className="w-3.5 h-3.5 text-red-500" />}
          label="Duplicação (jscpd)"
          value={`${formatNumber(selectedTrial.duplication_percentage, 1)}%`}
          subtitle={`${selectedTrial.duplicated_lines} linhas duplicadas`}
        />
      </div>
    </div>
  );
};
