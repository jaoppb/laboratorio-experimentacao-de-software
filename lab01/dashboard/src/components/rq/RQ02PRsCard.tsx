import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmt } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ02PRsCardProps {
  stats: RQStats;
}

export const RQ02PRsCard: React.FC<RQ02PRsCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('log');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      x: stats.rq02.q_labels,
      y: stats.rq02.q_values,
      marker: {
        color: ['#388bfd', '#2f81f7', '#1f6feb', '#8957e5', '#d29922'],
      },
      text: stats.rq02.q_values.map((v) => fmt(v)),
      textposition: 'outside' as const,
      textfont: { size: 10, color: axisFontColor },
      hovertemplate: '<b>%{x}</b>: %{y:,} PRs mesclados<extra></extra>',
    },
  ];

  const layout = {
    yaxis: {
      type: scale === 'log' ? ('log' as const) : ('linear' as const),
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: gridColor,
      title: { text: scale === 'log' ? 'PRs Mesclados (Log)' : 'PRs Mesclados', font: { size: 11, color: axisFontColor } },
    },
    xaxis: {
      tickfont: { size: 11, color: axisFontColor },
      gridcolor: 'transparent',
    },
    margin: { l: 50, r: 20, t: 25, b: 40 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ02 · Pull Requests Mesclados"
      pillColorClass="bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300"
      title="Curva de Quantis de PRs (Assimetria)"
      subtitle={
        <>
          P50: <b>{fmt(stats.rq02.median)} PRs</b> · P90: <b>{fmt(stats.rq02.q_values[3])}</b> · P99: <b>{fmt(stats.rq02.q_values[4])} PRs</b>
        </>
      }
      scale={scale}
      onToggleScale={() => setScale(scale === 'linear' ? 'log' : 'linear')}
    >
      <div className="w-full h-64">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
