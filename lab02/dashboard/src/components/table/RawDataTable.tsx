import React, { useState, useMemo } from 'react';
import {
  Table,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  ExternalLink,
  Target,
} from 'lucide-react';
import { UnifiedTrial } from '../../types/dataset';
import { formatDuration, formatNumber } from '../../utils/formatters';

interface RawDataTableProps {
  trials: UnifiedTrial[];
  onSelectTrial: (trialId: string) => void;
  selectedTrialId: string;
}

type SortField =
  | 'trial_id'
  | 'participant'
  | 'treatment'
  | 'kata'
  | 'ai_model'
  | 'time_seconds'
  | 'loc'
  | 'cc_avg'
  | 'mi'
  | 'duplication_percentage';

export const RawDataTable: React.FC<RawDataTableProps> = ({
  trials,
  onSelectTrial,
  selectedTrialId,
}) => {
  const [sortField, setSortField] = useState<SortField>('trial_id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedTrials = useMemo(() => {
    return [...trials].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
  }, [trials, sortField, sortDirection]);

  const exportCsv = () => {
    if (sortedTrials.length === 0) return;

    const headers = [
      'trial_id',
      'participant',
      'treatment',
      'ai_model',
      'kata',
      'time_seconds',
      'passed_tests',
      'total_tests',
      'loc',
      'cc_avg',
      'cc_max',
      'cc_rank',
      'mi',
      'mi_rank',
      'duplication_percentage',
      'file',
    ];

    const csvRows = [
      headers.join(','),
      ...sortedTrials.map((t) =>
        [
          t.trial_id,
          t.participant,
          t.treatment,
          t.ai_model || 'manual',
          t.kata,
          t.time_seconds,
          t.passed_tests,
          t.total_tests,
          t.loc,
          t.cc_avg,
          t.cc_max,
          t.cc_rank,
          t.mi,
          t.mi_rank,
          t.duplication_percentage,
          `"${t.file}"`,
        ].join(',')
      ),
    ];

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'lab02_unified_trials.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-gray-400 opacity-60" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="w-3 h-3 text-blue-500" />
    ) : (
      <ArrowDown className="w-3 h-3 text-blue-500" />
    );
  };

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 transition-all space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-100 dark:border-github-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <Table className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-bold text-base text-gray-900 dark:text-white">
              Tabela de Dados Brutos Unificados
            </h2>
            <p className="text-xs text-gray-500 dark:text-github-muted">
              {trials.length} trials (trials.csv unificado com metrics.csv via trial_id)
            </p>
          </div>
        </div>

        <button
          onClick={exportCsv}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-github-text bg-gray-50 dark:bg-github-dark hover:bg-gray-100 dark:hover:bg-github-border/50 border border-gray-200 dark:border-github-border rounded-lg transition self-start sm:self-auto"
        >
          <Download className="w-3.5 h-3.5" />
          Exportar CSV Unificado
        </button>
      </div>

      <div className="overflow-x-auto -mx-4 sm:mx-0">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-gray-200 dark:border-github-border text-gray-500 dark:text-github-muted font-semibold">
              <th
                onClick={() => handleSort('trial_id')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Trial ID {renderSortIcon('trial_id')}
                </div>
              </th>
              <th
                onClick={() => handleSort('participant')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Participante {renderSortIcon('participant')}
                </div>
              </th>
              <th
                onClick={() => handleSort('treatment')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Tratamento {renderSortIcon('treatment')}
                </div>
              </th>
              <th
                onClick={() => handleSort('ai_model')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Modelo IA {renderSortIcon('ai_model')}
                </div>
              </th>
              <th
                onClick={() => handleSort('kata')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Kata {renderSortIcon('kata')}
                </div>
              </th>
              <th
                onClick={() => handleSort('time_seconds')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Tempo {renderSortIcon('time_seconds')}
                </div>
              </th>
              <th className="py-2.5 px-3">Testes</th>
              <th
                onClick={() => handleSort('loc')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  LOC {renderSortIcon('loc')}
                </div>
              </th>
              <th
                onClick={() => handleSort('cc_avg')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  CC Média {renderSortIcon('cc_avg')}
                </div>
              </th>
              <th
                onClick={() => handleSort('mi')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  MI {renderSortIcon('mi')}
                </div>
              </th>
              <th
                onClick={() => handleSort('duplication_percentage')}
                className="py-2.5 px-3 cursor-pointer hover:text-gray-900 dark:hover:text-white"
              >
                <div className="flex items-center gap-1">
                  Dup % {renderSortIcon('duplication_percentage')}
                </div>
              </th>
              <th className="py-2.5 px-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-github-border/40">
            {sortedTrials.map((t) => {
              const isSelected = t.trial_id === selectedTrialId;
              return (
                <tr
                  key={t.trial_id}
                  className={`transition hover:bg-gray-50 dark:hover:bg-github-darker/60 ${
                    isSelected ? 'bg-blue-50/70 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 font-mono font-medium text-gray-900 dark:text-white">
                    {t.trial_id}
                  </td>
                  <td className="py-2.5 px-3 capitalize text-gray-700 dark:text-github-text">
                    {t.participant}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        t.treatment === 'ai'
                          ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                          : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                      }`}
                    >
                      {t.treatment === 'ai' ? 'IA' : 'Manual'}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-gray-600 dark:text-github-muted">
                    {t.ai_model || '—'}
                  </td>
                  <td className="py-2.5 px-3 text-gray-900 dark:text-white font-medium">
                    {t.kata_title}
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-gray-900 dark:text-white">
                    {formatDuration(t.time_seconds, true)}
                  </td>
                  <td className="py-2.5 px-3 text-emerald-600 dark:text-emerald-400 font-medium">
                    {t.passed_tests}/{t.total_tests}
                  </td>
                  <td className="py-2.5 px-3 text-gray-700 dark:text-github-text">
                    {t.loc}
                  </td>
                  <td className="py-2.5 px-3 text-gray-700 dark:text-github-text font-medium">
                    {formatNumber(t.cc_avg, 1)} ({t.cc_rank})
                  </td>
                  <td className="py-2.5 px-3 text-teal-600 dark:text-teal-400 font-medium">
                    {formatNumber(t.mi, 1)}
                  </td>
                  <td className="py-2.5 px-3 text-gray-700 dark:text-github-text">
                    {formatNumber(t.duplication_percentage, 1)}%
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onSelectTrial(t.trial_id)}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-github-border text-gray-600 dark:text-github-muted hover:text-blue-600 dark:hover:text-blue-400 transition"
                        title="Inspecionar no Trial Inspector"
                      >
                        <Target className="w-3.5 h-3.5" />
                      </button>
                      <a
                        href={t.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-github-border text-gray-600 dark:text-github-muted hover:text-gray-900 dark:hover:text-white transition"
                        title="Ver Código no GitHub"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
