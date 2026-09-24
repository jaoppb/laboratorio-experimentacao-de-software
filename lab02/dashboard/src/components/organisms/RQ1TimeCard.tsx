import React, { useState } from 'react';
import { SummaryStats, UnifiedTrial } from '../../types/dataset';
import { formatDuration } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { Button } from '../atoms/Button';
import { SegmentedControl } from '../atoms/SegmentedControl';
import { RQCardWrapper } from '../molecules/RQCardWrapper';

interface RQ1TimeCardProps {
  stats: SummaryStats;
  trials: UnifiedTrial[];
}

type ViewMode = 'overall' | 'kata' | 'model';
type Unit = 'seconds' | 'minutes';

export const RQ1TimeCard: React.FC<RQ1TimeCardProps> = ({ stats, trials }) => {
  const { isDark } = useTheme();
  const [viewMode, setViewMode] = useState<ViewMode>('overall');
  const [unit, setUnit] = useState<Unit>('seconds');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const unitMultiplier = unit === 'minutes' ? 1 / 60 : 1;
  const unitLabel = unit === 'minutes' ? 'minutos' : 'segundos';

  const aiTimes = trials
    .filter((t) => t.treatment === 'ai')
    .map((t) => t.time_seconds * unitMultiplier);
  const manualTimes = trials
    .filter((t) => t.treatment === 'manual')
    .map((t) => t.time_seconds * unitMultiplier);

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
    const kataLabels = stats.kata_comparisons.map((k) => k.kata_title);
    const aiMedians = stats.kata_comparisons.map((k) => k.ai_time_median * unitMultiplier);
    const manualMedians = stats.kata_comparisons.map((k) => k.manual_time_median * unitMultiplier);

    const lineX: (number | null)[] = [];
    const lineY: (string | null)[] = [];
    stats.kata_comparisons.forEach((k) => {
      lineX.push(k.manual_time_median * unitMultiplier, k.ai_time_median * unitMultiplier, null);
      lineY.push(k.kata_title, k.kata_title, null);
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
        x: manualMedians,
        y: kataLabels,
        name: 'Manual (Mediana)',
        marker: {
          color: '#f85149',
          symbol: 'diamond',
          size: 11,
          line: { color: isDark ? '#0d1117' : '#ffffff', width: 1 },
        },
        hovertemplate: `<b>%{y}</b> (Manual): %{x:.1f} ${unitLabel}<extra></extra>`,
      },
      {
        type: 'scatter',
        mode: 'markers',
        x: aiMedians,
        y: kataLabels,
        name: 'IA (Mediana)',
        marker: {
          color: '#2f81f7',
          symbol: 'circle',
          size: 13,
          line: { color: isDark ? '#0d1117' : '#ffffff', width: 1.5 },
        },
        hovertemplate: `<b>%{y}</b> (IA): %{x:.1f} ${unitLabel}<extra></extra>`,
      },
    ];
  } else {
    // Model view: Boxplot with points showing the distribution of times per model/manual
    const modelColors: Record<string, string> = {
      'Gemini 3.8 Flash': '#2f81f7',
      'Gemini Flash 3.8': '#2f81f7',
      'Claude Sonnet 5': '#a371f7',
      'GPT-4o': '#10b981',
      'Manual (Sem IA)': '#f85149',
    };

    chartData = stats.model_comparisons.map((m) => {
      const modelTrials = trials.filter((t) => {
        const key = t.ai_model || 'Manual (Sem IA)';
        return key === m.model_name;
      });

      return {
        type: 'box',
        y: modelTrials.map((t) => t.time_seconds * unitMultiplier),
        name: m.model_name,
        marker: { color: modelColors[m.model_name] || '#8b949e' },
        boxpoints: 'all',
        jitter: 0.3,
        pointpos: -1.8,
        text: modelTrials.map((t) => `${t.kata_title} (${t.participant})`),
        hovertemplate: `<b>%{text}</b><br>${m.model_name}: %{y:.1f} ${unitLabel}<extra></extra>`,
      };
    });
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
        : {
            title: { text: `Tempo (${unitLabel})`, font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
            zerolinecolor: gridColor,
          },
    xaxis:
      viewMode === 'kata'
        ? {
            title: { text: `Tempo Mediano (${unitLabel})`, font: { size: 11, color: axisFontColor } },
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: gridColor,
          }
        : {
            tickfont: { size: 10, color: axisFontColor },
            gridcolor: 'transparent',
          },
    margin: viewMode === 'kata' ? { l: 120, r: 20, t: 15, b: 40 } : { l: 55, r: 20, t: 15, b: 40 },
    legend: {
      orientation: 'h',
      y: 1.15,
      x: 0,
      font: { size: 10, color: axisFontColor },
    },
  };

  const actionControls = (
    <div className="flex items-center gap-2">
      <SegmentedControl<ViewMode>
        value={viewMode}
        onChange={setViewMode}
        options={[
          { value: 'overall', label: 'Geral' },
          { value: 'kata', label: 'Por Kata' },
          { value: 'model', label: 'Por Modelo' },
        ]}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={() => setUnit(unit === 'seconds' ? 'minutes' : 'seconds')}
        title="Alternar entre segundos e minutos"
      >
        {unit === 'seconds' ? 'Segundos (s)' : 'Minutos (m)'}
      </Button>
    </div>
  );

  return (
    <RQCardWrapper
      pillLabel="RQ1 · Tempo de Resolução"
      pillVariant="primary"
      title="O assistente de IA reduz o tempo para resolver a tarefa?"
      subtitle={
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          <span>
            Mediana IA: <b>{formatDuration(stats.time_ai.median, true)}</b> (IQR:{' '}
            {formatDuration(stats.time_ai.iqr, true)})
          </span>
          <span>·</span>
          <span>
            Mediana Manual: <b>{formatDuration(stats.time_manual.median, true)}</b> (IQR:{' '}
            {formatDuration(stats.time_manual.iqr, true)})
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
