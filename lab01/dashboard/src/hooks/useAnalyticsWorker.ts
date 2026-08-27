import { useEffect, useRef, useState, useCallback } from 'react';
import {
  BenchmarkReport,
  CorrelationMatrix,
  FilterState,
  RQStats,
} from '../types/dataset';
import { WorkerIncomingMessage, WorkerOutgoingMessage } from '../types/worker';

export const INITIAL_FILTERS: FilterState = {
  ageMinYears: 0,
  ageMaxYears: 20,
  minMergedPRs: 0,
  minReleases: 0,
  maxDaysSinceUpdate: 3650,
  selectedLanguages: [],
  minTotalIssues: 0,
  minClosedIssuesRatio: 0,
  maxClosedIssuesRatio: 1.0,
  searchQuery: '',
};

const REMOTE_PARQUET_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab01/dados/unified_sample.parquet';

export function useAnalyticsWorker() {
  const workerRef = useRef<Worker | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [progressMsg, setProgressMsg] = useState<string>('Iniciando Analytics Engine...');
  const [error, setError] = useState<string | null>(null);

  const [totalRows, setTotalRows] = useState<number>(0);
  const [topRepos, setTopRepos] = useState<string[]>([]);
  const [languages, setLanguages] = useState<{ name: string; count: number }[]>([]);
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([]);

  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [stats, setStats] = useState<RQStats | null>(null);
  const [correlation, setCorrelation] = useState<CorrelationMatrix | null>(null);
  const [filteredCount, setFilteredCount] = useState<number>(0);
  const [computeTimeMs, setComputeTimeMs] = useState<number>(0);

  const [benchmark, setBenchmark] = useState<BenchmarkReport | null>(null);
  const [inspectingRepoName, setInspectingRepoName] = useState<string>('');
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Initialize Worker
  useEffect(() => {
    const worker = new Worker(
      new URL('../worker/analytics.worker.ts', import.meta.url),
      { type: 'module' }
    );
    workerRef.current = worker;

    worker.onmessage = (e: MessageEvent<WorkerOutgoingMessage>) => {
      const { type, payload } = e.data;

      switch (type) {
        case 'LOAD_PROGRESS':
          setProgressMsg(payload.message);
          break;
        case 'LOAD_SUCCESS':
          setTotalRows(payload.totalRows);
          setTopRepos(payload.topRepos);
          setLanguages(payload.languages);
          setAvailableMetrics(payload.availableMetrics);
          setIsLoading(false);
          // Auto trigger initial filter computation and inspect top 1 repo from dataset
          worker.postMessage({
            type: 'APPLY_FILTER',
            payload: { filter: INITIAL_FILTERS },
          });
          worker.postMessage({
            type: 'INSPECT_REPO',
            payload: { repoName: payload.topRepos[0] || 'facebook/react' },
          });
          break;
        case 'LOAD_ERROR':
          setError(payload.error);
          setIsLoading(false);
          break;
        case 'FILTER_SUCCESS':
          setStats(payload.stats);
          setCorrelation(payload.correlation);
          setFilteredCount(payload.filteredCount);
          setComputeTimeMs(payload.executionTimeMs);
          break;
        case 'INSPECT_SUCCESS':
          setBenchmark(payload.benchmark);
          break;
        case 'SUGGESTIONS_SUCCESS':
          setSuggestions(payload.results);
          break;
      }
    };

    // Load Parquet file (try local first, fallback to GitHub)
    async function loadDataset() {
      try {
        setProgressMsg('Buscando arquivo Parquet (unified_sample.parquet)...');
        let res: Response | null = null;

        // Try candidate paths
        const localCandidates = [
          '../dados/unified_sample.parquet',
          './dados/unified_sample.parquet',
          '/dados/unified_sample.parquet',
        ];

        for (const path of localCandidates) {
          try {
            const check = await fetch(path);
            if (check.ok && check.headers.get('content-type') !== 'text/html') {
              res = check;
              break;
            }
          } catch {
            // ignore and try next
          }
        }

        if (!res) {
          setProgressMsg('Baixando amostra de 100k repositórios do GitHub...');
          res = await fetch(REMOTE_PARQUET_URL);
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ao carregar Parquet.`);
        }

        const buffer = await res.arrayBuffer();
        worker.postMessage(
          {
            type: 'LOAD_DATA',
            payload: { buffer },
          },
          [buffer]
        );
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar dataset');
        setIsLoading(false);
      }
    }

    loadDataset();

    return () => {
      worker.terminate();
    };
  }, []);

  // Debounced filter dispatch to worker
  const filterTimeoutRef = useRef<number | null>(null);
  const updateFilters = useCallback((newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => {
    setFilters((prev) => {
      const next = typeof newFilters === 'function' ? newFilters(prev) : { ...prev, ...newFilters };
      if (filterTimeoutRef.current) clearTimeout(filterTimeoutRef.current);
      filterTimeoutRef.current = window.setTimeout(() => {
        if (workerRef.current) {
          workerRef.current.postMessage({
            type: 'APPLY_FILTER',
            payload: { filter: next },
          });
        }
      }, 40);
      return next;
    });
  }, []);

  const inspectRepo = useCallback((repoName: string) => {
    setInspectingRepoName(repoName);
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'INSPECT_REPO',
        payload: { repoName },
      });
    }
  }, []);

  const searchSuggestions = useCallback((query: string) => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'SEARCH_SUGGESTIONS',
        payload: { query, limit: 12 },
      });
    }
  }, []);

  return {
    isLoading,
    progressMsg,
    error,
    totalRows,
    topRepos,
    languages,
    availableMetrics,
    filters,
    updateFilters,
    stats,
    correlation,
    filteredCount,
    computeTimeMs,
    benchmark,
    inspectingRepoName,
    inspectRepo,
    suggestions,
    searchSuggestions,
  };
}
