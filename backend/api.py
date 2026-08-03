"""
backend/api.py — FastAPI adapter for the Refinador.

REGRA ZERO: este arquivo é um ADAPTADOR FINO. Ele recebe requisições HTTP,
chama as funções de negócio dos módulos Python existentes (normalizer.py,
ai_analysis.py, llm_provider.py) e devolve os resultados. Nenhuma lógica
de negócio é implementada aqui.

Sessão:
  - Cada aba/usuário recebe um UUID session_id no primeiro request.
  - O estado (arquivos temporários + config DataFrame) é isolado por sessão.
  - Sessões expiram após SESSION_EXPIRY_SECONDS de inatividade.
  - Um thread de limpeza remove sessões expiradas periodicamente.
  - Múltiplas sessões simultâneas não se interferem.
"""
import sys
import time
import uuid
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ── Adiciona a raiz do projeto ao path para importar os módulos de negócio ─────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd
from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Módulos de negócio (Regra Zero: só importar, nunca modificar) ──────────────
from normalizer import (
    VALID_TYPES,
    build_config,
    check_sentiment_eligibility,
    normalize,
)
from llm_provider import (
    LLMConfig,
    LLMProviderError,
    MockProvider,
    build_provider,
    load_config_from_env,
    persist_to_env,
)
from .instrumentation import instrument_provider

# ══════════════════════════════════════════════════════════════════════════════
# Gerenciamento de sessão
# ══════════════════════════════════════════════════════════════════════════════

SESSION_EXPIRY_SECONDS = 4 * 60 * 60    # 4 horas de inatividade
CLEANUP_INTERVAL_SECONDS = 15 * 60      # varredura a cada 15 minutos
COOKIE_NAME = "normalizer_session"

# Campos internos de encoding — nunca expostos ao frontend
_INTERNAL_KEYS = {"_encoding_strategy", "_value_map", "_grouped_with"}

# Campos editáveis pelo usuário na etapa de classificação
_EDITABLE_FIELDS = {"include", "group", "type", "short_name", "subitem", "revisar"}


@dataclass
class SessionState:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    # Diretório temporário desta sessão (isolado em disco)
    session_dir: Optional[str] = None

    # Caminhos de arquivos temporários
    qsf_path: Optional[str] = None
    xlsx_path: Optional[str] = None
    output_path: Optional[str] = None
    base_name: str = ""

    # Estado de processamento
    config: Optional[List[Dict]] = None         # list[dict] — config rows
    df_data: Optional[pd.DataFrame] = None      # DataFrame de respondentes (em memória)
    classification_confirmed: bool = False
    result: Optional[Dict] = None               # {rows, columns, headers}
    analyzed_ids: List[str] = field(default_factory=list)

    # Config de LLM (pode diferir da .env nesta sessão)
    llm_config: Optional[LLMConfig] = None


# Dicionário global de sessões (isolado por session_id)
_sessions: Dict[str, SessionState] = {}
_sessions_lock = threading.Lock()


def _cleanup_expired() -> None:
    """Remove sessões inativas há mais de SESSION_EXPIRY_SECONDS."""
    now = time.time()
    with _sessions_lock:
        expired = [
            sid for sid, s in _sessions.items()
            if now - s.last_active > SESSION_EXPIRY_SECONDS
        ]
        for sid in expired:
            sess = _sessions.pop(sid)
            if sess.session_dir and Path(sess.session_dir).exists():
                shutil.rmtree(sess.session_dir, ignore_errors=True)


def _cleanup_loop() -> None:
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        _cleanup_expired()


# Thread daemon: morre com o processo principal
threading.Thread(target=_cleanup_loop, daemon=True).start()


def _get_or_create_session(
    response: Response,
    session_id: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
) -> "SessionState":
    """
    Dependency FastAPI: resolve sessão existente ou cria nova.
    Cookie HttpOnly garante isolamento entre abas/usuários.
    """
    with _sessions_lock:
        if session_id and session_id in _sessions:
            sess = _sessions[session_id]
            sess.last_active = time.time()
            return sess

        # Nova sessão
        new_id = str(uuid.uuid4())
        sess_dir = tempfile.mkdtemp(prefix=f"normalizer_{new_id[:8]}_")
        sess = SessionState(
            session_id=new_id,
            session_dir=sess_dir,
            llm_config=load_config_from_env(),
        )
        _sessions[new_id] = sess

    response.set_cookie(
        key=COOKIE_NAME,
        value=new_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_EXPIRY_SECONDS,
    )
    return sess


SessionDep = Depends(_get_or_create_session)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _public_config(config: List[Dict]) -> List[Dict]:
    """Remove campos internos de encoding antes de enviar ao frontend."""
    return [{k: v for k, v in row.items() if k not in _INTERNAL_KEYS} for row in config]


def _config_stats(config: List[Dict]) -> Dict:
    return {
        "total":      len(config),
        "included":   sum(1 for r in config if r.get("include", True)),
        "open_text":  sum(1 for r in config if r.get("type") == "open_text"),
        "to_review":  sum(1 for r in config if r.get("confidence") == "low"),
    }


def _current_step(sess: SessionState) -> int:
    """Retorna a etapa atual do wizard (1–4) baseado no estado da sessão."""
    if sess.result is not None:
        return 4
    if sess.config is not None and sess.classification_confirmed:
        return 3
    if sess.config is not None:
        return 2
    return 1


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic models
# ══════════════════════════════════════════════════════════════════════════════

class ConfigRowUpdate(BaseModel):
    original_id: str
    include:    Optional[bool] = None
    type:       Optional[str]  = None
    short_name: Optional[str]  = None
    subitem:    Optional[str]  = None
    group:      Optional[str]  = None
    revisar:    Optional[str]  = None


class ConfigPatch(BaseModel):
    rows: List[ConfigRowUpdate]


class NormalizeRequest(BaseModel):
    ai_original_ids: Optional[List[str]] = None


class LLMConfigRequest(BaseModel):
    provider:          str
    api_key:           str
    azure_endpoint:    str = ""
    azure_deployment:  str = ""
    azure_api_version: str = "2024-08-01-preview"
    save:              bool = False


# ══════════════════════════════════════════════════════════════════════════════
# App FastAPI
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Refinador API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Assets estáticos de marca — servidos em /brand/logos/..., /brand/icones/...
_BRAND_DIR = _ROOT / "localiza-brand-assets"
if _BRAND_DIR.exists():
    app.mount("/brand", StaticFiles(directory=str(_BRAND_DIR)), name="brand")

# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

# ── Sessão ────────────────────────────────────────────────────────────────────

@app.get("/api/session/status")
def session_status(sess: SessionState = SessionDep):
    """Retorna etapa atual e flags da sessão. Frontend usa para inicializar estado."""
    cfg = sess.llm_config
    return {
        "step":                      _current_step(sess),
        "has_config":                sess.config is not None,
        "classification_confirmed":  sess.classification_confirmed,
        "has_result":                sess.result is not None,
        "ai_provider":               cfg.provider if (cfg and cfg.api_key) else None,
        "base_name":                 sess.base_name,
    }


@app.delete("/api/session")
def reset_session(sess: SessionState = SessionDep):
    """Reinicia a sessão (mesmo efeito que enviar novos arquivos)."""
    if sess.session_dir:
        sess_dir = Path(sess.session_dir)
        for f in sess_dir.iterdir():
            try:
                f.unlink()
            except Exception:
                pass
    sess.qsf_path = None
    sess.xlsx_path = None
    sess.output_path = None
    sess.base_name = ""
    sess.config = None
    sess.df_data = None
    sess.classification_confirmed = False
    sess.result = None
    sess.analyzed_ids = []
    return {"ok": True}


# ── Etapa 1 — Upload e processamento ─────────────────────────────────────────

@app.post("/api/process")
async def process_files(
    response: Response,
    qsf_file:  UploadFile = File(..., description="Arquivo .qsf exportado do Qualtrics"),
    xlsx_file: UploadFile = File(..., description="Arquivo .xlsx com valores numéricos"),
    sess: SessionState = SessionDep,
):
    """
    Recebe QSF + XLSX, chama build_config() e armazena resultado na sessão.
    Espelha o fluxo de upload do app.py (linhas 524–568).
    Regra Zero: build_config() chamada como está, sem modificação.
    """
    sess_dir = Path(sess.session_dir)

    # Salva arquivos no diretório isolado desta sessão
    qsf_bytes  = await qsf_file.read()
    xlsx_bytes = await xlsx_file.read()

    qsf_path  = str(sess_dir / (qsf_file.filename  or "survey.qsf"))
    xlsx_path = str(sess_dir / (xlsx_file.filename or "data.xlsx"))
    Path(qsf_path).write_bytes(qsf_bytes)
    Path(xlsx_path).write_bytes(xlsx_bytes)

    # Reseta estado derivado (equivalente a _reset_workflow do app.py)
    sess.qsf_path  = qsf_path
    sess.xlsx_path = xlsx_path
    sess.base_name = Path(xlsx_file.filename or "data").stem
    sess.config = None
    sess.df_data = None
    sess.result = None
    sess.output_path = None
    sess.classification_confirmed = False
    sess.analyzed_ids = []

    # Provider: mock se nenhuma chave configurada (equivalente ao app.py linha 551–552)
    provider      = build_provider(sess.llm_config)
    real_provider = None if isinstance(provider, MockProvider) else provider
    ai_used       = real_provider is not None

    try:
        # ── Regra Zero: chama build_config exatamente como no app.py ─────────
        # Assinatura: build_config(xlsx_path, qsf_path, provider) — ordem importa
        config, df = build_config(xlsx_path, qsf_path, real_provider)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Erro ao processar arquivos: {exc}")

    # Adiciona campo "revisar" (equivalente ao app.py linhas 560–562)
    for row in config:
        row["revisar"] = "Revisar" if row.get("confidence") == "low" else "OK"

    sess.config  = config
    sess.df_data = df

    return {
        "config":  _public_config(config),
        "stats":   _config_stats(config),
        "ai_used": ai_used,
    }


# ── Etapa 2 — Classificação ───────────────────────────────────────────────────

@app.get("/api/config")
def get_config(sess: SessionState = SessionDep):
    """Retorna config atual + estatísticas da sessão."""
    if sess.config is None:
        raise HTTPException(status_code=404, detail="Nenhum arquivo processado nesta sessão.")
    return {
        "config":                   _public_config(sess.config),
        "stats":                    _config_stats(sess.config),
        "classification_confirmed": sess.classification_confirmed,
        "valid_types":              VALID_TYPES,
    }


@app.patch("/api/config")
def patch_config(body: ConfigPatch, sess: SessionState = SessionDep):
    """
    Aplica edições parciais nas linhas do config.
    Espelha o sync do data_editor no app.py (linhas 618–623).
    Apenas campos em _EDITABLE_FIELDS são aceitos.
    """
    if sess.config is None:
        raise HTTPException(status_code=404, detail="Nenhum arquivo processado nesta sessão.")

    idx = {row["original_id"]: row for row in sess.config}

    for update in body.rows:
        row = idx.get(update.original_id)
        if row is None:
            continue
        # exclude_unset=True: distingue "não enviado" de "enviado como false/null"
        data = update.model_dump(exclude_unset=True)
        data.pop("original_id", None)
        for key, val in data.items():
            if key in _EDITABLE_FIELDS and val is not None:
                row[key] = val

    return {"ok": True, "stats": _config_stats(sess.config)}


@app.post("/api/config/confirm")
def confirm_config(sess: SessionState = SessionDep):
    """
    Marca classificação como confirmada, liberando a etapa 3.
    Equivale a classification_confirmed = True no app.py (linha 641).
    """
    if sess.config is None:
        raise HTTPException(status_code=404, detail="Nenhum arquivo processado nesta sessão.")
    sess.classification_confirmed = True
    return {"ok": True}


# ── Etapa 3 — Elegibilidade de respostas abertas ──────────────────────────────

@app.get("/api/eligibility")
def get_eligibility(sess: SessionState = SessionDep):
    """
    Calcula elegibilidade de sentimento para colunas open_text incluídas.
    Espelha o loop do app.py (linhas 666–670).
    Regra Zero: check_sentiment_eligibility() chamada como está.
    """
    if sess.config is None or sess.df_data is None:
        raise HTTPException(status_code=404, detail="Nenhum arquivo processado nesta sessão.")

    results = []
    for row in sess.config:
        if not row.get("include", True):
            continue
        if row.get("type") != "open_text":
            continue
        oid    = row["original_id"]
        series = sess.df_data[oid] if oid in sess.df_data.columns else None

        # ── Regra Zero: chama check_sentiment_eligibility como está ──────────
        elig = check_sentiment_eligibility(row["question_text"], series)
        results.append({
            "original_id":    oid,
            "question_text":  row["question_text"],
            "eligible":       elig.eligible,
            "score":          elig.score,
            "reasons_for":    elig.reasons_for,
            "reasons_against": elig.reasons_against,
            "summary":        elig.summary(),
        })

    return {"columns": results}


# ── Etapa 4 — Normalizar e exportar ──────────────────────────────────────────

@app.post("/api/normalize")
def run_normalize(body: NormalizeRequest, sess: SessionState = SessionDep):
    """
    Chama normalize() e armazena o resultado na sessão.
    Espelha o fluxo do app.py (linhas 727–755).
    Regra Zero: normalize() chamada exatamente como no app.py.
    """
    if sess.config is None or sess.df_data is None or sess.xlsx_path is None:
        raise HTTPException(
            status_code=400,
            detail="Upload e classificação são necessários antes de exportar.",
        )

    sess_dir    = Path(sess.session_dir)
    output_path = str(sess_dir / f"{sess.base_name}_normalized.xlsx")

    provider = build_provider(sess.llm_config)
    is_real  = not isinstance(provider, MockProvider)

    # Equivalente ao app.py linhas 729–731: sem IA se provider for mock
    ai_ids = list(body.ai_original_ids) if body.ai_original_ids and is_real else []

    # Instrumentação de consumo de IA — decora o provider no ponto de injeção,
    # sem tocar em normalizer.py / ai_analysis.py / llm_provider.py.
    provider = instrument_provider(provider, sess.session_id)

    try:
        # ── Regra Zero: chama normalize() exatamente como no app.py ──────────
        result = normalize(
            sess.xlsx_path,
            output_path,
            list(sess.config),       # cópia superficial; não muta o config da sessão
            sess.df_data,
            ai_original_ids=ai_ids or None,
            provider=provider if ai_ids else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro na normalização: {exc}")

    sess.output_path  = output_path
    sess.result       = result
    sess.analyzed_ids = ai_ids

    return result  # {status, rows, columns, headers}


@app.get("/api/download")
def download_file(sess: SessionState = SessionDep):
    """Serve o .xlsx gerado por normalize(). Equivale ao download_button do app.py."""
    if not sess.output_path or not Path(sess.output_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Planilha ainda não gerada. Execute Normalizar e exportar primeiro.",
        )
    filename = f"{sess.base_name}_normalized.xlsx"
    return FileResponse(
        path=sess.output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


# ── Configuração de IA ────────────────────────────────────────────────────────

@app.get("/api/llm-config")
def get_llm_config(sess: SessionState = SessionDep):
    """Retorna config de LLM da sessão (sem expor o valor da chave)."""
    cfg = sess.llm_config or load_config_from_env()
    return {
        "provider":          cfg.provider,
        "has_key":           bool(cfg.api_key),
        "azure_endpoint":    cfg.azure_endpoint,
        "azure_deployment":  cfg.azure_deployment,
        "azure_api_version": cfg.azure_api_version,
    }


@app.post("/api/llm-config")
def set_llm_config(body: LLMConfigRequest, sess: SessionState = SessionDep):
    """
    Atualiza config de LLM para esta sessão e opcionalmente persiste no .env.
    Espelha o dialog de Configurar IA do app.py (linhas 328–364).
    Regra Zero: persist_to_env() chamada como está.
    """
    cfg = LLMConfig(
        provider          = body.provider,
        api_key           = body.api_key,
        azure_endpoint    = body.azure_endpoint,
        azure_deployment  = body.azure_deployment,
        azure_api_version = body.azure_api_version,
    )
    sess.llm_config = cfg

    if body.save:
        _PROV_KEY = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "azure":     "AZURE_OPENAI_API_KEY",
        }
        updates = {"LLM_PROVIDER": body.provider}
        if key_name := _PROV_KEY.get(body.provider):
            updates[key_name] = body.api_key
        if body.provider == "azure":
            updates.update({
                "AZURE_OPENAI_ENDPOINT":    body.azure_endpoint,
                "AZURE_OPENAI_DEPLOYMENT":  body.azure_deployment,
                "AZURE_OPENAI_API_VERSION": body.azure_api_version,
            })
        persist_to_env(updates)   # Regra Zero: chamada como está

    return {"ok": True}


@app.post("/api/llm-config/test")
def test_llm_connection(body: LLMConfigRequest):
    """
    Testa conectividade sem salvar.
    Espelha o botão 'Testar conexão' do app.py (linhas 347–351).
    """
    cfg = LLMConfig(
        provider          = body.provider,
        api_key           = body.api_key,
        azure_endpoint    = body.azure_endpoint,
        azure_deployment  = body.azure_deployment,
        azure_api_version = body.azure_api_version,
    )
    try:
        build_provider(cfg).complete("Responda ok.", "ok?", 5)
        return {"ok": True, "message": "Conexão OK"}
    except LLMProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro: {exc}")
