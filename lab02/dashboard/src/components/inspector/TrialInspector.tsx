import React from 'react';
import {
  Target,
  ExternalLink,
  Clock,
  CheckCircle2,
  FileCode,
  Activity,
  Layers,
  Sparkles,
  User,
} from 'lucide-react';
import { UnifiedTrial } from '../../types/dataset';
import { formatDuration, formatNumber } from '../../utils/formatters';

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
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-gray-500 dark:text-github-muted whitespace-nowrap">
            Selecionar Trial:
          </label>
          <select
            value={selectedTrial.trial_id}
            onChange={(e) => onSelectTrial(e.target.value)}
            className="text-xs font-medium bg-gray-50 dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-lg px-3 py-2 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            {trials.map((t) => (
              <option key={t.trial_id} value={t.trial_id}>
                {t.trial_id} ({t.participant} · {t.treatment === 'ai' ? t.ai_model || 'IA' : 'manual'} · {t.kata_title})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Trial Overview Badge Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-gray-50 dark:bg-github-dark/50 border border-gray-100 dark:border-github-border/40 rounded-xl">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono font-bold text-sm text-gray-900 dark:text-white">
            {selectedTrial.trial_id}
          </span>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
              selectedTrial.treatment === 'ai'
                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
            }`}
          >
            {selectedTrial.treatment === 'ai' ? 'Tratamento: Com IA' : 'Tratamento: Manual'}
          </span>
          {selectedTrial.ai_model && (
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              {selectedTrial.ai_model}
            </span>
          )}
          <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-gray-200 dark:bg-github-border text-gray-700 dark:text-github-text flex items-center gap-1">
            <User className="w-3 h-3" />
            {selectedTrial.participant}
          </span>
          <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-gray-200 dark:bg-github-border text-gray-700 dark:text-github-text">
            {selectedTrial.kata_title}
          </span>
        </div>

        <a
          href={selectedTrial.github_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500 rounded-lg shadow-sm transition"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Ver Solução no GitHub
        </a>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Tempo */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <Clock className="w-3.5 h-3.5 text-blue-500" /> Tempo Registrado
          </div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {formatDuration(selectedTrial.time_seconds)}
          </div>
          <div className="text-[10px] text-gray-400 dark:text-github-muted mt-0.5">
            Status: {selectedTrial.status}
          </div>
        </div>

        {/* Testes */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Testes Aceitação
          </div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
            {selectedTrial.passed_tests}/{selectedTrial.total_tests}
          </div>
          <div className="text-[10px] text-emerald-600 dark:text-emerald-500 mt-0.5 font-medium">
            100% dos testes passaram
          </div>
        </div>

        {/* Complexidade Ciclomática */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <Activity className="w-3.5 h-3.5 text-purple-500" /> CC Média (Radon)
          </div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {formatNumber(selectedTrial.cc_avg, 1)}
          </div>
          <div className="text-[10px] text-gray-500 dark:text-github-muted mt-0.5">
            Rank CC: <b>{selectedTrial.cc_rank}</b> · Máx: {selectedTrial.cc_max}
          </div>
        </div>

        {/* Manutenibilidade MI */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <Layers className="w-3.5 h-3.5 text-teal-500" /> Índice MI
          </div>
          <div className="text-lg font-bold text-teal-600 dark:text-teal-400">
            {formatNumber(selectedTrial.mi, 1)}
          </div>
          <div className="text-[10px] text-gray-500 dark:text-github-muted mt-0.5">
            Rank MI: <b>{selectedTrial.mi_rank}</b> (Excelente)
          </div>
        </div>

        {/* LOC */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <FileCode className="w-3.5 h-3.5 text-amber-500" /> Linhas (LOC)
          </div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {selectedTrial.loc}
          </div>
          <div className="text-[10px] text-gray-500 dark:text-github-muted mt-0.5">
            SLOC: {selectedTrial.sloc} · Funções: {selectedTrial.functions_count}
          </div>
        </div>

        {/* Duplicação */}
        <div className="p-3 bg-white dark:bg-github-dark border border-gray-200 dark:border-github-border rounded-xl">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-github-muted mb-1 font-semibold">
            <Layers className="w-3.5 h-3.5 text-red-500" /> Duplicação (jscpd)
          </div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {formatNumber(selectedTrial.duplication_percentage, 1)}%
          </div>
          <div className="text-[10px] text-gray-500 dark:text-github-muted mt-0.5">
            {selectedTrial.duplicated_lines} linhas duplicadas
          </div>
        </div>
      </div>
    </div>
  );
};
