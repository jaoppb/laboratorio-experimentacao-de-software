import React, { useState } from 'react';
import { SummaryStats, UnifiedTrial } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { useTheme } from '../../hooks/useTheme';

interface RQ2SuccessCardProps {
  stats: SummaryStats;
  trials: UnifiedTrial[];
}

export const RQ2SuccessCard: React.FC<RQ2SuccessCardProps> = ({ stats, trials }) => {
  const { isDark } = useTheme();
  const [splitBy, setSplitBy] = useState<'kata' | 'treatment'>('kata');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  let chartData: Plotly.Data[] = [];

  if (splitBy === 'kata') {
    const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);
    const aiPassed = stats.kata_comparisons.map((k) => k.ai_tests_passed);
    const manualPassed = stats.kata_comparisons.map((k) => k.manual_tests_passed);

    chartData = [
      {
        type: 'bar',
        x: kataLabels,
        y: aiPassed,
        name: 'Testes Passados (IA)',
        marker: { color: '#2f81f7' },
        hovertemplate: '<b>%{x}</b> (IA): %{y} testes passados<extra></extra>',
      },
      {
        type: 'bar',
        x: kataLabels,
        y: manualPassed,
        name: 'Testes Passados (Manual)',
        marker: { color: '#238636' },
        hovertemplate: '<b>%{x}</b> (Manual): %{y} testes passados<extra></extra>',
      },
    ];
  } else {
    // Treatment level summary
    const aiPassCount = trials
      .filter((t) => t.treatment === 'ai')
      .reduce((sum, t) => sum + t.passed_tests, 0);
    const aiFailCount = trials
      .filter((t) => t.treatment === 'ai')
      .reduce((sum, t) => sum + t.failed_tests, 0);

    const manualPassCount = trials
      .filter((t) => t.treatment === 'manual')
      .reduce((sum, t) => sum + t.passed_tests, 0);
    const manualFailCount = trials
      .filter((t) => t.treatment === 'manual')
      .reduce((sum, t) => sum + t.failed_tests, 0);

    chartData = [
      {
        type: 'bar',
        x: ['Com IA', 'Manual (Sem IA)'],
        y: [aiPassCount, manualPassCount],
        name: 'Testes Passados',
        marker: { color: '#238636' },
        hovertemplate: '<b>%{x}</b>: %{y} testes passados<extra></extra>',
      },
      {
        type: 'bar',
        x: ['Com IA', 'Manual (Sem IA)'],
        y: [aiFailCount, manualFailCount],
        name: 'Testes Falhando',
        marker: { color: '#f85149' },
        hovertemplate: '<b>%{x}</b>: %{y} testes falhando<extra></extra>',
      },
    ];
  }

  const layout: Partial<Plotly.Layout> = {
    barmode: splitBy === 'treatment' ? 'stack' : 'group',
    yaxis: {
      title: { text: 'Quantidade de Testes', font: { size: 11, color: axisFontColor } },
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
        onClick={() => setSplitBy('kata')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          splitBy === 'kata'
            ? 'bg-white dark:bg-github-card text-emerald-600 dark:text-emerald-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Por Kata
      </button>
      <button
        onClick={() => setSplitBy('treatment')}
        className={`px-2 py-1 text-[11px] font-semibold rounded-md transition ${
          splitBy === 'treatment'
            ? 'bg-white dark:bg-github-card text-emerald-600 dark:text-emerald-400 shadow-sm'
            : 'text-gray-600 dark:text-github-muted hover:text-gray-900'
        }`}
      >
        Por Tratamento
      </button>
    </div>
  );

  return (
    <RQCardWrapper
      pillLabel="RQ2 · Taxa de Defeitos & Sucesso"
      pillColorClass="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
      title="O assistente de IA reduz a quantidade de defeitos nos testes?"
      subtitle={
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          <span>
            Taxa de Sucesso IA: <b>{stats.success_rate_ai.toFixed(0)}%</b>
          </span>
          <span>·</span>
          <span>
            Taxa de Sucesso Manual: <b>{stats.success_rate_manual.toFixed(0)}%</b>
          </span>
          <span>·</span>
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
            Status: Todos os 24 trials atingiram time-to-green (20/20 testes)
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
