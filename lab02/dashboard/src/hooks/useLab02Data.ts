import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FilterState,
  MetricsRow,
  SummaryStats,
  TrialRow,
  UnifiedTrial,
} from '../types/dataset';
import { parseCsv } from '../utils/csv';
import { getKataTitle, KATA_INFO } from '../utils/formatters';
import { computeSummaryStats } from '../utils/stats';

export const INITIAL_FILTERS: FilterState = {
  participant: 'all',
  treatment: 'all',
  kata: 'all',
  ai_model: 'all',
  searchQuery: '',
};

const REMOTE_TRIALS_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab02/dados/trials.csv';
const REMOTE_METRICS_URL =
  'https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab02/dados/metrics.csv';

async function fetchCsvWithFallback(fileName: string, remoteUrl: string): Promise<string> {
  const candidatePaths = [
    `./dados/${fileName}`,
    `../dados/${fileName}`,
    `/dados/${fileName}`,
    `dados/${fileName}`,
  ];

  for (const path of candidatePaths) {
    try {
      const res = await fetch(path);
      if (res.ok) {
        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('text/html')) {
          return await res.text();
        }
      }
    } catch {
      // try next
    }
  }

  // Fallback to GitHub raw
  const remoteRes = await fetch(remoteUrl);
  if (!remoteRes.ok) {
    throw new Error(`Falha ao carregar ${fileName} (HTTP ${remoteRes.status})`);
  }
  return await remoteRes.text();
}

export function useLab02Data() {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [allTrials, setAllTrials] = useState<UnifiedTrial[]>([]);
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [selectedTrialId, setSelectedTrialId] = useState<string>('');

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [trialsCsv, metricsCsv] = await Promise.all([
        fetchCsvWithFallback('trials.csv', REMOTE_TRIALS_URL),
        fetchCsvWithFallback('metrics.csv', REMOTE_METRICS_URL),
      ]);

      const rawTrials = parseCsv<Record<string, string>>(trialsCsv);
      const rawMetrics = parseCsv<Record<string, string>>(metricsCsv);

      const metricsMap = new Map<string, Record<string, string>>();
      rawMetrics.forEach((m) => {
        if (m.trial_id) {
          metricsMap.set(m.trial_id.trim(), m);
        }
      });

      const unified: UnifiedTrial[] = rawTrials.map((t) => {
        const trial_id = t.trial_id.trim();
        const m = metricsMap.get(trial_id) || {};
        const file = t.file || m.file || '';
        const treatment = (t.treatment || m.treatment || 'manual').toLowerCase() as 'ai' | 'manual';
        const kata = t.kata || m.kata || 'unknown';

        let ai_model: string | null = null;
        let ai_model_key = 'manual';

        if (treatment === 'ai') {
          if (file.includes('gemini-flash-3.8')) {
            ai_model = 'Gemini 3.8 Flash';
            ai_model_key = 'gemini-flash-3.8';
          } else if (file.includes('claude-sonnet-5')) {
            ai_model = 'Claude Sonnet 5';
            ai_model_key = 'claude-sonnet-5';
          } else {
            ai_model = 'Outro Assistente IA';
            ai_model_key = 'other-ai';
          }
        }

        const cleanFilePath = file.replace(/^(\.\/|\/)/, '');
        const github_url = `https://github.com/jaoppb/laboratorio-experimentacao-de-software/blob/main/${cleanFilePath}`;

        return {
          trial_id,
          participant: t.participant || m.participant || '',
          treatment,
          kata,
          kata_title: getKataTitle(kata),
          kata_num: KATA_INFO[kata]?.num || kata.split('-')[0] || '',
          file,
          ai_model,
          ai_model_key,
          time_seconds: parseFloat(t.time_seconds || '0') || 0,
          actual_elapsed_seconds: parseFloat(t.actual_elapsed_seconds || '0') || 0,
          censored: t.censored === 'True' || t.censored === 'true',
          passed_tests: parseInt(t.passed_tests || '0', 10) || 0,
          total_tests: parseInt(t.total_tests || '0', 10) || 0,
          failed_tests: parseInt(t.failed_tests || '0', 10) || 0,
          success_rate: parseFloat(t.success_rate || '0') || 0,
          timestamp: t.timestamp || '',
          status: t.status || m.status || 'completed',
          loc: parseInt(m.loc || '0', 10) || 0,
          sloc: parseInt(m.sloc || '0', 10) || 0,
          lloc: parseInt(m.lloc || '0', 10) || 0,
          comments: parseInt(m.comments || '0', 10) || 0,
          blank: parseInt(m.blank || '0', 10) || 0,
          functions_count: parseInt(m.functions_count || '0', 10) || 0,
          cc_avg: parseFloat(m.cc_avg || '0') || 0,
          cc_max: parseFloat(m.cc_max || '0') || 0,
          cc_min: parseFloat(m.cc_min || '0') || 0,
          cc_total: parseFloat(m.cc_total || '0') || 0,
          cc_rank: m.cc_rank || 'A',
          duplicated_lines: parseInt(m.duplicated_lines || '0', 10) || 0,
          duplication_percentage: parseFloat(m.duplication_percentage || '0') || 0,
          clones_count: parseInt(m.clones_count || '0', 10) || 0,
          duplication_tool: m.duplication_tool || 'jscpd',
          mi: parseFloat(m.mi || '0') || 0,
          mi_rank: m.mi_rank || 'A',
          github_url,
        };
      });

      setAllTrials(unified);
      if (unified.length > 0) {
        setSelectedTrialId(unified[0].trial_id);
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err?.message || 'Erro inesperado ao carregar dados do Lab 02.');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filtering
  const filteredTrials = useMemo(() => {
    return allTrials.filter((t) => {
      if (filters.participant !== 'all' && t.participant !== filters.participant) {
        return false;
      }
      if (filters.treatment !== 'all' && t.treatment !== filters.treatment) {
        return false;
      }
      if (filters.kata !== 'all' && t.kata !== filters.kata) {
        return false;
      }
      if (filters.ai_model !== 'all') {
        if (filters.ai_model === 'manual' && t.treatment !== 'manual') return false;
        if (filters.ai_model !== 'manual' && t.ai_model_key !== filters.ai_model) return false;
      }
      if (filters.searchQuery.trim() !== '') {
        const query = filters.searchQuery.toLowerCase();
        const matches =
          t.trial_id.toLowerCase().includes(query) ||
          t.participant.toLowerCase().includes(query) ||
          t.kata.toLowerCase().includes(query) ||
          t.kata_title.toLowerCase().includes(query) ||
          (t.ai_model && t.ai_model.toLowerCase().includes(query));
        if (!matches) return false;
      }
      return true;
    });
  }, [allTrials, filters]);

  // Summary statistics
  const stats: SummaryStats = useMemo(() => {
    return computeSummaryStats(allTrials, filteredTrials);
  }, [allTrials, filteredTrials]);

  const updateFilters = useCallback(
    (newFilters: Partial<FilterState> | ((prev: FilterState) => FilterState)) => {
      setFilters((prev) => (typeof newFilters === 'function' ? newFilters(prev) : { ...prev, ...newFilters }));
    },
    []
  );

  const resetFilters = useCallback(() => {
    setFilters(INITIAL_FILTERS);
  }, []);

  const selectedTrial = useMemo(() => {
    return allTrials.find((t) => t.trial_id === selectedTrialId) || allTrials[0] || null;
  }, [allTrials, selectedTrialId]);

  const participantsList = useMemo(() => {
    return Array.from(new Set(allTrials.map((t) => t.participant))).sort();
  }, [allTrials]);

  const katasList = useMemo(() => {
    return Array.from(new Set(allTrials.map((t) => t.kata))).sort();
  }, [allTrials]);

  const isFiltered =
    filters.participant !== 'all' ||
    filters.treatment !== 'all' ||
    filters.kata !== 'all' ||
    filters.ai_model !== 'all' ||
    filters.searchQuery !== '';

  return {
    isLoading,
    error,
    allTrials,
    filteredTrials,
    stats,
    filters,
    updateFilters,
    resetFilters,
    isFiltered,
    selectedTrial,
    selectedTrialId,
    setSelectedTrialId,
    participantsList,
    katasList,
    reload: loadData,
  };
}
