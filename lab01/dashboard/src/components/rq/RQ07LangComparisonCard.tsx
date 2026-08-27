import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { useTheme } from '../../hooks/useTheme';

interface RQ07LangComparisonCardProps {
  stats: RQStats;
}

export const RQ07LangComparisonCard: React.FC<RQ07LangComparisonCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('linear');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      name: 'Mediana de PRs',
      x: stats.rq07.labels,
      y: stats.rq07.median_prs,
      marker: { color: '#2f81f7' },
    },
    {
      type: 'bar' as const,
      name: 'Mediana de Releases',
      x: stats.rq07.labels,
      y: stats.rq07.median_releases,
      marker: { color: '#238636' },
    },
    {
      type: 'bar' as const,
      name: 'Mediana Dias s/ Update',
      x: stats.rq07.labels,
      y: stats.rq07.median_update_days,
      marker: { color: '#d29922' },
    },
  ];

  const layout = {
    barmode: 'group' as const,
    yaxis: {
      type: scale === 'log' ? ('log' as const) : ('linear' as const),
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: gridColor,
      title: { text: scale === 'log' ? 'Valor da Mediana (Log)' : 'Valor da Mediana', font: { size: 11, color: axisFontColor } },
    },
    xaxis: {
      tickfont: { size: 10, color: axisFontColor },
      tickangle: -30,
      gridcolor: 'transparent',
    },
    legend: {
      orientation: 'h' as const,
      x: 0.5,
      xanchor: 'center' as const,
      y: -0.25,
      font: { size: 11, color: axisFontColor },
    },
    margin: { l: 50, r: 20, t: 15, b: 70 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ07 · Comparativo Multidimensional por Linguagem"
      title="Medianas de PRs, Releases e Dias sem Update por Linguagem"
      subtitle="Compara o comportamento e fluxo de entrega nas linguagens de maior volume."
      scale={scale}
      onToggleScale={() => setScale(scale === 'linear' ? 'log' : 'linear')}
      className="p-4 sm:p-6"
    >
      <div className="w-full h-80 mt-1">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
