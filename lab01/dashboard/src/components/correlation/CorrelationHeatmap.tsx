import React from 'react';
import { Network, Info } from 'lucide-react';
import { CorrelationMatrix } from '../../types/dataset';
import { PlotlyChart } from '../PlotlyChart';
import { CorrelationLegend } from './CorrelationLegend';
import { useTheme } from '../../hooks/useTheme';

interface CorrelationHeatmapProps {
  correlation: CorrelationMatrix | null;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({ correlation }) => {
  const { isDark } = useTheme();

  if (!correlation || !correlation.variables.length) return null;

  const names = correlation.variables.map((v) => v.name);
  const zValues = correlation.matrix;

  const annotations = names.flatMap((rowName, i) =>
    names.map((colName, j) => {
      const val = zValues[i][j];
      const isExtreme = Math.abs(val) > 0.45;
      return {
        x: colName,
        y: rowName,
        text: val === 1 ? '1.00' : (val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)),
        font: { color: isDark ? '#ffffff' : (isExtreme ? '#ffffff' : '#1f2328'), size: 11, weight: 'bold' as const },
        showarrow: false,
      };
    })
  );

  const colorscale = isDark
    ? [[0, '#f85149'], [0.35, '#da3633'], [0.5, '#161b22'], [0.65, '#1f6feb'], [1, '#2f81f7']]
    : [[0, '#cf222e'], [0.35, '#ff8182'], [0.5, '#f6f8fa'], [0.65, '#54aeff'], [1, '#0969da']];

  const heatmapData = [{
    type: 'heatmap' as const,
    z: zValues,
    x: names,
    y: names,
    colorscale: colorscale as any,
    zmin: -1,
    zmax: 1,
    hoverongaps: false,
    hovertemplate: '<b>%{y}</b> × <b>%{x}</b><br>Spearman &rho;: <b>%{z:.3f}</b><extra></extra>',
    colorbar: {
      title: { text: '&rho; Spearman', side: 'right' as const, font: { size: 11 } },
      tickvals: [-1, -0.5, 0, 0.5, 1],
      ticktext: ['-1.0', '-0.5', '0.0', '+0.5', '+1.0'],
      len: 0.85,
      thickness: 14,
      tickfont: { size: 10, color: isDark ? '#8b949e' : '#6e7781' },
    },
  }];

  const heatmapLayout = {
    annotations,
    xaxis: { tickfont: { size: 11, color: isDark ? '#c9d1d9' : '#24292f' }, tickangle: -25, gridcolor: 'transparent' },
    yaxis: { tickfont: { size: 11, color: isDark ? '#c9d1d9' : '#24292f' }, autorange: 'reversed' as const, gridcolor: 'transparent' },
    margin: { l: 110, r: 40, t: 20, b: 70 },
  };

  return (
    <div className="bg-white dark:bg-github-card border border-gray-200 dark:border-github-border rounded-xl shadow-sm p-4 sm:p-6 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-gray-100 dark:border-github-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-bold text-base sm:text-lg text-gray-900 dark:text-white">Interactive Correlation Heatmap</h2>
            <p className="text-xs text-gray-500 dark:text-github-muted">Matriz de correlação de Spearman (&rho;) sobre os repositórios filtrados ({correlation.sampleSize.toLocaleString('pt-BR')} amostras).</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-3 py-1 rounded-full font-medium self-start sm:self-auto">
          <Info className="w-3.5 h-3.5" /><span>Não-paramétrico</span>
        </div>
      </div>
      <div className="w-full h-[400px] mt-2">
        <PlotlyChart data={heatmapData} layout={heatmapLayout} className="w-full h-full" />
      </div>
      <CorrelationLegend />
    </div>
  );
};
