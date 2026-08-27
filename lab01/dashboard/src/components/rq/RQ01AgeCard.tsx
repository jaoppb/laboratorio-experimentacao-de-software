import React, { useState } from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmtDec } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ01AgeCardProps {
  stats: RQStats;
}

export const RQ01AgeCard: React.FC<RQ01AgeCardProps> = ({ stats }) => {
  const { isDark } = useTheme();
  const [scale, setScale] = useState<'linear' | 'log'>('linear');

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';
  const gridColor = isDark ? '#30363d' : '#e1e4e8';

  const chartData = [
    {
      type: 'bar' as const,
      x: stats.rq01.years_labels.map((l) => `${l} a`),
      y: stats.rq01.years_counts,
      marker: { color: '#2f81f7', opacity: 0.9 },
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
    margin: { l: 50, r: 20, t: 15, b: 50 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ01 · Idade dos Repositórios"
      title="Distribuição da Idade (em anos)"
      subtitle={
        <>
          Mediana: <b>{fmtDec(stats.rq01.median_years, 1)} anos</b> · Média: <b>{fmtDec(stats.rq01.mean_years, 1)} anos</b> · Máx: <b>{fmtDec(stats.rq01.max_years, 1)} anos</b>
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
