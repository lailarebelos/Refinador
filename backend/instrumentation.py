"""
backend/instrumentation.py — Medição de consumo de IA (tokens, custo, cache).

REGRA ZERO: este módulo NÃO modifica normalizer.py, ai_analysis.py nem
llm_provider.py. Ele decora a instância de LLMProvider já construída por
llm_provider.build_provider(), interceptando a chamada real ao SDK
(Anthropic/OpenAI) no ponto exato em que ela ocorre dentro de
LLMProvider.complete(), para:

  1. Registrar o uso real de tokens (input/output) e a duração de cada
     chamada em metrics/usage.jsonl (uma linha JSONL por chamada).
  2. Servir como cache de chamadas idênticas (mesmo modelo + mesmo
     prompt): se o mesmo lote de comentários já deduplicado por
     ai_analysis.py se repetir (ex.: nova normalização com os mesmos
     dados), a chamada real ao provedor é evitada e o registro sai com
     cache_hit=true e tokens=0.

Ponto de injeção: backend/api.py, imediatamente após build_provider(...),
antes de repassar o provider para normalize().
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from llm_provider import (
    AnthropicProvider,
    AzureOpenAIProvider,
    LLMProvider,
    MockProvider,
    OpenAIProvider,
)

_METRICS_DIR  = Path(__file__).resolve().parent.parent / "metrics"
_METRICS_PATH = _METRICS_DIR / "usage.jsonl"

_write_lock = Lock()
_cache_lock = Lock()

# etapa (Passo A / Passo B de ai_analysis.py) é reconhecida pelo texto fixo
# dos prompts de sistema definidos em _discover_categories / _classify_batch.
_DISCOVERY_MARKER = "proponha categorias"
_CLASSIFY_MARKER  = "CATEGORIAS DISPONÍVEIS"

# Cache de chamadas idênticas (mesmo modelo + mesmo prompt), em memória do
# processo. Chave: hash(modelo, system, user). Valor: texto já devolvido
# pelo provedor na primeira chamada real.
_call_cache: dict[str, str] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guess_etapa(system: str) -> str:
    if _CLASSIFY_MARKER in system:
        return "sentimento"
    if _DISCOVERY_MARKER in system.lower():
        return "categorizacao"
    return "desconhecida"


def _cache_key(model: str, system: str, user: str) -> str:
    h = hashlib.sha256()
    for part in (model, system, user):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _append_jsonl(record: dict) -> None:
    _METRICS_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _write_lock:
        with _METRICS_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _record(session_id: str, etapa: str, provider_name: str, model: str,
            input_tokens: int, output_tokens: int, duracao_ms: float, cache_hit: bool) -> None:
    _append_jsonl({
        "timestamp":     _now_iso(),
        "sessao":        session_id,
        "etapa":         etapa,
        "provider":      provider_name,
        "model":         model,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "total_tokens":  input_tokens + output_tokens,
        "duracao_ms":    duracao_ms,
        "cache_hit":     cache_hit,
    })


# ─── Respostas "de cache" — imitam a interface mínima usada por complete() ────

class _CachedAnthropicBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _CachedAnthropicMessage:
    def __init__(self, text: str) -> None:
        self.content = [_CachedAnthropicBlock(text)]


class _CachedOpenAIMessage:
    def __init__(self, text: str) -> None:
        self.content = text


class _CachedOpenAIChoice:
    def __init__(self, text: str) -> None:
        self.message = _CachedOpenAIMessage(text)


class _CachedOpenAICompletion:
    def __init__(self, text: str) -> None:
        self.choices = [_CachedOpenAIChoice(text)]


# ─── Wrappers por tipo de provider ────────────────────────────────────────────

def _wrap_anthropic_client(provider: AnthropicProvider, session_id: str) -> None:
    client = provider._client
    original_create = client.messages.create

    def patched_create(*args, **kwargs):
        model  = kwargs.get("model") or provider._model
        system = kwargs.get("system") or ""
        user   = ""
        for m in kwargs.get("messages", []):
            if m.get("role") == "user":
                user = m.get("content", "")
                break

        etapa = _guess_etapa(system)
        key   = _cache_key(model, system, user)

        with _cache_lock:
            cached_text = _call_cache.get(key)
        if cached_text is not None:
            _record(session_id, etapa, provider.name(), model, 0, 0, 0.0, True)
            return _CachedAnthropicMessage(cached_text)

        start    = time.perf_counter()
        response = original_create(*args, **kwargs)
        duracao_ms = round((time.perf_counter() - start) * 1000, 1)

        usage         = getattr(response, "usage", None)
        input_tokens  = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0

        with _cache_lock:
            _call_cache[key] = response.content[0].text

        _record(session_id, etapa, provider.name(), model, input_tokens, output_tokens, duracao_ms, False)
        return response

    client.messages.create = patched_create


def _wrap_openai_client(provider, session_id: str, model_attr: str) -> None:
    client = provider._client
    original_create = client.chat.completions.create

    def patched_create(*args, **kwargs):
        model  = kwargs.get("model") or getattr(provider, model_attr, "")
        system = ""
        user   = ""
        for m in kwargs.get("messages", []):
            if m.get("role") == "system":
                system = m.get("content", "")
            elif m.get("role") == "user":
                user = m.get("content", "")

        etapa = _guess_etapa(system)
        key   = _cache_key(model, system, user)

        with _cache_lock:
            cached_text = _call_cache.get(key)
        if cached_text is not None:
            _record(session_id, etapa, provider.name(), model, 0, 0, 0.0, True)
            return _CachedOpenAICompletion(cached_text)

        start    = time.perf_counter()
        response = original_create(*args, **kwargs)
        duracao_ms = round((time.perf_counter() - start) * 1000, 1)

        usage         = getattr(response, "usage", None)
        input_tokens  = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        with _cache_lock:
            _call_cache[key] = response.choices[0].message.content

        _record(session_id, etapa, provider.name(), model, input_tokens, output_tokens, duracao_ms, False)
        return response

    client.chat.completions.create = patched_create


def _wrap_mock(provider: MockProvider, session_id: str) -> None:
    original_complete = provider.complete

    def patched_complete(system, user, max_tokens=4096):
        etapa      = _guess_etapa(system)
        start      = time.perf_counter()
        text       = original_complete(system, user, max_tokens)
        duracao_ms = round((time.perf_counter() - start) * 1000, 1)
        _record(session_id, etapa, provider.name(), "mock", 0, 0, duracao_ms, False)
        return text

    provider.complete = patched_complete


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def instrument_provider(provider: Optional[LLMProvider], session_id: str) -> Optional[LLMProvider]:
    """
    Decora `provider` in-place para registrar uso de IA em metrics/usage.jsonl.
    Retorna o mesmo objeto recebido (ou None, se nenhum provider foi passado).

    Deve ser chamado no ponto onde o provider é criado/injetado em
    backend/api.py — nunca dentro de normalizer.py / ai_analysis.py.
    """
    if provider is None:
        return None
    if isinstance(provider, AnthropicProvider):
        _wrap_anthropic_client(provider, session_id)
    elif isinstance(provider, (OpenAIProvider, AzureOpenAIProvider)):
        model_attr = "_model" if isinstance(provider, OpenAIProvider) else "_deployment"
        _wrap_openai_client(provider, session_id, model_attr)
    elif isinstance(provider, MockProvider):
        _wrap_mock(provider, session_id)
    return provider
