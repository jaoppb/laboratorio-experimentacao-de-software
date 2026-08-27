import React from 'react';
import Plotly from 'plotly.js-dist-min';
import { PlotlyChart } from '../PlotlyChart';
import { useTheme } from '../../hooks/useTheme';

interface BenchmarkRadarChartProps {
  radarData: { metric: string; score: number }[];
  repoName: string;
}

export const BenchmarkRadarChart: React.FC<BenchmarkRadarChartProps> = ({
  radarData,
  repoName,
}) => {
  const { isDark } = useTheme();

  const radarMetrics = radarData.map((d) => d.metric);
  const radarScores = radarData.map((d) => d.score);

  const chartData = [
    {
      type: 'scatterpolar' as const,
      r: radarScores.concat([radarScores[0]]), // close polygon
      theta: radarMetrics.concat([radarMetrics[0]]),
      fill: 'toself',
      name: repoName,
      line: { color: '#2f81f7', width: 2.5 },
      fillcolor: isDark ? 'rgba(47, 129, 247, 0.25)' : 'rgba(47, 129, 247, 0.15)',
    },
    {
      type: 'scatterpolar' as const,
      r: [50, 50, 50, 50, 50, 50, 50],
      theta: radarMetrics.concat([radarMetrics[0]]),
      name: 'Mediana Global (P50)',
      line: { color: isDark ? '#8b949e' : '#6e7781', dash: 'dot', width: 1.5 },
      fill: 'none',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    polar: {
      radialaxis: {
        visible: true,
        range: [0, 100] as [number, number],
        tickfont: { size: 10, color: isDark ? '#8b949e' : '#6e7781' },
        gridcolor: isDark ? '#30363d' : '#e1e4e8',
      },
      angularaxis: {
        tickfont: { size: 11, color: isDark ? '#c9d1d9' : '#24292f' },
        gridcolor: isDark ? '#30363d' : '#e1e4e8',
        linecolor: isDark ? '#30363d' : '#e1e4e8',
      },
      bgcolor: 'transparent',
    },
    showlegend: true,
    legend: {
      orientation: 'h' as const,
      x: 0.5,
      xanchor: 'center' as const,
      y: -0.15,
      font: { size: 11, color: isDark ? '#c9d1d9' : '#24292f' },
    },
    margin: { l: 30, r: 30, t: 20, b: 30 },
  };

  return (
    <div className="lg:col-span-5 flex flex-col items-center justify-center p-2 rounded-xl bg-gray-50/50 dark:bg-github-darker/50 border border-gray-200 dark:border-github-border">
      <div className="text-xs font-bold text-gray-700 dark:text-github-text uppercase tracking-wider mb-1 flex items-center gap-1.5">
        Radar Multidimensional (Percentis)
      </div>
      <div className="w-full h-[320px]">
        <PlotlyChart data={chartData} layout={layout} className="w-full h-full" />
      </div>
    </div>
  );
};
