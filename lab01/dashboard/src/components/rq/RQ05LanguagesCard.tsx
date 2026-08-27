import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmt, fmtPct } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ05LanguagesCardProps {
  stats: RQStats;
}

export const RQ05LanguagesCard: React.FC<RQ05LanguagesCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('linear');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      x: stats.rq05.labels,
      y: stats.rq05.counts,
      marker: { color: '#8957e5' },
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
      tickangle: -30,
      gridcolor: 'transparent',
    },
    margin: { l: 50, r: 20, t: 15, b: 60 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ05 · Linguagens Mais Populares"
      pillColorClass="bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300"
      title="Top 12 Linguagens Primárias"
      subtitle={
        <>
          Sem linguagem: <b>{fmt(stats.rq05.missing)} repos ({fmtPct(stats.rq05.missing_pct, 1)})</b>
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
