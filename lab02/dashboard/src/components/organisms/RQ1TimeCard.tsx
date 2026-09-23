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
