export interface TrialRow {
  trial_id: string;
  participant: string;
  treatment: 'ai' | 'manual' | string;
  kata: string;
  file: string;
  time_seconds: number;
  censored: boolean;
  passed_tests: number;
  total_tests: number;
  failed_tests: number;
  success_rate: number;
  timestamp: string;
  status: string;
  actual_elapsed_seconds: number;
}

export interface MetricsRow {
  file: string;
  kata: string;
  participant: string;
  treatment: string;
  trial_id: string;
  loc: number;
  sloc: number;
  lloc: number;
  comments: number;
  blank: number;
  functions_count: number;
  cc_avg: number;
  cc_max: number;
  cc_min: number;
  cc_total: number;
  cc_rank: string;
  duplicated_lines: number;
  duplication_percentage: number;
  clones_count: number;
  duplication_tool: string;
  mi: number;
  mi_rank: string;
  status: string;
  error_message: string;
}

export interface UnifiedTrial {
  trial_id: string;
  participant: string;
  treatment: 'ai' | 'manual';
  kata: string;
  kata_title: string;
  kata_num: string;
  file: string;
  ai_model: string | null;
  ai_model_key: 'gemini-flash-3.8' | 'claude-sonnet-5' | 'manual' | string;
  time_seconds: number;
  actual_elapsed_seconds: number;
  censored: boolean;
  passed_tests: number;
  total_tests: number;
  failed_tests: number;
  success_rate: number;
  timestamp: string;
  status: string;
  loc: number;
  sloc: number;
  lloc: number;
  comments: number;
  blank: number;
  functions_count: number;
  cc_avg: number;
  cc_max: number;
  cc_min: number;
  cc_total: number;
  cc_rank: string;
  duplicated_lines: number;
  duplication_percentage: number;
  clones_count: number;
  duplication_tool: string;
  mi: number;
  mi_rank: string;
  github_url: string;
}

export interface FilterState {
  participant: string;
  treatment: 'all' | 'ai' | 'manual';
  kata: string;
  ai_model: string;
  searchQuery: string;
}

export interface DescriptiveStats {
  count: number;
  mean: number;
  median: number;
  q25: number;
  q75: number;
  iqr: number;
  min: number;
  max: number;
}

export interface GroupedKataComparison {
  kata: string;
  kata_title: string;
  ai_time_median: number;
  manual_time_median: number;
  ai_cc_mean: number;
  manual_cc_mean: number;
  ai_mi_mean: number;
  manual_mi_mean: number;
  ai_loc_mean: number;
  manual_loc_mean: number;
  ai_tests_passed: number;
  manual_tests_passed: number;
  total_tests: number;
}

export interface ModelComparison {
  model_name: string;
  count: number;
  time_median: number;
  time_mean: number;
  cc_mean: number;
  mi_mean: number;
  loc_mean: number;
}

export interface SummaryStats {
  total_trials: number;
  filtered_trials: number;
  count_ai: number;
  count_manual: number;
  time_ai: DescriptiveStats;
  time_manual: DescriptiveStats;
  time_reduction_pct: number;
  success_rate_ai: number;
  success_rate_manual: number;
  total_tests_passed: number;
  total_tests_count: number;
  cc_ai: DescriptiveStats;
  cc_manual: DescriptiveStats;
  mi_ai: DescriptiveStats;
  mi_manual: DescriptiveStats;
  loc_ai: DescriptiveStats;
  loc_manual: DescriptiveStats;
  dup_ai: DescriptiveStats;
  dup_manual: DescriptiveStats;
  kata_comparisons: GroupedKataComparison[];
  model_comparisons: ModelComparison[];
}
