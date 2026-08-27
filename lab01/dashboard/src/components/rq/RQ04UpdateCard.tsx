import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmt, fmtDec } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ04UpdateCardProps {
  stats: RQStats;
}

export const RQ04UpdateCard: React.FC<RQ04UpdateCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('linear');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      x: stats.rq04.labels,
      y: stats.rq04.counts,
      marker: {
        color: ['#238636', '#2ea043', '#56d364', '#d29922', '#db6d28', '#f85149'],
      },
      hovertemplate: '<b>%{x}</b>: %{y:,} repositórios<extra></extra>',
    },
  ];

  const layout = {
    yaxis: {
      type: scale === 'log' ? ('log' as const) : ('linear' as const),
      tickfont: { size: 10, color: axisFontColor },
      gridcolor: gridColor,
      title: { text: scale === 'log' ? 'Repositórios (Log)' : 'Repositórios', font: { size: 11, color: axisFontColor } },
    },
    xaxis: {
      tickfont: { size: 10, color: axisFontColor },
      tickangle: -20,
      gridcolor: 'transparent',
    },
    margin: { l: 50, r: 20, t: 15, b: 50 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ04 · Recência de Atualização"
      pillColorClass="bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300"
      title="Intervalo até o Último Push / Update"
      subtitle={
        <>
          Mediana: <b>{fmt(stats.rq04.median)} dias</b> · Média: <b>{fmtDec(stats.rq04.mean, 1)} dias</b>
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
