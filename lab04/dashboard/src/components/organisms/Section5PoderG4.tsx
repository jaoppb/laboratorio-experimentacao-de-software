import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import { AlertCircle, Sliders } from 'lucide-react';
import { DashboardBundle, FilterState } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { useTheme } from '../../hooks/useTheme';
import { NOME_TESTE, ROTULO_SITUACAO } from '../../utils/formatters';
import { Badge } from '../atoms/Badge';

interface Section5PoderG4Props {
  bundle: DashboardBundle;
  filters: FilterState;
}

const DASH_STYLES: Plotly.Dash[] = ['solid', 'dash', 'dot', 'dashdot', 'longdash', 'longdashdot'];
const SYMBOLS = ['circle', 'square', 'diamond', 'triangle-up', 'x', 'cross'];

export const Section5PoderG4: React.FC<Section5PoderG4Props> = ({
  bundle,
  filters,
}) => {
  const { isDark } = useTheme();
  const is01 = filters.alpha === 0.01;
  const texto = is01 ? bundle.textos.secao_5_alfa_001 : bundle.textos.secao_5_alfa_005;
  const textoSensibilidade = bundle.textos.sensibilidade_alfa;
  const rows = is01 ? bundle.simulacoes.poder_001 : bundle.simulacoes.poder_005;

  const { chartData, chartLayout } = useMemo(() => {
    let filtered = rows;
    if (filters.selectedScenario !== 'all') {
      filtered = filtered.filter((r) => r.cenario === filters.selectedScenario);
    }
    if (filters.selectedTest !== 'all') {
      filtered = filtered.filter((r) => r.teste === filters.selectedTest);
    }

    const scenarios = Array.from(new Set(filtered.map((r) => r.cenario)));
    const corWelch = '#0072B2';
    const corMW = '#D55E00';
    const data: Plotly.Data[] = [];

    const testsToInclude =
      filters.selectedTest === 'all'
        ? ['welch', 'mannwhitney']
        : [filters.selectedTest];

    scenarios.forEach((scen, idx) => {
      const dash = DASH_STYLES[idx % DASH_STYLES.length];
      const symbol = SYMBOLS[idx % SYMBOLS.length];
      const scenLabel = ROTULO_SITUACAO[scen] || scen;

      for (const teste of testsToInclude) {
        const sub = filtered
          .filter((r) => r.cenario === scen && r.teste === teste)
          .sort((a, b) => a.razao_medianas - b.razao_medianas);

        if (sub.length === 0) continue;

        const color = teste === 'welch' ? corWelch : corMW;
        const testLabel = NOME_TESTE[teste] || teste;

        data.push({
          type: 'scatter',
          mode: 'lines+markers',
          x: sub.map((r) => r.razao_medianas),
          y: sub.map((r) => r.taxa_rejeicao * 100.0),
          name: `${testLabel} — ${scenLabel}`,
          line: { color, dash, width: 2 },
          marker: { color, symbol: symbol as any, size: 7 },
          legendgroup: scen,
          hovertemplate:
            'razão %{x}×<br>%{y:.1f}% de rejeições<extra>' +
            `${testLabel} — ${scenLabel}` +
            '</extra>',
        });
      }
    });

    const expectedAlpha = filters.alpha * 100.0;

    const layout: Partial<Plotly.Layout> = {
      title: {
        text: `G4 — Curvas de poder dos testes (α = ${filters.alpha})`,
        font: { size: 14, color: isDark ? '#ffffff' : '#0f172a' },
        x: 0.5,
        xanchor: 'center',
        y: 0.96,
        yanchor: 'top',
      },
      margin: { l: 64, r: 110, t: 90, b: 170 },
      xaxis: {
        title: { text: 'Tamanho do efeito (razão entre as medianas M_com / M_sem)' },
        range: [0.8, 8.2],
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      yaxis: {
        title: { text: 'Taxa de rejeição (%) — Poder' },
        range: [0, 102],
        gridcolor: isDark ? '#30363d' : '#e2e8f0',
      },
      shapes: [
        {
          type: 'line',
          xref: 'paper',
          yref: 'y',
          x0: 0,
          x1: 1,
          y0: expectedAlpha,
          y1: expectedAlpha,
          line: {
            color: '#E69F00',
            width: 1.5,
            dash: 'dash',
          },
        },
      ],
      annotations: [
        {
          xref: 'paper',
          yref: 'y',
          x: 1.005,
          y: expectedAlpha + 3,
          text: `α = ${expectedAlpha}%`,
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
      id="poder"
      pillLabel="Seção 5"
      pillVariant="primary"
      title="5. Poder Estatístico (G4): Capacidade de Detecção por Razão de Medianas"
      subtitle="Curvas de poder empírico variando a razão de medianas de 1,0× (H₀) até 8,0× sob 10.000 repetições"
    >
      <div className="space-y-4">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        <div id="grafico_g4" className="w-full bg-white dark:bg-github-dark border border-gray-100 dark:border-github-border rounded-xl p-2 sm:p-4">
          <PlotlyChart
            data={chartData}
            layout={chartLayout}
            className="w-full h-[440px]"
          />
        </div>

        {/* Card / Bloco de Análise de Sensibilidade */}
        <div className="p-4 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 space-y-2">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <h4 className="text-xs sm:text-sm font-bold text-amber-900 dark:text-amber-200 uppercase tracking-wider">
              Análise de Sensibilidade ao Nível de Significância (α = 0,01 vs. α = 0,05)
            </h4>
            <Badge variant="warning">Impacto do Limiar</Badge>
          </div>
          <p id="sensibilidade-alfa" className="secao-texto text-xs sm:text-sm text-amber-900/90 dark:text-amber-200/90 leading-relaxed">
            {textoSensibilidade}
          </p>
        </div>
      </div>
    </RQCardWrapper>
  );
};
