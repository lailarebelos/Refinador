"""
ai_analysis.py — Análise de sentimento e categorização de colunas qualitativas.

Fluxo por coluna:
  Passo A (discovery): amostra aleatoria de comentarios validos → IA propoe 30 categorias tematicas.
  Passo B (classificação): 100% dos comentários únicos → IA classifica sentimento + categorias.
  Cache: hash normalizado deduplica chamadas repetidas para comentários idênticos.
"""

import hashlib
import json
import random
import re
import unicodedata
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_SENTIMENT_MAP: dict[str, int] = {"negativo": 1, "neutro": 2, "positivo": 3}
_DISCOVERY_CATEGORY_COUNT: int = 30
_FALLBACK_CATEGORIES: list[str] = [
    "atendimento",
    "tempo_espera",
    "preco",
    "qualidade",
    "limpeza",
    "estrutura",
    "facilidade_uso",
    "comunicacao",
    "clareza_informacao",
    "cordialidade",
    "agilidade",
    "resolucao_problema",
    "prazo",
    "confianca",
    "localizacao",
    "acessibilidade",
    "disponibilidade",
    "variedade",
    "conforto",
    "experiencia_geral",
    "expectativa",
    "seguranca",
    "organizacao",
    "navegacao",
    "desempenho",
    "estabilidade",
    "personalizacao",
    "suporte",
    "sugestao_melhoria",
    "outros",
]
_BATCH_SIZE: int   = 800   # máx comentários únicos por chamada de classificação
_SAMPLE_SIZE: int  = 300   # amostra aleatoria de comentarios validos para discovery


# ---------------------------------------------------------------------------
# Estrutura de resultado
# ---------------------------------------------------------------------------


@dataclass
class SentimentCategoryResult:
    """Resultado para uma coluna analisada."""
    column_id: str
    categories_discovered: list[str]                = field(default_factory=list)
    sentiment_values:      list[int | None]         = field(default_factory=list)
    category_values:       list[str | None]         = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _normalize_for_hash(text: str) -> str:
    """Lowercase, sem acentos, espaços colapsados — para deduplicação."""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _dedup_comments(
    comments: list[str],
) -> tuple[list[str], dict[int, int]]:
    """
    Remove duplicatas mantendo a ordem de primeira aparição.

    Retorna:
      unique_list — comentários únicos na ordem em que apareceram
      index_map   — {índice_original → índice_em_unique_list}
    """
    seen: dict[str, int] = {}
    unique_list: list[str] = []
    index_map: dict[int, int] = {}
    for i, c in enumerate(comments):
        key = _normalize_for_hash(c)
        if key not in seen:
            seen[key] = len(unique_list)
            unique_list.append(c)
        index_map[i] = seen[key]
    return unique_list, index_map


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences do output do LLM."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw).strip()
    return raw


# ---------------------------------------------------------------------------
# Passo A — Discovery de categorias
# ---------------------------------------------------------------------------


def _discover_categories(
    samples: list[str],
    provider,
) -> list[str]:
    """
    Propõe 30 categorias temáticas a partir de uma amostra aleatória de comentários válidos.
    Retorna lista de strings snake_case em português.
    Em caso de falha, retorna _FALLBACK_CATEGORIES.
    """
    system = (
        "Você é especialista em análise de conteúdo de pesquisas de satisfação.\n"
        "Analise os comentários e proponha categorias temáticas mutuamente exclusivas.\n\n"
        "REGRAS:\n"
        f"1. Gere exatamente {_DISCOVERY_CATEGORY_COUNT} categorias distintas com base na amostra aleatória fornecida.\n"
        "2. snake_case, 1-3 palavras, português, sem acentos nem cedilha.\n"
        "   Exemplos: atendimento, tempo_espera, preco_custo, qualidade_comida, limpeza.\n"
        "3. Responda APENAS com JSON válido: {\"categories\": [\"cat1\", \"cat2\", ...]}\n"
        "4. Sem texto extra, sem markdown, sem ```json."
    )
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(samples))
    user = f"Comentários:\n{numbered}"

    try:
        raw = provider.complete(system, user, max_tokens=256).strip()
        data = json.loads(_strip_fences(raw))
        cats = [str(c).strip() for c in data.get("categories", []) if str(c).strip()]
        if cats:
            seen: set[str] = set()
            normalized_cats: list[str] = []
            for cat in cats:
                if cat not in seen:
                    seen.add(cat)
                    normalized_cats.append(cat)

            if len(normalized_cats) < _DISCOVERY_CATEGORY_COUNT:
                for fallback_cat in _FALLBACK_CATEGORIES:
                    if fallback_cat not in seen:
                        seen.add(fallback_cat)
                        normalized_cats.append(fallback_cat)
                    if len(normalized_cats) >= _DISCOVERY_CATEGORY_COUNT:
                        break

            return normalized_cats[:_DISCOVERY_CATEGORY_COUNT]
    except Exception as exc:
        warnings.warn(f"[ai_analysis] Discovery falhou: {exc}. Usando categorias fallback.")

    return list(_FALLBACK_CATEGORIES)


# ---------------------------------------------------------------------------
# Passo B — Classificação em lote
# ---------------------------------------------------------------------------


def _classify_batch(
    comments: list[str],
    categories: list[str],
    provider,
) -> list[dict]:
    """
    Classifica sentimento + categorias para um lote de comentários únicos.

    Retorna lista de dicts {"sentiment": str, "categories": list[str]}.
    Em caso de falha, devolve lista de dicts com None.
    """
    null_results = [{"sentiment": None, "categories": []} for _ in comments]
    if not comments:
        return null_results

    system = (
        "Você é especialista em análise de sentimento e categorização de pesquisas.\n\n"
        f"CATEGORIAS DISPONÍVEIS: {', '.join(categories)}\n\n"
        "Para cada comentário numerado, devolva:\n"
        "  sentiment  — exatamente um de: negativo, neutro, positivo\n"
        "  categories — lista de 1-3 categorias da lista acima\n\n"
        "REGRAS:\n"
        "1. Use SOMENTE as categorias da lista. Sem novas categorias.\n"
        "2. Responda APENAS com JSON válido:\n"
        '   {"results": [{"sentiment": "...", "categories": ["..."]}, ...]}\n'
        "3. A lista results deve ter EXATAMENTE o mesmo número de itens que os comentários.\n"
        "4. Sem texto extra, sem markdown, sem ```json."
    )
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(comments))
    user = f"Classifique:\n{numbered}"

    try:
        raw = provider.complete(system, user, max_tokens=1024).strip()
        data = json.loads(_strip_fences(raw))
        results: list[dict] = data.get("results", [])

        # Garante comprimento correto (pad / trunca)
        if len(results) != len(comments):
            warnings.warn(
                f"[ai_analysis] LLM retornou {len(results)} resultados "
                f"para {len(comments)} comentários — ajustando."
            )
        while len(results) < len(comments):
            results.append({"sentiment": None, "categories": []})
        return results[: len(comments)]

    except Exception as exc:
        warnings.warn(f"[ai_analysis] Classificação falhou: {exc}. Marcando batch como None.")
        return null_results


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def analyze_columns(
    normalized_columns,
    selected_ids: list[str],
    provider,
    status_fn: Callable[[str], None] | None = None,
) -> list[SentimentCategoryResult]:
    """
    Executa discovery + classificação para cada coluna selecionada.

    normalized_columns — list[NormalizedColumn] com valores já codificados.
    selected_ids       — new_ids das colunas OPEN_TEXT a analisar.
    provider           — instância de LLMProvider.
    status_fn          — callback opcional para mensagens de progresso na UI.
    """
    nc_by_id   = {nc.new_id: nc for nc in normalized_columns}
    results: list[SentimentCategoryResult] = []
    _log_path = Path(__file__).parent / "diagnostico.log"

    for col_id in selected_ids:
        nc = nc_by_id.get(col_id)
        if nc is None:
            warnings.warn(f"[ai_analysis] Coluna {col_id!r} não encontrada — pulando.")
            continue

        raw_values = nc.values
        total = len(raw_values)

        # Separa índices e textos não-vazios
        non_empty_indices: list[int] = []
        non_empty_comments: list[str] = []
        for i, v in enumerate(raw_values):
            if v is not None and str(v).strip():
                non_empty_indices.append(i)
                non_empty_comments.append(str(v).strip())

        non_empty = len(non_empty_comments)
        if non_empty == 0:
            results.append(SentimentCategoryResult(
                column_id=col_id,
                sentiment_values=[None] * total,
                category_values=[None] * total,
            ))
            continue

        # ── Deduplicação ────────────────────────────────────────────────────
        unique_comments, index_map = _dedup_comments(non_empty_comments)
        n_unique   = len(unique_comments)
        dedup_pct  = (1.0 - n_unique / non_empty) * 100.0

        # ── Passo A — discovery ──────────────────────────────────────────────
        random.seed(42)
        sample_pool_size = len(unique_comments)
        sample_idx = sorted(random.sample(range(sample_pool_size), min(_SAMPLE_SIZE, sample_pool_size)))
        samples = [unique_comments[i] for i in sample_idx]

        if status_fn:
            status_fn(f"Analisando {col_id}: descobrindo categorias...")

        categories = _discover_categories(samples, provider)

        # ── Passo B — classificação de únicos em lotes ───────────────────────
        classified_unique: list[dict] = []
        for batch_start in range(0, n_unique, _BATCH_SIZE):
            batch     = unique_comments[batch_start: batch_start + _BATCH_SIZE]
            batch_end = batch_start + len(batch)

            if status_fn:
                status_fn(
                    f"Analisando {col_id}: classificando "
                    f"{batch_start + 1}–{batch_end} de {n_unique} comentários únicos..."
                )

            classified_unique.extend(_classify_batch(batch, categories, provider))

        # ── Reconstrói vetores na ordem original ─────────────────────────────
        sentiment_values: list[int | None]  = [None] * total
        category_values:  list[str | None]  = [None] * total

        for local_i, orig_i in enumerate(non_empty_indices):
            uid = index_map[local_i]
            if uid >= len(classified_unique):
                continue
            r = classified_unique[uid]

            # Sentimento
            sent_raw = (r.get("sentiment") or "").lower().strip()
            sentiment_values[orig_i] = _SENTIMENT_MAP.get(sent_raw)

            # Categorias — filtra só as descobertas no Passo A
            cats = [
                str(c).strip() for c in (r.get("categories") or [])
                if str(c).strip() in categories
            ][:3]
            category_values[orig_i] = ", ".join(cats) if cats else None

        # ── Estimativa de custo (Haiku apr. $0.80/Mtok in, $4.00/Mtok out) ──
        tokens_in  = sum(_estimate_tokens(c) for c in unique_comments)
        tokens_out = n_unique * 15  # ~15 tokens por item de resultado
        cost_usd   = (tokens_in * 0.80 + tokens_out * 4.00) / 1_000_000

        # ── Diagnóstico ──────────────────────────────────────────────────────
        try:
            with _log_path.open("a", encoding="utf-8") as _f:
                _f.write(f"\n--- Análise IA: {col_id} ---\n")
                _f.write(f"  total respostas       : {total}\n")
                _f.write(f"  não-vazias            : {non_empty}\n")
                _f.write(f"  únicas (após dedup)   : {n_unique}\n")
                _f.write(f"  economia via cache    : {dedup_pct:.1f}%\n")
                _f.write(f"  tokens estimados      : ~{tokens_in} (in) + ~{tokens_out} (out)\n")
                _f.write(f"  custo estimado US$    : ~{cost_usd:.4f}\n")
                _f.write(f"  categorias descobertas: {categories}\n")
        except Exception:
            pass

        results.append(SentimentCategoryResult(
            column_id=col_id,
            categories_discovered=categories,
            sentiment_values=sentiment_values,
            category_values=category_values,
        ))

    return results
