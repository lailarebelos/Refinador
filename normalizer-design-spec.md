# Especificação de Design — Qualtrics Normalizer (Localiza&CO)

> **Leia primeiro.** Este documento descreve **somente a interface** (UI/UX, layout, cores,
> tipografia, componentes visuais e comportamento de tela) do *Qualtrics Normalizer*. Ele é
> **autocontido**: tudo o que você precisa para implementar a aparência está aqui dentro. Você não
> precisa de nenhum outro projeto, repositório ou app de referência.
>
> A linguagem visual aqui descrita é a identidade oficial da **Localiza&CO**, destilada do código
> real de produtos já existentes. Os valores (hex, medidas, raios) são **fonte de verdade** — não os
> invente nem os "melhore"; copie-os.

---

## ⛔ Regra zero — NÃO TOCAR NA FUNCIONALIDADE

Esta é a restrição mais importante do projeto. **É absolutamente proibido alterar qualquer
comportamento, lógica ou saída do programa.** Você vai mexer **exclusivamente** em estilo, layout,
marcação de apresentação e componentes visuais.

Especificamente, **NÃO** modifique:
- a leitura/parse dos arquivos `.qsf` (questionário) e `.xlsx` (respondentes);
- a classificação das colunas (dicotômica, múltipla escolha, etc.) e sua lógica;
- a análise de respostas de texto aberto por LLM e qualquer chamada de API;
- o formato, o conteúdo, a estrutura de abas (`data` / `codebook`), os rótulos, a codificação de
  respostas ou qualquer característica da **planilha gerada para download**;
- nomes de funções, contratos de dados, estado de negócio, rotas de processamento.

Se uma mudança visual exigir tocar em lógica, **pare e pergunte** antes. O redesign deve ser
"plug-in" sobre a aplicação existente: as mesmas funções, com uma casca nova.

---

## ⚙️ Arquitetura (contexto para o frontend)

O Normalizer está migrando de uma interface Streamlit para um **frontend React + TypeScript + Vite**
que consome um **backend Python via FastAPI** — a mesma arquitetura de produtos irmãos da casa
(pastas `frontend/` e `backend/`, iniciadas de forma independente; o Vite dev server roda em
`localhost:5173`).

**A lógica de negócio já existe e está isolada em Python puro** (módulos `normalizer.py`,
`ai_analysis.py`, `llm_provider.py`, sem nenhuma dependência de Streamlit). Ela **não é reescrita**:
é apenas exposta por uma fina camada FastAPI (`backend/api.py`) que chama as funções existentes. O
frontend descrito nesta spec consome esses endpoints; ele **não** reimplementa parse, classificação,
análise por IA nem geração de planilha.

**Endpoints que o frontend consome** (contratos estáveis — o frontend só exibe/coleta dados):

| Endpoint | Para que serve no fluxo |
|---|---|
| `POST /api/process` | Envia os dois arquivos (`.qsf` + `.xlsx`); recebe a classificação das colunas (etapa 2) |
| `GET /api/config` | Recupera a classificação atual da sessão |
| `POST /api/normalize` | Dispara a normalização; recebe `{ rows, columns, headers }` (etapa 4) |
| `GET /api/download` | Baixa a planilha `.xlsx` gerada |
| `POST /api/llm-config` | Salva configuração de IA (tela "Configurar IA") |
| `GET /api/open-text-eligibility` *(ou equivalente)* | Lista colunas elegíveis a análise de texto aberto (etapa 3) |

O frontend mantém **sessão** com o backend (via cookie/`session_id`) para preservar arquivos e a
tabela de classificação entre as chamadas. Estados de **carregando** e **erro** desta spec (§11)
aplicam-se às chamadas de rede: toda chamada tem um estado de loading (com o indicador de marca da
§7.6) e tratamento de erro (banner da §11). Nenhum nome de campo dos contratos acima deve ser
renomeado pelo frontend.

---

## 0. O que é o Normalizer (contexto funcional, só para você entender a tela)

Aplicativo web de uso **local**. O usuário:
1. Faz **upload de dois arquivos** exportados do Qualtrics — um questionário `.qsf` e uma planilha
   de respondentes `.xlsx` (ambos da mesma pesquisa).
2. O programa **classifica as colunas** e mostra todas as perguntas com o tipo detectado, sinalizando
   as que ficaram em dúvida, para o usuário **revisar** antes de gerar.
3. Opcionalmente, o usuário **seleciona colunas de texto aberto** para o programa identificar (via
   LLM) o sentimento das respostas (negativo / neutro / positivo).
4. O usuário **gera e baixa** uma planilha normalizada (organizada, com abas `data` + `codebook`,
   colunas rotuladas, respostas simplificadas), legível por qualquer colaborador.

A tela é um **wizard de 4 etapas** que se revela conforme o usuário avança (rolagem vertical que se
prolonga). As etapas: **1 Upload · 2 Classificação · 3 Respostas abertas · 4 Exportar**.

---

## 1. Princípios inegociáveis (a "alma" da marca)

Sete pontos definem o que faz uma tela "parecer Localiza". Implementar isto errado é o que faria o
app destoar da identidade.

1. **Eco do "L" — o canto único de 4px.** Superfícies usam raio grande (16px) em três cantos e **um
   canto reduzido a 4px**, como referência ao "L" do logotipo. O canto reduzido tem **posição fixa
   por tipo de elemento** (ver §7.1).
2. **Três verdes sempre juntos; cítrico sempre em minoria.** Verde Escuro (`#003418`) nas
   superfícies profundas (sidebar); Verde Bandeira (`#018444`) nas ações; Verde Cítrico (`#78DE1F`)
   só em acentos pontuais. Como a UI é densa em texto, o fundo claro/neutro domina e os verdes
   ocupam a minoria.
3. **O cítrico NUNCA é cor de texto sobre fundo claro** (contraste 1.6:1, reprova WCAG AA). Só
   `background`, `border`, `box-shadow`, `fill` de SVG. No escuro, quando precisar de "verde como
   texto", use **`#4FC27D`** (token `--lds-color-accent-primary-default` no dark).
4. **Logos têm cor embutida — nunca recolorir SVG via CSS.** Troca-se de **arquivo** (variante por
   fundo/tema), não de `fill`. Ícones funcionais de UI são a exceção (podem usar `currentColor`).
5. **Grafismos são decoração de fundo discreta** (contorno fino, baixa opacidade, sangrando bordas),
   nunca atrás de texto denso ou de tabelas.
6. **Dark mode é verde-quase-preto, não cinza neutro** — mantém a identidade mesmo no escuro.
7. **Tipografia limpa, formatação contida** — pesos 400/500/600/700, sem excesso de negrito,
   *sentence case* (sem caixa-alta exceto micro-labels).

---

## 2. Fundações técnicas (como construir, sem dependências externas)

| Item | Decisão | Observação |
|---|---|---|
| Stack | **React + TypeScript + Vite** (pasta `frontend/`) | Backend Python em `backend/`, exposto por FastAPI. Ver "Arquitetura" acima. |
| Componentes | **CSS puro + componentes React próprios** | Não use bibliotecas de design system com registry privado. Construa os componentes com os tokens deste doc. |
| Ícones funcionais | **set de SVG inline próprio**, monocromático (`currentColor`), grade 24px, mesmo stroke | Não misture lucide/heroicons soltos. Mantenha um único set coeso. |
| Tipografia | **Inter** (efetiva) com Roobert declarada à frente no fallback | Ver §3. |
| Cores/tokens | Arquivo `tokens.css` (fornecido junto) | Copie-o para `frontend/src/styles/tokens.css` e importe na raiz. |
| Temas | **Claro e escuro** via atributo `data-theme` no `<html>` | Ver §6. |
| Assets de marca | pasta `localiza-brand-assets/` (SVGs) | Importados como **URL de string** em `<img>`, sem SVGR. Ver §4. |

---

## 3. Tipografia

**Fonte:** Roobert (fonte da marca) com fallback Inter. Stack canônica (já no `tokens.css`):

```css
--lds-font-family-base: 'Roobert', 'Inter', 'Segoe UI', system-ui, sans-serif;
```

Carregamento (em `index.css`): Inter via Google Fonts CDN + `@font-face` locais da Roobert
apontando para `/fonts/roobert/Roobert-{Regular|Medium|SemiBold|Bold}.woff2`
(`font-display: swap`, pesos 400/500/600/700).

> **Nota de herança (manter como está):** os `.woff2` da Roobert podem **não estar presentes** em
> `public/fonts/roobert/`; nesse caso a fonte efetiva é o fallback **Inter** — e está correto.
> Mantenha a Roobert declarada + fallback Inter. Quando os arquivos da marca chegarem, basta
> colocá-los no caminho e a Roobert ativa sem mudar código.

**Corpo padrão:** `font-size: var(--lds-font-size-base)` (15px) no `body`.

### Escala (tokens)

| Token | px | Uso no Normalizer |
|---|---|---|
| `--lds-font-size-2xs` | 11px | timestamps, micro-meta |
| `--lds-font-size-xs` | 12px | labels de etapa, captions, badges |
| `--lds-font-size-sm` | 13px | mínimo para texto corrido; meta de arquivo |
| `--lds-font-size-md` | 14px | corpo secundário, texto de célula, CTA |
| `--lds-font-size-base` | 15px | corpo principal |
| `--lds-font-size-lg` | 16px | — |
| `--lds-font-size-xl` | 18px | título do header |
| `--lds-font-size-2xl` | 22px | subtítulos de seção |
| `--lds-font-size-3xl` | 28px | título do hero / empty state |

**Pesos:** 400/500/600/700. **Line-heights:** tight 1.2 (títulos), snug 1.4, base 1.5 (corpo),
relaxed 1.6.

**Micro-labels** (os rótulos curtos em caixa-alta que já existem — "ETAPA 1 — UPLOAD", "TOTAL",
"INCLUÍDAS", "TEXTO LIVRE", "PARA REVISAR", "LINHAS EXPORTADAS", "COLUNAS EXPORTADAS"):
`font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;` cor
`--lds-color-neutral-foreground-low`. **Nenhum outro texto em caixa-alta.**

**Fonte mono (blocos de código/`<pre>`, se houver):** `--lds-font-family-mono`. Blocos de código
ficam **sempre escuros** independentemente do tema (claro `#1C2333`/`#E2E8F0`; escuro
`#0D1117`/`#E6EDF3`).

---

## 4. Assets de marca (`./localiza-brand-assets/`)

Coloque a pasta descompactada na raiz do projeto. Os arquivos são **SVGs vetoriais oficiais** — não
os redesenhe nem recolorize.

**Forma de importação:** SVGs entram como **URL de string** (Vite), usados em `<img src={...} />`.
**Não** são componentes React (sem SVGR). Exemplo:

```ts
import localizaCoHorizontalPrincipal from './localiza-brand-assets/logos/localiza-co/localiza-co-horizontal-principal.svg';
// uso: <img src={localizaCoHorizontalPrincipal} alt="Localiza&CO" />
```

**Regra de variante por fundo (NUNCA recolorir via CSS):**
`fundo claro → *-principal` · `fundo verde-escuro → *-branco-e-citrico` / `*-branco-folha-citrica` ·
`fundo cítrico → *-verde-*`.

**Seleção por tema — mapa `THEMED_ASSETS`** (padrão a replicar):

```ts
export const THEMED_ASSETS = {
  light: {
    logoCoHorizontal: localizaCoHorizontalPrincipal,
    logoCoCompact:    lcoCompactoPrincipal,
    simboloLocaliza:  simboloLocalizaPrincipal,
  },
  dark: {
    logoCoHorizontal: localizaCoHorizontalBrancoECitrico,
    logoCoCompact:    lcoCompactoBrancoECitrico,
    simboloLocaliza:  simboloLocalizaBrancoFolhaCitrica,
  },
} as const;
// uso: const { theme } = useTheme(); <img src={THEMED_ASSETS[theme].logoCoHorizontal} />
```

### Assets que o Normalizer usa (e onde)

| Asset (caminho no kit) | viewBox | Onde |
|---|---|---|
| `logos/localiza-co/localiza-co-horizontal-principal.svg` | 294×48 | Modais (fundo branco); selo, quando sobre claro |
| `logos/localiza-co/localiza-co-horizontal-branco-e-citrico.svg` | 294×48 | **Topo da sidebar** (fundo escuro), via `THEMED_ASSETS[*].logoCoHorizontal` |
| `logos/localiza-co/lco-compacto-principal.svg` | 48×48 | **Selo no canto sup-direito do header** (claro), via `logoCoCompact` |
| `logos/localiza-co/lco-compacto-branco-e-citrico.svg` | 48×48 | Selo do header / topo da sidebar colapsada (escuro) |
| `logos/localiza/simbolo-localiza-principal.svg` | 48×48 | Favicon; bullets/avatar pequeno se necessário |
| `grafismos/grafismo-ampersand-contorno-citrico.svg` | 548×557 | **Marca-d'água** sangrando a borda direita da área de conteúdo (§7.4) |
| `grafismos/grafismo-folha-grande-contorno-escuro.svg` | 345×478 | Alternativa de marca-d'água / empty states |
| `grafismos/grafismo-recorte-*.svg` | ~160×160 | **Tile de fundo** da tela inicial de upload (§7.5) |
| `icones/balao-check.svg` | 97×100 | Banner "Questionário analisado com IA"; sucesso da exportação |
| `icones/balao-alerta.svg` | 97×100 | Erros/avisos |
| `icones/balao-info.svg` | 97×100 | Dicas inline |
| `icones/balao-interrogacao-citrico.svg` | 93×105 | **Botão de ajuda** no header (abre modal "Como usar") |
| `icones/compartilhar-citrico.svg` | — | Ação **exportar/compartilhar** no header |
| `icones/megafone.svg` | 124×109 | (Opcional) ilustração de algum empty state |

> **Não usar** logos/cores de sub-marcas (Meoo, Seminovos, eqip, Zarp, Empresas, GF). O Normalizer é
> institucional. (Nomes como "Meoo", "Zarp" podem aparecer apenas dentro do **texto** do nome de uma
> pesquisa, nunca como logotipo na casca.)

### Ícones funcionais (set inline próprio)

Crie um set inline coeso (mesmo stroke 1.5–2px, grade 24px, `currentColor`) para:
`upload`, `documento` (.qsf), `planilha` (.xlsx), `check`, `alerta`, `info`, `seta-direita`,
`fechar` (×), `chevron` (accordion/select), `engrenagem` (configurar IA), `lua`, `sol`,
`painel` (colapsar sidebar), `lixeira` (remover arquivo).

---

## 5. Tokens (referência rápida — fonte completa no `tokens.css`)

Os blocos completos estão em `tokens.css`. Resumo dos que você mais usa:

**Marca:** `--brand-verde-bandeira:#018444` · `--brand-verde-citrico:#78DE1F` ·
`--brand-verde-escuro:#003418` · `--brand-verde-tint:#CEFDAF` (claro) /
`rgba(120,222,31,0.14)` (escuro) · `--brand-sidebar-bg:#003418` (claro) / `#0A1A11` (escuro).

**Acento (LDS):** `--lds-color-accent-primary-default` = `#018444` (claro) / `#4FC27D` (escuro);
`-hover` = `#003418` (claro) / `#62D891` (escuro); `-subtle`; `-tint`.

**Superfícies:** `--lds-color-neutral-background-default` `#F2F2F2`/`#0E1F16` ·
`-surface-default` `#FFFFFF`/`#14271C` · `-surface-low` `#F2F2F2`/`#1B3325` ·
`-surface-mid` `#E8E8E8`/`#22402F`.

**Texto:** `-foreground-default` `#4A4A4A`/`#F2F7F3` · `-low` `#6E6E6E`/`#9FB3A8` ·
`-minimal` `#9E9E9E`/`#6B8577`.

**Bordas:** `-border-low` `#E6E6E6`/`rgba(255,255,255,0.10)` · `-border-default`
`#CCCCCC`/`rgba(255,255,255,0.16)`.

**Raio:** `-radius-sm:8px` · `-radius-soft:16px` · `-radius-xl:24px` · `-radius-pill:9999px` ·
`-radius-sharp:4px`.

**Layout:** sidebar `280px`/`72px` · header `64px` · `--lds-content-max-width:960px`.

---

## 6. Troca de tema (replicar exatamente)

- **Mecanismo:** atributo `data-theme` no `<html>`
  (`document.documentElement.setAttribute('data-theme', theme)`).
- **Persistência:** `localStorage['normalizer:theme']`. Outras chaves do app:
  `normalizer:sidebar_collapsed`.
- **Primeiro acesso:** sem valor salvo → usa `prefers-color-scheme`.
- **Anti-FOUC:** aplicar o tema o quanto antes (script inline no `index.html`) para evitar flash.
- **Contexto React:** `ThemeContext` expõe `{ theme, toggleTheme }`; componentes leem o tema e
  selecionam assets via `THEMED_ASSETS[theme]`.

```tsx
const THEME_KEY = 'normalizer:theme';
function getInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
useEffect(() => {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
}, [theme]);
```

**Transição suave** — aplique `transition: background-color, border-color, color 200ms ease` a:
header, área de conteúdo, coluna central, cards, badges, dropzones, tabela, popovers/menus, inputs.
**A sidebar NÃO transita** (muda instantaneamente). Mantenha assim.

**Gatilho do toggle:** botão **lua/sol** no header (e também no canto superior-direito da tela
inicial de upload), ambos sincronizados pelo mesmo contexto.

---

## 7. Detalhes que definem a marca (replicar com precisão)

### 7.1 Eco do "L" — onde o canto de 4px vai em cada elemento

| Elemento | `border-radius` |
|---|---|
| Sidebar | `0 24px 0 0` (canto superior-direito, raio cheio de 24px) |
| Card de conteúdo padrão (estatística, painéis) | `16px 4px 16px 16px` (canto **superior-direito** = 4px) |
| Hero | `4px 16px 16px 16px` (canto **superior-esquerdo** = 4px; varia do card padrão e evoca o "L" no início da leitura) |
| Banner/alert (faixa) | `16px` com **um** canto a 4px do lado do ícone (superior-esquerdo) |
| Modal | `16px` + `border-top-right-radius: 4px` |
| Badge/pílula | `9999px` (sem canto reduzido) |

> Regra geral: cada *tipo* de elemento tem **um** canto a 4px, sempre o mesmo, para criar ritmo.
> Botões usam raio uniforme (não recebem o canto reduzido) — ver §7.11.

### 7.2 Regra do Verde Cítrico (comente no código)

```
Verde Cítrico (#78DE1F) — NUNCA como `color:` de texto sobre fundo claro (1.6:1, reprova WCAG AA).
Permitido: background, box-shadow, border, fill de SVG. No escuro, "verde de texto" = #4FC27D.
```

No Normalizer, o cítrico aparece em: marcador lateral da etapa ativa no stepper; barra/realce do
card "PARA REVISAR"; sombra-carimbo do card de sucesso na exportação; folha do indicador de loading;
detalhe de ícones-balão; tile de fundo e marca-d'água.

### 7.3 Anéis de foco por contexto

- Fundo claro: `outline: 2px solid var(--brand-verde-bandeira); outline-offset: 2px;`
- Sobre a sidebar escura: `outline: 2px solid rgba(255,255,255,0.85);`
- Override global no dark: `outline-color: var(--brand-verde-citrico);`

### 7.4 Marca-d'água (grafismo "&" no fundo da área de conteúdo)

`grafismo-ampersand-contorno-citrico.svg` posicionado:
`position:absolute; top:50%; transform: translateY(-50%); right:-24px; height:78%;`
(sangra a borda direita). Opacidade: claro `0.58` (tela sem conteúdo) / `0.25` (com conteúdo);
escuro `0.12` / `0.07`. `pointer-events:none; aria-hidden="true";` transição de opacidade 200ms.

### 7.5 Tile de fundo (somente na tela inicial de upload)

SVG inline `320×320px` (data URI) com `background-repeat: repeat`. Stroke fino: claro
`rgba(0,52,24,0.11)`; escuro `rgba(120,222,31,0.11)`. ~12 grafismos da marca por tile ("L", "&",
hélice, folhas) com `transform` variado e **bordas casadas** (sem cortes). Regra de ouro: glyphs
**espaçados, sem sobreposição** — densidade moderada vence amontoado.

### 7.6 Indicador de loading da marca

Folhas cítricas (recorte do símbolo Localiza) animadas com `bounce` 1.2s, delay 0.2s entre cada,
cor `var(--brand-verde-citrico)`. A folha é o "pixel de marca" — reutilizável como spinner/bullet.
Use durante o processamento da etapa 4.

### 7.7 Sombra-carimbo cítrica (uso pontual — máx. 1–2 por tela)

`box-shadow: 4px 4px 0 var(--brand-verde-citrico)` (sólida, sem blur). No Normalizer, reservada
para: o card **"PARA REVISAR"** (etapa 2) e o **card de resultado da exportação** (etapa 4).

### 7.8 Scrollbars

Sempre `width:6px; border-radius:999px; track transparente`. Thumb: conteúdo claro
`rgba(0,52,24,.25)`; conteúdo escuro `rgba(79,194,125,.30)`; sidebar `rgba(255,255,255,.18)`.

### 7.9 Animações compartilhadas

- Entrada de item/seção: opacity `0→1` + `translateY(6px)→0`.
- `popover-in` (menus/selects): opacity `0→1` + `translateY(-4px)→0`.
- `modal-in`: opacity `0→1` + `translateY(-8px) scale(0.98)→0/1`.
- Transição de largura (sidebar): 200–220ms ease.

### 7.10 Bloco de código `<pre>` — sempre escuro (se aparecer)

Independente do tema: claro `#1C2333`/`#E2E8F0`; escuro `#0D1117`/`#E6EDF3`.

### 7.11 Botões (estilos canônicos)

- **Primário:** `background: var(--brand-verde-bandeira)` (#018444); texto `#FFFFFF`; `font-weight:600`;
  `border-radius: var(--lds-border-radius-sm)` (8px); altura **44–48px**; hover
  `background: var(--brand-verde-escuro)` (#003418); desabilitado `surface-mid`/`foreground-minimal`.
  **Todos os CTAs grandes da área de conteúdo** (incluindo "Continuar…", "Normalizar e exportar" e
  "Baixar planilha normalizada") são assim — **nunca cítricos.**
- **Secundário/outline (fundo claro):** `background: surface-default`; `border:1px solid
  var(--brand-verde-bandeira)`; texto `var(--brand-verde-bandeira)`; hover `background:
  accent-primary-subtle`.
- **Outline sobre a sidebar escura:** `border:1px solid rgba(255,255,255,0.25)`; texto
  `rgba(255,255,255,0.92)`; hover `background: rgba(255,255,255,0.08)`.
- **Ghost:** transparente; texto `foreground-default`/`accent`; hover `background: surface-low`.
- **Destrutivo:** texto/borda `var(--brand-danger-fg)`; sólido (`--brand-danger-btn-bg`) só em
  confirmação de remoção.
- **Botão de ícone:** `36×36` (header) ou `44×44` (sidebar); `border-radius:8px`/`10px`; ver §8.

---

## 8. A casca (shell) — estrutura e valores

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ┌───────────┐ ┌──────────────────────────────────────────────────────┐  │
│ │  SIDEBAR  │ │ HEADER (64px)                                          │  │
│ │  280/72px │ ├──────────────────────────────────────────────────────┤  │
│ │  verde    │ │ ÁREA DE CONTEÚDO (rola; o wizard inteiro vive aqui)    │  │
│ │  escuro   │ │  Hero → Etapa 1 → 2 → 3 → 4 (revela conforme avança)   │  │
│ │  STEPPER  │ │  marca-d'água "&" sangrando a borda direita            │  │
│ │  vertical │ │                                                        │  │
│ └───────────┘ └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.1 App shell (CSS Grid)

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--lds-sidebar-width-expanded) 1fr; /* 280px + conteúdo */
  height: 100vh; overflow: hidden;
  transition: grid-template-columns 200ms ease;
  /* faixa de 64px no topo p/ o canto arredondado da sidebar descansar sobre fundo claro */
  background: linear-gradient(to bottom,
    var(--lds-color-neutral-surface-default) var(--lds-header-height),
    var(--lds-color-neutral-background-default) var(--lds-header-height));
}
.app-shell.sidebar-collapsed { grid-template-columns: var(--lds-sidebar-width-collapsed) 1fr; }
```
No escuro a faixa superior usa `--lds-color-neutral-surface-default` (#14271C) no lugar do branco
(já resolvido pelo token acima).

### 8.2 Sidebar (verde escuro; abriga o stepper)

- **Fundo:** `--brand-verde-escuro` (#003418) no claro; `--brand-sidebar-bg` (#0A1A11) no escuro.
  **Muda instantaneamente** (não está na lista de transição de tema).
- **Canto:** `border-radius: 0 24px 0 0` (superior-direito) vazando sobre a área de conteúdo.
- **Larguras:** 280px expandida / 72px recolhida. Estado persistido em
  `localStorage['normalizer:sidebar_collapsed']`. Botão de colapsar (ícone `painel`) no topo.
- **Header interno:** `padding: 20px 16px 16px`.
- **Logo:** `THEMED_ASSETS[theme].logoCoHorizontal` (Localiza&CO branco+cítrico), altura ~28px.
  Colapsada: `logoCoCompact` 32px.
- **Bloco de identidade do produto** (abaixo do logo): rótulo **"Normalizer"** (15px/600,
  `rgba(255,255,255,0.92)`) + sublinha **"Qualtrics → Análise"** (12px, `rgba(255,255,255,0.60)`).
  Se mantiver o quadradinho com o "N": fundo `--brand-verde-citrico`, e o "N" em
  `--brand-verde-escuro` (#003418) — **nunca branco sobre cítrico**.
- **Labels de seção** (ex.: "PROGRESSO"): `11px/600; letter-spacing:.06em; uppercase;
  color: rgba(255,255,255,0.60)`.
- **Stepper vertical** — o coração da sidebar. Quatro itens: *1 Upload · 2 Classificação ·
  3 Respostas abertas · 4 Exportar*. Cada item é uma linha com **número em círculo** (28px) +
  rótulo. Estados:
  - **Pendente:** círculo `background: rgba(255,255,255,0.12)`, número
    `rgba(255,255,255,0.55)`; rótulo `rgba(255,255,255,0.55)`.
  - **Ativo:** linha com `background: rgba(255,255,255,0.10); border-radius:10px;` +
    **marcador lateral** `::before` de `3px × 22px`, `background: var(--brand-verde-citrico)`,
    `border-radius: 0 9999px 9999px 0`, encostado na borda esquerda; círculo
    `background: var(--brand-verde-citrico)`, número `#003418`; rótulo `rgba(255,255,255,0.92)`/600.
  - **Concluído:** círculo `background: var(--brand-verde-bandeira)` com **check branco**; rótulo
    `rgba(255,255,255,0.92)`.
  - **Conector vertical** fino (2px) entre círculos: `rgba(255,255,255,0.12)`; no trecho já
    concluído, pintar de `var(--brand-verde-citrico)`.
  - Colapsada (72px): só os círculos (com `title`/tooltip no hover).
- **Rodapé da sidebar:**
  - Badge **"IA: Claude"**: pílula discreta — `background: rgba(255,255,255,0.08)`; texto
    `rgba(255,255,255,0.92)`; `border-radius:9999px; padding:4px 10px; font-size:12px;` com um
    **check cítrico** 12px à esquerda.
  - Botão **"Configurar IA"**: estilo *outline sobre escuro* (§7.11): `border:1px solid
    rgba(255,255,255,0.25)`; texto `rgba(255,255,255,0.92)`; hover `background:
    rgba(255,255,255,0.08)`. **Não** preencher de verde-claro chapado.
  - Divisor `rgba(255,255,255,0.12)` acima do rodapé.
- **Scrollbar:** `width:6px; thumb rgba(255,255,255,.18); radius:999px; track transparente`.

### 8.3 Header (topbar)

- `height:64px; padding:0 32px; background: surface-default; border-bottom:1px solid border-low.`
- **Esquerda:** título da sessão (18px/600/lh 1.2, `foreground-default`) — ex. "Qualtrics
  Normalizer", ou o nome da pesquisa em processamento; truncar ~48 chars com `…`. Ao lado, **Badge
  de status** (§9.3).
- **Botões de ícone:** `36×36; background:transparent; border-radius:8px; color: foreground-muted;`
  hover `background: surface-low`; ativo `color: var(--brand-verde-bandeira) + background:
  accent-primary-subtle`.
- **Ordem canônica à direita:** **tema (lua/sol)** → **exportar/compartilhar**
  (`compartilhar-citrico`) → **ajuda** (`balao-interrogacao-citrico`, abre modal "Como usar") →
  **selo L&CO compacto** (`THEMED_ASSETS[theme].logoCoCompact`, 32px).
  *(O Normalizer não tem os ícones de "fixar" nem "toggle de painel lateral" — eles não se aplicam.)*

### 8.4 Área de conteúdo

- `background: --lds-color-neutral-background-default`. Coluna central
  `max-width: var(--lds-content-max-width)` (960px), `margin:0 auto; padding:32px;`
  `gap` vertical de 24px entre seções. **Scroll vertical** que se prolonga conforme o usuário avança.
- **Marca-d'água "&"** conforme §7.4 (sangrando a borda direita, atrás do conteúdo).

---

## 9. Componentes do wizard (máximo detalhe)

> Lembrete da Regra Zero: você está reescrevendo **apenas a aparência** destes componentes. Os dados
> que eles exibem, a classificação, os números e a planilha gerada **não mudam**.

### 9.1 Hero "Qualtrics Normalizer" (topo da área de conteúdo)

- Card com **gradiente de marca**: `linear-gradient(135deg, var(--brand-verde-escuro) 0%,
  var(--brand-verde-bandeira) 100%)`. `border-radius: 4px 16px 16px 16px` (canto sup-esq = 4px, §7.1);
  `padding: 28px 32px;` `color:#FFFFFF;` sombra `--lds-shadow-md`.
- **Título** (28px): destaque por peso+cor dentro da frase — ex.
  **"Transforme exports do Qualtrics em planilhas prontas para análise."** com "prontas para análise"
  em `--brand-verde-citrico` e peso 700 (resto em 400/500 branco).
  *(Cítrico aqui é permitido: o fundo é escuro, não claro — passa no contraste.)*
- **Subtítulo** opcional (15px, `rgba(255,255,255,0.85)`).
- À direita, os ícones de fluxo `.qsf → .xlsx` podem permanecer, **menores e discretos**, ou ceder
  espaço a um recorte de grafismo cítrico sangrando o canto. Não competir com o título.

### 9.2 Etapa 1 — Upload (dois alvos lado a lado)

O Normalizer recebe **dois** arquivos. Layout em duas colunas (empilham no mobile).

**Cabeçalho da etapa:** micro-label "ETAPA 1 — UPLOAD" (§3) + título "Upload dos arquivos" (22px/600)
+ instrução (15px, `foreground-low`): "Exporte do Qualtrics o questionário (.qsf) e os dados
numéricos (.xlsx). Ambos são necessários para continuar."

**Por coluna:**
- **Cabeçalho da coluna:** ícone do tipo (`documento`/`planilha`) + título ("Questionário" / "Dados
  numéricos") + **chip de extensão** (".qsf"/".xlsx"): `background: var(--brand-verde-tint);` texto
  `#003418` (claro); `border-radius:9999px; padding:2px 8px; font-size:11px/600`.
- **Dropzone (estado vazio):**
  - `border: 2px dashed var(--brand-verde-bandeira);`
    `background: var(--lds-color-accent-primary-subtle);` (rgba(1,132,68,0.08))
    `border-radius: var(--lds-border-radius-soft);` `padding: 40px 24px;` centralizado.
  - Ícone `upload` 40px, cor `var(--brand-verde-bandeira)`.
  - Linha 1 (15px): "**Clique para selecionar** ou arraste o arquivo aqui" ("selecionar" em 600).
  - Linha 2 (13px, `foreground-minimal`): "Apenas .qsf • até 200MB" (ajuste por tipo).
  - **Drag-over:** `background: rgba(120,222,31,0.12);` borda **sólida** `var(--brand-verde-bandeira)`.
  - **Foco/hover:** leve elevação (`--lds-shadow-sm`).
- **Chip de arquivo enviado (substitui a dropzone):** linha
  `background: var(--lds-color-accent-primary-subtle); border:1px solid rgba(1,132,68,0.20);`
  `border-radius: 12px; padding: 10px 12px;` com: ícone do tipo + **nome truncado** (13px) +
  tamanho (12px `foreground-minimal`) + botão `×` (ícone `lixeira`/`fechar`) para remover. Durante
  upload, **barra de progresso** 3px cítrica na base.
- **Botão "+"** (trocar/adicionar) ao lado, discreto, estilo ghost.

**Banner "Questionário analisado com IA. Nomes das variáveis foram gerados automaticamente.":**
faixa `background: var(--lds-color-feedback-success-bg);` (#D1F5DC claro) texto
`var(--lds-color-feedback-success-fg);` (#003827) `border-radius:16px` com canto sup-esq 4px;
ícone `balao-check` 20px à esquerda; `padding:12px 16px`.

### 9.3 Badge de status (no header)

Pílula `padding:3px 10px; border-radius:9999px; font-size:12px; font-weight:600`. Estados do
Normalizer:

| Estado | Claro (bg / texto) | Escuro (bg / texto) |
|---|---|---|
| "Aguardando arquivos" | `#CEFDAF` / `#003418` | `rgba(120,222,31,0.18)` / `#BBF49A` |
| "Processando" | `#D8EFFD` / `#0B4260` | `rgba(79,194,125,0.16)` / `#BCE3FB` |
| "Pronto para exportar" | `#D1F5DC` / `#003827` | `rgba(79,194,125,0.18)` / `#BFEFCF` |
| "Revisar classificação" | `#FBE437` / `#003418` | `rgba(251,228,55,0.18)` / `#F2F7F3` |

### 9.4 Etapa 2 — Classificação

**Cabeçalho:** micro-label "ETAPA 2 — CLASSIFICAÇÃO" + título "Classificação das colunas" (22px/600)
+ instrução: "Revise e edite. Desmarque 'Incluir' para ignorar colunas. Ajuste tipo e rótulo
conforme necessário."

**Cards de estatística** (TOTAL / INCLUÍDAS / TEXTO LIVRE / PARA REVISAR) — fileira de 4:
- Card: `background: surface-default; border:1px solid border-low;`
  `border-radius: 16px 4px 16px 16px` (canto sup-dir = 4px, §7.1); `padding:20px;`
  `box-shadow: --lds-shadow-sm`.
- **Micro-label** (11px uppercase, `foreground-low`) em cima; **número grande** (32–40px/700) embaixo,
  cor `var(--brand-verde-bandeira)` no claro / `var(--lds-color-accent-primary-default)` (#4FC27D) no
  escuro.
- **"PARA REVISAR"** recebe destaque (pede ação): aplicar **`box-shadow: 4px 4px 0
  var(--brand-verde-citrico)`** (§7.7) **ou** uma borda superior cítrica 3px. (Um dos 2 usos de
  sombra-carimbo por tela.) Se o valor for 0, exibir em estado neutro (sem destaque).

**Filtros** (Todas / Para revisar / Incluídas / Excluídas / Texto livre) — **pílulas de rádio**:
- `border-radius:9999px; padding:6px 14px; font-size:13px;`
- **Ativo:** `background: var(--brand-verde-tint);` texto `#003418` (claro) /
  `--lds-color-accent-primary-tint` bg + `#BBF49A` texto (escuro).
- **Inativo:** `border:1px solid border-default;` texto `foreground-low;` hover
  `background: surface-low`.
- Rótulo "Filtrar:" (13px, `foreground-low`) antes das pílulas.

**Tabela de classificação de colunas:**
- Container: `background: surface-default; border:1px solid border-low;`
  `border-radius:16px; overflow:hidden;` com **cabeçalho sticky** ao rolar.
- **Cabeçalho:** `background: surface-low;` células `12px/600 uppercase; letter-spacing:.04em;
  color: foreground-low; padding:12px 14px;` mantendo os ícones de filtro de coluna que já existem
  (Status, Incluir, ID Qualtrics, Pergunta, Amostras, Grupo, Tipo, Rótulo, …).
- **Linhas:** zebra sutil (`surface-default` / `surface-low`); borda inferior `1px border-low`;
  hover `background: rgba(1,132,68,0.04)`; `padding:10px 14px; font-size:14px`.
- **Célula Status:** mini-badge — "OK" → `bg #D1F5DC / texto #003827` (claro); "Revisar" →
  `bg #FBE437 / texto #003418`. (Escuro: usar os bg translúcidos do §9.3.)
- **Célula Incluir:** checkbox — vazio: `border:2px solid border-strong; border-radius:4px;`
  marcado: `background: var(--brand-verde-bandeira);` com check branco.
- **Células editáveis (Tipo, Rótulo):** ao focar, viram input/select (§9.7). Texto longo da Pergunta
  trunca com `…` e tem `title` completo.
- **Accordion "Ver enunciado completo"** abaixo da tabela: §9.6.
- **CTA "Continuar para análise de respostas abertas →":** botão **primário** (§7.11) com ícone
  `seta-direita`. Largura confortável; alinhado conforme o layout atual.

### 9.5 Etapa 3 — Respostas abertas (opcional)

**Cabeçalho:** micro-label "ETAPA 3 — RESPOSTAS ABERTAS" + título "Análise de respostas abertas"
(22px/600) com **"(opcional)"** em `foreground-low` ao lado + instrução: "Selecione colunas com texto
opinativo para análise de sentimento e categorização por IA."

- **Multiselect "Colunas para analisar":** componente próprio (§9.7) — moldura de input + `chevron`;
  **chips selecionados** dentro do campo: `background: var(--brand-verde-tint); color:#003418;
  border-radius:9999px; padding:2px 8px; font-size:12px;` com `×`. Placeholder "Escolha as colunas…".
  Menu flutuante com checkboxes por coluna.
- **Accordions:** "Ver enunciado completo da análise" e "Ver classificação de elegibilidade de todas
  as colunas open text" — §9.6.

### 9.6 Accordion / disclosure

- **Cabeçalho:** linha clicável `border:1px solid border-low; border-radius:8px; background:
  surface-default; padding:10px 14px; font-size:14px/500;` ícone `chevron` à esquerda que rotaciona
  90° quando aberto; hover `background: surface-low`.
- **Conteúdo:** ao abrir, expande com `border-top:1px solid border-low; padding:12px 14px;` e
  animação de entrada (§7.9).

### 9.7 Inputs, selects, textarea, multiselect

- **Base:** `background: surface-default; border:1px solid border-default; border-radius:8px;`
  `padding:10px 12px; font-size:15px; color: foreground-default.`
- **Foco:** `border-color: var(--brand-verde-bandeira)` (claro) /
  `var(--lds-color-accent-primary-default)` #4FC27D (escuro); `border-width:2px` + reduzir padding em
  1px para não deslocar o layout. Mais o anel de foco do §7.3.
- **Select/multiselect:** mesma moldura + ícone `chevron` à direita; **menu flutuante:**
  `background: surface-low; border:1px solid border-low; border-radius:10px; box-shadow:
  --lds-shadow-lg;` item `padding:8px 12px; hover background: surface-mid;` item selecionado com
  check cítrico (`fill`, não texto).
- **Placeholder:** `color: foreground-minimal`.

### 9.8 Etapa 4 — Exportar

**Cabeçalho:** micro-label "ETAPA 4 — EXPORTAR" + título "Exportar" (22px/600) + instrução: "Processe
os dados e baixe a planilha normalizada pronta para análise."

- **Botão "Normalizar e exportar":** **primário** (§7.11), largura total ou confortável. Ao acionar,
  entra em **estado loading** (folha cítrica pulsando, §7.6) e desabilita ações conflitantes.
- Ao concluir, **revelar**:
  - **Cards "LINHAS EXPORTADAS" / "COLUNAS EXPORTADAS":** mesmo padrão dos cards de estatística
    (§9.4) — número grande verde-bandeira/#4FC27D.
  - **Accordion "Ver todas as colunas geradas":** §9.6.
  - **Botão "Baixar planilha normalizada":** **primário** verde-bandeira. (Substitui o cítrico atual.)
  - **Card de resultado (momento de sucesso):** pode receber **`box-shadow: 4px 4px 0
    var(--brand-verde-citrico)`** (§7.7, segundo uso permitido) + ícone `balao-check`. Texto curto de
    confirmação.

---

## 10. Modais

Padrão: card `background: surface-default;` (escuro: `surface-low` #1B3325, **sempre mais claro** que
o fundo); `border-radius:16px; border-top-right-radius:4px;` `width: min(560px, 100vw-32px);`
`box-shadow` forte; **overlay** `rgba(0,0,0,0.45)` (claro) / `rgba(0,0,0,0.6)` (escuro) +
`backdrop-filter: blur(3px)`. Topo: logo `localiza-co-horizontal-principal.svg` + botão `×`
(ícone `fechar`, canto sup-direito). Animação `modal-in` (§7.9). Trap de foco; `Esc` fecha.

- **Modal "Como usar" (ajuda)** — aberto pelo `balao-interrogacao-citrico` do header. Lista de passos
  numerados: **círculo `var(--brand-verde-bandeira)` com número branco** + título (15px/600) +
  descrição (14px, `foreground-low`), com um ícone à direita por passo. Conteúdo adaptado ao
  Normalizer:
  1. **Envie os dois arquivos do Qualtrics** — o questionário (.qsf) e os dados numéricos (.xlsx).
  2. **Revise a classificação das colunas** — confira tipos, rótulos e quais colunas incluir.
  3. **(Opcional) Analise respostas abertas** — selecione colunas de texto para análise por IA.
  4. **Normalize e baixe** — gere a planilha pronta para análise.
  CTA inferior: botão **primário** "Entendi".
- **Modal de confirmação** (ex.: recomeçar / descartar arquivos): título + texto (`foreground-low`)
  + botões ghost("Cancelar") / primário ou **destrutivo** conforme a ação.

> O Normalizer **não** possui modal de "busca em conversas" nem de "nova pesquisa por upload" — esses
> pertencem a outro tipo de produto e não se aplicam aqui.

---

## 11. Estados (vazio, carregando, erro)

- **Inicial (sem arquivos):** Hero + as duas dropzones; **tile de fundo** (§7.5) esparso e fraco +
  marca-d'água "&" (§7.4). Toggle de tema visível também no canto superior-direito.
- **Processando (etapa 4):** botão primário em loading (folha cítrica pulsando §7.6); desabilitar
  ações conflitantes; opcional skeleton nos cards que vão surgir.
- **Sucesso (pós-export):** §9.8.
- **Erro:** banner com `balao-alerta` + texto, cores `--lds-color-feedback-error-*`. Erro de arquivo
  inválido aparece **na própria dropzone**: borda `var(--lds-color-feedback-error-default)` + mensagem
  curta (13px) abaixo.

---

## 12. Responsivo

- **≥1024px:** layout completo (sidebar 280px + conteúdo).
- **768–1024px:** sidebar colapsa para 72px (só círculos do stepper, com tooltip); conteúdo ganha
  respiro.
- **<768px:** sidebar vira **drawer** (abre por botão no header); o stepper pode aparecer como barra
  horizontal compacta no topo do conteúdo. Hero e cards de estatística empilham; as **duas dropzones
  empilham** verticalmente; a tabela ganha **scroll horizontal** (com a primeira coluna eventualmente
  fixa). Modais usam `width: 100vw-32px`.

---

## 13. Acessibilidade

- Contraste: cítrico **nunca** como texto sobre claro (§7.2). `--brand-verde-bandeira` sobre branco é
  ok para ≥14px e UI. No escuro, validar `foreground-*` sobre `background/surface`.
- **Foco visível** universal (§7.3). Navegação por teclado em stepper, filtros, tabela, selects e
  modais (trap de foco; `Esc` fecha).
- `aria-current="step"` na etapa ativa do stepper; `aria-expanded` nos accordions; `role="dialog"` +
  `aria-modal="true"` nos modais; `<label>` associada a todos os campos; `aria-hidden` em grafismos
  decorativos.
- Alternância de tema respeita `prefers-color-scheme` no primeiro acesso; depois, escolha manual
  persistida.

---

## 14. Checklist de validação ("parece Localiza?")

1. Os três verdes coexistem? (escuro na sidebar, bandeira nas ações, cítrico só em acentos)
2. Cítrico está em minoria e **nunca** como texto sobre claro nem como fundo de CTA da área clara?
3. Cada tipo de superfície tem **um** canto a 4px na posição fixa (§7.1)?
4. A sidebar tem canto sup-direito de 24px vazando, logo Localiza&CO no topo, stepper com marcador
   lateral cítrico no item ativo, e colapsa?
5. Header com badge de status, alternador de tema, exportar (compartilhar-cítrico), ajuda
   (balão-interrogação cítrico) e selo L&CO compacto, **nesta ordem**?
6. **Os dois temas** (claro/escuro) cobrem todos os componentes? Dark mode é verde-quase-preto?
7. Marca-d'água "&" sangrando a borda direita (opacidades do §7.4) e tile de fundo só na tela
   inicial?
8. Tipografia Inter, corpo 15px, títulos 600, destaque por peso+cor no hero?
9. CTAs grandes (Continuar, Normalizar e exportar, Baixar) são **verde-bandeira**?
10. Sombra-carimbo cítrica em no máximo 2 elementos (PARA REVISAR + card de sucesso)?
11. Logos/SVGs do kit oficial, variante correta por fundo/tema (`THEMED_ASSETS`), **sem recolorir por
    CSS**?
12. Troca de tema por `data-theme`, persistida, anti-FOUC, **sidebar sem transição**?
13. **NADA** de lógica, parse, classificação, API ou formato da planilha foi alterado? (Regra Zero)
