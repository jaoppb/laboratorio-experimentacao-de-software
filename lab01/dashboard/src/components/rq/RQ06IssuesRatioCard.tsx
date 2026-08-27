import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmtPct } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ06IssuesRatioCardProps {
  stats: RQStats;
}

export const RQ06IssuesRatioCard: React.FC<RQ06IssuesRatioCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('linear');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      x: stats.rq06.labels,
      y: stats.rq06.counts,
      marker: { color: '#1f6feb' },
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
      tickfont: { size: 11, color: axisFontColor },
      gridcolor: 'transparent',
    },
    margin: { l: 50, r: 20, t: 15, b: 40 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ06 · Resolução de Issues"
      pillColorClass="bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300"
      title="Proporção de Issues Fechadas"
      subtitle={
        <>
          Mediana: <b>{fmtPct(stats.rq06.median * 100, 1)}</b> · Média: <b>{fmtPct(stats.rq06.mean * 100, 1)}</b>
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
