import React from 'react';
import { RQStats } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { RQCardWrapper } from '../common/RQCardWrapper';
import { fmtPct } from '../../utils/formatters';
import { useTheme } from '../../hooks/useTheme';

interface RQ03ReleasesCardProps {
  stats: RQStats;
}

export const RQ03ReleasesCard: React.FC<RQ03ReleasesCardProps> = ({ stats }) => {
  const { isDark } = useTheme();

  const axisFontColor = isDark ? '#c9d1d9' : '#24292f';

  const chartData = [
    {
      type: 'pie' as const,
      labels: ['Com Releases (>0)', 'Sem Releases (0)'],
      values: [stats.rq03.nonzero_pct, stats.rq03.zero_pct],
      hole: 0.6,
      marker: {
        colors: ['#238636', isDark ? '#30363d' : '#d0d7de'],
      },
      textinfo: 'label+percent' as const,
      textposition: 'outside' as const,
      textfont: { size: 11, color: axisFontColor },
      hovertemplate: '<b>%{label}</b>: %{value:.1f}%<extra></extra>',
    },
  ];

  const layout = {
    showlegend: false,
    margin: { l: 20, r: 20, t: 20, b: 20 },
  };

  return (
    <RQCardWrapper
      pillLabel="RQ03 · Total de Releases"
      pillColorClass="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
      title="Adesão ao Recurso Oficial de Releases"
      subtitle={
        <>
          <b>{fmtPct(stats.rq03.zero_pct, 1)}</b> dos repositórios possuem exatamente 0 releases cadastradas no GitHub.
        </>
      }
    >
      <div className="w-full h-64 flex items-center justify-center">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </RQCardWrapper>
  );
};
