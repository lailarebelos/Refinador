"""Qualtrics Normalizer v2 — QSF-driven approach.

Uses QSF (survey definition) for question metadata + numeric XLSX export.
No heuristics needed — QSF tells us everything.
"""
import html as _html_mod
import json, re, unicodedata
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from ai_analysis import analyze_columns

# ── Constants ─────────────────────────────────────────────────────────────────
VALID_TYPES = ["single_choice","multiple_choice","dichotomous","likert","ranking",
               "nps","open_text","numeric","date","metadata"]

TYPE_PT = {"single_choice":"Escolha única","multiple_choice":"Escolha múltipla",
    "dichotomous":"Dicotômica","likert":"Escala Likert","ranking":"Ranking",
    "nps":"NPS","open_text":"Campo aberto","numeric":"Quantitativa",
    "date":"Data","metadata":"Metadado externo"}

VAR_TYPE = {"single_choice":"Qualitativa nominal","multiple_choice":"Qualitativa nominal",
    "dichotomous":"Qualitativa nominal","likert":"Qualitativa ordinal",
    "ranking":"Qualitativa ordinal","nps":"Quantitativa discreta",
    "open_text":"Qualitativa nominal","numeric":"Quantitativa contínua",
    "date":"Data","metadata":"Qualitativa nominal"}

ANALYSIS = {"single_choice":"Frequência; Crosstab","multiple_choice":"Frequência; Regressão linear",
    "dichotomous":"Proporção; Crosstab","likert":"Média; Desvio padrão; Frequência",
    "ranking":"Média; Frequência","nps":"NPS; Média",
    "open_text":"Análise de conteúdo; Nuvem de palavras",
    "numeric":"Média; Mediana; Desvio padrão","date":"Distribuição temporal","metadata":"Frequência"}

LIKERT_KEYWORDS = {"muito insatisfeito","insatisfeito","neutro","satisfeito","muito satisfeito",
    "discordo totalmente","discordo","concordo","concordo totalmente",
    "nunca","raramente","as vezes","frequentemente","sempre"}

SHORT_NAME_STOPWORDS: frozenset[str] = frozenset({
    # ── Artigos, preposições, conjunções ──────────────────────────────────────
    "a","o","e","de","do","da","dos","das","em","no","na","nos","nas","num","numa",
    "um","uma","uns","umas","que","para","com","por","se","ou","mas","nem","porem",
    "ao","aos","os","as","pelo","pela","pelos","pelas","ate","desde","durante",
    "entre","sobre","sob","ante","apos","perante","conforme","segundo","exceto",
    # ── Pronomes pessoais e demonstrativos ────────────────────────────────────
    "voce","tu","ele","ela","nos","eles","elas",
    "isso","isto","aquilo","esse","essa","esta","este","esses","essas","aquele","aquela",
    "neste","nesta","nesse","nessa","naquele","naquela",
    "meu","minha","meus","minhas","seu","sua","seus","suas",
    "nosso","nossa","nossos","nossas","deles","delas","dele","dela",
    "alguem","ninguem","tudo","nada","algo","qualquer",
    "todo","toda","todos","todas","cada","varios","varias","alguns","algumas",
    "muito","muita","muitos","muitas","pouco","pouca","poucos","poucas",
    # ── Verbos auxiliares e de estado ─────────────────────────────────────────
    "ser","estar","ter","haver","ir","vir","poder","dever","querer","saber","precisar",
    "sao","esta","estao","tem","dao","vao","vai","ira","irao","sera","serao",
    "foi","era","tinha","havia","seria","estaria","teria","pudesse","devesse",
    "sendo","estando","tendo","indo","vindo","podendo","devendo","querendo",
    "houve","tive","tivesse","tiveram","tera","terao","foram","eram","tinham",
    # ── Verbos de instrução de survey (não identificam a variável) ────────────
    "marque","selecione","escolha","indique","diga","responda",
    "assinale","aponte","classifique","ordene","avalie","liste",
    "numere","identifique","especifique","descreva","explique",
    "comente","justifique","cite","mencione","relate","anote",
    "preencha","complete","informe","registre","pontue","escreva","sinalize",
    # ── Verbos introdutórios de contextualização ──────────────────────────────
    "pensando","considerando","analisando","lembrando","imaginando","supondo",
    "verificando","entendendo","compreendendo","levando","reconhecendo",
    "percebendo","notando","observando","partindo","baseando","tomando",
    "assumindo","contando","iniciando","iniciemos","iniciaremos",
    # ── Verbos de abertura de survey sem valor de variável ────────────────────
    "gostariamos","gostariam","saber","conhecer","entender","compreender","verificar",
    # ── Advérbios temporais e contextuais (típicos em aberturas de pergunta) ──
    "atualmente","agora","hoje","ainda","tambem","alem","apenas","somente",
    "so","ja","sempre","nunca","anteriormente","recentemente","ultimamente",
    "frequentemente","raramente","normalmente","geralmente","habitualmente",
    "regularmente","constantemente","eventualmente","ocasionalmente",
    # ── Palavras interrogativas e gradativas ─────────────────────────────────
    "qual","quais","como","quando","onde","porque","quanto","quanta","quantos","quantas",
    "mais","menos","assim","tanto","tao","tanta","tamanha","tamanho",
    # ── Unidades de tempo (raramente o tema da variável) ──────────────────────
    "dia","dias","semana","semanas","mes","meses","ano","anos",
    "hora","horas","minuto","minutos","quinzena","bimestre","trimestre","semestre",
    # ── Meta-linguagem Qualtrics e artefatos HTML ─────────────────────────────
    "selected","choice","text","matrix","response","score","rank","weak","strong",
    "span","nbsp","amp","div","bold","href","class","style","script",
    "other","item","block","survey","group",
    # ── Palavras funcionais de questionário ───────────────────────────────────
    "opcoes","opcao","alternativas","alternativa","abaixo","elementos",
    "grupos","lista","listas","itens","coluna","colunas","escala","escalas",
    "pontuacao","pontuacoes","nota","notas",
    # ── Substantivos genéricos de contexto (raramente identificam a variável) ─
    "momento","momentos","cenario","cenarios","contexto","contextos",
    "dentro","grupo","ultimos","vezes","vez","anos",
    # ── Outros stopwords operacionais ────────────────────────────────────────
    "acontece","aplicam","aplica","resposta","respostas",
    "precisa","precisam","alugar","locacao","fazer","faz","feito","feita",
    "normalmente","quando","onde","qualquer","porque",
})

# ── Content analysis constants ────────────────────────────────────────────────
_MIN_EVALUABLE_ROWS = 3
_MIN_AVG_TEXT_LEN   = 5
_TRIVIAL_PATTERN = re.compile(
    r"^(?:n/?a|n[aã]o\s+se\s+aplica|nao\s+se\s+aplica|sem\s+resposta|"
    r"nenhum[ao]?|[—\-\.]+|\d+(?:[.,]\d+)?|s/?n|yes|no|sim|n[aã]o|nao)$",
    re.IGNORECASE,
)

# Palavras avaliativas/emocionais normalizadas (sem acentos, lowercase)
_EMOTIONAL_WORDS: frozenset[str] = frozenset({
    "bom","boa","ruim","otimo","otima","excelente","pessimo","pessima",
    "satisfeito","satisfeita","insatisfeito","insatisfeita",
    "gostei","gostou","adorei","adorou","amei","odiei","detestei",
    "problema","problemas","dificuldade","dificuldades","facil","dificil",
    "rapido","rapida","lento","lenta","demorado","demorada",
    "agradavel","desagradavel","util","inutil",
    "recomendo","recomendaria","voltaria","voltei",
    "melhorou","piorou","gostaria","surpreendeu","decepcionou",
    "maravilhoso","horrivel","terrivel","incrivel","fantastico",
    "atendimento","qualidade","eficiente","eficiencia",
    "positivo","negativo","ótimo","péssimo",
})

# Padrões que indicam pergunta OPINATIVA/AVALIATIVA
# Formato: (regex sobre texto normalizado, peso, motivo legível)
_OPINION_PATTERNS: list[tuple] = [
    (re.compile(r"coment|descreva|descreve|conte\b|fale\s+sobre"),         2.0, "pede comentário/descrição"),
    (re.compile(r"experiencia|vivencia"),                                   2.0, "menciona experiência"),
    (re.compile(r"opiniao|o\s+que\s+(acha|achou|pensa|pensou)"),           2.5, "pede opinião"),
    (re.compile(r"satisfaca|satisfacao|insatisf"),                          2.5, "relacionada à satisfação"),
    (re.compile(r"sugestao|sugest[aã]o|sugerir"),                          2.0, "pede sugestão"),
    (re.compile(r"\bpor\s+que\b|porque\b|motivo\s+d[ao]\b|qual\s+o\s+motivo"), 1.5, "pede justificativa/motivo"),
    (re.compile(r"justif|explique|explicar\s+por\b"),                      1.5, "pede explicação"),
    (re.compile(r"feedback|avaliaca|avaliacao|avalie|como\s+avalia"),       2.0, "pede avaliação/feedback"),
    (re.compile(r"melhorar|melhoria|melhoraria|o\s+que\s+podemos\s+melhorar"), 1.5, "relacionada a melhorias"),
    (re.compile(r"reclamac|reclamacao|elogio|critica"),                     2.0, "campo para reclamação/elogio/crítica"),
    (re.compile(r"como\s+foi|o\s+que\s+(gostou|gosta|curtiu)"),            2.0, "pergunta de avaliação"),
    (re.compile(r"impressa|impressao|sentiu\b|sentimento"),                 1.5, "pede impressão/sentimento"),
    (re.compile(r"\bnota\b.*\bpor\b|\bpor\b.*\bnota\b|motivo.*nota|nps"),  1.5, "justificativa de nota/NPS"),
    (re.compile(r"o\s+que\s+poderia|o\s+que\s+faria\s+diferente"),         1.5, "pergunta contrafactual de melhoria"),
]

# Padrões que indicam pergunta FACTUAL/CADASTRAL
_FACTUAL_PATTERNS: list[tuple] = [
    (re.compile(r"^(nome|seu\s+nome|nome\s+completo)\s*[\?:]?$"),           3.5, "campo de nome isolado"),
    (re.compile(r"\bnome\s+(do|da|de|completo)\b"),                         2.5, "campo de nome"),
    (re.compile(r"\b(cidade|estado|pais|municipio|bairro|regiao)\b"),       2.5, "campo geográfico"),
    (re.compile(r"\b(empresa|razao\s+social|cnpj|instituicao|organizacao)\b"), 2.0, "campo de empresa/organização"),
    (re.compile(r"\b(endereco|cep|rua|avenida|logradouro)\b"),              3.0, "campo de endereço"),
    (re.compile(r"\b(telefone|celular|fone|whatsapp|contato)\b"),           3.0, "campo de telefone/contato"),
    (re.compile(r"\be[\s\-]?mail\b"),                                       3.0, "campo de e-mail"),
    (re.compile(r"\b(cpf|cnpj|rg|matricula|codigo\s+do|numero\s+do)\b"),   3.0, "campo de documento/código"),
    (re.compile(r"\b(cargo|departamento|setor|funcao|profissao)\b"),        2.0, "campo de cargo/área"),
    (re.compile(r"outros.{0,6}qual|qual\s+(empresa|cidade|estado|nome|cargo|marca|produto)\b"), 2.5, "campo 'Outros: qual?'"),
    (re.compile(r"\bespecifique\b|\bespecif\b"),                            1.5, "campo de especificação pontual"),
    (re.compile(r"(outros|other)[\s\-:]+texto"),                            2.0, "campo 'Outros - Texto'"),
    (re.compile(r"^qual\s+(e\s+)?(seu|sua|o|a)\s+(nome|email|telefone|cargo|empresa)\b"), 3.0, "pergunta cadastral direta"),
    (re.compile(r"\bidentificaca|identificacao\b|\bidentificador\b"),       2.5, "campo de identificação"),
]

# ── Column width limits ────────────────────────────────────────────────────────
_COL_MIN_WIDTH       = 10
_COL_MAX_TEXT_WIDTH  = 55
_COL_MAX_OTHER_WIDTH = 30

# ── Operational metadata detection ────────────────────────────────────────────
_OP_COL_KEYWORDS: frozenset[str] = frozenset({
    # Qualtrics system columns
    "startdate","enddate","recordeddate","responseid","ipaddress","ipaddr",
    "status","progress","duration","finished",
    "locationlatitude","locationlongitude","locationlat","locationlon",
    "distributionchannel","userlanguage","externalreference","externalref",
    # Recipient/contact info added by survey platform
    "recipientfirstname","recipientlastname","recipientemail",
    "emailaddress","firstname","lastname",
    # Survey metadata
    "surveyid","surveyname","collectorid","contactid","linkid","panelid",
    "respondentid","recordid","interviewid","formid","trackingid","deviceid",
    "sessionid","sessiontoken","accesstoken","apitoken","embeddata",
    # Generic tech timestamps / IDs
    "timestamp","createdat","updatedat","submittedat","completedat","startedat",
    "latitude","longitude","browserinfo","platforminfo","useragent",
})

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_LONG_TOKEN_RE = re.compile(r"^[0-9A-Za-z_\-\.]{16,}$")  # long token, no spaces


def _is_operational_metadata(col_id: str, series=None) -> tuple[bool, str]:
    """Return (is_operational, reason).

    Detects administrative/technical columns with no analytical value.
    Examples: StartDate, ResponseId, IPAddress, UUIDs, session tokens.

    Conservative: only removes columns that are CLEARLY operational.
    High-cardinality analytical fields (cidade, empresa) are NOT removed.
    """
    col_clean = re.sub(r"[_\-\.\s]", "", col_id.lower())

    # 1. Name-based: exact match against known operational keywords
    if col_clean in _OP_COL_KEYWORDS:
        return True, f"nome reconhecido como metadado operacional do fornecedor"

    # 2. Recipient* prefix (RecipientFirstName, RecipientLastName, etc.)
    if col_clean.startswith("recipient"):
        return True, "coluna Recipient* — metadado de distribuição da pesquisa"

    if series is None:
        return False, ""

    non_empty = [
        str(v).strip() for v in series
        if v is not None and str(v).strip() and str(v).strip().lower() not in ("nan", "none")
    ]
    if len(non_empty) < 5:
        return False, ""

    n         = len(non_empty)
    n_unique  = len(set(non_empty))
    u_ratio   = n_unique / n
    sample    = non_empty[:min(20, n)]

    # 3. UUID pattern (universally unique per respondent)
    uuid_hits = sum(1 for v in sample if _UUID_RE.match(v))
    if uuid_hits >= max(1, len(sample) * 0.8):
        return True, f"valores em formato UUID ({sample[0][:22]}…)"

    # 4. Near-unique + long token-like values (IDs, hashes, tokens, session keys)
    # Must have ≥95 % unique values AND long values with no spaces → not natural language
    if u_ratio > 0.95 and n >= 10:
        avg_len    = sum(len(v) for v in sample) / len(sample)
        space_pct  = sum(1 for v in sample if " " in v) / len(sample)
        token_hits = sum(1 for v in sample if _LONG_TOKEN_RE.match(v))
        if avg_len >= 16 and space_pct < 0.15 and token_hits >= len(sample) * 0.7:
            return True, (
                f"ID/token operacional — {u_ratio:.0%} únicos, "
                f"avg_len={avg_len:.0f}, sem espaços"
            )

    return False, ""

# ── Known scale orderings ─────────────────────────────────────────────────────
_KNOWN_SCALE_ORDERINGS: list[tuple] = [
    (frozenset({"muito insatisfeito","insatisfeito","neutro","satisfeito","muito satisfeito"}),
     ["muito insatisfeito","insatisfeito","neutro","satisfeito","muito satisfeito"]),
    (frozenset({"muito insatisfeito","insatisfeito","nem satisfeito nem insatisfeito","satisfeito","muito satisfeito"}),
     ["muito insatisfeito","insatisfeito","nem satisfeito nem insatisfeito","satisfeito","muito satisfeito"]),
    (frozenset({"pessimo","ruim","regular","bom","otimo"}),
     ["pessimo","ruim","regular","bom","otimo"]),
    (frozenset({"muito ruim","ruim","neutro","bom","muito bom"}),
     ["muito ruim","ruim","neutro","bom","muito bom"]),
    (frozenset({"discordo totalmente","discordo","neutro","concordo","concordo totalmente"}),
     ["discordo totalmente","discordo","neutro","concordo","concordo totalmente"]),
    (frozenset({"discordo totalmente","discordo parcialmente","nao concordo nem discordo","concordo parcialmente","concordo totalmente"}),
     ["discordo totalmente","discordo parcialmente","nao concordo nem discordo","concordo parcialmente","concordo totalmente"]),
    (frozenset({"nunca","raramente","as vezes","frequentemente","sempre"}),
     ["nunca","raramente","as vezes","frequentemente","sempre"]),
    (frozenset({"sim","nao"}), ["sim","nao"]),
    (frozenset({"masculino","feminino"}), ["feminino","masculino"]),
]

# ── UF map ────────────────────────────────────────────────────────────────────
_UF_MAP: dict[str, int] = {
    "acre":1,"alagoas":2,"amapa":3,"amazonas":4,"bahia":5,"ceara":6,
    "distrito federal":7,"espirito santo":8,"goias":9,"maranhao":10,
    "mato grosso":11,"mato grosso do sul":12,"minas gerais":13,"para":14,
    "paraiba":15,"parana":16,"pernambuco":17,"rio de janeiro":19,
    "rio grande do norte":20,"rio grande do sul":21,"rondonia":22,"roraima":23,
    "santa catarina":24,"sao paulo":25,"sergipe":26,"tocantins":27,
    "ac":1,"al":2,"ap":3,"am":4,"ba":5,"ce":6,"df":7,"es":8,"go":9,
    "ma":10,"mt":11,"ms":12,"mg":13,"pa":14,"pb":15,"pr":16,"pe":17,
    "pi":18,"rj":19,"rn":20,"rs":21,"ro":22,"rr":23,"sc":24,"sp":25,"se":26,"to":27,
}

# ── Dataclass de elegibilidade ────────────────────────────────────────────────
@dataclass
class SentimentEligibility:
    eligible: bool
    score: float
    reasons_for: list = field(default_factory=list)
    reasons_against: list = field(default_factory=list)

    def label(self) -> str:
        return "Elegível" if self.eligible else "Não elegível"

    def summary(self) -> str:
        parts = [f"{self.label()} (score {self.score:+.1f})"]
        if self.reasons_for:
            parts.append("✔ " + "; ".join(self.reasons_for))
        if self.reasons_against:
            parts.append("✖ " + "; ".join(self.reasons_against))
        return " | ".join(parts)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _non_empty_texts(series) -> list[str]:
    """Extract non-empty string values from a Series, excluding nan/None."""
    return [
        str(v).strip()
        for v in series
        if v is not None and str(v).strip() and str(v).strip().lower() not in ("nan", "none")
    ]

def is_evaluable_for_sentiment(series) -> bool:
    """Return True if series has enough real text (quantity + length) for sentiment analysis.

    This checks DATA QUANTITY only — not whether the question is opinion-bearing.
    Use check_sentiment_eligibility() for the full structural check.
    """
    non_empty = _non_empty_texts(series)
    if len(non_empty) < _MIN_EVALUABLE_ROWS:
        return False
    evaluable = [t for t in non_empty if not _TRIVIAL_PATTERN.match(t)]
    if len(evaluable) < _MIN_EVALUABLE_ROWS:
        return False
    return (sum(len(t) for t in evaluable) / len(evaluable)) >= _MIN_AVG_TEXT_LEN

def _content_sentiment_signals(series) -> tuple[float, list[str]]:
    """Analyse response content for signals of evaluative/opinion language.

    Returns (score_delta, reasons_list). Positive score = opinion-bearing evidence.
    """
    texts = _non_empty_texts(series)
    if not texts:
        return -3.0, ["sem respostas para analisar"]

    # Use _norm lazily — defined later in module but resolved at call time
    avg_len = sum(len(t) for t in texts) / len(texts)
    score = 0.0
    reasons: list[str] = []

    if avg_len > 60:
        score += 2.0
        reasons.append(f"respostas longas (média {avg_len:.0f} chars)")
    elif avg_len > 30:
        score += 1.0
        reasons.append(f"comprimento médio razoável ({avg_len:.0f} chars)")
    elif avg_len < 15:
        score -= 2.0
        reasons.append(f"respostas muito curtas (média {avg_len:.0f} chars) — provavelmente factual")

    hits = sum(
        1 for t in texts
        if _EMOTIONAL_WORDS & set(_norm(t).split())
    )
    ratio = hits / len(texts)
    if ratio > 0.25:
        score += 2.0
        reasons.append(f"{ratio:.0%} das respostas contêm linguagem avaliativa/emocional")
    elif ratio > 0.10:
        score += 0.5
        reasons.append(f"{ratio:.0%} das respostas contêm linguagem avaliativa")

    return score, reasons

def check_sentiment_eligibility(question_text: str, series=None) -> SentimentEligibility:
    """Determina se uma pergunta open-text é elegível para análise de sentimento.

    Separa dois conceitos distintos:
      - tipo estrutural (open_text, single_choice…) → tratado em _infer_type_from_content
      - elegibilidade para sentimento → esta função

    Critérios:
      1. Texto da pergunta: padrões de intenção opinativa vs. cadastral/factual
      2. Conteúdo das respostas: comprimento médio, presença de linguagem emocional
      3. Quantidade mínima de respostas avaliáveis (via is_evaluable_for_sentiment)
    """
    # Normalize question text for pattern matching (no accents, lowercase)
    qt = _norm(question_text or "")

    opinion_score = 0.0
    factual_score = 0.0
    reasons_for:     list[str] = []
    reasons_against: list[str] = []

    for pattern, weight, reason in _OPINION_PATTERNS:
        if pattern.search(qt):
            opinion_score += weight
            reasons_for.append(reason)

    for pattern, weight, reason in _FACTUAL_PATTERNS:
        if pattern.search(qt):
            factual_score += weight
            reasons_against.append(reason)

    # Content signals (requires series)
    content_score = 0.0
    if series is not None:
        if not is_evaluable_for_sentiment(series):
            reasons_against.append("respostas insuficientes ou triviais")
            return SentimentEligibility(False, round(opinion_score - factual_score, 2),
                                        reasons_for, reasons_against)
        cscore, creasons = _content_sentiment_signals(series)
        content_score = cscore
        (reasons_for if cscore >= 0 else reasons_against).extend(creasons)

    net = round(opinion_score + content_score - factual_score, 2)

    # Hard block: strong cadastral/factual signal wins regardless of other signals
    if factual_score >= 3.0:
        reasons_against.append(f"sinal cadastral forte (factual={factual_score:.1f})")
        return SentimentEligibility(False, net, reasons_for, reasons_against)

    eligible = net >= 1.5
    if not eligible and net >= 0:
        reasons_against.append("sinal opinativo insuficiente para análise de sentimento")

    return SentimentEligibility(eligible, net, reasons_for, reasons_against)

def _infer_type_from_content(series) -> str | None:
    """Infer structural question type from response data.

    This is about STRUCTURE only (open_text vs single_choice vs numeric).
    It does NOT decide sentiment eligibility — use check_sentiment_eligibility() for that.

    PRIMARY criterion: does the data come from a finite, fixed set of alternatives?
    Text length is NOT used as the primary signal — a faixa de renda label can be 60 chars
    but is still unambiguously categorical because the same strings repeat across rows.
    """
    non_empty = _non_empty_texts(series)
    if len(non_empty) < 2:
        return None

    n            = len(non_empty)
    unique_vals  = set(non_empty)
    n_unique     = len(unique_vals)
    unique_ratio = n_unique / n
    avg_reps     = n / n_unique   # average times each unique value repeats across respondents
    avg_len      = sum(len(t) for t in non_empty) / n

    # ── Numeric branch (unchanged) ────────────────────────────────────────────
    def _to_float(s):
        try: return float(s.replace(",", "."))
        except: return None

    floats        = [_to_float(t) for t in non_empty]
    numeric_ratio = sum(1 for f in floats if f is not None) / n

    if numeric_ratio > 0.9:
        valid = [f for f in floats if f is not None]
        if valid:
            lo, hi = min(valid), max(valid)
            if lo >= 0 and hi <= 10 and n_unique >= 5 and all(f == int(f) for f in valid):
                return "nps"
        return "single_choice" if n_unique <= 7 else "numeric"

    # ── PRIMARY: closed categorical detected by REPETITION, not text length ──
    # Each unique value appearing ≥2× on average is strong evidence of a fixed option set.
    # This correctly classifies faixa de renda, escolaridade, motivo, plano, etc.
    # even when their labels are long descriptive strings.
    if n_unique <= 30 and avg_reps >= 2.0:
        return "single_choice"

    # Very small fixed set (handles tiny samples where avg_reps < 2 but set is tiny)
    if n_unique <= 5 and unique_ratio < 1.0:
        return "single_choice"

    # ── High-diversity signals → open_text ───────────────────────────────────
    # avg_len > 8 prevents misclassifying short repeated sets (Sim/Não) that
    # fall through here due to small sample sizes.
    if unique_ratio > 0.6 and avg_len > 8:
        return "open_text"

    # Long text with moderate-to-high diversity (true free comments, not caught above)
    if avg_len > 25 and unique_ratio > 0.3:
        return "open_text"

    # Few unique values as final fallback
    if n_unique <= 8:
        return "single_choice"

    return "open_text"

def _auto_col_width(col) -> float:
    """Compute Excel column width (characters) from content at the 90th percentile."""
    lengths = [len(str(col.header))]
    for v in col.values:
        if v is not None:
            lengths.append(len(str(v).split("\n")[0][:300]))
    if len(lengths) < 2:
        return 14.0
    lengths.sort()
    p90 = lengths[max(0, int(len(lengths) * 0.90) - 1)]
    raw = p90 * 1.1 + 2
    if col.col_type == "open_text":
        return max(_COL_MIN_WIDTH, min(_COL_MAX_TEXT_WIDTH, raw))
    return max(_COL_MIN_WIDTH, min(_COL_MAX_OTHER_WIDTH, raw))

def _strip_html(text: str) -> str:
    """Decode HTML entities and remove HTML tags from Qualtrics QuestionText."""
    text = _html_mod.unescape(text)          # &amp; → &,  &nbsp; → \xa0, &#8203; → ''
    text = re.sub(r"<[^>]+>", " ", text)     # <strong>…</strong> → " "
    return re.sub(r"\s+", " ", text).strip()

def _norm(s):
    if not isinstance(s, str): s = str(s) if s is not None else ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").strip().lower()

def _deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def _is_already_numeric(series) -> bool:
    """Return True if >90% of non-empty values in series are numeric strings."""
    non_empty = [str(v).strip() for v in series
                 if v is not None and str(v).strip() and str(v).strip().lower() not in ("nan", "none")]
    if not non_empty:
        return True
    numeric_count = sum(1 for v in non_empty if re.match(r"^-?\d+(?:[.,]\d+)?$", v))
    return numeric_count / len(non_empty) > 0.9


def _infer_value_map(
    series,
    qsf_q: "QsfQuestion | None",
) -> tuple[dict[str, int], str]:
    """Return (value_map, alternatives_string).

    value_map: {_norm(label): code}
    alternatives: "1=Label; 2=Label2; ..."

    Priority:
    1. QSF choices
    2. Known scale orderings
    3. UF map
    4. First-appearance order
    """
    # 1. QSF choices
    if qsf_q and qsf_q.choices:
        ordered = qsf_q.choice_order or sorted(qsf_q.choices.keys())
        value_map: dict[str, int] = {}
        display_map: dict[int, str] = {}
        for code in ordered:
            label = qsf_q.choices.get(code, "")
            if label:
                value_map[_norm(label)] = int(code)
                display_map[int(code)] = label
        if value_map:
            alts = "; ".join(f"{c}={display_map[c]}" for c in sorted(display_map))
            return value_map, alts

    # Collect unique non-empty normalised values from data
    non_empty = [str(v).strip() for v in series
                 if v is not None and str(v).strip() and str(v).strip().lower() not in ("nan", "none")]
    unique_normed = list(dict.fromkeys(_norm(v) for v in non_empty))  # order-preserving unique

    if not unique_normed:
        return {}, ""

    # 2. Known scale orderings
    unique_set = frozenset(unique_normed)
    for scale_set, scale_order in _KNOWN_SCALE_ORDERINGS:
        if unique_set <= scale_set:
            value_map = {}
            display_map = {}
            for i, key in enumerate(scale_order, 1):
                if key in unique_set:
                    value_map[key] = i
                    display_map[i] = key.capitalize()
            if value_map:
                alts = "; ".join(f"{c}={display_map[c]}" for c in sorted(display_map))
                return value_map, alts

    # 3. UF map — if all unique normed values are in _UF_MAP
    if unique_set and all(v in _UF_MAP for v in unique_set):
        value_map = {v: _UF_MAP[v] for v in unique_set}
        # Build display map from original (non-normed) values
        seen: dict[int, str] = {}
        for raw in non_empty:
            k = _norm(raw)
            code = _UF_MAP.get(k)
            if code is not None and code not in seen:
                seen[code] = raw
        alts = "; ".join(f"{c}={seen.get(c, str(c))}" for c in sorted(seen))
        return value_map, alts

    # 4. First-appearance order
    value_map = {}
    display_map = {}
    code = 1
    for nv in unique_normed:
        value_map[nv] = code
        # Use first original value that normalises to nv
        orig = next((str(v).strip() for v in non_empty if _norm(str(v).strip()) == nv), nv)
        display_map[code] = orig
        code += 1
    alts = "; ".join(f"{c}={display_map[c]}" for c in sorted(display_map))
    return value_map, alts


def _apply_value_map(value: str, value_map: dict[str, int]):
    """Convert a cell value using value_map. Returns int, or original numeric, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    normed = _norm(s)
    if normed in value_map:
        return value_map[normed]
    # Already numeric — keep it
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return s  # fallback — should not happen if value_map is complete


def _is_one_hot_group(sibling_series: "list[pd.Series]") -> bool:
    """Return True if at most one sibling is non-zero/non-empty per row."""
    if not sibling_series:
        return False
    n_rows = len(sibling_series[0])
    for row_i in range(n_rows):
        non_zero = 0
        for s in sibling_series:
            v = str(s.iloc[row_i]).strip() if row_i < len(s) else ""
            if v and v.lower() not in ("nan", "none", "0", ""):
                non_zero += 1
        if non_zero > 1:
            return False
    return True


def _compute_encoding(
    qid: str,
    col_type: str,
    qsf_q: "QsfQuestion | None",
    series: "pd.Series | None",
    sibling_col_ids: list[str],
    sibling_series_map: "dict[str, pd.Series]",
    all_qids_in_base: list[str],
) -> tuple[str, dict, list[str], str]:
    """Return (encoding_strategy, value_map, grouped_with, alternatives)."""
    # ── open text / NPS / numeric / metadata ─────────────────────────────────
    if col_type == "open_text":
        return "text_preserve", {}, [], "Texto livre"
    if col_type == "nps":
        return "direct", {}, [], "0-10"
    if col_type == "numeric":
        return "direct", {}, [], ""
    if col_type == "metadata":
        return "text_preserve", {}, [], ""
    if col_type == "date":
        return "direct", {}, [], ""

    # ── multiple_choice indicator (MAVR sub-columns) ──────────────────────────
    if col_type == "multiple_choice":
        return "indicator", {}, [], "0=Não selecionado; 1=Selecionado"

    # ── ranking ───────────────────────────────────────────────────────────────
    if col_type == "ranking":
        if qsf_q:
            n = len(qsf_q.choices)
            alts = f"1=Mais importante; {n}=Menos importante"
        else:
            alts = ""
        return "direct", {}, [], alts

    # ── NPS GROUP ─────────────────────────────────────────────────────────────
    if "_NPS_GROUP" in qid:
        return "direct", {}, [], "1=Detrator; 2=Passivo; 3=Promotor"

    # ── single_choice / likert / dichotomous ─────────────────────────────────
    # Detect one-hot group: QSF SAVR with numeric sub-columns Q{n}_1, Q{n}_2…
    # or data-pattern detection when no QSF
    m_sub = re.match(r"(Q\d+)_(\d+)$", qid)
    is_sub_column = bool(m_sub)

    if is_sub_column:
        base_id = m_sub.group(1)
        # Check if parent QSF says SAVR — then these sub-columns are one-hot
        parent_qsf = qsf_q  # qsf_q is already looked up on the base tag
        qsf_says_savr = (parent_qsf is not None and
                         parent_qsf.question_type == "MC" and
                         parent_qsf.selector == "SAVR")

        # All numeric sub-column IDs for this base (including self)
        numeric_sub_ids = [sid for sid in all_qids_in_base
                           if re.match(r"Q\d+_\d+$", sid) and not sid.endswith("_TEXT")]

        if len(numeric_sub_ids) > 1:
            # Determine if one-hot via QSF or data pattern
            if qsf_says_savr:
                is_one_hot = True
            else:
                # Data-pattern detection
                sib_series = [sibling_series_map[sid] for sid in numeric_sub_ids
                              if sid in sibling_series_map]
                is_one_hot = _is_one_hot_group(sib_series) if sib_series else False

            if is_one_hot:
                # First numeric sub-column alphabetically becomes the collapse host
                first_sub = sorted(numeric_sub_ids)[0]
                others = [s for s in sorted(numeric_sub_ids) if s != first_sub]

                if qid == first_sub:
                    # This column is the collapse host
                    # Build value_map from QSF choices: choice_code → choice_label
                    # For one-hot: each sub-column index maps to a choice code
                    value_map: dict[str, int] = {}
                    display_map: dict[int, str] = {}
                    if parent_qsf and parent_qsf.choices:
                        ordered = parent_qsf.choice_order or sorted(parent_qsf.choices.keys())
                        for rank, code in enumerate(ordered, 1):
                            label = parent_qsf.choices.get(code, "")
                            if label:
                                value_map[str(code)] = int(code)
                                display_map[int(code)] = label
                        alts = "; ".join(f"{c}={display_map[c]}" for c in sorted(display_map))
                    else:
                        # Fallback: sub-column index → code
                        for sid in sorted(numeric_sub_ids):
                            m = re.match(r"Q\d+_(\d+)$", sid)
                            if m:
                                idx = int(m.group(1))
                                value_map[str(idx)] = idx
                                display_map[idx] = str(idx)
                        alts = "; ".join(f"{c}={display_map[c]}" for c in sorted(display_map))
                    return "onehot_collapse", value_map, others, alts
                else:
                    # This is a subsumed sub-column
                    return "subsumed", {}, [], ""

    # ── Standard single_choice / likert / dichotomous column ─────────────────
    if series is not None and _is_already_numeric(series):
        # Already numeric — figure out alternatives from QSF choices
        if qsf_q and qsf_q.choices:
            ordered = qsf_q.choice_order or sorted(qsf_q.choices.keys())
            alts = "; ".join(f"{c}={qsf_q.choices[c]}" for c in ordered if c in qsf_q.choices)
        else:
            alts = ""
        return "direct", {}, [], alts

    # Text values need encoding
    value_map, alts = _infer_value_map(series, qsf_q)
    return "text_encode", value_map, [], alts


# Padrões de abertura típicos de perguntas de survey em português.
# Aplicados sobre texto já normalizado (_norm): sem acentos, lowercase.
# Cada padrão remove uma construção formulaica de introdução,
# deixando apenas o conteúdo substantivo da pergunta.
_INTRO_STRIP_PATTERNS: tuple[re.Pattern, ...] = (
    # "Pensando agora[,]..." ou "Pensando [no/em/sobre] X[,]..."
    re.compile(r"^pensando\s+(?:agora\s*[,;.]\s*|[^,;.]{5,70}[,;.]\s*)"),
    # "Ainda pensando [no/em] X[,]..."
    re.compile(r"^ainda\s+pensando\s+[^,;.]{5,70}[,;.]\s*"),
    # "Considerando [que/sua/seu] X[,]..."
    re.compile(r"^considerando\s+[^,;.]{5,80}[,;.]\s*"),
    # "Atualmente[,] ..." — apenas quando seguido de vírgula
    re.compile(r"^atualmente\s*[,;.]\s*"),
    # "Agora[,] ..."
    re.compile(r"^agora\s*[,;.]\s*"),
    # "Hoje[,] ..."
    re.compile(r"^hoje\s*[,;.]\s*"),
    # "Além do/da/de X[,]..."
    re.compile(r"^alem\s+d[oae]?\s+[^,;.]{5,80}[,;.]\s*"),
    # "Gostaríamos de saber [se/qual/como] ..."
    re.compile(r"^(?:nos\s+)?gostari[ao]mos\s+de\s+saber\b[^,;.]{0,50}[,;]?\s*"),
    # "Iniciaremos/Iniciando X[,]..."
    re.compile(r"^inici(?:aremos|ando|amos|almente)\b[^,;.]{0,60}[,;.]\s*"),
    # "Em relação a X[,]..."
    re.compile(r"^em\s+relacao\s+ao?\s+[^,;.]{5,60}[,;.]\s*"),
    # "Com base em X[,]..."
    re.compile(r"^com\s+base\s+em\s+[^,;.]{5,60}[,;.]\s*"),
    # "De acordo com X[,]..."
    re.compile(r"^de\s+acordo\s+com\s+[^,;.]{5,60}[,;.]\s*"),
    # "No contexto de X[,]..."
    re.compile(r"^no\s+contexto\s+d[eo]?\s+[^,;.]{5,60}[,;.]\s*"),
    # "Você[,]..." — endereçamento direto inicial
    re.compile(r"^voce\s*,\s*"),
    # "Neste/Nessa momento/cenário[,]..."
    re.compile(r"^n(?:este|essa|esse|aquele|aquela)\s+(?:momento|cenario|contexto)\s*[,;.]\s*"),
    # "No momento de X[,]..." — ex.: "No momento de escolha alugar X, selecione..."
    re.compile(r"^no\s+momento\s+d[eo]?\s+[^,;.]{5,80}[,;.]\s*"),
)
_MIN_WORDS_AFTER_STRIP = 3  # não aplica o strip se restar menos que isso


def _strip_intro_phrases(text: str) -> str:
    """Remove construções introdutórias comuns do início de texto normalizado.

    Recebe texto já passado por _norm() (sem acentos, lowercase).
    Aplica cada padrão uma vez. Só aceita o strip se restar texto suficiente.
    """
    result = text
    for pattern in _INTRO_STRIP_PATTERNS:
        candidate = pattern.sub("", result, count=1).strip()
        remaining_words = len(re.findall(r"[a-z]+", candidate))
        if candidate != result and remaining_words >= _MIN_WORDS_AFTER_STRIP:
            result = candidate
    return result


def _extract_meaningful_words(text: str, limit: int = 3) -> list[str]:
    cleaned = _norm(text)
    cleaned = re.sub(r"\[.*?\]", " ", cleaned)
    cleaned = re.sub(r"\(.*?\)", " ", cleaned)
    # Remover tags HTML antes de processar (defesa em profundidade)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Strip de construções introdutórias antes de extrair palavras
    cleaned = _strip_intro_phrases(cleaned)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    words = re.findall(r"[a-z0-9]+", cleaned)
    chosen = []
    for word in words:
        if len(word) <= 2 or word in SHORT_NAME_STOPWORDS:
            continue
        chosen.append(word.capitalize())
        if len(chosen) >= limit:
            break
    return chosen

def _sanitize_short_name(text: str, fallback: str = "") -> str:
    parts = _extract_meaningful_words(text, limit=3)
    if len(parts) < 3 and fallback:
        for word in _extract_meaningful_words(fallback, limit=3):
            if word not in parts:
                parts.append(word)
            if len(parts) >= 3:
                break
    if not parts:
        raw = _deaccent(text or fallback).strip("_ ")
        raw = re.sub(r"[^A-Za-z0-9_ ]", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        tokens = [token.capitalize() for token in raw.replace("_", " ").split() if token][:3]
        return "_".join(tokens)
    return "_".join(parts[:3])

# ── QSF parsing ───────────────────────────────────────────────────────────────
@dataclass
class QsfQuestion:
    export_tag: str          # Q1, Q6, Q11, Q12, Q13
    question_text: str       # Full question text
    question_type: str       # MC, RO, TE, Matrix, Slider...
    selector: str            # SAVR, MAVR, NPS, DND, SL...
    choices: dict            # {1: "Masculino", 2: "Feminino"}
    has_text_entry: bool     # True if any choice has TextEntry
    choice_order: list       # [1, 2, 3...]

def parse_qsf(path: str) -> tuple[dict[str, QsfQuestion], set[str]]:
    """Parse QSF file. Returns (questions dict keyed by DataExportTag, set of timing tags)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = {}
    timing_tags = set()
    for el in data.get("SurveyElements", []):
        if el.get("Element") != "SQ":
            continue
        p = el.get("Payload", {})
        tag = p.get("DataExportTag", "")
        if not tag:
            continue

        if p.get("QuestionType") == "Timing":
            timing_tags.add(tag)
            continue

        # Parse choices
        raw_choices = p.get("Choices", {})
        choices = {}
        has_text = False
        if isinstance(raw_choices, dict):
            for ck, cv in raw_choices.items():
                if isinstance(cv, dict):
                    choices[int(ck)] = cv.get("Display", "")
                    if cv.get("TextEntry") == "true":
                        has_text = True

        questions[tag] = QsfQuestion(
            export_tag=tag,
            question_text=_strip_html(p.get("QuestionText", "")),
            question_type=p.get("QuestionType", ""),
            selector=p.get("Selector", ""),
            choices=choices,
            has_text_entry=has_text,
            choice_order=p.get("ChoiceOrder", list(choices.keys())),
        )
    return questions, timing_tags

def _qsf_to_type(q: QsfQuestion) -> str:
    """Map QSF question type/selector to our type system."""
    qt, sel = q.question_type, q.selector
    if qt == "TE": return "open_text"
    if qt == "RO": return "ranking"
    if qt == "MC":
        if sel == "NPS": return "nps"
        if sel == "MAVR": return "multiple_choice"
        # SAVR: check if it's Likert-like or dichotomous
        labels = set(_norm(v) for v in q.choices.values())
        if len(q.choices) == 2 and labels.issubset({"sim","nao","yes","no"}):
            return "dichotomous"
        if labels & LIKERT_KEYWORDS:
            return "likert"
        return "single_choice"
    if qt == "Slider": return "numeric"
    if qt == "Matrix": return "single_choice"  # Simplified
    return "single_choice"

# ── Reading XLSX ──────────────────────────────────────────────────────────────
@dataclass
class DataColumn:
    col_index: int
    qualtrics_id: str     # Q1, Q6_1, Q6_6_TEXT, Q11_1, Q12_NPS_GROUP
    question_text: str    # Line 2 of export
    sample_values: list

def read_xlsx(path: str) -> tuple[pd.DataFrame, list[DataColumn]]:
    """Read Qualtrics numeric XLSX export."""
    import openpyxl as xl
    wb = xl.load_workbook(path, data_only=True); ws = wb.active
    ids = [ws.cell(1,c).value or f"col_{c}" for c in range(1, ws.max_column+1)]
    texts = [ws.cell(2,c).value or "" for c in range(1, ws.max_column+1)]
    df = pd.read_excel(path, header=None, skiprows=2, dtype=str)
    df.columns = ids
    columns = []
    for i,(qid,qtxt) in enumerate(zip(ids,texts)):
        samples = [str(ws.cell(r,i+1).value).strip() for r in range(3, min(ws.max_row+1,20))
                   if ws.cell(r,i+1).value and str(ws.cell(r,i+1).value).strip()][:5]
        columns.append(DataColumn(i, str(qid), str(qtxt), samples))
    wb.close()
    return df, columns

def _drop_technical(df, columns):
    si = next((i for i,c in enumerate(columns) if c.qualtrics_id == "StartDate"), None)
    ei = next((i for i,c in enumerate(columns) if c.qualtrics_id == "UserLanguage"), None)
    if si is not None and ei is not None and ei >= si:
        drop_ids = [columns[j].qualtrics_id for j in range(si, ei+1)]
        df = df.drop(columns=[c for c in drop_ids if c in df.columns], errors="ignore")
        columns = columns[:si] + columns[ei+1:]
    return df, columns

# ── Config table builder ─────────────────────────────────────────────────────
def _extract_base_tag(qid: str) -> str:
    """Q6_1 -> Q6, Q6_6_TEXT -> Q6, Q12_NPS_GROUP -> Q12, Q11_1 -> Q11."""
    if "_NPS_GROUP" in qid:
        return qid.replace("_NPS_GROUP", "")
    if qid.endswith("_TEXT"):
        # Q6_6_TEXT -> base is Q6
        m = re.match(r"(Q\d+)", qid)
        return m.group(1) if m else qid
    m = re.match(r"(Q\d+)", qid)
    return m.group(1) if m else qid

def _choice_label(qsf_q: QsfQuestion, choice_num: int) -> str:
    """Get the choice label for a specific choice number."""
    return qsf_q.choices.get(choice_num, "")

def _make_short_name_ai(question_text: str, provider) -> str:
    """Use AI to generate a 3-word summary."""
    try:
        sys_prompt = ("Resuma a pergunta abaixo em exatamente 3 palavras-chave em portugues, "
                      "separadas por underscore, sem acentos, sem artigos e sem cortar palavras. "
                      "Responda APENAS o resumo, nada mais. "
                      "Exemplos: Perfil_Do_Cliente, Motivo_Da_Visita, Satisfacao_Com_Atendimento")
        result = provider.complete(sys_prompt, question_text, max_tokens=20)
        name = _sanitize_short_name(result.strip().replace(" ", "_"), fallback=question_text)
        if name and len(name) <= 40:
            return name
    except:
        pass
    return ""

def _make_short_name_heuristic(question_text: str) -> str:
    """Fallback: extract 3 meaningful full words from question text."""
    return _sanitize_short_name(question_text)

def build_output_header(qid: str, short_name: str, subitem: str = "") -> str:
    if subitem:
        sub_clean = _sanitize_short_name(subitem, fallback=qid)
        return f"{qid}_{sub_clean}" if sub_clean else qid
    normalized_short = _sanitize_short_name(short_name, fallback=qid)
    return f"{qid}_{normalized_short}" if normalized_short and normalized_short != _deaccent(qid) else qid

def _resolve_duplicate_codes(config: list[dict]) -> None:
    """Resolve short_name colisions by adding discriminating semantic context.

    Operates in-place on config rows. For each group of included rows that share
    the same short_name, finds words unique to each question and appends them.
    Numeric suffixes are used only as a last resort.
    """
    from collections import defaultdict, Counter

    # Index included rows by their short_name
    by_code: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(config):
        if row.get("include", True):
            by_code[row["short_name"]].append(i)

    for code, indices in by_code.items():
        if len(indices) <= 1:
            continue

        # Extract substantive words from each question text
        per_q: list[list[str]] = []
        for idx in indices:
            qtxt = _norm(config[idx].get("question_text", ""))
            qtxt = _strip_intro_phrases(qtxt)
            words = [w for w in re.findall(r"[a-z]+", qtxt)
                     if len(w) > 3 and w not in SHORT_NAME_STOPWORDS]
            per_q.append(words)

        # Words that appear in exactly one of the duplicated questions → discriminating
        in_how_many: Counter = Counter()
        for words in per_q:
            for w in set(words):
                in_how_many[w] += 1
        discriminating: set[str] = {w for w, n in in_how_many.items() if n == 1}

        for list_pos, cfg_idx in enumerate(indices):
            my_words = per_q[list_pos]
            my_disc = [w for w in my_words if w in discriminating]

            if my_disc:
                # Prefer the longest discriminating word (more specific)
                my_disc.sort(key=lambda w: -len(w))
                config[cfg_idx]["short_name"] = f"{code}_{my_disc[0].capitalize()}"
            elif list_pos > 0:
                # No unique discriminating word found — numeric suffix as last resort
                config[cfg_idx]["short_name"] = f"{code}_{list_pos + 1}"


def build_config(xlsx_path: str, qsf_path: str, provider=None) -> tuple[list[dict], pd.DataFrame]:
    """Build configuration table from QSF + XLSX. Returns (config_rows, dataframe)."""
    qsf_questions, timing_tags = parse_qsf(qsf_path)
    df, data_cols = read_xlsx(xlsx_path)
    df, data_cols = _drop_technical(df, data_cols)

    # Pre-compute: group col IDs by base tag (for one-hot detection)
    base_to_qids: dict[str, list[str]] = {}
    for dc in data_cols:
        base = _extract_base_tag(dc.qualtrics_id)
        base_to_qids.setdefault(base, []).append(dc.qualtrics_id)

    # Pre-compute: first clean XLSX question text per base tag.
    # XLSX row-2 text is the canonical source for short_name generation:
    # it contains no HTML, no chapter headings embedded by survey designers,
    # and matches exactly what is stored in each config row's question_text.
    base_to_xlsx_text: dict[str, str] = {}
    for dc in data_cols:
        b = _extract_base_tag(dc.qualtrics_id)
        if b not in base_to_xlsx_text and dc.question_text.strip():
            base_to_xlsx_text[b] = dc.question_text

    # Build series map once for cheap lookup
    series_map: dict[str, "pd.Series"] = {
        dc.qualtrics_id: df[dc.qualtrics_id]
        for dc in data_cols if dc.qualtrics_id in df.columns
    }

    # Batch AI naming if provider available
    ai_names = {}
    if provider:
        # Collect unique question texts — prefer XLSX text (cleaner, no headings)
        unique_texts = {}
        for dc in data_cols:
            base = _extract_base_tag(dc.qualtrics_id)
            if base in qsf_questions and base not in unique_texts:
                unique_texts[base] = (base_to_xlsx_text.get(base)
                                      or qsf_questions[base].question_text)
        # Single batch call for all names
        if unique_texts:
            try:
                sys_p = (
                    "Voce e um analista de dados. Para cada pergunta de survey abaixo, gere um codigo analitico "
                    "em PORTUGUES SEM ACENTOS que identifique o TEMA PRINCIPAL da variavel — o que ela mede. "
                    "IGNORAR: palavras introdutorias ('pensando', 'considerando', 'atualmente', 'agora', 'alem', "
                    "'gostariamos'), verbos de instrucao ('selecione', 'marque', 'indique'), pronomes e artigos. "
                    "FOCAR: substantivo principal + acao + contexto diferenciador. "
                    "Exemplos: 'Atualmente, alem do trabalho, voce tem outra ocupacao?' -> 'Outra_Ocupacao' | "
                    "'Quantas horas por semana voce trabalha como motorista?' -> 'Horas_Trabalho_Semanal' | "
                    "'Qual o seu genero?' -> 'Genero' | "
                    "'Por que voce escolheu a Localiza?' -> 'Motivo_Escolha_Localiza'. "
                    "Gere 2 a 4 palavras, sem artigos, separadas por underscore. "
                    "Responda APENAS JSON: {\"names\":{\"Q1\":\"Genero\",\"Q2\":\"Faixa_Etaria\",...}}"
                )
                user_p = json.dumps(unique_texts, ensure_ascii=False)
                raw = provider.complete(sys_p, user_p, max_tokens=2048)
                raw = re.sub(r"^```(?:json)?\s*","",raw.strip())
                raw = re.sub(r"\s*```$","",raw.strip())
                ai_names = json.loads(raw).get("names", {})
            except:
                pass

    _log_path = Path(__file__).parent / "diagnostico.log"
    _removed_cols: list[tuple[str, str]] = []   # (col_id, reason)

    config = []
    for dc in data_cols:
        qid = dc.qualtrics_id
        base = _extract_base_tag(qid)
        # Match both numeric (Q5_Page Submit → base Q5) and non-numeric (Q_TIMER_Page Submit)
        if base in timing_tags or any(qid == t or qid.startswith(t + "_") for t in timing_tags):
            _removed_cols.append((qid, "coluna de timing — removida automaticamente"))
            continue

        # Operational/administrative metadata check (ResponseId, IPAddress, UUIDs, tokens…)
        series_for_check = series_map.get(qid)
        is_op, op_reason = _is_operational_metadata(qid, series_for_check)
        if is_op:
            _removed_cols.append((qid, op_reason))
            continue

        qsf_q = qsf_questions.get(base)

        # Determine type: QSF metadata is primary, content inference fills gaps
        series = series_map.get(qid)
        if "_NPS_GROUP" in qid:
            col_type = "single_choice"
        elif qid.endswith("_TEXT"):
            col_type = "open_text"
        elif qsf_q:
            col_type = _qsf_to_type(qsf_q)
            # Matrix is a container type — refine with actual response content
            if qsf_q.question_type == "Matrix" and series is not None:
                inferred = _infer_type_from_content(series)
                if inferred:
                    col_type = inferred
        elif series is not None:
            col_type = _infer_type_from_content(series) or "single_choice"
        else:
            col_type = "single_choice"

        # For MC subitems (Q6_1, Q6_2...), type is already multiple_choice binary in data
        if qsf_q and qsf_q.selector == "MAVR" and re.match(r"Q\d+_\d+$", qid) and not qid.endswith("_TEXT"):
            col_type = "multiple_choice"

        # Generate short name.
        # Source priority:
        #   1. AI-generated name (when provider configured)
        #   2. XLSX question text (dc.question_text) — canonical, clean, no headings
        #   3. QSF question text — may contain chapter headings or HTML artifacts
        # Using dc.question_text as primary ensures question_code is derived from
        # the same text displayed in the UI and stored in question_text, preventing
        # semantic misalignment when QSF QuestionText contains embedded section headings.
        ai_raw      = ai_names.get(base, "")
        xlsx_text   = base_to_xlsx_text.get(base, dc.question_text)
        qsf_text    = qsf_q.question_text if qsf_q else ""
        short = _sanitize_short_name(ai_raw, fallback=xlsx_text)
        if not short:
            short = _make_short_name_heuristic(xlsx_text)
        if not short and qsf_text:
            short = _make_short_name_heuristic(qsf_text)
        if not short:
            short = _deaccent(qid)

        # For subitems, add the choice label
        subitem = ""
        m_sub = re.match(r"Q\d+_(\d+)$", qid)
        if m_sub and qsf_q:
            choice_num = int(m_sub.group(1))
            subitem = _choice_label(qsf_q, choice_num)

        # For ranking subitems
        if col_type == "ranking" and m_sub and qsf_q:
            choice_num = int(m_sub.group(1))
            subitem = _choice_label(qsf_q, choice_num)

        # Compute encoding metadata
        all_qids_in_base = base_to_qids.get(base, [qid])
        sibling_col_ids = [s for s in all_qids_in_base if s != qid]
        enc_strategy, value_map_dict, grouped_with, alternatives = _compute_encoding(
            qid, col_type, qsf_q, series,
            sibling_col_ids, series_map, all_qids_in_base,
        )

        # Build alternatives fallback for types not handled by _compute_encoding
        if not alternatives:
            if col_type == "open_text":
                alternatives = "Texto livre"
            elif col_type == "nps":
                alternatives = "0-10"
            elif col_type == "multiple_choice":
                alternatives = "0=Não selecionado; 1=Selecionado"
            elif col_type == "ranking" and qsf_q:
                n = len(qsf_q.choices)
                alternatives = f"1=Mais importante; {n}=Menos importante"
            elif "_NPS_GROUP" in qid:
                alternatives = "1=Detrator; 2=Passivo; 3=Promotor"
            elif qsf_q and qsf_q.choices:
                alternatives = "; ".join(f"{k}={v}" for k, v in sorted(qsf_q.choices.items()))

        # Group = base question tag
        group = base

        # Confidence
        confidence = "high" if qsf_q else "low"

        row = {
            "original_id": qid,
            "question_text": dc.question_text,
            "sample": "; ".join(dc.sample_values[:3])[:100],
            "include": True,
            "group": group,
            "type": col_type,
            "short_name": _sanitize_short_name(short, fallback=dc.question_text),
            "subitem": subitem,
            "alternatives": alternatives,
            "confidence": confidence,
            # Internal encoding metadata (not shown in UI)
            "_encoding_strategy": enc_strategy,
            "_value_map": value_map_dict,
            "_grouped_with": grouped_with,
        }

        # Subsumed columns are excluded by default
        if enc_strategy == "subsumed":
            row["include"] = False

        config.append(row)

    # Resolve duplicate short_names with semantic disambiguation
    _resolve_duplicate_codes(config)

    # Write removal log
    try:
        with _log_path.open("a", encoding="utf-8") as _f:
            _f.write("\n--- build_config: colunas removidas ---\n")
            for _cid, _reason in _removed_cols:
                _f.write(f"  REMOVIDA  {_cid}: {_reason}\n")
            kept = [c["original_id"] for c in config]
            for _cid in kept:
                _f.write(f"  MANTIDA   {_cid}\n")
    except Exception:
        pass

    return config, df

# ── AI sentiment + categorization ─────────────────────────────────────────────
DISC_SYS = ("Você é um analista de pesquisa. Analise os comentários e proponha até 10 categorias "
            "temáticas em português, snake_case sem acentos. Responda APENAS JSON: "
            "{\"categorias\":[\"preco\",\"atendimento\",...]}")
CLAS_SYS = ("Você é um analista. Para cada comentário, classifique sentimento (positivo/neutro/negativo) "
            "e até 3 categorias da lista. Responda APENAS JSON: "
            "{\"results\":[{\"idx\":0,\"sent\":\"positivo\",\"cats\":\"preco, atendimento\"},...]}")

@dataclass
class OutputColumn:
    header: str; question_text: str; col_type: str; values: list
    value_map: dict = field(default_factory=dict); group_key: str = ""
    alternatives: str = ""

@dataclass
class NormalizedColumn:
    new_id: str
    values: list

def _run_ai_analysis(columns, selected_headers, provider, n_rows):
    open_text_columns = [
        NormalizedColumn(new_id=col.header, values=col.values)
        for col in columns
        if col.col_type == "open_text"
    ]
    analysis_by_id = {
        result.column_id: result
        for result in analyze_columns(open_text_columns, selected_headers, provider)
    }

    result = []
    for col in columns:
        result.append(col)
        analysis = analysis_by_id.get(col.header)
        if analysis is None: continue

        categories = analysis.categories_discovered
        categories_label = ", ".join(categories) if categories else "Sem categorias"
        gk = col.group_key
        result.append(OutputColumn(f"{col.header}_sentimento", f"{col.question_text} - Sentimento",
            "single_choice", analysis.sentiment_values[:n_rows],
            {"Sem resposta":0,"Negativo":1,"Neutro":2,"Positivo":3}, gk,
            "0=Sem resposta; 1=Negativo; 2=Neutro; 3=Positivo"))
        result.append(OutputColumn(f"{col.header}_categorias", f"{col.question_text} - Categorias ({categories_label})",
            "open_text", analysis.category_values[:n_rows], {}, gk, f"Categorias: {categories_label}"))
    return result

# ── Normalize ─────────────────────────────────────────────────────────────────
def normalize(xlsx_path, output_path, config, df, ai_original_ids=None, provider=None):
    """Normalize using user-edited config. Applies encoding strategies per column.

    ai_original_ids — list of original Qualtrics IDs (e.g. ["Q3","Q7_TEXT"]) whose
                      open-text columns should have sentiment/category analysis applied.
                      The header lookup is done here so the caller never has to pre-compute
                      output headers, which avoids the dropdown-mismatch bug.
    """
    active = [c for c in config if c.get("include", True)]

    all_out = []
    id_to_header: dict[str, str] = {}
    # Track which qids have already been emitted (subsumed cols consumed by collapse)
    emitted: set[str] = set()

    for cfg in active:
        qid = cfg["original_id"]
        if qid in emitted:
            continue
        if qid not in df.columns:
            continue

        series = df[qid]
        col_type = cfg.get("type", "single_choice")
        short = cfg.get("short_name", qid)
        subitem = cfg.get("subitem", "")
        qtxt = cfg.get("question_text", "")
        group = cfg.get("group", qid)
        alt = cfg.get("alternatives", "")

        enc_strategy = cfg.get("_encoding_strategy", "direct")
        value_map = cfg.get("_value_map", {}) or {}
        grouped_with = cfg.get("_grouped_with", []) or []

        # Build header: keep Qualtrics numbering + short name
        header = build_output_header(qid, short, subitem)
        id_to_header[qid] = header

        # ── Convert values based on encoding strategy ─────────────────────────
        if enc_strategy == "text_preserve" or col_type == "open_text":
            values = [
                str(v).strip()
                if not pd.isna(v) and str(v).strip() and str(v).strip().lower() != "nan"
                else None
                for v in series
            ]

        elif enc_strategy == "indicator":
            values = []
            for v in series:
                s = str(v).strip() if not pd.isna(v) else ""
                if not s or s.lower() in ("nan", "none", "0", "false", ""):
                    values.append(0)
                else:
                    values.append(1)

        elif enc_strategy == "text_encode":
            values = []
            for v in series:
                s = str(v).strip() if not pd.isna(v) else ""
                if not s or s.lower() in ("nan", "none"):
                    values.append(None)
                else:
                    values.append(_apply_value_map(s, value_map))

        elif enc_strategy == "onehot_collapse":
            # Collect sibling series (grouped_with IDs) — index maps to choice code
            # value_map: {str(choice_code): int(choice_code)}
            # Each sibling sub-column Q{n}_k is selected when its value is truthy
            # The output value is the choice code of the selected sub-column

            # Build list of (sub_col_id, choice_code) sorted by sub-column index
            sub_col_id_to_code: dict[str, int] = {}
            # Self column
            m_self = re.match(r"Q\d+_(\d+)$", qid)
            if m_self:
                self_idx = int(m_self.group(1))
                # Find code for self index from value_map
                self_code = value_map.get(str(self_idx), self_idx)
                sub_col_id_to_code[qid] = self_code
            for sib_id in grouped_with:
                m_sib = re.match(r"Q\d+_(\d+)$", sib_id)
                if m_sib:
                    sib_idx = int(m_sib.group(1))
                    sib_code = value_map.get(str(sib_idx), sib_idx)
                    sub_col_id_to_code[sib_id] = sib_code

            n_rows_col = len(series)
            values = []
            for row_i in range(n_rows_col):
                selected_code = None
                for sub_id, code in sub_col_id_to_code.items():
                    if sub_id not in df.columns:
                        continue
                    sub_series = df[sub_id]
                    raw = str(sub_series.iloc[row_i]).strip() if row_i < len(sub_series) else ""
                    if raw and raw.lower() not in ("nan", "none", "0", "false", ""):
                        selected_code = code
                        break
                values.append(selected_code)

            # Mark grouped_with as emitted so they aren't re-processed
            for sib_id in grouped_with:
                emitted.add(sib_id)

        else:
            # direct (already numeric)
            values = []
            for v in series:
                s = str(v).strip() if not pd.isna(v) else ""
                if s and s.lower() != "nan":
                    try:
                        values.append(int(float(s)))
                    except (ValueError, TypeError):
                        try:
                            values.append(float(s))
                        except (ValueError, TypeError):
                            values.append(s)
                else:
                    values.append(None)

        emitted.add(qid)
        all_out.append(OutputColumn(header, qtxt, col_type, values, {}, group, alt))

    # Map original IDs → computed headers for AI analysis (guarantees consistency)
    ai_headers = None
    if ai_original_ids:
        ai_headers = [id_to_header[oid] for oid in ai_original_ids if oid in id_to_header]

    n_rows = len(df) if not all_out else len(all_out[0].values)
    if ai_headers and provider:
        all_out = _run_ai_analysis(all_out, ai_headers, provider, n_rows)

    _write_excel(all_out, n_rows, output_path)
    return {"status": "ok", "rows": n_rows, "columns": len(all_out), "headers": [c.header for c in all_out]}

# ── Validation ───────────────────────────────────────────────────────────────
def validate_output(columns: list) -> list[str]:
    """Return list of warning strings. Empty list = no issues."""
    warnings = []
    codes_seen: set[str] = set()
    for col in columns:
        qcode = col.header  # OutputColumn uses .header as the question_code
        if qcode in codes_seen:
            warnings.append(f"Duplicated question_code: {qcode}")
        codes_seen.add(qcode)
        if col.col_type not in ("open_text", "numeric", "date", "metadata") and not col.alternatives:
            warnings.append(f"{qcode}: alternatives empty for coded column")
        if col.col_type != "open_text":
            text_values = [
                v for v in col.values
                if v is not None and isinstance(v, str)
                and not v.replace(".", "").replace("-", "").isdigit()
            ]
            if text_values:
                warnings.append(
                    f"{qcode}: {len(text_values)} text values remain in Data tab (should be numeric)"
                )
    return warnings


# ── Excel writer ──────────────────────────────────────────────────────────────
GROUP_PALETTE = [
    ("05662B","E6F4EA"), ("008C3C","D4F5DC"), ("1A7A5C","D0EDE4"),
    ("2C6E8A","D6EAF2"), ("5B2C6F","E8D5F0"), ("96304A","F4D6DE"),
    ("C05702","FADED0"), ("7D5A2D","F0E6D6"), ("2C3E6B","D6DCE8"),
    ("556B2F","E4EBD5"), ("7D2150","F0D4E0"), ("4A5568","E2E5E9"),
    ("1B6B5A","D2EDE6"), ("8B4513","F2E4D4"), ("4B0082","E6D8F0"),
    ("8B0000","F4D4D4"), ("006400","D4F0D4"), ("4682B4","D8E8F4"),
]

_BRD = Border(left=Side("thin",color="B0B0B0"),right=Side("thin",color="B0B0B0"),
              top=Side("thin",color="B0B0B0"),bottom=Side("thin",color="B0B0B0"))
_HBRD = Border(left=Side("thin",color="333333"),right=Side("thin",color="333333"),
               top=Side("medium",color="333333"),bottom=Side("medium",color="333333"))
_HF = Font(name="Arial",bold=True,color="FFFFFF",size=10)
_HA = Alignment(horizontal="center",vertical="top",wrap_text=True)
_DF = Font(name="Arial",size=10,color="333333")
_DC = Alignment(horizontal="center",vertical="center")
_DL = Alignment(horizontal="left",vertical="center",wrap_text=True)
_CBL = Alignment(horizontal="left",vertical="top",wrap_text=True)
_CBC = Alignment(horizontal="center",vertical="top")

def _write_excel(columns, n_rows, path):
    wb = Workbook()
    # Color per group
    gc = {}; gi = 0
    for c in columns:
        gk = c.group_key
        if gk not in gc: gc[gk] = gi % len(GROUP_PALETTE); gi += 1
    def _f(col):
        h,z = GROUP_PALETTE[gc.get(col.group_key, 0)]
        return PatternFill("solid",fgColor=h), PatternFill("solid",fgColor=z)

    # Pre-compute column widths
    col_widths = [_auto_col_width(c) for c in columns]

    # Data
    ws = wb.active; ws.title = "Data"
    for ci,c in enumerate(columns,1):
        hf,_ = _f(c); cell = ws.cell(1,ci,c.header)
        cell.fill = hf; cell.font = _HF; cell.alignment = _HA; cell.border = _HBRD
    for ri in range(n_rows):
        max_lines = 1
        for ci,c in enumerate(columns,1):
            v = c.values[ri] if ri < len(c.values) else None
            cell = ws.cell(ri+2,ci,v); cell.font = _DF; cell.border = _BRD
            cell.alignment = _DL if c.col_type == "open_text" else _DC
            if ri % 2 == 1: _,zf = _f(c); cell.fill = zf
            if c.col_type == "open_text" and v is not None:
                chars_per_line = max(10, int(col_widths[ci-1] / 1.1))
                text = str(v)
                lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line) + text.count("\n")
                max_lines = max(max_lines, lines)
        if max_lines > 1:
            ws.row_dimensions[ri+2].height = min(120, max_lines * 15)
    for ci,w in enumerate(col_widths,1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[1].height = 30
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}1"

    # Codebook
    wc = wb.create_sheet("Codebook")
    cb_h = ["question_code","question","alternatives","question_type","variable_type","suggested_analysis"]
    hf0 = PatternFill("solid",fgColor="05662B")
    for ci,h in enumerate(cb_h,1):
        cell = wc.cell(1,ci,h); cell.fill = hf0; cell.font = _HF; cell.alignment = _HA; cell.border = _HBRD
    zfcb = PatternFill("solid",fgColor="E6F4EA")
    for ri,c in enumerate(columns,2):
        ct = c.col_type
        alt = c.alternatives or ""
        hf,_ = _f(c)
        vals = [c.header, c.question_text, alt, TYPE_PT.get(ct,ct), VAR_TYPE.get(ct,""), ANALYSIS.get(ct,"")]
        aligns = [_CBL,_CBL,_CBL,_CBC,_CBC,_CBL]
        for ci,(v,al) in enumerate(zip(vals,aligns),1):
            cell = wc.cell(ri,ci,v); cell.font = _DF; cell.alignment = al; cell.border = _BRD
            if ci == 1: cell.fill = hf; cell.font = Font(name="Arial",size=10,color="FFFFFF",bold=True)
            elif (ri-1) % 2 == 0: cell.fill = zfcb
    for ci,w in enumerate([35,55,50,20,22,35],1):
        wc.column_dimensions[get_column_letter(ci)].width = w
    wc.row_dimensions[1].height = 30
    wb.save(path)
