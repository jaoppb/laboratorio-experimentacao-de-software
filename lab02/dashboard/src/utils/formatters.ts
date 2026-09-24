export function formatDuration(seconds: number, compact = false): string {
  if (seconds === 0) return '0.0s';
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (compact) {
    return `${mins}m ${secs}s`;
  }
  return `${mins}m ${secs}s (${seconds.toFixed(1)}s)`;
}

export function formatNumber(val: number, decimals = 1): string {
  if (isNaN(val)) return '0';
  return val.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(val: number, decimals = 1): string {
  if (isNaN(val)) return '0%';
  return `${val.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}

export const KATA_INFO: Record<string, { num: string; title: string; pretty: string }> = {
  '01-bario-world': { num: '01', title: 'Bario World', pretty: '01 · Bario World' },
  '02-cards': { num: '02', title: 'Cards', pretty: '02 · Cards' },
  '03-exploring-terrain': { num: '03', title: 'Exploring Terrain', pretty: '03 · Exploring Terrain' },
  '04-garment-groups': { num: '04', title: 'Garment Groups', pretty: '04 · Garment Groups' },
  '05-dish-rack': { num: '05', title: 'Dish Rack', pretty: '05 · Dish Rack' },
  '06-n-checkers': { num: '06', title: 'N Checkers', pretty: '06 · N Checkers' },
};

export function getKataPrettyName(kata: string): string {
  return KATA_INFO[kata]?.pretty || kata;
}

export function getKataTitle(kata: string): string {
  return KATA_INFO[kata]?.title || kata;
}

export function getModelDisplayName(modelKey: string | null): string {
  if (!modelKey || modelKey === 'manual') return 'Manual (Sem IA)';
  if (modelKey === 'gemini-flash-3.8') return 'Gemini 3.8 Flash';
  if (modelKey === 'claude-sonnet-5') return 'Claude Sonnet 5';
  if (modelKey === 'gpt-4o') return 'GPT-4o';
  return modelKey;
}
