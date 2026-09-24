import React, { useState } from 'react';
import { SummaryStats, UnifiedTrial } from '../../types/dataset';
import { formatNumber } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { SegmentedControl } from '../atoms/SegmentedControl';
import { RQCardWrapper } from '../molecules/RQCardWrapper';

interface RQ3StructureCardProps {
  stats: SummaryStats;
  trials: UnifiedTrial[];
}

type MetricKey = 'cc' | 'mi' | 'loc' | 'dup';
type ViewMode = 'overall' | 'kata' | 'scatter';

export const RQ3StructureCard: React.FC<RQ3StructureCardProps> = ({ stats, trials }) => {
  const { isDark } = useTheme();
  const [viewMode, setViewMode] = useState<ViewMode>('overall');
  const [metric, setMetric] = useState<MetricKey>('cc');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const aiTrials = trials.filter((t) => t.treatment === 'ai');
  const manualTrials = trials.filter((t) => t.treatment === 'manual');

  let yAxisTitle = '';
  let formatDecimals = 1;
  let metricDescription = '';

  switch (metric) {
    case 'cc':
      yAxisTitle = 'CC Média (McCabe)';
      formatDecimals = 1;
      metricDescription = `Média IA: ${formatNumber(stats.cc_ai.mean, 1)} (Mediana: ${formatNumber(
        stats.cc_ai.median,
        1
      )}) · Manual: ${formatNumber(stats.cc_manual.mean, 1)} (Mediana: ${formatNumber(
        stats.cc_manual.median,
        1
      )}) · Wilcoxon p = 0.0259`;
      break;
    case 'mi':
      yAxisTitle = 'Índice de Manutenibilidade (0–100)';
      formatDecimals = 1;
      metricDescription = `Média IA: ${formatNumber(stats.mi_ai.mean, 1)} (Mediana: ${formatNumber(
        stats.mi_ai.median,
        1
      )}) · Manual: ${formatNumber(stats.mi_manual.mean, 1)} (Mediana: ${formatNumber(
        stats.mi_manual.median,
        1
      )}) · Wilcoxon p = 0.0342`;
      break;
    case 'loc':
      yAxisTitle = 'Linhas Físicas (LOC)';
      formatDecimals = 0;
      metricDescription = `Média IA: ${formatNumber(stats.loc_ai.mean, 0)} LOC (Mediana: ${formatNumber(
        stats.loc_ai.median,
        0
      )}) · Manual: ${formatNumber(stats.loc_manual.mean, 0)} LOC (Mediana: ${formatNumber(
        stats.loc_manual.median,
        0
      )}) · Wilcoxon p = 0.0003`;
      break;
    case 'dup':
      yAxisTitle = '% Linhas Duplicadas (jscpd)';
      formatDecimals = 1;
      metricDescription = `Duplicação IA: ${formatNumber(
        stats.dup_ai.mean,
        1
      )}% · Duplicação Manual: ${formatNumber(stats.dup_manual.mean, 1)}% (Diferenças nulas)`;
      break;
  }

  const getMetricValue = (t: UnifiedTrial, m: MetricKey): number => {
    switch (m) {
      case 'cc':
        return t.cc_avg;
      case 'mi':
        return t.mi;
      case 'loc':
        return t.loc;
      case 'dup':
        return t.duplication_percentage;
    }
  };

  let chartData: Plotly.Data[] = [];

  if (viewMode === 'overall') {
    const aiVals = aiTrials.map((t) => getMetricValue(t, metric));
    const manualVals = manualTrials.map((t) => getMetricValue(t, metric));

    chartData = [
      {
        type: 'box',
        y: aiVals,
        name: 'Com Assistente de IA',
        marker: { color: '#a371f7' },
        boxpoints: 'all',
        jitter: 0.3,
        pointpos: -1.8,
        text: aiTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: `<b>%{text}</b> (IA): %{y:.${formatDecimals}f}<extra></extra>`,
      },
      {
        type: 'box',
        y: manualVals,
        name: 'Manual (Sem IA)',
        marker: { color: '#f59e0b' },
        boxpoints: 'all',
        jitter: 0.3,
        pointpos: -1.8,
        text: manualTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: `<b>%{text}</b> (Manual): %{y:.${formatDecimals}f}<extra></extra>`,
      },
    ];
  } else if (viewMode === 'kata') {
    const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);
    let aiValues: number[] = [];
    let manualValues: number[] = [];

    switch (metric) {
      case 'cc':
        aiValues = stats.kata_comparisons.map((k) => k.ai_cc_mean);
        manualValues = stats.kata_comparisons.map((k) => k.manual_cc_mean);
        break;
      case 'mi':
        aiValues = stats.kata_comparisons.map((k) => k.ai_mi_mean);
        manualValues = stats.kata_comparisons.map((k) => k.manual_mi_mean);
        break;
      case 'loc':
        aiValues = stats.kata_comparisons.map((k) => k.ai_loc_mean);
        manualValues = stats.kata_comparisons.map((k) => k.manual_loc_mean);
        break;
      case 'dup':
        aiValues = stats.kata_comparisons.map((k) =>
          k.ai_time_median ? stats.dup_ai.mean : 0
        );
        manualValues = stats.kata_comparisons.map((k) =>
          k.manual_time_median ? stats.dup_manual.mean : 0
        );
        break;
    }

    const lineX: (number | null)[] = [];
    const lineY: (string | null)[] = [];
    kataLabels.forEach((label, i) => {
      lineX.push(manualValues[i], aiValues[i], null);
      lineY.push(label, label, null);
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
        x: manualValues,
        y: kataLabels,
        name: 'Manual (Sem IA)',
        marker: {
          color: '#f59e0b',
          symbol: 'diamond',
          size: 11,
          line: { color: isDark ? '#0d1117' : '#ffffff', width: 1 },
        },
        hovertemplate: `<b>%{y}</b> (Manual): %{x:.${formatDecimals}f}<extra></extra>`,
      },
      {
        type: 'scatter',
        mode: 'markers',
        x: aiValues,
        y: kataLabels,
        name: 'Com IA',
        marker: {
          color: '#a371f7',
          symbol: 'circle',
          size: 13,
          line: { color: isDark ? '#0d1117' : '#ffffff', width: 1.5 },
        },
        hovertemplate: `<b>%{y}</b> (IA): %{x:.${formatDecimals}f}<extra></extra>`,
      },
    ];
  } else {
    // Scatter mode: LOC (controle) vs CC Média
    chartData = [
      {
        type: 'scatter',
        mode: 'markers',
        x: aiTrials.map((t) => t.loc),
        y: aiTrials.map((t) => t.cc_avg),
        name: 'Com Assistente de IA',
        marker: { color: '#a371f7', size: 10, symbol: 'circle' },
        text: aiTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: '<b>%{text}</b> (IA)<br>LOC: %{x} · CC: %{y:.1f}<extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'markers',
        x: manualTrials.map((t) => t.loc),
        y: manualTrials.map((t) => t.cc_avg),
        name: 'Manual (Sem IA)',
        marker: { color: '#f59e0b', size: 10, symbol: 'diamond' },
        text: manualTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: '<b>%{text}</b> (Manual)<br>LOC: %{x} · CC: %{y:.1f}<extra></extra>',
      },
    ];
  }

  const layout: Partial<Plotly.Layout> = {
    yaxis:
      viewMode === 'kata'
        ? {
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
            autorange: 'reversed',
            automargin: true,
          }
        : viewMode === 'scatter'
        ? {
            title: { text: 'Complexidade Ciclomática (CC Média)', font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
          }
        : {
            title: { text: yAxisTitle, font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
          },
    xaxis:
      viewMode === 'kata'
        ? {
            title: { text: yAxisTitle, font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
          }
        : viewMode === 'scatter'
        ? {
            title: { text: 'Linhas Físicas (LOC) — Controle GQM', font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
          }
        : {
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: 'transparent',
          },
    margin: viewMode === 'kata' ? { l: 115, r: 20, t: 15, b: 40 } : { l: 55, r: 20, t: 15, b: 40 },
    legend: {
      orientation: 'h',
      y: 1.15,
      x: 0,
      font: { size: 10, color: axisFontColor },
    },
  };

  const actionControls = (
    <div className="flex flex-wrap items-center gap-2">
      <SegmentedControl<ViewMode>
        value={viewMode}
        onChange={setViewMode}
        activeColorClass="text-purple-600 dark:text-purple-400"
        options={[
          { value: 'overall', label: 'Geral (Boxplot)' },
          { value: 'kata', label: 'Por Kata (Dumbbell)' },
          { value: 'scatter', label: 'Dispersão (LOC vs CC)' },
        ]}
      />
      {viewMode !== 'scatter' && (
        <SegmentedControl<MetricKey>
          value={metric}
          onChange={setMetric}
          activeColorClass="text-purple-600 dark:text-purple-400"
          options={[
            { value: 'cc', label: 'CC' },
            { value: 'mi', label: 'MI' },
            { value: 'loc', label: 'LOC' },
            { value: 'dup', label: 'Duplicação' },
          ]}
        />
      )}
    </div>
  );

  const currentSubtitle =
    viewMode === 'scatter'
      ? 'Dispersão de Linhas de Código (LOC) vs Complexidade Ciclomática (CC) como métrica de controle metodológico'
      : metricDescription;

  return (
    <RQCardWrapper
      pillLabel="RQ3 · Métricas Estruturais de Código"
      pillVariant="purple"
      title="O assistente de IA altera a complexidade ou manutenibilidade do código?"
      subtitle={currentSubtitle}
      action={actionControls}
    >
      <div className="w-full h-72">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
