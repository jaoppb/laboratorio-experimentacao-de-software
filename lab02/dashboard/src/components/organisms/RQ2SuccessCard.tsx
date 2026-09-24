import React, { useState } from 'react';
import { SummaryStats, UnifiedTrial } from '../../types/dataset';
import { useTheme } from '../../hooks/useTheme';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { SegmentedControl } from '../atoms/SegmentedControl';
import { RQCardWrapper } from '../molecules/RQCardWrapper';

interface RQ2SuccessCardProps {
  stats: SummaryStats;
  trials: UnifiedTrial[];
}

type SplitBy = 'kata' | 'treatment';

export const RQ2SuccessCard: React.FC<RQ2SuccessCardProps> = ({ stats, trials }) => {
  const { isDark } = useTheme();
  const [splitBy, setSplitBy] = useState<SplitBy>('kata');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  let chartData: Plotly.Data[] = [];

  if (splitBy === 'kata') {
    const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);
    const lineX: (number | null)[] = [];
    const lineY: (string | null)[] = [];
    const aiRates: (number | null)[] = [];
    const manualRates: (number | null)[] = [];
    const aiHoverTexts: string[] = [];
    const manualHoverTexts: string[] = [];

    stats.kata_comparisons.forEach((k) => {
      const aiKataTrials = trials.filter((t) => t.kata === k.kata && t.treatment === 'ai');
      const manualKataTrials = trials.filter((t) => t.kata === k.kata && t.treatment === 'manual');

      const aiTotal = aiKataTrials.reduce((sum, t) => sum + t.total_tests, 0);
      const aiPassed = aiKataTrials.reduce((sum, t) => sum + t.passed_tests, 0);
      const aiRate = aiTotal > 0 ? (aiPassed / aiTotal) * 100 : null;

      const manualTotal = manualKataTrials.reduce((sum, t) => sum + t.total_tests, 0);
      const manualPassed = manualKataTrials.reduce((sum, t) => sum + t.passed_tests, 0);
      const manualRate = manualTotal > 0 ? (manualPassed / manualTotal) * 100 : null;

      aiRates.push(aiRate);
      manualRates.push(manualRate);

      aiHoverTexts.push(
        aiRate !== null
          ? `${aiRate.toFixed(0)}% (${aiPassed}/${aiTotal} testes)`
          : 'Sem dados'
      );
      manualHoverTexts.push(
        manualRate !== null
          ? `${manualRate.toFixed(0)}% (${manualPassed}/${manualTotal} testes)`
          : 'Sem dados'
      );

      if (aiRate !== null && manualRate !== null) {
        lineX.push(manualRate, aiRate, null);
        lineY.push(k.kata_title, k.kata_title, null);
      }
    });

    chartData = [
      {
        type: 'scatter',
        mode: 'lines',
        x: lineX,
        y: lineY,
        line: { color: isDark ? '#484f58' : '#d0d7de', width: 3 },
        hoverinfo: 'none',
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        x: manualRates,
        y: kataLabels,
        name: 'Manual (Sem IA)',
        marker: {
          color: '#238636',
          symbol: 'diamond',
          size: 11,
          line: { color: isDark ? '#0d1117' : '#ffffff', width: 1 },
        },
        text: manualHoverTexts,
        hovertemplate: '<b>%{y}</b> (Manual): %{text}<extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'markers',
        x: aiRates,
        y: kataLabels,
        name: 'Com IA',
        marker: {
          color: '#2f81f7',
          symbol: 'circle-open',
          size: 15,
          line: { color: '#2f81f7', width: 3 },
        },
        text: aiHoverTexts,
        hovertemplate: '<b>%{y}</b> (IA): %{text}<extra></extra>',
      },
    ];
  } else {
    // Strip Plot with Jitter: displays each trial's success rate per treatment
    const aiTrials = trials.filter((t) => t.treatment === 'ai');
    const manualTrials = trials.filter((t) => t.treatment === 'manual');

    chartData = [
      {
        type: 'box',
        y: aiTrials.map((t) => (t.total_tests > 0 ? (t.passed_tests / t.total_tests) * 100 : 0)),
        name: 'Com IA',
        marker: { color: '#2f81f7', size: 9 },
        boxpoints: 'all',
        jitter: 0.35,
        pointpos: 0,
        fillcolor: isDark ? 'rgba(47, 129, 247, 0.15)' : 'rgba(47, 129, 247, 0.1)',
        line: { color: '#2f81f7', width: 1.5 },
        text: aiTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: '<b>%{text}</b><br>Com IA: %{y}% aprovados<extra></extra>',
      },
      {
        type: 'box',
        y: manualTrials.map((t) => (t.total_tests > 0 ? (t.passed_tests / t.total_tests) * 100 : 0)),
        name: 'Manual (Sem IA)',
        marker: { color: '#238636', size: 9 },
        boxpoints: 'all',
        jitter: 0.35,
        pointpos: 0,
        fillcolor: isDark ? 'rgba(35, 134, 54, 0.15)' : 'rgba(35, 134, 54, 0.1)',
        line: { color: '#238636', width: 1.5 },
        text: manualTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: '<b>%{text}</b><br>Manual: %{y}% aprovados<extra></extra>',
      },
    ];
  }

  const layout: Partial<Plotly.Layout> = {
    yaxis:
      splitBy === 'kata'
        ? {
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
            autorange: 'reversed',
            automargin: true,
          }
        : {
            title: { text: 'Taxa de Sucesso (%)', font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
            range: [0, 105],
            dtick: 20,
          },
    xaxis:
      splitBy === 'kata'
        ? {
            title: { text: 'Taxa de Sucesso nos Testes (%)', font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
            range: [0, 105],
            dtick: 20,
          }
        : {
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: 'transparent',
          },
    margin: splitBy === 'kata' ? { l: 120, r: 25, t: 15, b: 40 } : { l: 50, r: 20, t: 15, b: 40 },
    legend: {
      orientation: 'h',
      y: 1.15,
      x: 0,
      font: { size: 10, color: axisFontColor },
    },
  };

  const actionControls = (
    <SegmentedControl<SplitBy>
      value={splitBy}
      onChange={setSplitBy}
      activeColorClass="text-emerald-600 dark:text-emerald-400"
      options={[
        { value: 'kata', label: 'Pareado por Kata (Dumbbell)' },
        { value: 'treatment', label: 'Dispersão Geral (Strip Plot)' },
      ]}
    />
  );

  return (
    <RQCardWrapper
      pillLabel="RQ2 · Taxa de Defeitos & Sucesso"
      pillVariant="success"
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
            Status: Todos os trials atingiram time-to-green (20/20 testes)
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
