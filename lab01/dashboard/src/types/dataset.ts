export interface RepoRow {
  repo: string;
  created_at?: string;
  age_days: number;
  merged_pull_requests: number;
  total_releases: number;
  updated_at?: string;
  time_since_update_days: number;
  primary_language: string | null;
  closed_issues: number;
  open_issues: number;
  total_issues: number;
  closed_issues_ratio: number | null;
  id?: string;
  // Optional extended metrics
  stargazer_count?: number;
  fork_count?: number;
  watchers_count?: number;
  disk_usage_kb?: number;
  open_pull_requests?: number;
  total_pull_requests?: number;
  is_archived?: boolean;
  is_fork?: boolean;
}

export interface FilterState {
  ageMinYears: number;
  ageMaxYears: number;
  minMergedPRs: number;
  minReleases: number;
  maxDaysSinceUpdate: number;
  selectedLanguages: string[]; // empty means all
  minTotalIssues: number;
  minClosedIssuesRatio: number;
  maxClosedIssuesRatio: number;
  searchQuery: string;
}

export interface PercentileResult {
  metric: string;
  label: string;
  value: number;
  percentile: number; // 0 to 100
  tier: string; // e.g. "Top 1%", "Top 10%", "Mediana", "Base 25%"
  formattedValue: string;
}

export interface BenchmarkReport {
  repo: RepoRow;
  percentiles: PercentileResult[];
  rankScore: number; // 0 - 100 overall composite score
  radarData: {
    metric: string;
    score: number; // 0 - 100 percentile
  }[];
}

export interface RQStats {
  n_total: number;
  n_filtered: number;
  rq01: {
    mean_years: number;
    median_years: number;
    max_years: number;
    years_labels: string[];
    years_counts: number[];
  };
  rq02: {
    mean: number;
    median: number;
    max: number;
    q_labels: string[];
    q_values: number[];
  };
  rq03: {
    mean: number;
    median: number;
    zero_pct: number;
    nonzero_pct: number;
  };
  rq04: {
    mean: number;
    median: number;
    max: number;
    labels: string[];
    counts: number[];
  };
  rq05: {
    missing: number;
    missing_pct: number;
    labels: string[];
    counts: number[];
  };
  rq06: {
    missing_pct: number;
    mean: number;
    median: number;
    labels: string[];
    counts: number[];
  };
  rq07: {
    labels: string[];
    median_prs: number[];
    median_releases: number[];
    median_update_days: number[];
  };
}

export interface CorrelationMatrix {
  variables: { id: string; name: string }[];
  matrix: number[][]; // 2D array of Spearman coefficients (-1 to 1)
  sampleSize: number;
}
