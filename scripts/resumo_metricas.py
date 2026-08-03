"""
scripts/resumo_metricas.py — Resumo de consumo de IA a partir de metrics/usage.jsonl.

Uso:
    python scripts/resumo_metricas.py [caminho/para/usage.jsonl]

Lê apenas o log JSONL gerado por backend/instrumentation.py — não importa
nem depende de normalizer.py, ai_analysis.py ou llm_provider.py.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

# Preço aproximado por token (mesma ordem de grandeza referenciada no
# diagnostico.log de ai_analysis.py, modelo Haiku) — usado só para dar uma
# noção de custo; não influencia nenhuma lógica de negócio.
_PRICE_PER_TOKEN_IN  = 0.80 / 1_000_000
_PRICE_PER_TOKEN_OUT = 4.00 / 1_000_000

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "metrics" / "usage.jsonl"


def _load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _cost(input_tokens: float, output_tokens: float) -> float:
    return input_tokens * _PRICE_PER_TOKEN_IN + output_tokens * _PRICE_PER_TOKEN_OUT


def summarize(records: list[dict]) -> dict:
    reais      = [r for r in records if not r.get("cache_hit")]
    cache_hits = [r for r in records if r.get("cache_hit")]

    total_input  = sum(r.get("input_tokens", 0) for r in reais)
    total_output = sum(r.get("output_tokens", 0) for r in reais)

    por_etapa: dict = defaultdict(lambda: {"chamadas": 0, "tokens": 0})
    for r in reais:
        e = r.get("etapa", "desconhecida")
        por_etapa[e]["chamadas"] += 1
        por_etapa[e]["tokens"]   += r.get("total_tokens", 0)

    media_tokens_por_etapa = {
        e: (v["tokens"] / v["chamadas"]) if v["chamadas"] else 0.0
        for e, v in por_etapa.items()
    }

    # Economia estimada: cada cache_hit evitou uma chamada real; como o
    # registro do hit tem tokens=0 (não houve chamada), usamos a média de
    # tokens das chamadas reais da mesma etapa como proxy do custo evitado.
    economia_tokens = 0.0
    for r in cache_hits:
        e = r.get("etapa", "desconhecida")
        economia_tokens += media_tokens_por_etapa.get(e, 0.0)

    # "Execução de normalização" ~= uma sessão (sessao); cada normalização
    # roda em uma sessão isolada, então tokens por sessão == tokens por execução.
    por_execucao: dict = defaultdict(lambda: {"chamadas": 0, "tokens": 0})
    for r in records:
        por_execucao[r.get("sessao", "?")]["chamadas"] += 1
        por_execucao[r.get("sessao", "?")]["tokens"]   += r.get("total_tokens", 0)

    return {
        "total_chamadas":                 len(records),
        "chamadas_reais":                 len(reais),
        "chamadas_via_cache":             len(cache_hits),
        "total_input_tokens":             total_input,
        "total_output_tokens":            total_output,
        "total_tokens":                   total_input + total_output,
        "custo_estimado_usd":             round(_cost(total_input, total_output), 4),
        "por_etapa":                      dict(por_etapa),
        "tokens_por_execucao_sessao":     dict(por_execucao),
        "economia_cache_tokens_estimada": round(economia_tokens, 1),
        "economia_cache_usd_estimada":    round(_cost(economia_tokens / 2, economia_tokens / 2), 4),
    }


def main() -> None:
    path    = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_PATH
    records = _load_records(path)
    if not records:
        print(f"Nenhum registro encontrado em {path}")
        return
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
