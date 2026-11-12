import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import { DashboardBundle, FilterState } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { useTheme } from '../../hooks/useTheme';
import { NOME_TESTE, ROTULO_SITUACAO } from '../../utils/formatters';

interface Section4ErroTipo1G3Props {
  bundle: DashboardBundle;
  filters: FilterState;
}

export const Section4ErroTipo1G3: React.FC<Section4ErroTipo1G3Props> = ({
  bundle,
  filters,
}) => {
  const { isDark } = useTheme();
  const is01 = filters.alpha === 0.01;
  const texto = is01 ? bundle.textos.secao_4_alfa_001 : bundle.textos.secao_4_alfa_005;
  const rows = is01 ? bundle.simulacoes.erro_tipo1_001 : bundle.simulacoes.erro_tipo1_005;

  const { chartData, chartLayout } = useMemo(() => {
    // Filter rows by selectedScenario and selectedTest
    let filtered = rows;
    if (filters.selectedScenario !== 'all') {
      filtered = filtered.filter((r) => r.cenario === filters.selectedScenario);
    }
    if (filters.selectedTest !== 'all') {
      filtered = filtered.filter((r) => r.teste === filters.selectedTest);
    }

    // Get unique scenarios in order
    const allScenarios = Array.from(new Set(rows.map((r) => r.cenario)));
    const scenarios = allScenarios.filter((s) => filtered.some((r) => r.cenario === s));
    const labels = scenarios.map((s) => ROTULO_SITUACAO[s] || s);

    const corWelch = '#0072B2';
    const corMW = '#D55E00';
    const data: Plotly.Data[] = [];

    const testsToInclude =
      filters.selectedTest === 'all'
        ? ['welch', 'mannwhitney']
        : [filters.selectedTest];

    for (const teste of testsToInclude) {
      const sub = scenarios.map((scen) => {
        const found = filtered.find((r) => r.cenario === scen && r.teste === teste);
        return found ? found.taxa_rejeicao * 100.0 : 0;
      });
      const errors = scenarios.map((scen) => {
        const found = filtered.find((r) => r.cenario === scen && r.teste === teste);
        return found ? found.margem_erro_pct : 0;
      });

      data.push({
        type: 'bar',
        x: labels,
        y: sub,
        name: NOME_TESTE[teste] || teste,
        marker: {
          color: teste === 'welch' ? corWelch : corMW,
        },
        error_y: {
          type: 'data',
          array: errors,
          visible: true,
          color: isDark ? '#c9d1d9' : '#334155',
        },
        text: sub.map((v) => `${v.toFixed(1)}%`),
        textposition: 'outside',
        hovertemplate: '%{x}<br>%{y:.2f}% ± %{error_y.array:.2f}%<extra>' + (NOME_TESTE[teste] || teste) + '</extra>',
      });
    }

    const expectedAlpha = filters.alpha * 100.0;
    const maxVal = Math.max(expectedAlpha, ...data.flatMap((d) => ((d as any).y as number[]) || [0]));
    const yMax = Math.max(8.0, maxVal * 1.3);

    const layout: Partial<Plotly.Layout> = {
      title: {
        text: `G3 — Erro tipo I dos testes sob H0 verdadeira (α = ${filters.alpha})`,
        font: { size: 14, color: isDark ? '#ffffff' : '#0f172a' },
        x: 0.5,
        xanchor: 'center',
        y: 0.96,
        yanchor: 'top',
      },
      margin: { l: 64, r: 110, t: 90, b: 160 },
      barmode: 'group',
      xaxis: {
        title: { text: 'Situação simulada (cenários de H0 verdadeira)' },
        tickangle: -20,
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      yaxis: {
        title: { text: 'Taxa de rejeição (%)' },
        range: [0, yMax],
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      shapes: [
        {
          type: 'line',
          layer: 'below',
          xref: 'paper',
          yref: 'y',
          x0: 0,
          x1: 1,
          y0: expectedAlpha,
          y1: expectedAlpha,
          line: {
            color: '#E69F00',
            width: 2,
            dash: 'dash',
          },
        },
      ],
      annotations: [
        {
          xref: 'paper',
          yref: 'y',
          x: 1.005,
          y: expectedAlpha + yMax * 0.03,
          text: `α = ${expectedAlpha}%<br>esperado`,
          showarrow: false,
          xanchor: 'left',
          font: { color: '#E69F00', size: 11, family: 'monospace' },
        },
      ],
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
  }, [rows, filters.selectedScenario, filters.selectedTest, filters.alpha, isDark]);

  return (
    <RQCardWrapper
      id="erro-tipo-i"
      pillLabel="Seção 4"
      pillVariant="primary"
      title="4. Erro tipo I (G3): Controle de Falsos Positivos sob H₀ Verdadeira"
      subtitle="Proporção de rejeições empíricas em 10.000 repetições de Monte Carlo com intervalo de confiança de 95%"
    >
      <div className="space-y-4">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        <div id="grafico_g3" className="w-full bg-white dark:bg-github-dark border border-gray-100 dark:border-github-border rounded-xl p-2 sm:p-4">
          <PlotlyChart
            data={chartData}
            layout={chartLayout}
            className="w-full h-[420px]"
          />
        </div>
      </div>
    </RQCardWrapper>
  );
};
