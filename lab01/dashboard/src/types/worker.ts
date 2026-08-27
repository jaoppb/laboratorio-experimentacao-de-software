import { BenchmarkReport, CorrelationMatrix, FilterState, RepoRow, RQStats } from './dataset';

export type WorkerIncomingMessage =
  | { type: 'LOAD_DATA'; payload: { buffer: ArrayBuffer } }
  | { type: 'APPLY_FILTER'; payload: { filter: FilterState } }
  | { type: 'INSPECT_REPO'; payload: { repoName: string } }
  | { type: 'SEARCH_SUGGESTIONS'; payload: { query: string; limit?: number } };

export type WorkerOutgoingMessage =
  | { type: 'LOAD_PROGRESS'; payload: { message: string; percent?: number } }
  | { type: 'LOAD_SUCCESS'; payload: { totalRows: number; topRepos: string[]; languages: { name: string; count: number }[]; availableMetrics: string[] } }
  | { type: 'LOAD_ERROR'; payload: { error: string } }
  | { type: 'FILTER_SUCCESS'; payload: { stats: RQStats; correlation: CorrelationMatrix; executionTimeMs: number; filteredCount: number } }
  | { type: 'INSPECT_SUCCESS'; payload: { benchmark: BenchmarkReport | null } }
  | { type: 'SUGGESTIONS_SUCCESS'; payload: { query: string; results: string[] } };
