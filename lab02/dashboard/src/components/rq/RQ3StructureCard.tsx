import React, { useState } from 'react';
import { SummaryStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { formatNumber } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ3StructureCardProps {
  stats: SummaryStats;
}

type MetricKey = 'cc' | 'mi' | 'loc' | 'dup';

export const RQ3StructureCard: React.FC<RQ3StructureCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [metric, setMetric] = useState<MetricKey>('cc');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);

  let aiValues: number[] = [];
  let manualValues: number[] = [];
  let yAxisTitle = '';
  let formatDecimals = 1;
  let metricDescription = '';

  switch (metric) {
    case 'cc':
      aiValues = stats.kata_comparisons.map((k) => k.ai_cc_mean);
      manualValues = stats.kata_comparisons.map((k) => k.manual_cc_mean);
      yAxisTitle = 'CC Média (McCabe)';
      formatDecimals = 1;
      metricDescription = `Média IA: ${formatNumber(stats.cc_ai.mean, 1)} · Média Manual: ${formatNumber(stats.cc_manual.mean, 1)} (Radon CC por função)`;
      break;
    case 'mi':
      aiValues = stats.kata_comparisons.map((k) => k.ai_mi_mean);
      manualValues = stats.kata_comparisons.map((k) => k.manual_mi_mean);
      yAxisTitle = 'Índice de Manutenibilidade (0–100)';
      formatDecimals = 1;
      metricDescription = `Média IA: ${formatNumber(stats.mi_ai.mean, 1)} · Média Manual: ${formatNumber(stats.mi_manual.mean, 1)} (Radon MI)`;
      break;
    case 'loc':
      aiValues = stats.kata_comparisons.map((k) => k.ai_loc_mean);
      manualValues = stats.kata_comparisons.map((k) => k.manual_loc_mean);
      yAxisTitle = 'Linhas Físicas (LOC)';
      formatDecimals = 0;
      metricDescription = `Média IA: ${formatNumber(stats.loc_ai.mean, 0)} LOC · Média Manual: ${formatNumber(stats.loc_manual.mean, 0)} LOC (Controle)`;
      break;
    case 'dup':
      aiValues = stats.kata_comparisons.map((k) =>
        k.ai_time_median ? stats.dup_ai.mean : 0
      );
      manualValues = stats.kata_comparisons.map((k) =>
        k.manual_time_median ? stats.dup_manual.mean : 0
      );
      yAxisTitle = '% Linhas Duplicadas (jscpd)';
      formatDecimals = 1;
      metricDescription = `Duplicação IA: ${formatNumber(stats.dup_ai.mean, 1)}% · Duplicação Manual: ${formatNumber(stats.dup_manual.mean, 1)}%`;
      break;
  }

  const chartData: Plotly.Data[] = [
    {
      type: 'bar',
      x: kataLabels,
      y: aiValues,
      name: 'Com IA',
      marker: { color: '#a371f7' },
      hovertemplate: `<b>%{x}</b> (IA): %{y:.${formatDecimals}f}<extra></extra>`,
    },
    {
      type: 'bar',
      x: kataLabels,
      y: manualValues,
      name: 'Manual (Sem IA)',
      marker: { color: '#f59e0b' },
      hovertemplate: `<b>%{x}</b> (Manual): %{y:.${formatDecimals}f}<extra></extra>`,
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    barmode: 'group',
    yaxis: {
      title: { text: yAxisTitle, font: { size: 11, color: axisFontColor } },
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: gridColor,
    },
    xaxis: {
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: 'transparent',
    },
    margin: { l: 50, r: 20, t: 15, b: 40 },
    legend: {
      orientation: 'h',
      y: 1.15,
      x: 0,
      font: { size: 10, color: axisFontColor },
    },
  };

  const actionControls = (
    <div className="flex rounded-lg border border-gray-200 dark:border-github-border overflow-hidden bg-gray-50 dark:bg-github-dark p-0.5">
      <button
        onClick={() => setMetric('cc')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          metric === 'cc'
            ? 'bg-white dark:bg-github-card text-purple-600 dark:text-purple-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Complexidade (CC)
      </button>
      <button
        onClick={() => setMetric('mi')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          metric === 'mi'
            ? 'bg-white dark:bg-github-card text-purple-600 dark:text-purple-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Manutenibilidade (MI)
      </button>
      <button
        onClick={() => setMetric('loc')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          metric === 'loc'
            ? 'bg-white dark:bg-github-card text-purple-600 dark:text-purple-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Tamanho (LOC)
      </button>
      <button
        onClick={() => setMetric('dup')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          metric === 'dup'
            ? 'bg-white dark:bg-github-card text-purple-600 dark:text-purple-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Duplicação %
      </button>
    </div>
  );

  return (
    <RQCardWrapper
      pillLabel="RQ3 · Métricas Estruturais de Código"
      pillColorClass="bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300"
      title="O assistente de IA altera a complexidade ou manutenibilidade do código?"
      subtitle={metricDescription}
      action={actionControls}
    >
      <div className="w-full h-72">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
