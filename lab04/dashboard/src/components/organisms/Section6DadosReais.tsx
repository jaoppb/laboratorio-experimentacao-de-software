import React from 'react';
import { DashboardBundle, RealPR } from '../../types/dataset';
import { RQCardWrapper } from '../molecules/RQCardWrapper';
import { RawDataTable } from './RawDataTable';
import { formatNumber, formatPValue } from '../../utils/formatters';
import { Badge } from '../atoms/Badge';

interface Section6DadosReaisProps {
  bundle: DashboardBundle;
  realPRs: RealPR[];
  grupoFilter?: 'all' | 'com_bot' | 'sem_bot';
  onGrupoFilterChange?: (grupo: 'all' | 'com_bot' | 'sem_bot') => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export const Section6DadosReais: React.FC<Section6DadosReaisProps> = ({
  bundle,
  realPRs,
  grupoFilter,
  onGrupoFilterChange,
  searchQuery,
  onSearchChange,
}) => {
  const r = bundle.resultado_testes;
  const texto = bundle.textos.secao_6;

  const w = r.welch;
  const mw = r.mannwhitney;
  const alpha = r.alfa;

  const wRejeita = w.p_valor < alpha;
  const mwRejeita = mw.p_valor < alpha;

  return (
    <RQCardWrapper
      id="dados-reais"
      pillLabel="Seção 6"
      pillVariant="primary"
      title="6. Dados reais: Aplicação Empírica dos Testes ao Repositório tailwindcss"
      subtitle="Resultados dos testes de hipótese aplicados diretamente aos 60 PRs coletados"
    >
      <div className="space-y-6">
        <p className="secao-texto text-sm sm:text-base text-gray-700 dark:text-github-text leading-relaxed">
          {texto}
        </p>

        {/* Tabela Comparativa de Testes */}
        <div className="overflow-x-auto border border-gray-200 dark:border-github-border rounded-xl shadow-sm">
          <table className="tabela-testes w-full text-left text-xs sm:text-sm text-gray-700 dark:text-github-text">
            <thead className="bg-gray-50 dark:bg-github-dark border-b border-gray-200 dark:border-github-border text-gray-600 dark:text-github-muted uppercase font-semibold text-xs">
              <tr>
                <th className="py-3 px-4">Teste</th>
                <th className="py-3 px-4">Estatística</th>
                <th className="py-3 px-4">p-valor</th>
                <th className="py-3 px-4">Tamanho do efeito</th>
                <th className="py-3 px-4">Conclusão</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-github-border/60">
              <tr className="hover:bg-gray-50/50 dark:hover:bg-github-dark/40 transition">
                <td className="py-3 px-4 font-bold text-gray-900 dark:text-white">
                  <Badge variant="welch">t de Welch</Badge>
                </td>
                <td className="py-3 px-4 font-mono">
                  t = {formatNumber(w.estatistica, 3)} (gl = {formatNumber(w.gl, 1)})
                </td>
                <td className="py-3 px-4 font-mono font-bold">
                  {formatNumber(w.p_valor, 4)}
                </td>
                <td className="py-3 px-4">
                  d de Cohen = {formatNumber(w.tamanho_efeito, 3)} ({w.magnitude_efeito})
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        wRejeita ? 'bg-red-500' : 'bg-emerald-500'
                      }`}
                    />
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {wRejeita ? 'Rejeita H₀' : 'Não rejeita H₀'}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-github-muted">
                      (α = {formatNumber(alpha, 2)}): sem evidência de diferença
                    </span>
                  </div>
                </td>
              </tr>

              <tr className="hover:bg-gray-50/50 dark:hover:bg-github-dark/40 transition">
                <td className="py-3 px-4 font-bold text-gray-900 dark:text-white">
                  <Badge variant="mannwhitney">Mann-Whitney</Badge>
                </td>
                <td className="py-3 px-4 font-mono">
                  z = {formatNumber(mw.estatistica, 3)} (U = {mw.u})
                </td>
                <td className="py-3 px-4 font-mono font-bold">
                  {formatNumber(mw.p_valor, 4)}
                </td>
                <td className="py-3 px-4">
                  rank-biserial = {formatNumber(mw.tamanho_efeito, 3)} ({mw.magnitude_efeito})
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        mwRejeita ? 'bg-red-500' : 'bg-emerald-500'
                      }`}
                    />
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {mwRejeita ? 'Rejeita H₀' : 'Não rejeita H₀'}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-github-muted">
                      (α = {formatNumber(alpha, 2)}): sem evidência de diferença
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Inspetor Explorável dos PRs Reais */}
        <RawDataTable
          prs={realPRs}
          grupoFilter={grupoFilter}
          onGrupoFilterChange={onGrupoFilterChange}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
        />
      </div>
    </RQCardWrapper>
  );
};
