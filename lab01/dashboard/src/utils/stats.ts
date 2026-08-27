/**
 * Math and Statistical Utilities for Fast Client-Side Analytics (100k+ rows)
 */

export const mean = (arr: number[]): number => {
  if (!arr.length) return 0;
  let sum = 0;
  for (let i = 0; i < arr.length; i++) sum += arr[i];
  return sum / arr.length;
};

export const sortNums = (arr: number[] | Float64Array | Int32Array): number[] => {
  return Array.from(arr).sort((a, b) => a - b);
};

export function quantile(sortedArr: number[], p: number): number {
  if (!sortedArr.length) return 0;
  const idx = p * (sortedArr.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sortedArr[lo];
  return sortedArr[lo] + (sortedArr[hi] - sortedArr[lo]) * (idx - lo);
}

export const median = (arr: number[]): number => {
  if (!arr.length) return 0;
  return quantile(sortNums(arr), 0.5);
};

export function histogramCounts(values: number[], edges: number[]): number[] {
  const counts = new Array(edges.length - 1).fill(0);
  const numEdges = edges.length;
  for (let j = 0; j < values.length; j++) {
    const v = values[j];
    for (let i = 0; i < numEdges - 1; i++) {
      const isLast = i === numEdges - 2;
      if (v >= edges[i] && (isLast ? v <= edges[i + 1] : v < edges[i + 1])) {
        counts[i]++;
        break;
      }
    }
  }
  return counts;
}

/**
 * Computes fractional ranks of an array of numbers (handles ties properly).
 */
export function computeRanks(values: number[]): Float64Array {
  const n = values.length;
  const indices = new Int32Array(n);
  for (let i = 0; i < n; i++) indices[i] = i;

  // Sort indices by value
  indices.sort((a, b) => values[a] - values[b]);

  const ranks = new Float64Array(n);
  let i = 0;
  while (i < n) {
    let j = i;
    const v = values[indices[i]];
    while (j < n && values[indices[j]] === v) {
      j++;
    }
    // Average rank for ties (1-based ranking)
    const tieRank = (i + 1 + j) / 2;
    for (let k = i; k < j; k++) {
      ranks[indices[k]] = tieRank;
    }
    i = j;
  }
  return ranks;
}

/**
 * Pearson correlation coefficient between two numeric arrays.
 */
export function pearsonCorrelation(x: Float64Array | number[], y: Float64Array | number[]): number {
  const n = x.length;
  if (n < 2) return 0;

  let sumX = 0, sumY = 0;
  for (let i = 0; i < n; i++) {
    sumX += x[i];
    sumY += y[i];
  }
  const meanX = sumX / n;
  const meanY = sumY / n;

  let numerator = 0;
  let denomX = 0;
  let denomY = 0;

  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    numerator += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }

  const denom = Math.sqrt(denomX * denomY);
  if (denom === 0) return 0;
  return Math.max(-1, Math.min(1, numerator / denom));
}

/**
 * Computes Spearman Rank Correlation between two variables.
 */
export function spearmanCorrelation(x: number[], y: number[]): number {
  if (x.length !== y.length || x.length < 2) return 0;
  const ranksX = computeRanks(x);
  const ranksY = computeRanks(y);
  return pearsonCorrelation(ranksX, ranksY);
}

/**
 * Computes the exact percentile (0 - 100) of a target value within a sorted distribution array.
 */
export function calculatePercentile(sortedArr: number[], value: number): number {
  if (!sortedArr.length) return 50;
  let lo = 0;
  let hi = sortedArr.length - 1;
  let countBelow = 0;

  // Binary search for position
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (sortedArr[mid] <= value) {
      countBelow = mid + 1;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }

  return (countBelow / sortedArr.length) * 100;
}

/**
 * Returns a human-friendly tier string based on percentile rank (0 - 100).
 */
export function getPercentileTier(percentile: number): string {
  if (percentile >= 99) return "Top 1% 🔥";
  if (percentile >= 95) return "Top 5% 🌟";
  if (percentile >= 90) return "Top 10% ⚡";
  if (percentile >= 75) return "Top 25% (Q3)";
  if (percentile >= 50) return "Acima da Mediana (P50+)";
  if (percentile >= 25) return "Faixa Média (Q2)";
  return "Base 25% (Q1)";
}
