import {
  DescriptiveStats,
  GroupedKataComparison,
  ModelComparison,
  SummaryStats,
  UnifiedTrial,
} from '../types/dataset';

export function mean(arr: number[]): number {
  if (arr.length === 0) return 0;
  return arr.reduce((acc, v) => acc + v, 0) / arr.length;
}

export function quantile(sortedArr: number[], q: number): number {
  if (sortedArr.length === 0) return 0;
  if (q <= 0) return sortedArr[0];
  if (q >= 1) return sortedArr[sortedArr.length - 1];

  const pos = (sortedArr.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;

  if (sortedArr[base + 1] !== undefined) {
    return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base]);
  }
  return sortedArr[base];
}

export function median(arr: number[]): number {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  return quantile(sorted, 0.5);
}

export function calcDescriptiveStats(values: number[]): DescriptiveStats {
  if (values.length === 0) {
    return { count: 0, mean: 0, median: 0, q25: 0, q75: 0, iqr: 0, min: 0, max: 0 };
  }

  const sorted = [...values].sort((a, b) => a - b);
  const q25 = quantile(sorted, 0.25);
  const q75 = quantile(sorted, 0.75);

  return {
    count: values.length,
    mean: mean(values),
    median: quantile(sorted, 0.5),
    q25,
    q75,
    iqr: q75 - q25,
    min: sorted[0],
    max: sorted[sorted.length - 1],
  };
}

export function computeSummaryStats(
  allTrials: UnifiedTrial[],
  filteredTrials: UnifiedTrial[]
): SummaryStats {
  const aiTrials = filteredTrials.filter((t) => t.treatment === 'ai');
  const manualTrials = filteredTrials.filter((t) => t.treatment === 'manual');

  const timeAiValues = aiTrials.map((t) => t.time_seconds);
  const timeManualValues = manualTrials.map((t) => t.time_seconds);

  const timeAi = calcDescriptiveStats(timeAiValues);
  const timeManual = calcDescriptiveStats(timeManualValues);

  // Reduction % calculated via medians
  const timeReductionPct =
    timeManual.median > 0
      ? ((timeManual.median - timeAi.median) / timeManual.median) * 100
      : 0;

  const totalPassedTests = filteredTrials.reduce((sum, t) => sum + t.passed_tests, 0);
  const totalTests = filteredTrials.reduce((sum, t) => sum + t.total_tests, 0);

  const aiPassedTests = aiTrials.reduce((sum, t) => sum + t.passed_tests, 0);
  const aiTotalTests = aiTrials.reduce((sum, t) => sum + t.total_tests, 0);
  const manualPassedTests = manualTrials.reduce((sum, t) => sum + t.passed_tests, 0);
  const manualTotalTests = manualTrials.reduce((sum, t) => sum + t.total_tests, 0);

  // Group by kata
  const kataMap = new Map<string, { ai: UnifiedTrial[]; manual: UnifiedTrial[]; title: string }>();
  filteredTrials.forEach((t) => {
    if (!kataMap.has(t.kata)) {
      kataMap.set(t.kata, { ai: [], manual: [], title: t.kata_title });
    }
    const group = kataMap.get(t.kata)!;
    if (t.treatment === 'ai') group.ai.push(t);
    else group.manual.push(t);
  });

  const kata_comparisons: GroupedKataComparison[] = Array.from(kataMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([kata, grp]) => ({
      kata,
      kata_title: grp.title,
      ai_time_median: median(grp.ai.map((t) => t.time_seconds)),
      manual_time_median: median(grp.manual.map((t) => t.time_seconds)),
      ai_cc_mean: mean(grp.ai.map((t) => t.cc_avg)),
      manual_cc_mean: mean(grp.manual.map((t) => t.cc_avg)),
      ai_mi_mean: mean(grp.ai.map((t) => t.mi)),
      manual_mi_mean: mean(grp.manual.map((t) => t.mi)),
      ai_loc_mean: mean(grp.ai.map((t) => t.loc)),
      manual_loc_mean: mean(grp.manual.map((t) => t.loc)),
      ai_tests_passed: grp.ai.reduce((sum, t) => sum + t.passed_tests, 0),
      manual_tests_passed: grp.manual.reduce((sum, t) => sum + t.passed_tests, 0),
      total_tests:
        grp.ai.reduce((sum, t) => sum + t.total_tests, 0) +
        grp.manual.reduce((sum, t) => sum + t.total_tests, 0),
    }));

  // Group by model
  const modelMap = new Map<string, UnifiedTrial[]>();
  filteredTrials.forEach((t) => {
    const key = t.ai_model || 'Manual (Sem IA)';
    if (!modelMap.has(key)) modelMap.set(key, []);
    modelMap.get(key)!.push(t);
  });

  const model_comparisons: ModelComparison[] = Array.from(modelMap.entries()).map(
    ([model_name, trials]) => ({
      model_name,
      count: trials.length,
      time_median: median(trials.map((t) => t.time_seconds)),
      time_mean: mean(trials.map((t) => t.time_seconds)),
      cc_mean: mean(trials.map((t) => t.cc_avg)),
      mi_mean: mean(trials.map((t) => t.mi)),
      loc_mean: mean(trials.map((t) => t.loc)),
    })
  );

  return {
    total_trials: allTrials.length,
    filtered_trials: filteredTrials.length,
    count_ai: aiTrials.length,
    count_manual: manualTrials.length,
    time_ai: timeAi,
    time_manual: timeManual,
    time_reduction_pct: Number(timeReductionPct.toFixed(1)),
    success_rate_ai: aiTotalTests > 0 ? (aiPassedTests / aiTotalTests) * 100 : 0,
    success_rate_manual: manualTotalTests > 0 ? (manualPassedTests / manualTotalTests) * 100 : 0,
    total_tests_passed: totalPassedTests,
    total_tests_count: totalTests,
    cc_ai: calcDescriptiveStats(aiTrials.map((t) => t.cc_avg)),
    cc_manual: calcDescriptiveStats(manualTrials.map((t) => t.cc_avg)),
    mi_ai: calcDescriptiveStats(aiTrials.map((t) => t.mi)),
    mi_manual: calcDescriptiveStats(manualTrials.map((t) => t.mi)),
    loc_ai: calcDescriptiveStats(aiTrials.map((t) => t.loc)),
    loc_manual: calcDescriptiveStats(manualTrials.map((t) => t.loc)),
    dup_ai: calcDescriptiveStats(aiTrials.map((t) => t.duplication_percentage)),
    dup_manual: calcDescriptiveStats(manualTrials.map((t) => t.duplication_percentage)),
    kata_comparisons,
    model_comparisons,
  };
}
