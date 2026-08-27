export const fmt = (n: number | null | undefined): string => {
  if (n == null || isNaN(n)) return "—";
  return n.toLocaleString("pt-BR");
};

export const fmtDec = (n: number | null | undefined, digits = 2): string => {
  if (n == null || isNaN(n)) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
};

export const fmtPct = (n: number | null | undefined, digits = 1): string => {
  if (n == null || isNaN(n)) return "—";
  return `${fmtDec(n, digits)}%`;
};

export const fmtCompact = (n: number | null | undefined): string => {
  if (n == null || isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${fmtDec(n / 1_000_000, 1)}M`;
  if (Math.abs(n) >= 1_000) return `${fmtDec(n / 1_000, 1)}k`;
  return fmt(n);
};
