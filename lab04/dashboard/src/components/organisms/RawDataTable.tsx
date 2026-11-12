import React, { useMemo, useState } from 'react';
import { Table, Download, ExternalLink, Search, Bot, User } from 'lucide-react';
import { RealPR } from '../../types/dataset';
import { formatHours, formatNumber } from '../../utils/formatters';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Input } from '../atoms/Input';
import { TableHeaderCell } from '../molecules/TableHeaderCell';

interface RawDataTableProps {
  prs: RealPR[];
  grupoFilter?: 'all' | 'com_bot' | 'sem_bot';
  onGrupoFilterChange?: (grupo: 'all' | 'com_bot' | 'sem_bot') => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

type SortField = 'pr_number' | 'grupo' | 'tempo_merge_horas';

export const RawDataTable: React.FC<RawDataTableProps> = ({
  prs,
  grupoFilter: externalGrupo,
  onGrupoFilterChange,
  searchQuery: externalSearch,
  onSearchChange,
}) => {
  const [sortField, setSortField] = useState<SortField>('tempo_merge_horas');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [internalSearch, setInternalSearch] = useState<string>('');
  const [internalGrupo, setInternalGrupo] = useState<'all' | 'com_bot' | 'sem_bot'>('all');

  const activeGrupo = externalGrupo !== undefined ? externalGrupo : internalGrupo;
  const activeSearch = externalSearch !== undefined ? externalSearch : internalSearch;

  const setGrupo = (g: 'all' | 'com_bot' | 'sem_bot') => {
    if (onGrupoFilterChange) {
      onGrupoFilterChange(g);
    } else {
      setInternalGrupo(g);
    }
  };

  const setSearch = (q: string) => {
    if (onSearchChange) {
      onSearchChange(q);
    } else {
      setInternalSearch(q);
    }
  };

  const comBotCount = useMemo(() => prs.filter((p) => p.grupo === 'com_bot').length, [prs]);
  const semBotCount = useMemo(() => prs.filter((p) => p.grupo === 'sem_bot').length, [prs]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedPRs = useMemo(() => {
    let result = prs;
    if (activeGrupo !== 'all') {
      result = result.filter((p) => p.grupo === activeGrupo);
    }
    if (activeSearch.trim() !== '') {
      const q = activeSearch.toLowerCase();
      result = result.filter(
        (p) =>
          String(p.pr_number).includes(q) ||
          p.grupo.toLowerCase().includes(q) ||
          p.repo.toLowerCase().includes(q)
      );
    }

    return [...result].sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }
      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
  }, [prs, activeGrupo, activeSearch, sortField, sortDirection]);

  const exportCsv = () => {
    if (filteredAndSortedPRs.length === 0) return;
    const headers = ['repo', 'pr_number', 'grupo', 'tempo_merge_horas', 'url'];
    const rows = filteredAndSortedPRs.map((p) => [
      p.repo,
      p.pr_number,
      p.grupo,
      p.tempo_merge_horas,
      p.url,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'pr_merge_time_filtered.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-5 space-y-4">
      {/* Table Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-gray-100 dark:border-github-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <Table className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm sm:text-base text-gray-900 dark:text-white">
              Inspetor de Pull Requests Reais ({filteredAndSortedPRs.length} de {prs.length})
            </h3>
            <p className="text-xs text-gray-500 dark:text-github-muted">
              Dados empíricos coletados via API do GitHub para o repositório tailwindlabs/tailwindcss
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={exportCsv}
            icon={<Download className="w-3.5 h-3.5" />}
          >
            Exportar CSV
          </Button>
        </div>
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setGrupo('all')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
              activeGrupo === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-github-dark text-gray-600 dark:text-github-muted hover:bg-gray-200'
            }`}
          >
            Todos ({prs.length})
          </button>
          <button
            type="button"
            onClick={() => setGrupo('com_bot')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
              activeGrupo === 'com_bot'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 dark:bg-github-dark text-gray-600 dark:text-github-muted hover:bg-gray-200'
            }`}
          >
            com_bot ({comBotCount})
          </button>
          <button
            type="button"
            onClick={() => setGrupo('sem_bot')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
              activeGrupo === 'sem_bot'
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-100 dark:bg-github-dark text-gray-600 dark:text-github-muted hover:bg-gray-200'
            }`}
          >
            sem_bot ({semBotCount})
          </button>
        </div>

        <div className="w-full sm:w-64">
          <Input
            value={activeSearch}
            onChange={setSearch}
            placeholder="Buscar por PR # ou grupo..."
            icon={<Search className="w-3.5 h-3.5" />}
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-gray-200 dark:border-github-border rounded-lg">
        <table className="w-full text-left text-xs text-gray-700 dark:text-github-text">
          <thead className="bg-gray-50 dark:bg-github-dark border-b border-gray-200 dark:border-github-border text-gray-600 dark:text-github-muted uppercase font-semibold">
            <tr>
              <TableHeaderCell
                field="pr_number"
                currentSortField={sortField}
                sortDirection={sortDirection}
                onSort={handleSort}
              >
                PR #
              </TableHeaderCell>
              <th className="py-2.5 px-3">Repositório</th>
              <TableHeaderCell
                field="grupo"
                currentSortField={sortField}
                sortDirection={sortDirection}
                onSort={handleSort}
              >
                Grupo
              </TableHeaderCell>
              <TableHeaderCell
                field="tempo_merge_horas"
                currentSortField={sortField}
                sortDirection={sortDirection}
                onSort={handleSort}
              >
                Tempo até o Merge
              </TableHeaderCell>
              <th className="py-2.5 px-3 text-right">Link GitHub</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-github-border/60 font-mono">
            {filteredAndSortedPRs.map((pr) => (
              <tr
                key={pr.pr_number}
                className="hover:bg-gray-50/80 dark:hover:bg-github-dark/50 transition-colors"
              >
                <td className="py-2 px-3 font-bold text-gray-900 dark:text-white">
                  #{pr.pr_number}
                </td>
                <td className="py-2 px-3 font-sans text-gray-500 dark:text-github-muted">
                  {pr.repo}
                </td>
                <td className="py-2 px-3 font-sans">
                  {pr.grupo === 'com_bot' ? (
                    <Badge variant="purple" icon={<Bot className="w-3 h-3" />}>
                      com_bot (CodeRabbit)
                    </Badge>
                  ) : (
                    <Badge variant="success" icon={<User className="w-3 h-3" />}>
                      sem_bot (Humano)
                    </Badge>
                  )}
                </td>
                <td className="py-2 px-3 font-bold text-gray-900 dark:text-white">
                  {formatHours(pr.tempo_merge_horas)}
                </td>
                <td className="py-2 px-3 text-right font-sans">
                  <a
                    href={pr.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                    title={`Abrir PR #${pr.pr_number} no GitHub`}
                  >
                    <span>Abrir PR</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </td>
              </tr>
            ))}
            {filteredAndSortedPRs.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-500 font-sans">
                  Nenhum PR encontrado para os filtros aplicados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
