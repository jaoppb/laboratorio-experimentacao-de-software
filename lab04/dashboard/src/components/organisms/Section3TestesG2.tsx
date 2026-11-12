import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import { DashboardBundle } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { useTheme } from '../../hooks/useTheme';
import { formatNumber, formatPValue } from '../../utils/formatters';

interface Section3TestesG2Props {
  bundle: DashboardBundle;
  activeAlpha: number;
}

export const Section3TestesG2: React.FC<Section3TestesG2Props> = ({
  bundle,
  activeAlpha,
}) => {
  const { isDark } = useTheme();
  const g2 = bundle.g2;
  const texto = bundle.textos.secao_3;

  const { chartData, chartLayout } = useMemo(() => {
    const data: Plotly.Data[] = [];
    const is01 = activeAlpha === 0.01;

    // Helper to generate panel traces
    const buildPanelTraces = (
      distInfo: {
        x: number[];
        y: number[];
        estatistica: number;
        p_valor: number;
        critico_005: number;
        critico_001: number;
      },
      rotulo: string,
      xAxis: string,
      yAxis: string,
      colGroup: string
    ) => {
      const crit = is01 ? distInfo.critico_001 : distInfo.critico_005;
      const obs = distInfo.estatistica;
      const absObs = Math.abs(obs);
      const x = distInfo.x;
      const y = distInfo.y;

      // 1. Density line
      data.push({
        type: 'scatter',
        mode: 'lines',
        x,
        y,
        name: `Densidade H₀ (${rotulo})`,
        line: { color: '#0072B2', width: 2 },
        xaxis: xAxis,
        yaxis: yAxis,
        legendgroup: `dens_${colGroup}`,
        hoverinfo: 'x+y',
      });

      // 2. Critical rejection region (|x| >= crit)
      // Left tail
      const xEsqRej: number[] = [];
      const yEsqRej: number[] = [];
      for (let i = 0; i < x.length; i++) {
        if (x[i] <= -crit) {
          xEsqRej.push(x[i]);
          yEsqRej.push(y[i]);
        }
      }
      if (xEsqRej.length > 0) {
        data.push({
          type: 'scatter',
          mode: 'none',
          x: [xEsqRej[0], ...xEsqRej, xEsqRej[xEsqRej.length - 1]],
          y: [0, ...yEsqRej, 0],
          fill: 'tozeroy',
          fillcolor: 'rgba(230, 159, 0, 0.45)',
          xaxis: xAxis,
          yaxis: yAxis,
          showlegend: false,
          legendgroup: `rej_${colGroup}`,
          hoverinfo: 'skip',
        });
      }

      // Right tail
      const xDirRej: number[] = [];
      const yDirRej: number[] = [];
      for (let i = 0; i < x.length; i++) {
        if (x[i] >= crit) {
          xDirRej.push(x[i]);
          yDirRej.push(y[i]);
        }
      }
      if (xDirRej.length > 0) {
        data.push({
          type: 'scatter',
          mode: 'none',
          x: [xDirRej[0], ...xDirRej, xDirRej[xDirRej.length - 1]],
          y: [0, ...yDirRej, 0],
          fill: 'tozeroy',
          fillcolor: 'rgba(230, 159, 0, 0.45)',
          name: `Rejeição (α = ${activeAlpha})`,
          xaxis: xAxis,
          yaxis: yAxis,
          showlegend: colGroup === '1',
          legendgroup: `rej_${colGroup}`,
          hoverinfo: 'skip',
        });
      }

      // 3. Observed p-value shaded area (|x| >= absObs)
      const xEsqP: number[] = [];
      const yEsqP: number[] = [];
      const xDirP: number[] = [];
      const yDirP: number[] = [];
      for (let i = 0; i < x.length; i++) {
        if (x[i] <= -absObs) {
          xEsqP.push(x[i]);
          yEsqP.push(y[i]);
        }
        if (x[i] >= absObs) {
          xDirP.push(x[i]);
          yDirP.push(y[i]);
        }
      }

      if (xEsqP.length > 0) {
        data.push({
          type: 'scatter',
          mode: 'none',
          x: [xEsqP[0], ...xEsqP, xEsqP[xEsqP.length - 1]],
          y: [0, ...yEsqP, 0],
          fill: 'tozeroy',
          fillcolor: 'rgba(86, 180, 233, 0.55)',
          xaxis: xAxis,
          yaxis: yAxis,
          showlegend: false,
          legendgroup: `pval_${colGroup}`,
          hoverinfo: 'skip',
        });
      }

      if (xDirP.length > 0) {
        data.push({
          type: 'scatter',
          mode: 'none',
          x: [xDirP[0], ...xDirP, xDirP[xDirP.length - 1]],
          y: [0, ...yDirP, 0],
          fill: 'tozeroy',
          fillcolor: 'rgba(86, 180, 233, 0.55)',
          name: `p-valor = ${formatPValue(distInfo.p_valor)} (duas caudas)`,
          xaxis: xAxis,
          yaxis: yAxis,
          showlegend: colGroup === '1',
          legendgroup: `pval_${colGroup}`,
          hoverinfo: 'skip',
        });
      }

      // 4. Critical vertical lines
      const maxY = Math.max(...y);
      for (const cVal of [-crit, crit]) {
        data.push({
          type: 'scatter',
          mode: 'lines',
          x: [cVal, cVal],
          y: [0, maxY * 0.95],
          line: { color: '#D55E00', width: 1.5, dash: 'dash' },
          xaxis: xAxis,
          yaxis: yAxis,
          showlegend: false,
          hoverinfo: 'skip',
        });
      }

      // 5. Observed statistic line
      data.push({
        type: 'scatter',
        mode: 'lines',
        x: [obs, obs],
        y: [0, maxY * 1.02],
        name: `Observada = ${formatNumber(obs, 3)}`,
        line: { color: isDark ? '#f0f6fc' : '#111827', width: 2.5 },
        xaxis: xAxis,
        yaxis: yAxis,
        legendgroup: `obs_${colGroup}`,
      });
    };

    // Panel 1: Welch
    buildPanelTraces(g2.welch, 'Welch', 'x', 'y', '1');
    // Panel 2: Mann-Whitney
    buildPanelTraces(g2.mannwhitney, 'Mann-Whitney', 'x2', 'y2', '2');

    const welchCrit = is01 ? g2.welch.critico_001 : g2.welch.critico_005;
    const mwCrit = is01 ? g2.mannwhitney.critico_001 : g2.mannwhitney.critico_005;

    const layout: Partial<Plotly.Layout> = {
      title: {
        text: 'G2 — Distribuição da estatística de teste sob H0',
        font: { size: 14, color: isDark ? '#ffffff' : '#0f172a' },
        x: 0.5,
        xanchor: 'center',
        y: 0.96,
        yanchor: 'top',
      },
      margin: { l: 64, r: 24, t: 90, b: 120 },
      grid: { rows: 1, columns: 2, pattern: 'independent' },
      annotations: [
        {
          text: `<b>Welch: t de Student (gl = ${formatNumber(g2.welch.gl, 1)})</b>`,
          showarrow: false,
          xref: 'paper',
          yref: 'paper',
          x: 0.22,
          y: 1.03,
            yanchor: 'bottom',
          font: { size: 12, color: isDark ? '#c9d1d9' : '#334155' },
        },
        {
          text: '<b>Mann-Whitney: normal padrão N(0, 1)</b>',
          showarrow: false,
          xref: 'paper',
          yref: 'paper',
          x: 0.78,
          y: 1.03,
            yanchor: 'bottom',
          font: { size: 12, color: isDark ? '#c9d1d9' : '#334155' },
        },
        {
          x: welchCrit,
          y: Math.max(...g2.welch.y) * 0.5,
          text: `±${formatNumber(welchCrit, 3)}`,
          showarrow: false,
          xanchor: 'left',
          font: { color: '#E69F00', size: 11 },
          xref: 'x',
          yref: 'y',
        },
        {
          x: mwCrit,
          y: Math.max(...g2.mannwhitney.y) * 0.5,
          text: `±${formatNumber(mwCrit, 3)}`,
          showarrow: false,
          xanchor: 'left',
          font: { color: '#E69F00', size: 11 },
          xref: 'x2',
          yref: 'y2',
        },
      ],
      xaxis: {
        title: { text: 'Estatística t (adimensional)' },
        domain: [0, 0.46],
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      yaxis: {
        title: { text: 'Densidade de probabilidade' },
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      xaxis2: {
        title: { text: 'Estatística z (adimensional)' },
        domain: [0.54, 1.0],
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      yaxis2: {
        title: { text: 'Densidade de probabilidade' },
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      legend: {
        orientation: 'h',
        yref: 'container',
        y: 0.01,
        yanchor: 'bottom',
        x: 0.5,
        xanchor: 'center',
      },
    };

    return { chartData: data, chartLayout: layout };
  }, [g2, activeAlpha, isDark]);

  return (
    <RQCardWrapper
      id="testes"
      pillLabel="Seção 3"
      pillVariant="primary"
      title="3. Como os testes funcionam (G2): Distribuições sob H₀ e Regiões Críticas"
      subtitle="Densidades teóricas sob a hipótese nula, limites críticos de decisão bilateral e p-valor da amostra piloto"
    >
      <div className="space-y-4">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        <div id="grafico_g2" className="w-full bg-white dark:bg-github-dark border border-gray-100 dark:border-github-border rounded-xl p-2 sm:p-4">
          <PlotlyChart
            data={chartData}
            layout={chartLayout}
            className="w-full h-[400px]"
          />
        </div>
      </div>
    </RQCardWrapper>
  );
};
