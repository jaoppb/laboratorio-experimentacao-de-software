import React, { useMemo, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { DashboardBundle, ExemploSimuladoRow, RealPR } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { SegmentedControl } from '../atoms/SegmentedControl';
import { PlotlyChart } from '../atoms/PlotlyChart';
import { useTheme } from '../../hooks/useTheme';

interface Section2DadosG1Props {
  bundle: DashboardBundle;
  realPRs: RealPR[];
  exemploRows: ExemploSimuladoRow[];
}

type G1ViewMode = 'both' | 'com_bot' | 'sem_bot';

export const Section2DadosG1: React.FC<Section2DadosG1Props> = ({
  bundle,
  realPRs,
  exemploRows,
}) => {
  const { isDark } = useTheme();
  const [viewMode, setViewMode] = useState<G1ViewMode>('both');
  const texto = bundle.textos.secao_2;

  const realCom = useMemo(
    () => realPRs.filter((p) => p.grupo === 'com_bot').map((p) => p.tempo_merge_horas),
    [realPRs]
  );
  const realSem = useMemo(
    () => realPRs.filter((p) => p.grupo === 'sem_bot').map((p) => p.tempo_merge_horas),
    [realPRs]
  );
  const simCom = useMemo(
    () => exemploRows.filter((p) => p.grupo === 'com_bot').map((p) => p.valor),
    [exemploRows]
  );
  const simSem = useMemo(
    () => exemploRows.filter((p) => p.grupo === 'sem_bot').map((p) => p.valor),
    [exemploRows]
  );

  const { chartData, chartLayout } = useMemo(() => {
    const corReal = '#0072B2';
    const corSimulado = '#E69F00';
    const data: Plotly.Data[] = [];

    if (viewMode === 'both') {
      // 2 subplots side by side
      data.push(
        {
          type: 'histogram',
          x: realCom,
          name: `Real: com_bot (n=${realCom.length})`,
          marker: { color: corReal, opacity: 0.65 },
          nbinsx: 15,
          xaxis: 'x',
          yaxis: 'y',
          legendgroup: 'real',
        },
        {
          type: 'histogram',
          x: simCom,
          name: `Simulado: com_bot (n=${simCom.length})`,
          marker: { color: corSimulado, opacity: 0.65 },
          nbinsx: 15,
          xaxis: 'x',
          yaxis: 'y',
          legendgroup: 'simulado',
        },
        {
          type: 'histogram',
          x: realSem,
          name: `Real: sem_bot (n=${realSem.length})`,
          marker: { color: corReal, opacity: 0.65 },
          nbinsx: 15,
          xaxis: 'x2',
          yaxis: 'y2',
          legendgroup: 'real',
        },
        {
          type: 'histogram',
          x: simSem,
          name: `Simulado: sem_bot (n=${simSem.length})`,
          marker: { color: corSimulado, opacity: 0.65 },
          nbinsx: 15,
          xaxis: 'x2',
          yaxis: 'y2',
          legendgroup: 'simulado',
        }
      );

      const layout: Partial<Plotly.Layout> = {
        title: {
          text: 'G1 — Comparação dos dados reais e simulados (tempo até o merge)',
          font: { size: 14, color: isDark ? '#ffffff' : '#0f172a' },
          x: 0.5,
          xanchor: 'center',
        },
        barmode: 'overlay',
        grid: { rows: 1, columns: 2, pattern: 'independent' },
        annotations: [
          {
            text: `<b>com_bot (CodeRabbit)</b> — Real (n=${realCom.length}) vs Simulado (n=${simCom.length})`,
            showarrow: false,
            xref: 'paper',
            yref: 'paper',
            x: 0.22,
            y: 1.12,
            font: { size: 12, color: isDark ? '#c9d1d9' : '#334155' },
          },
          {
            text: `<b>sem_bot (Controle)</b> — Real (n=${realSem.length}) vs Simulado (n=${simSem.length})`,
            showarrow: false,
            xref: 'paper',
            yref: 'paper',
            x: 0.78,
            y: 1.12,
            font: { size: 12, color: isDark ? '#c9d1d9' : '#334155' },
          },
        ],
        xaxis: {
          type: 'log',
          title: { text: 'Tempo até o merge (horas, escala log10)' },
          domain: [0, 0.46],
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        yaxis: {
          title: { text: 'Contagem de PRs' },
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        xaxis2: {
          type: 'log',
          title: { text: 'Tempo até o merge (horas, escala log10)' },
          domain: [0.54, 1.0],
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        yaxis2: {
          title: { text: 'Contagem de PRs' },
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        legend: {
          orientation: 'h',
          y: -0.22,
          x: 0.5,
          xanchor: 'center',
        },
      };

      return { chartData: data, chartLayout: layout };
    } else {
      // Single group view
      const isCom = viewMode === 'com_bot';
      const realVals = isCom ? realCom : realSem;
      const simVals = isCom ? simCom : simSem;
      const label = isCom ? 'com_bot (CodeRabbit)' : 'sem_bot (Controle)';

      data.push(
        {
          type: 'histogram',
          x: realVals,
          name: `Real: ${label} (n=${realVals.length})`,
          marker: { color: corReal, opacity: 0.65 },
          nbinsx: 20,
        },
        {
          type: 'histogram',
          x: simVals,
          name: `Simulado: ${label} (n=${simVals.length})`,
          marker: { color: corSimulado, opacity: 0.65 },
          nbinsx: 20,
        }
      );

      const layout: Partial<Plotly.Layout> = {
        title: {
          text: `G1 — ${label}: Dados Reais vs Simulados`,
          font: { size: 14, color: isDark ? '#ffffff' : '#0f172a' },
          x: 0.5,
          xanchor: 'center',
        },
        barmode: 'overlay',
        xaxis: {
          type: 'log',
          title: { text: 'Tempo até o merge (horas, escala log10)' },
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        yaxis: {
          title: { text: 'Contagem de PRs' },
          gridcolor: isDark ? '#30363d' : '#e2e8f0',
        },
        legend: {
          orientation: 'h',
          y: -0.2,
          x: 0.5,
          xanchor: 'center',
        },
      };

      return { chartData: data, chartLayout: layout };
    }
  }, [viewMode, realCom, realSem, simCom, simSem, isDark]);

  return (
    <RQCardWrapper
      id="dados"
      pillLabel="Seção 2"
      pillVariant="primary"
      title="2. Os dados (G1): Distribuições Empíricas vs. Sintéticas em Escala Logarítmica"
      subtitle="Validação da calibração lognormal por comparação de histogramas sobrepostos"
      action={
        <SegmentedControl<G1ViewMode>
          value={viewMode}
          onChange={setViewMode}
          options={[
            { value: 'both', label: 'Ambos os Grupos' },
            { value: 'com_bot', label: 'Apenas com_bot' },
            { value: 'sem_bot', label: 'Apenas sem_bot' },
          ]}
        />
      }
    >
      <div className="space-y-4">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        <div id="grafico_g1" className="w-full bg-white dark:bg-github-dark border border-gray-100 dark:border-github-border rounded-xl p-2 sm:p-4">
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
