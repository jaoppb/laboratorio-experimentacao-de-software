import React, { useState } from 'react';
import { SummaryStats, UnifiedTrial } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { formatDuration, formatNumber } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ1TimeCardProps {
  stats: SummaryStats;
  trials: UnifiedTrial[];
}

export const RQ1TimeCard: React.FC<RQ1TimeCardProps> = ({ stats, trials }) => {
  const { isDark } = useTheme();
  const [viewMode, setViewMode] = useState<'overall' | 'kata' | 'model'>('overall');
  const [unit, setUnit] = useState<'seconds' | 'minutes'>('seconds');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const unitMultiplier = unit === 'minutes' ? 1 / 60 : 1;
  const unitLabel = unit === 'minutes' ? 'minutos' : 'segundos';

  // 1. Overall Boxplot / Distribution
  const aiTimes = trials.filter((t) => t.treatment === 'ai').map((t) => t.time_seconds * unitMultiplier);
  const manualTimes = trials.filter((t) => t.treatment === 'manual').map((t) => t.time_seconds * unitMultiplier);

  let chartData: Plotly.Data[] = [];

  if (viewMode === 'overall') {
    chartData = [
      {
        type: 'box',
        y: aiTimes,
        name: 'Com Assistente de IA',
        marker: { color: '#2f81f7' },
        boxpoints: 'all',
        jitter: 0.3,
        pointpos: -1.8,
        hoverinfo: 'y+name',
      },
      {
        type: 'box',
        y: manualTimes,
        name: 'Manual (Sem IA)',
        marker: { color: '#f85149' },
        boxpoints: 'all',
        jitter: 0.3,
        pointpos: -1.8,
        hoverinfo: 'y+name',
      },
    ];
  } else if (viewMode === 'kata') {
    // Grouped Bar by Kata
    const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);
    const aiMedians = stats.kata_comparisons.map((k) => k.ai_time_median * unitMultiplier);
    const manualMedians = stats.kata_comparisons.map((k) => k.manual_time_median * unitMultiplier);

    chartData = [
      {
        type: 'bar',
        x: kataLabels,
        y: aiMedians,
        name: 'IA (Mediana)',
        marker: { color: '#2f81f7' },
        hovertemplate: `<b>%{x}</b> (IA): %{y:.1f} ${unitLabel}<extra></extra>`,
      },
      {
        type: 'bar',
        x: kataLabels,
        y: manualMedians,
        name: 'Manual (Mediana)',
        marker: { color: '#f85149' },
        hovertemplate: `<b>%{x}</b> (Manual): %{y:.1f} ${unitLabel}<extra></extra>`,
      },
    ];
  } else {
    // By AI Model
    const modelLabels = stats.model_comparisons.map((m) => m.model_name);
    const medians = stats.model_comparisons.map((m) => m.time_median * unitMultiplier);

    chartData = [
      {
        type: 'bar',
        x: modelLabels,
        y: medians,
        marker: {
          color: modelLabels.map((l) =>
            l.includes('Gemini') ? '#2f81f7' : l.includes('Claude') ? '#a371f7' : '#f85149'
          ),
        },
        hovertemplate: `<b>%{x}</b>: %{y:.1f} ${unitLabel}<extra></extra>`,
      },
    ];
  }

  const layout: Partial<Plotly.Layout> = {
    barmode: viewMode === 'kata' ? 'group' : undefined,
    yaxis: {
      title: { text: `Tempo (${unitLabel})`, font: { size: 11, color: axisFontColor } },
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: gridColor,
      zerolinecolor: gridColor,
    },
    xaxis: {
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: 'transparent',
    },
    margin: { l: 55, r: 20, t: 15, b: 40 },
    legend: {
      orientation: 'h',
      y: 1.15,
      x: 0,
      font: { size: 10, color: axisFontColor },
    },
  };

  const actionControls = (
    <div className="flex items-center gap-2">
      {/* View mode selector */}
      <div className="flex rounded-lg border border-gray-200 dark:border-github-border overflow-hidden bg-gray-50 dark:bg-github-dark p-0.5">
        <button
          onClick={() => setViewMode('overall')}
          className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
            viewMode === 'overall'
              ? 'bg-white dark:bg-github-card text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
          }`}
        >
          Geral
        </button>
        <button
          onClick={() => setViewMode('kata')}
          className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
            viewMode === 'kata'
              ? 'bg-white dark:bg-github-card text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
          }`}
        >
          Por Kata
        </button>
        <button
          onClick={() => setViewMode('model')}
          className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
            viewMode === 'model'
              ? 'bg-white dark:bg-github-card text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
          }`}
        >
          Por Modelo
        </button>
      </div>

      {/* Unit toggle */}
      <button
        onClick={() => setUnit(unit === 'seconds' ? 'minutes' : 'seconds')}
        className="px-2 py-1 text-[11px] font-semibold rounded-lg border border-gray-200 dark:border-github-border bg-gray-50 dark:bg-github-dark hover:bg-gray-100 dark:hover:bg-github-card text-gray-700 dark:text-github-text transition"
        title="Alternar entre segundos e minutos"
      >
        {unit === 'seconds' ? 'Segundos (s)' : 'Minutos (m)'}
      </button>
    </div>
  );

  return (
    <RQCardWrapper
      pillLabel="RQ1 · Tempo de Resolução"
      pillColorClass="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
      title="O assistente de IA reduz o tempo para resolver a tarefa?"
      subtitle={
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          <span>
            Mediana IA: <b>{formatDuration(stats.time_ai.median, true)}</b> (IQR: {formatDuration(stats.time_ai.iqr, true)})
          </span>
          <span>·</span>
          <span>
            Mediana Manual: <b>{formatDuration(stats.time_manual.median, true)}</b> (IQR: {formatDuration(stats.time_manual.iqr, true)})
          </span>
          <span>·</span>
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
            Redução Mediana: {stats.time_reduction_pct}%
          </span>
        </div>
      }
      action={actionControls}
    >
      <div className="w-full h-72">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
