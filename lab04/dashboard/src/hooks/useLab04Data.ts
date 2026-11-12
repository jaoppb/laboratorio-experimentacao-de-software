import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  DashboardBundle,
  ExemploSimuladoRow,
  FilterState,
  RealPR,
} from '../types/dataset';
import { parseCsv } from '../utils/csv';

export const INITIAL_FILTERS: FilterState = {
  alpha: 0.05,
  selectedScenario: 'all',
  selectedTest: 'all',
  grupoFilter: 'all',
  searchQuery: '',
};

const REMOTE_BUNDLE_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab04/dados/dashboard_bundle.json';
const REMOTE_PRS_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab04/dados/reais/pr_merge_time.csv';
const REMOTE_EXEMPLO_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab04/dados/simulado/exemplo.csv';

async function fetchWithFallback(candidatePaths: string[], remoteUrl: string): Promise<string> {
  for (const path of candidatePaths) {
    try {
      const res = await fetch(path);
      if (res.ok) {
        const ct = res.headers.get('content-type') || '';
        if (!ct.includes('text/html')) {
          return await res.text();
        }
      }
    } catch {
      // try next candidate
    }
  }

  // Fallback to GitHub raw
  const remoteRes = await fetch(remoteUrl);
  if (!remoteRes.ok) {
    throw new Error(`Falha ao obter arquivo remoto (${remoteRes.status})`);
  }
  return await remoteRes.text();
}

export function useLab04Data() {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<DashboardBundle | null>(null);
  const [realPRs, setRealPRs] = useState<RealPR[]>([]);
  const [exemploRows, setExemploRows] = useState<ExemploSimuladoRow[]>([]);
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [bundleRaw, prsRaw, exemploRaw] = await Promise.all([
        fetchWithFallback(
          [
            './dados/dashboard_bundle.json',
            '../dados/dashboard_bundle.json',
            '/lab04/dados/dashboard_bundle.json',
            '/dados/dashboard_bundle.json',
            'dados/dashboard_bundle.json',
          ],
          REMOTE_BUNDLE_URL
        ),
        fetchWithFallback(
          [
            './dados/reais/pr_merge_time.csv',
            '../dados/reais/pr_merge_time.csv',
            '/lab04/dados/reais/pr_merge_time.csv',
            '/dados/reais/pr_merge_time.csv',
            './dados/pr_merge_time.csv',
            '../dados/pr_merge_time.csv',
            '/dados/pr_merge_time.csv',
            'dados/reais/pr_merge_time.csv',
          ],
          REMOTE_PRS_URL
        ),
        fetchWithFallback(
          [
            './dados/simulado/exemplo.csv',
            '../dados/simulado/exemplo.csv',
            '/lab04/dados/simulado/exemplo.csv',
            '/dados/simulado/exemplo.csv',
            './dados/exemplo.csv',
            '../dados/exemplo.csv',
            '/dados/exemplo.csv',
            'dados/simulado/exemplo.csv',
          ],
          REMOTE_EXEMPLO_URL
        ),
      ]);

      const parsedBundle = JSON.parse(bundleRaw) as DashboardBundle;
      const rawPRs = parseCsv<Record<string, string>>(prsRaw);
      const parsedPRs: RealPR[] = rawPRs
        .map((row) => {
          const pr_num = parseInt(row.pr_number || '0', 10);
          const repo = row.repo || 'tailwindlabs/tailwindcss';
          const tempo = parseFloat(row.tempo_merge_horas || '0');
          return {
            repo,
            pr_number: pr_num,
            grupo: (row.grupo === 'com_bot' ? 'com_bot' : 'sem_bot') as 'com_bot' | 'sem_bot',
            tempo_merge_horas: Number.isFinite(tempo) ? tempo : 0,
            url: row.url || `https://github.com/${repo}/pull/${pr_num}`,
          };
        })
        .filter((pr) => pr.pr_number > 0);

      const rawExemplo = parseCsv<Record<string, string>>(exemploRaw);
      const parsedExemplo: ExemploSimuladoRow[] = rawExemplo.map((row) => {
        const val = parseFloat(row.valor || '0');
        return {
          grupo: (row.grupo === 'com_bot' ? 'com_bot' : 'sem_bot') as 'com_bot' | 'sem_bot',
          valor: Number.isFinite(val) ? val : 0,
        };
      });

      setBundle(parsedBundle);
      setRealPRs(parsedPRs);
      setExemploRows(parsedExemplo);
      setIsLoading(false);
    } catch (err: any) {
      setError(err?.message || 'Erro inesperado ao carregar dados do Lab 04.');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateFilters = useCallback(
    (newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => {
      setFilters((prev) => (typeof newFilters === 'function' ? newFilters(prev) : { ...prev, ...newFilters }));
    },
    []
  );

  const resetFilters = useCallback(() => {
    setFilters(INITIAL_FILTERS);
  }, []);

  const isFiltered =
    filters.alpha !== 0.05 ||
    filters.selectedScenario !== 'all' ||
    filters.selectedTest !== 'all' ||
    filters.grupoFilter !== 'all' ||
    filters.searchQuery.trim() !== '';

  const filteredPRs = useMemo(() => {
    return realPRs.filter((pr) => {
      if (filters.grupoFilter !== 'all' && pr.grupo !== filters.grupoFilter) {
        return false;
      }
      if (filters.searchQuery.trim() !== '') {
        const query = filters.searchQuery.toLowerCase();
        const matches =
          String(pr.pr_number).includes(query) ||
          pr.grupo.toLowerCase().includes(query) ||
          pr.repo.toLowerCase().includes(query);
        if (!matches) return false;
      }
      return true;
    });
  }, [realPRs, filters.grupoFilter, filters.searchQuery]);

  return {
    isLoading,
    error,
    bundle,
    realPRs,
    filteredPRs,
    exemploRows,
    filters,
    updateFilters,
    resetFilters,
    isFiltered,
    reload: loadData,
  };
}
