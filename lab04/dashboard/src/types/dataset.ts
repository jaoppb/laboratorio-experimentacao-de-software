export interface RealPR {
  repo: string;
  pr_number: number;
  grupo: 'com_bot' | 'sem_bot';
  tempo_merge_horas: number;
  url: string;
}

export interface ParametroGrupo {
  n: number;
  mediana: number;
  sigma_log: number;
}

export interface ParametrosJson {
  com_bot: ParametroGrupo;
  sem_bot: ParametroGrupo;
}

export interface ResultadoTesteWelch {
  estatistica: number;
  p_valor: number;
  tamanho_efeito: number;
  alternativa: string;
  gl: number;
  magnitude_efeito: string;
  conclusao: string;
}

export interface ResultadoTesteMannWhitney {
  estatistica: number;
  p_valor: number;
  tamanho_efeito: number;
  alternativa: string;
  u: number;
  magnitude_efeito: string;
  conclusao: string;
}

export interface ResultadoTestesJson {
  alfa: number;
  alternativa: string;
  n: {
    com_bot: number;
    sem_bot: number;
  };
  medianas_horas: {
    com_bot: number;
    sem_bot: number;
  };
  medias_horas: {
    com_bot: number;
    sem_bot: number;
  };
  welch: ResultadoTesteWelch;
  mannwhitney: ResultadoTesteMannWhitney;
  concordam: boolean;
}

export interface ExemploSimuladoRow {
  grupo: 'com_bot' | 'sem_bot';
  valor: number;
}

export interface ExemploResultadoJson {
  semente: number;
  parametros: {
    com_bot: ParametroGrupo;
    sem_bot: ParametroGrupo;
    alpha: number;
  };
  welch: {
    estatistica: number;
    p_valor: number;
    tamanho_efeito: number;
    alternativa?: string;
    gl: number;
  };
  mannwhitney: {
    estatistica: number;
    p_valor: number;
    tamanho_efeito: number;
    alternativa?: string;
    u: number;
  };
  medianas_amostrais: {
    com_bot: number;
    sem_bot: number;
  };
  medias_amostrais: {
    com_bot: number;
    sem_bot: number;
  };
}

export interface ErroTipo1Row {
  cenario: string;
  teste: 'welch' | 'mannwhitney';
  n_rep: number;
  alfa: number;
  taxa_rejeicao: number;
  margem_erro_pct: number;
}

export interface PoderRow {
  cenario: string;
  teste: 'welch' | 'mannwhitney';
  razao_medianas: number;
  n_rep: number;
  alfa: number;
  taxa_rejeicao: number;
}

export interface G2DistData {
  welch: {
    gl: number;
    estatistica: number;
    p_valor: number;
    critico_005: number;
    critico_001: number;
    x: number[];
    y: number[];
  };
  mannwhitney: {
    estatistica: number;
    p_valor: number;
    u: number;
    critico_005: number;
    critico_001: number;
    x: number[];
    y: number[];
  };
}

export interface DashboardBundle {
  links: {
    repo: string;
    projects: string;
    pages: string;
  };
  parametros: ParametrosJson;
  resultado_exemplo: ExemploResultadoJson;
  resultado_testes: ResultadoTestesJson;
  textos: {
    secao_1: string;
    secao_2: string;
    secao_3: string;
    secao_4_alfa_005: string;
    secao_4_alfa_001: string;
    secao_5_alfa_005: string;
    secao_5_alfa_001: string;
    sensibilidade_alfa: string;
    secao_6: string;
    secao_7: string;
  };
  g2: G2DistData;
  simulacoes: {
    erro_tipo1_005: ErroTipo1Row[];
    erro_tipo1_001: ErroTipo1Row[];
    poder_005: PoderRow[];
    poder_001: PoderRow[];
  };
}

export interface FilterState {
  alpha: 0.05 | 0.01;
  selectedScenario: string;
  selectedTest: 'all' | 'welch' | 'mannwhitney';
  grupoFilter: 'all' | 'com_bot' | 'sem_bot';
  searchQuery: string;
}
