import { parquetReadObjects } from 'hyparquet';
import {
  BenchmarkReport,
  CorrelationMatrix,
  FilterState,
  PercentileResult,
  RepoRow,
  RQStats,
} from '../types/dataset';
import { WorkerIncomingMessage, WorkerOutgoingMessage } from '../types/worker';
import { fmt, fmtDec, fmtPct } from '../utils/formatters';
import {
  calculatePercentile,
  getPercentileTier,
  histogramCounts,
  mean,
  median,
  quantile,
  sortNums,
  spearmanCorrelation,
} from '../utils/stats';

let datasetRows: RepoRow[] = [];
let repoIndex = new Map<string, number>();
let repoNamesList: string[] = [];

// Pre-sorted global distributions for fast percentile rank calculation
let sortedAgeDays: number[] = [];
let sortedMergedPRs: number[] = [];
let sortedReleases: number[] = [];
let sortedUpdateDays: number[] = [];
let sortedTotalIssues: number[] = [];
let sortedClosedIssueRatios: number[] = [];
let sortedStars: number[] = [];
let sortedForks: number[] = [];

const YEAR_EDGES = Array.from({ length: 21 }, (_, i) => i); // 0..20
const YEAR_LABELS = YEAR_EDGES.slice(0, -1).map((e) => `${e}–${e + 1}`);

const DAY_BUCKET_EDGES = [0, 1, 7, 30, 90, 365, Infinity];
const DAY_BUCKET_LABELS = [
  '<1 dia',
  '1–7 dias',
  '7–30 dias',
  '30–90 dias',
  '90–365 dias',
  '>365 dias',
];

const RATIO_BUCKET_EDGES = [0, 0.25, 0.5, 0.75, 0.9, 1.0000001];
const RATIO_BUCKET_LABELS = ['0–25%', '25–50%', '50–75%', '75–90%', '90–100%'];

const TOP_LANGUAGES_N = 12;

function postMsg(msg: WorkerOutgoingMessage) {
  self.postMessage(msg);
}

function computeRQStats(rows: RepoRow[], totalDatasetCount: number): RQStats {
  const n_filtered = rows.length;
  if (n_filtered === 0) {
    return {
      n_total: totalDatasetCount,
      n_filtered: 0,
      rq01: { mean_years: 0, median_years: 0, max_years: 0, years_labels: YEAR_LABELS, years_counts: new Array(YEAR_LABELS.length).fill(0) },
      rq02: { mean: 0, median: 0, max: 0, q_labels: ["P25", "Mediana (P50)", "P75", "P90", "P99"], q_values: [0, 0, 0, 0, 0] },
      rq03: { mean: 0, median: 0, zero_pct: 0, nonzero_pct: 0 },
      rq04: { mean: 0, median: 0, max: 0, labels: DAY_BUCKET_LABELS, counts: new Array(DAY_BUCKET_LABELS.length).fill(0) },
      rq05: { missing: 0, missing_pct: 0, labels: [], counts: [] },
      rq06: { missing_pct: 0, mean: 0, median: 0, labels: RATIO_BUCKET_LABELS, counts: new Array(RATIO_BUCKET_LABELS.length).fill(0) },
      rq07: { labels: [], median_prs: [], median_releases: [], median_update_days: [] }
    };
  }

  // RQ01 - Age
  const ageDays = rows.map((r) => r.age_days);
  const ageDaysSorted = sortNums(ageDays);
  const ageYears = ageDays.map((d) => d / 365.25);
  const rq01 = {
    mean_years: mean(ageDays) / 365.25,
    median_years: quantile(ageDaysSorted, 0.5) / 365.25,
    max_years: ageDaysSorted[ageDaysSorted.length - 1] / 365.25,
    years_labels: YEAR_LABELS,
    years_counts: histogramCounts(ageYears, YEAR_EDGES),
  };

  // RQ02 - Merged PRs
  const prs = rows.map((r) => r.merged_pull_requests);
  const prsSorted = sortNums(prs);
  const rq02 = {
    mean: mean(prs),
    median: quantile(prsSorted, 0.5),
    max: prsSorted[prsSorted.length - 1],
    q_labels: ['P25', 'Mediana (P50)', 'P75', 'P90', 'P99'],
    q_values: [0.25, 0.5, 0.75, 0.9, 0.99].map((p) =>
      Math.round(quantile(prsSorted, p))
    ),
  };

  // RQ03 - Releases
  const releases = rows.map((r) => r.total_releases);
  const zero_count = releases.filter((v) => v === 0).length;
  const zero_pct = (zero_count / n_filtered) * 100;
  const rq03 = {
    mean: mean(releases),
    median: median(releases),
    zero_pct,
    nonzero_pct: 100 - zero_pct,
  };

  // RQ04 - Time since update
  const upd = rows.map((r) => r.time_since_update_days);
  const updSorted = sortNums(upd);
  const rq04 = {
    mean: mean(upd),
    median: quantile(updSorted, 0.5),
    max: updSorted[updSorted.length - 1],
    labels: DAY_BUCKET_LABELS,
    counts: histogramCounts(upd, DAY_BUCKET_EDGES),
  };

  // RQ05 - Languages
  const langCounts = new Map<string, number>();
  let missingLang = 0;
  for (let i = 0; i < rows.length; i++) {
    const lang = rows[i].primary_language;
    if (!lang) {
      missingLang++;
      continue;
    }
    langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
  }

  const topLangs = [...langCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, TOP_LANGUAGES_N);

  const rq05 = {
    missing: missingLang,
    missing_pct: (missingLang / n_filtered) * 100,
    labels: [...topLangs.map(([lang]) => lang), '(sem linguagem)'],
    counts: [...topLangs.map(([, c]) => c), missingLang],
  };

  // RQ06 - Closed issues ratio
  const validRatios: number[] = [];
  let missingRatio = 0;
  for (let i = 0; i < rows.length; i++) {
    const val = rows[i].closed_issues_ratio;
    if (val != null && !isNaN(val)) {
      validRatios.push(val);
    } else {
      missingRatio++;
    }
  }

  const rq06 = {
    missing_pct: (missingRatio / n_filtered) * 100,
    mean: validRatios.length ? mean(validRatios) : 0,
    median: validRatios.length ? median(validRatios) : 0,
    labels: RATIO_BUCKET_LABELS,
    counts: histogramCounts(validRatios, RATIO_BUCKET_EDGES),
  };

  // RQ07 - Comparison across top languages
  const topLangNames = topLangs.map(([lang]) => lang);
  const groups = new Map<
    string,
    { prs: number[]; rel: number[]; upd: number[] }
  >(
    topLangNames.map((l) => [l, { prs: [], rel: [], upd: [] }])
  );

  for (let i = 0; i < rows.length; i++) {
    const lang = rows[i].primary_language;
    if (!lang) continue;
    const g = groups.get(lang);
    if (!g) continue;
    g.prs.push(rows[i].merged_pull_requests);
    g.rel.push(rows[i].total_releases);
    g.upd.push(rows[i].time_since_update_days);
  }

  const rq07 = {
    labels: topLangNames,
    median_prs: topLangNames.map((l) => median(groups.get(l)!.prs)),
    median_releases: topLangNames.map((l) => median(groups.get(l)!.rel)),
    median_update_days: topLangNames.map((l) => median(groups.get(l)!.upd)),
  };

  return {
    n_total: totalDatasetCount,
    n_filtered,
    rq01,
    rq02,
    rq03,
    rq04,
    rq05,
    rq06,
    rq07,
  };
}

function computeCorrelationMatrix(rows: RepoRow[]): CorrelationMatrix {
  // Downsample to max 15,000 for instantaneous Spearman matrix calculation if dataset is large
  const targetSample = rows.length > 15000 ? rows.slice(0, 15000) : rows;

  const hasStars = targetSample.some((r) => r.stargazer_count != null);
  const hasForks = targetSample.some((r) => r.fork_count != null);

  const variables = [
    { id: 'age_days', name: 'Idade (Dias)' },
    { id: 'merged_prs', name: 'PRs Mesclados' },
    { id: 'releases', name: 'Total Releases' },
    { id: 'update_recency', name: 'Dias s/ Update' },
    { id: 'total_issues', name: 'Total Issues' },
    { id: 'closed_ratio', name: 'Razão Fechadas' },
  ];

  if (hasStars) variables.push({ id: 'stars', name: 'Estrelas' });
  if (hasForks) variables.push({ id: 'forks', name: 'Forks' });

  const arrays: number[][] = variables.map((v) => {
    switch (v.id) {
      case 'age_days':
        return targetSample.map((r) => r.age_days);
      case 'merged_prs':
        return targetSample.map((r) => r.merged_pull_requests);
      case 'releases':
        return targetSample.map((r) => r.total_releases);
      case 'update_recency':
        return targetSample.map((r) => r.time_since_update_days);
      case 'total_issues':
        return targetSample.map((r) => r.total_issues);
      case 'closed_ratio':
        return targetSample.map((r) => r.closed_issues_ratio ?? 0);
      case 'stars':
        return targetSample.map((r) => r.stargazer_count ?? 0);
      case 'forks':
        return targetSample.map((r) => r.fork_count ?? 0);
      default:
        return [];
    }
  });

  const matrix: number[][] = [];
  const numVars = variables.length;

  for (let i = 0; i < numVars; i++) {
    matrix[i] = new Array(numVars);
    for (let j = 0; j < numVars; j++) {
      if (i === j) {
        matrix[i][j] = 1.0;
      } else if (j < i) {
        matrix[i][j] = matrix[j][i];
      } else {
        const coeff = spearmanCorrelation(arrays[i], arrays[j]);
        matrix[i][j] = Number(coeff.toFixed(3));
      }
    }
  }

  return {
    variables,
    matrix,
    sampleSize: targetSample.length,
  };
}

function inspectRepoBenchmark(repoName: string): BenchmarkReport | null {
  const cleanName = repoName.trim().toLowerCase();
  const idx = repoIndex.get(cleanName);
  if (idx === undefined || !datasetRows[idx]) {
    // Try substring fallback
    const foundIdx = datasetRows.findIndex((r) =>
      r.repo.toLowerCase().includes(cleanName)
    );
    if (foundIdx === -1) return null;
    return generateBenchmark(datasetRows[foundIdx]);
  }
  return generateBenchmark(datasetRows[idx]);
}

function generateBenchmark(repo: RepoRow): BenchmarkReport {
  const agePercentile = calculatePercentile(sortedAgeDays, repo.age_days);
  const prPercentile = calculatePercentile(
    sortedMergedPRs,
    repo.merged_pull_requests
  );
  const releasePercentile = calculatePercentile(
    sortedReleases,
    repo.total_releases
  );
  // For update days, lower is more recent / better, so invert: 100 - percentile
  const rawUpdatePct = calculatePercentile(
    sortedUpdateDays,
    repo.time_since_update_days
  );
  const recencyPercentile = Math.max(0, 100 - rawUpdatePct);
  const issuesPercentile = calculatePercentile(
    sortedTotalIssues,
    repo.total_issues
  );
  const ratioPercentile = calculatePercentile(
    sortedClosedIssueRatios,
    repo.closed_issues_ratio ?? 0
  );

  const percentiles: PercentileResult[] = [
    {
      metric: 'age_years',
      label: 'Idade',
      value: repo.age_days / 365.25,
      percentile: agePercentile,
      tier: getPercentileTier(agePercentile),
      formattedValue: `${fmtDec(repo.age_days / 365.25, 1)} anos`,
    },
    {
      metric: 'merged_pull_requests',
      label: 'PRs Mesclados',
      value: repo.merged_pull_requests,
      percentile: prPercentile,
      tier: getPercentileTier(prPercentile),
      formattedValue: fmt(repo.merged_pull_requests),
    },
    {
      metric: 'total_releases',
      label: 'Total de Releases',
      value: repo.total_releases,
      percentile: releasePercentile,
      tier: getPercentileTier(releasePercentile),
      formattedValue: fmt(repo.total_releases),
    },
    {
      metric: 'recency',
      label: 'Recência de Update',
      value: repo.time_since_update_days,
      percentile: recencyPercentile,
      tier: getPercentileTier(recencyPercentile),
      formattedValue: `${fmt(repo.time_since_update_days)} dias atrás`,
    },
    {
      metric: 'total_issues',
      label: 'Volume de Issues',
      value: repo.total_issues,
      percentile: issuesPercentile,
      tier: getPercentileTier(issuesPercentile),
      formattedValue: fmt(repo.total_issues),
    },
    {
      metric: 'closed_issues_ratio',
      label: 'Taxa de Fechamento',
      value: repo.closed_issues_ratio ?? 0,
      percentile: ratioPercentile,
      tier: getPercentileTier(ratioPercentile),
      formattedValue: repo.closed_issues_ratio != null ? fmtPct(repo.closed_issues_ratio * 100, 1) : 'Sem dados',
    },
  ];

  if (repo.stargazer_count != null && sortedStars.length) {
    const starPct = calculatePercentile(sortedStars, repo.stargazer_count);
    percentiles.unshift({
      metric: 'stars',
      label: 'Estrelas',
      value: repo.stargazer_count,
      percentile: starPct,
      tier: getPercentileTier(starPct),
      formattedValue: fmt(repo.stargazer_count),
    });
  }

  // Composite Rank Score: weighted average
  const rankScore =
    (prPercentile * 0.25 +
      releasePercentile * 0.2 +
      recencyPercentile * 0.2 +
      ratioPercentile * 0.2 +
      agePercentile * 0.15);

  const radarData = [
    { metric: 'PR Throughput', score: Number(prPercentile.toFixed(1)) },
    { metric: 'Releases Cadence', score: Number(releasePercentile.toFixed(1)) },
    { metric: 'Update Recency', score: Number(recencyPercentile.toFixed(1)) },
    { metric: 'Issue Resolution', score: Number(ratioPercentile.toFixed(1)) },
    { metric: 'Community Issues', score: Number(issuesPercentile.toFixed(1)) },
    { metric: 'Project Maturity', score: Number(agePercentile.toFixed(1)) },
  ];

  return {
    repo,
    percentiles,
    rankScore: Number(rankScore.toFixed(1)),
    radarData,
  };
}

// Handle messages from main thread
self.onmessage = async (e: MessageEvent<WorkerIncomingMessage>) => {
  const { type, payload } = e.data;

  switch (type) {
    case 'LOAD_DATA': {
      try {
        postMsg({
          type: 'LOAD_PROGRESS',
          payload: { message: 'Decodificando Parquet (100k registros)...', percent: 30 },
        });

        const rawRows = (await parquetReadObjects({
          file: payload.buffer,
        })) as any[];

        postMsg({
          type: 'LOAD_PROGRESS',
          payload: { message: 'Indexando colunas e criando distribuições...', percent: 70 },
        });

        datasetRows = rawRows.map((r) => ({
          repo: String(r.repo || ''),
          created_at: r.created_at ? String(r.created_at) : undefined,
          age_days: Number(r.age_days || 0),
          merged_pull_requests: Number(r.merged_pull_requests || 0),
          total_releases: Number(r.total_releases || 0),
          updated_at: r.updated_at ? String(r.updated_at) : undefined,
          time_since_update_days: Number(r.time_since_update_days || 0),
          primary_language: r.primary_language ? String(r.primary_language) : null,
          closed_issues: Number(r.closed_issues || 0),
          open_issues: Number(r.open_issues || 0),
          total_issues: Number(r.total_issues || 0),
          closed_issues_ratio:
            r.closed_issues_ratio != null && !isNaN(Number(r.closed_issues_ratio))
              ? Number(r.closed_issues_ratio)
              : null,
          id: r.id ? String(r.id) : undefined,
          stargazer_count: r.stargazer_count != null ? Number(r.stargazer_count) : undefined,
          fork_count: r.fork_count != null ? Number(r.fork_count) : undefined,
          watchers_count: r.watchers_count != null ? Number(r.watchers_count) : undefined,
          disk_usage_kb: r.disk_usage_kb != null ? Number(r.disk_usage_kb) : undefined,
          open_pull_requests: r.open_pull_requests != null ? Number(r.open_pull_requests) : undefined,
          total_pull_requests: r.total_pull_requests != null ? Number(r.total_pull_requests) : undefined,
          is_archived: r.is_archived != null ? Boolean(r.is_archived) : undefined,
          is_fork: r.is_fork != null ? Boolean(r.is_fork) : undefined,
        }));

        repoIndex.clear();
        repoNamesList = [];
        const langCounts = new Map<string, number>();

        for (let i = 0; i < datasetRows.length; i++) {
          const row = datasetRows[i];
          repoIndex.set(row.repo.toLowerCase(), i);
          repoNamesList.push(row.repo);

          if (row.primary_language) {
            langCounts.set(
              row.primary_language,
              (langCounts.get(row.primary_language) || 0) + 1
            );
          }
        }

        // Build sorted distribution arrays for fast quantile/percentile queries
        sortedAgeDays = sortNums(datasetRows.map((r) => r.age_days));
        sortedMergedPRs = sortNums(datasetRows.map((r) => r.merged_pull_requests));
        sortedReleases = sortNums(datasetRows.map((r) => r.total_releases));
        sortedUpdateDays = sortNums(datasetRows.map((r) => r.time_since_update_days));
        sortedTotalIssues = sortNums(datasetRows.map((r) => r.total_issues));
        sortedClosedIssueRatios = sortNums(
          datasetRows
            .map((r) => r.closed_issues_ratio)
            .filter((v): v is number => v != null && !isNaN(v))
        );

        if (datasetRows.some((r) => r.stargazer_count != null)) {
          sortedStars = sortNums(
            datasetRows.map((r) => r.stargazer_count ?? 0)
          );
        }
        if (datasetRows.some((r) => r.fork_count != null)) {
          sortedForks = sortNums(
            datasetRows.map((r) => r.fork_count ?? 0)
          );
        }

        const languages = [...langCounts.entries()]
          .sort((a, b) => b[1] - a[1])
          .map(([name, count]) => ({ name, count }));

        const availableMetrics = [
          'Idade (Anos)',
          'PRs Mesclados',
          'Releases',
          'Dias sem Update',
          'Total Issues',
          'Razão de Issues Fechadas',
        ];
        if (sortedStars.length) availableMetrics.push('Estrelas');
        const topRepos = datasetRows.slice(0, 100).map((r) => r.repo);

        postMsg({
          type: 'LOAD_SUCCESS',
          payload: {
            totalRows: datasetRows.length,
            topRepos,
            languages,
            availableMetrics,
          },
        });
      } catch (err: any) {
        postMsg({
          type: 'LOAD_ERROR',
          payload: { error: err?.message || 'Falha ao processar arquivo Parquet' },
        });
      }
      break;
    }

    case 'APPLY_FILTER': {
      const startTime = performance.now();
      const { filter } = payload;

      const minAgeDays = filter.ageMinYears * 365.25;
      const maxAgeDays = filter.ageMaxYears * 365.25;
      const langSet =
        filter.selectedLanguages.length > 0
          ? new Set(filter.selectedLanguages)
          : null;
      const search = filter.searchQuery.trim().toLowerCase();

      const filtered: RepoRow[] = [];
      const totalLen = datasetRows.length;

      for (let i = 0; i < totalLen; i++) {
        const r = datasetRows[i];

        // Age filter
        if (r.age_days < minAgeDays || r.age_days > maxAgeDays) continue;

        // PRs filter
        if (r.merged_pull_requests < filter.minMergedPRs) continue;

        // Releases filter
        if (r.total_releases < filter.minReleases) continue;

        // Recency filter
        if (r.time_since_update_days > filter.maxDaysSinceUpdate) continue;

        // Issues filter
        if (r.total_issues < filter.minTotalIssues) continue;

        // Closed issue ratio
        if (r.closed_issues_ratio != null) {
          if (
            r.closed_issues_ratio < filter.minClosedIssuesRatio ||
            r.closed_issues_ratio > filter.maxClosedIssuesRatio
          ) {
            continue;
          }
        } else if (filter.minClosedIssuesRatio > 0) {
          continue;
        }

        // Language filter
        if (langSet) {
          if (!r.primary_language || !langSet.has(r.primary_language)) {
            continue;
          }
        }

        // Search text
        if (search && !r.repo.toLowerCase().includes(search)) {
          continue;
        }

        filtered.push(r);
      }

      const stats = computeRQStats(filtered, totalLen);
      const correlation = computeCorrelationMatrix(filtered);
      const executionTimeMs = Number((performance.now() - startTime).toFixed(1));

      postMsg({
        type: 'FILTER_SUCCESS',
        payload: {
          stats,
          correlation,
          executionTimeMs,
          filteredCount: filtered.length,
        },
      });
      break;
    }

    case 'INSPECT_REPO': {
      const benchmark = inspectRepoBenchmark(payload.repoName);
      postMsg({
        type: 'INSPECT_SUCCESS',
        payload: { benchmark },
      });
      break;
    }

    case 'SEARCH_SUGGESTIONS': {
      const q = (payload.query || '').trim().toLowerCase();
      const limit = payload.limit || 30;
      if (!q) {
        postMsg({
          type: 'SUGGESTIONS_SUCCESS',
          payload: { query: q, results: datasetRows.slice(0, Math.min(limit, 100)).map((r) => r.repo) },
        });
        break;
      }

      const results: string[] = [];
      for (let i = 0; i < repoNamesList.length && results.length < limit; i++) {
        if (repoNamesList[i].toLowerCase().includes(q)) {
          results.push(repoNamesList[i]);
        }
      }

      postMsg({
        type: 'SUGGESTIONS_SUCCESS',
        payload: { query: q, results },
      });
      break;
    }
  }
};
