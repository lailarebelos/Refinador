"""Qualtrics Normalizer v2 — QSF-driven approach.

Uses QSF (survey definition) for question metadata + numeric XLSX export.
No heuristics needed — QSF tells us everything.
"""
import json, re, unicodedata
from dataclasses import dataclass, field
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

SHORT_NAME_STOPWORDS = {"a","o","e","de","do","da","dos","das","em","no","na","nos","nas","um","uma","que",
    "para","com","por","se","ou","seu","sua","voce","qual","quais","como","mais","ate",
    "ao","os","as","pelo","pela","foi","sao","esta","este","ter","ser","ir",
    "marque","selecione","opcoes","opcao","alternativas","alternativa",
    "abaixo","elementos","todas","cada","ainda","dentro","cenario","selected","choice","text",
    "ultimos","meses","vezes","vez","anos","grupo","group","quando","onde","porque","qualquer",
    "todas","todos","normalmente","acontece","aplicam","aplica","resposta","respostas",
    "precisa","precisam","alugar","locacao","fazer","faz","feito","feita"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(s):
    if not isinstance(s, str): s = str(s) if s is not None else ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").strip().lower()

def _deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def _extract_meaningful_words(text: str, limit: int = 3) -> list[str]:
    cleaned = _norm(text)
    cleaned = re.sub(r"\[.*?\]", " ", cleaned)
    cleaned = re.sub(r"\(.*?\)", " ", cleaned)
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
    if len(parts) < 3:
        for word in ["Perfil", "Respondente", "Pesquisa"]:
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

def parse_qsf(path: str) -> dict[str, QsfQuestion]:
    """Parse QSF file. Returns dict keyed by DataExportTag."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = {}
    for el in data.get("SurveyElements", []):
        if el.get("Element") != "SQ":
            continue
        p = el.get("Payload", {})
        tag = p.get("DataExportTag", "")
        if not tag:
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
            question_text=p.get("QuestionText", ""),
            question_type=p.get("QuestionType", ""),
            selector=p.get("Selector", ""),
            choices=choices,
            has_text_entry=has_text,
            choice_order=p.get("ChoiceOrder", list(choices.keys())),
        )
    return questions

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

def build_config(xlsx_path: str, qsf_path: str, provider=None) -> tuple[list[dict], pd.DataFrame]:
    """Build configuration table from QSF + XLSX. Returns (config_rows, dataframe)."""
    qsf_questions = parse_qsf(qsf_path)
    df, data_cols = read_xlsx(xlsx_path)
    df, data_cols = _drop_technical(df, data_cols)

    # Batch AI naming if provider available
    ai_names = {}
    if provider:
        # Collect unique question texts
        unique_texts = {}
        for dc in data_cols:
            base = _extract_base_tag(dc.qualtrics_id)
            if base in qsf_questions and base not in unique_texts:
                unique_texts[base] = qsf_questions[base].question_text
        # Single batch call for all names
        if unique_texts:
            try:
                sys_p = ("Para cada pergunta abaixo, gere um resumo em exatamente 3 palavras completas em portugues, sem acentos, "
                         "sem artigos e separadas por underscore. Responda APENAS JSON: {\"names\":{\"Q1\":\"Genero_Do_Cliente\",\"Q2\":\"Faixa_Etaria_Publico\",...}}")
                user_p = json.dumps(unique_texts, ensure_ascii=False)
                raw = provider.complete(sys_p, user_p, max_tokens=2048)
                raw = re.sub(r"^```(?:json)?\s*","",raw.strip())
                raw = re.sub(r"\s*```$","",raw.strip())
                ai_names = json.loads(raw).get("names", {})
            except:
                pass

    config = []
    for dc in data_cols:
        qid = dc.qualtrics_id
        base = _extract_base_tag(qid)
        qsf_q = qsf_questions.get(base)

        # Determine type
        if qid.endswith("_TEXT"):
            col_type = "open_text"
        elif "_NPS_GROUP" in qid:
            col_type = "single_choice"
        elif qsf_q:
            col_type = _qsf_to_type(qsf_q)
        else:
            col_type = "single_choice"

        # For MC subitems (Q6_1, Q6_2...), type is already multiple_choice binary in data
        if qsf_q and qsf_q.selector == "MAVR" and re.match(r"Q\d+_\d+$", qid) and not qid.endswith("_TEXT"):
            col_type = "multiple_choice"

        # Generate short name
        short = _sanitize_short_name(ai_names.get(base, ""), fallback=qsf_q.question_text if qsf_q else dc.question_text)
        if not short and qsf_q:
            short = _make_short_name_heuristic(qsf_q.question_text)
        if not short:
            short = _make_short_name_heuristic(dc.question_text)
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

        # Build alternatives string
        alternatives = ""
        if col_type == "open_text":
            alternatives = "Texto livre"
        elif col_type == "nps":
            alternatives = "0-10"
        elif col_type == "multiple_choice":
            alternatives = "0=Não; 1=Sim"
        elif col_type == "ranking" and qsf_q:
            n = len(qsf_q.choices)
            alternatives = f"1=Mais importante; {n}=Menos importante"
        elif qsf_q and qsf_q.choices:
            alternatives = "; ".join(f"{k}={v}" for k,v in sorted(qsf_q.choices.items()))
        elif "_NPS_GROUP" in qid:
            alternatives = "1=Detractor; 2=Passive; 3=Promoter"

        # Group = base question tag
        group = base

        # Confidence
        confidence = "high" if qsf_q else "low"

        config.append({
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
        })

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
            "single_choice", analysis.sentiment_values[:n_rows], {"Negativo":1,"Neutro":2,"Positivo":3}, gk, "1=Negativo; 2=Neutro; 3=Positivo"))
        result.append(OutputColumn(f"{col.header}_categorias", f"{col.question_text} - Categorias ({categories_label})",
            "open_text", analysis.category_values[:n_rows], {}, gk, f"Categorias: {categories_label}"))
    return result

# ── Normalize ─────────────────────────────────────────────────────────────────
def normalize(xlsx_path, output_path, config, df, ai_columns=None, provider=None):
    """Normalize using user-edited config. Data is already numeric from Qualtrics."""
    active = [c for c in config if c.get("include", True)]

    all_out = []
    for cfg in active:
        qid = cfg["original_id"]
        if qid not in df.columns: continue

        series = df[qid]
        col_type = cfg.get("type", "single_choice")
        short = cfg.get("short_name", qid)
        subitem = cfg.get("subitem", "")
        qtxt = cfg.get("question_text", "")
        group = cfg.get("group", qid)
        alt = cfg.get("alternatives", "")

        # Build header: keep Qualtrics numbering + short name
        header = build_output_header(qid, short, subitem)

        # Convert values
        if col_type == "open_text":
            values = [str(v).strip() if not pd.isna(v) and str(v).strip() and str(v).strip().lower()!="nan" else None for v in series]
        else:
            values = []
            for v in series:
                s = str(v).strip() if not pd.isna(v) else ""
                if s and s.lower() != "nan":
                    try: values.append(int(float(s)))
                    except:
                        try: values.append(float(s))
                        except: values.append(s)
                else:
                    values.append(None)

        all_out.append(OutputColumn(header, qtxt, col_type, values, {}, group, alt))

    n_rows = len(df) if not all_out else len(all_out[0].values)
    if ai_columns and provider:
        all_out = _run_ai_analysis(all_out, ai_columns, provider, n_rows)

    _write_excel(all_out, n_rows, output_path)
    return {"status":"ok", "rows":n_rows, "columns":len(all_out), "headers":[c.header for c in all_out]}

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

    # Data
    ws = wb.active; ws.title = "Data"
    for ci,c in enumerate(columns,1):
        hf,_ = _f(c); cell = ws.cell(1,ci,c.header)
        cell.fill = hf; cell.font = _HF; cell.alignment = _HA; cell.border = _HBRD
    for ri in range(n_rows):
        for ci,c in enumerate(columns,1):
            v = c.values[ri] if ri < len(c.values) else None
            cell = ws.cell(ri+2,ci,v); cell.font = _DF; cell.border = _BRD
            cell.alignment = _DL if c.col_type == "open_text" else _DC
            if ri % 2 == 1: _,zf = _f(c); cell.fill = zf
    for ci,c in enumerate(columns,1):
        ws.column_dimensions[get_column_letter(ci)].width = 20 if c.col_type == "open_text" else 14
    ws.row_dimensions[1].height = 30
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}1"

    # Codebook
    wc = wb.create_sheet("Codebook")
    cb_h = ["Codebook","Question","Alternatives","Question_type","Variable_type","Suggested_analysis"]
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
