export const ROTULO_SITUACAO: Record<string, string> = {
  com_bot: 'com_bot (parâmetros reais)',
  sem_bot: 'sem_bot (parâmetros reais)',
  referencia: 'referência (n=30, σ=1)',
  n_pequeno: 'n pequeno (n=10)',
  assimetria_extrema: 'assimetria extrema (σ=3)',
  outliers: 'outliers (5% × 20)',
};

export const NOME_TESTE: Record<string, string> = {
  welch: 't de Welch',
  mannwhitney: 'Mann-Whitney',
};

export function formatNumber(val: number | null | undefined, decimals = 2): string {
  if (val === null || val === undefined || !Number.isFinite(val)) return '—';
  return val.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined || !Number.isFinite(val)) return '—';
  const pct = val <= 1.0 ? val * 100 : val;
  return `${pct.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}

export function formatPValue(p: number | null | undefined): string {
  if (p === null || p === undefined || !Number.isFinite(p)) return '—';
  if (p < 0.0001) return '< 0,0001';
  return formatNumber(p, 4);
}

export function formatHours(hours: number | null | undefined, decimals = 2): string {
  if (hours === null || hours === undefined || !Number.isFinite(hours)) return '—';
  return `${formatNumber(hours, decimals)} h`;
}
