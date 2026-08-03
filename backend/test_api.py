"""Script de teste ponta a ponta do backend FastAPI."""
import sys, json, tempfile, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.test_normalizer import _write_sample_qsf, _write_sample_xlsx

BASE = "http://localhost:8000"

with tempfile.TemporaryDirectory() as tmp:
    qsf_path  = Path(tmp) / "survey.qsf"
    xlsx_path = Path(tmp) / "data.xlsx"
    _write_sample_qsf(qsf_path)
    _write_sample_xlsx(xlsx_path)

    # POST /api/process
    with open(qsf_path, "rb") as qf, open(xlsx_path, "rb") as xf:
        r = requests.post(
            f"{BASE}/api/process",
            files={"qsf_file": ("survey.qsf", qf), "xlsx_file": ("data.xlsx", xf)},
        )
    assert r.status_code == 200, f"process failed: {r.text}"
    data    = r.json()
    cookies = r.cookies
    print(f"[OK] POST /api/process  — stats={data['stats']}  ai_used={data['ai_used']}")
    assert all("_encoding" not in k for row in data["config"] for k in row), \
        "ERRO: campos internos vazaram para o frontend!"
    print("[OK] Campos internos (_encoding_*) filtrados corretamente")

    # GET /api/config
    r2 = requests.get(f"{BASE}/api/config", cookies=cookies)
    assert r2.status_code == 200, f"get_config failed: {r2.text}"
    cfg = r2.json()
    print(f"[OK] GET  /api/config   — {len(cfg['config'])} linhas, confirmed={cfg['classification_confirmed']}")

    # GET /api/eligibility
    r3 = requests.get(f"{BASE}/api/eligibility", cookies=cookies)
    assert r3.status_code == 200, f"eligibility failed: {r3.text}"
    elig = r3.json()
    eligible = [(c["original_id"], c["eligible"]) for c in elig["columns"]]
    print(f"[OK] GET  /api/eligibility — {eligible}")

    # PATCH /api/config (marcar Q1 como não incluída)
    patch = {"rows": [{"original_id": "Q1", "include": False}]}
    r4 = requests.patch(f"{BASE}/api/config", json=patch, cookies=cookies)
    assert r4.status_code == 200
    print(f"[OK] PATCH /api/config  — stats após patch={r4.json()['stats']}")

    # POST /api/config/confirm
    r5 = requests.post(f"{BASE}/api/config/confirm", cookies=cookies)
    assert r5.json()["ok"] is True
    print("[OK] POST /api/config/confirm")

    # POST /api/normalize
    r6 = requests.post(f"{BASE}/api/normalize", json={"ai_original_ids": []}, cookies=cookies)
    assert r6.status_code == 200, f"normalize failed: {r6.text}"
    result = r6.json()
    print(f"[OK] POST /api/normalize — rows={result['rows']} cols={result['columns']} headers={result['headers']}")

    # GET /api/download
    r7 = requests.get(f"{BASE}/api/download", cookies=cookies)
    assert r7.status_code == 200, f"download failed: {r7.text}"
    assert len(r7.content) > 1000, "arquivo muito pequeno"
    print(f"[OK] GET  /api/download  — {len(r7.content)} bytes  type={r7.headers.get('content-type','')}")

    # Verificação de isolamento: segunda sessão não enxerga config da primeira
    r8 = requests.get(f"{BASE}/api/config")  # sem cookies → nova sessão
    assert r8.status_code == 404, f"ERRO de isolamento! sessão nova retornou config: {r8.text}"
    print("[OK] Isolamento de sessão — nova sessão retorna 404 corretamente")

print("\n=== TODOS OS TESTES PASSARAM ===")
