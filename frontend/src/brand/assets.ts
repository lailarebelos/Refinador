const BASE = '/brand'

export interface AssetSet {
  /** Logo horizontal para uso em fundos do mesmo tom do tema (header/modais) */
  logoHorizontal: string
  /** Logo compacto 48×48 para uso em fundos do mesmo tom do tema (header) */
  logoCompact: string
  ampersand: string
  iconCheck: string
  iconAlert: string
  iconInfo: string
  iconQuestion: string
}

/**
 * Assets por tema — usados no HEADER (muda de fundo com o tema) e em modais.
 * Regra: "principal" = fundo claro · "branco-e-citrico" = fundo escuro.
 * NUNCA recolorir SVGs via CSS — troque de arquivo.
 */
export const THEMED_ASSETS: Record<'light' | 'dark', AssetSet> = {
  light: {
    logoHorizontal: `${BASE}/logos/localiza-co/localiza-co-horizontal-principal.svg`,
    logoCompact:    `${BASE}/logos/localiza-co/lco-compacto-principal.svg`,
    ampersand:      `${BASE}/grafismos/grafismo-ampersand-contorno-citrico.svg`,
    iconCheck:      `${BASE}/icones/balao-check.svg`,
    iconAlert:      `${BASE}/icones/balao-alerta.svg`,
    iconInfo:       `${BASE}/icones/balao-info.svg`,
    iconQuestion:   `${BASE}/icones/balao-interrogacao-citrico.svg`,
  },
  dark: {
    logoHorizontal: `${BASE}/logos/localiza-co/localiza-co-horizontal-branco-e-citrico.svg`,
    logoCompact:    `${BASE}/logos/localiza-co/lco-compacto-branco-e-citrico.svg`,
    ampersand:      `${BASE}/grafismos/grafismo-ampersand-contorno-citrico.svg`,
    iconCheck:      `${BASE}/icones/balao-check.svg`,
    iconAlert:      `${BASE}/icones/balao-alerta.svg`,
    iconInfo:       `${BASE}/icones/balao-info.svg`,
    iconQuestion:   `${BASE}/icones/balao-interrogacao-citrico.svg`,
  },
}

/**
 * Assets fixos para a SIDEBAR — que é SEMPRE verde-escura independente do tema.
 * Usa sempre as variantes "branco-e-citrico" (legíveis sobre fundo escuro).
 */
export const SIDEBAR_ASSETS = {
  logoHorizontal: `${BASE}/logos/localiza-co/localiza-co-horizontal-branco-e-citrico.svg`,
  logoCompact:    `${BASE}/logos/localiza-co/lco-compacto-branco-e-citrico.svg`,
} as const
