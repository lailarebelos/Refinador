"""Qualtrics Normalizer v2 — Interface Streamlit."""
import sys, io, os, tempfile
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except: pass

import streamlit as st
import pandas as pd
from pathlib import Path
from normalizer import build_config, normalize, VALID_TYPES, build_output_header
from llm_provider import LLMConfig, build_provider, persist_to_env, load_config_from_env, LLMProviderError, MockProvider

def _question_preview(text: str, limit: int = 90) -> str:
    text = str(text or "").strip()
    return text if len(text) <= limit else f"{text[:limit-1].rstrip()}…"

def _question_option_label(row) -> str:
    return f"{row['original_id']} - {row['question_text']}"

def _render_question_detail(row) -> None:
    st.markdown(f"**{row['original_id']}**")
    st.markdown(
        f"""
        <div class="question-detail-card">
            {row["question_text"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="Qualtrics Normalizer", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
.block-container { max-width: 1200px; padding-top: 2.75rem; }
h1, h2, h3 { color: #05662B !important; }
.loc-header { background: linear-gradient(135deg, #05662B 0%, #008C3C 100%);
    padding: 1.5rem 2rem; border-radius: 12px; margin-top: 0.35rem; margin-bottom: 1.5rem; }
.loc-header h1 { color: white !important; margin: 0; font-size: 1.8rem; font-weight: 700; }
.loc-header p { color: #7DDE21; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
.stButton > button[kind="primary"], .stDownloadButton > button {
    background: linear-gradient(135deg, #05662B, #008C3C) !important;
    color: white !important; border: none !important;
    padding: 0.7rem 2rem !important; font-size: 1rem !important;
    border-radius: 8px !important; font-weight: 600 !important; }
.stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #008C3C, #7DDE21) !important; }
div[data-testid="stMetric"] { background: #f8fdf8; border-left: 4px solid #008C3C;
    padding: 0.8rem 1rem; border-radius: 0 8px 8px 0; }
div[data-testid="stMetric"] label { color: #05662B !important; font-weight: 600; }
.badge { padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
.badge-ok { background: #E6F4EA; color: #05662B; }
.badge-warn { background: #FFF8E1; color: #E65100; }
div[data-testid="stDataEditor"] { border: 1px solid #E6F4EA; border-radius: 8px; }
hr { border-color: #E6F4EA !important; }
details { border: 1px solid #E6F4EA !important; border-radius: 8px !important; }
details summary { color: #05662B !important; font-weight: 600; }
[data-baseweb="select"] [role="option"] { white-space: normal !important; line-height: 1.25rem !important; }
[data-baseweb="popover"] [role="option"] { white-space: normal !important; line-height: 1.25rem !important; }
[data-baseweb="tag"] { height: auto !important; white-space: normal !important; }
.question-detail-card {
    border: 2px solid #C62828;
    background: #FFF8F8;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-top: 0.5rem;
    color: #3A1A1A;
    line-height: 1.5;
    box-shadow: 0 14px 30px rgba(198, 40, 40, 0.16), 0 3px 8px rgba(0, 0, 0, 0.08);
}
</style>
""", unsafe_allow_html=True)

if "llm_config" not in st.session_state: st.session_state.llm_config = load_config_from_env()
if "config_df" not in st.session_state: st.session_state.config_df = None
if "df_data" not in st.session_state: st.session_state.df_data = None
if "upload_key" not in st.session_state: st.session_state.upload_key = ""
if "tmp_xlsx" not in st.session_state: st.session_state.tmp_xlsx = None
if "tmp_qsf" not in st.session_state: st.session_state.tmp_qsf = None

# ── Diálogo de configuração de IA ────────────────────────────────────────────
@st.dialog("Configuração de IA", width="large")
def settings_dialog():
    provs = {"Claude (Anthropic)":"anthropic", "ChatGPT (OpenAI)":"openai", "Azure OpenAI":"azure"}
    cur = st.session_state.llm_config.provider
    idx = list(provs.values()).index(cur) if cur in provs.values() else 0
    choice = st.radio("Provedor:", list(provs.keys()), index=idx, horizontal=True)
    prov = provs[choice]
    ph = {"anthropic":"sk-ant-...","openai":"sk-...","azure":"(chave Azure)"}
    ek = {"anthropic":"ANTHROPIC_API_KEY","openai":"OPENAI_API_KEY","azure":"AZURE_OPENAI_API_KEY"}
    api_key = st.text_input("Chave da API:", value=os.getenv(ek.get(prov,""),""), type="password", placeholder=ph.get(prov,""))
    ae, ad, av = "", "", "2024-08-01-preview"
    if prov == "azure":
        ae = st.text_input("Endpoint:", value=os.getenv("AZURE_OPENAI_ENDPOINT",""), placeholder="https://...openai.azure.com/")
        ad = st.text_input("Nome do deployment:", value=os.getenv("AZURE_OPENAI_DEPLOYMENT",""))
        av = st.text_input("Versão da API:", value=os.getenv("AZURE_OPENAI_API_VERSION","2024-08-01-preview"))
    save = st.checkbox("Salvar para a próxima sessão (.env)")
    c1,_,c3 = st.columns([1,1,1])
    with c1:
        if st.button("🔌 Testar conexão"):
            cfg = LLMConfig(provider=prov, api_key=api_key, azure_endpoint=ae, azure_deployment=ad, azure_api_version=av)
            try: build_provider(cfg).complete("Responda ok.","ok?",5); st.success("✅ Conexão OK!")
            except Exception as e: st.error(f"❌ Erro: {e}")
    with c3:
        if st.button("💾 Salvar", type="primary"):
            st.session_state.llm_config = LLMConfig(provider=prov, api_key=api_key, azure_endpoint=ae, azure_deployment=ad, azure_api_version=av)
            if save:
                persist_to_env({"LLM_PROVIDER":prov, ek[prov]:api_key})
                if prov=="azure": persist_to_env({"AZURE_OPENAI_ENDPOINT":ae,"AZURE_OPENAI_DEPLOYMENT":ad,"AZURE_OPENAI_API_VERSION":av})
            st.rerun()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
h1, h2 = st.columns([0.88, 0.12])
with h1:
    st.markdown('<div class="loc-header"><h1>📊 Qualtrics Normalizer</h1><p>Transforme exports do Qualtrics em planilhas prontas para análise.</p></div>', unsafe_allow_html=True)
with h2:
    cfg = st.session_state.llm_config
    pn = {"anthropic":"Claude","openai":"ChatGPT","azure":"Azure"}
    if cfg.api_key: st.markdown(f'<span class="badge badge-ok">✅ {pn.get(cfg.provider, cfg.provider)}</span>', unsafe_allow_html=True)
    else: st.markdown('<span class="badge badge-warn">⚠ IA não configurada.</span>', unsafe_allow_html=True)
    if st.button("⚙", key="settings", help="Configurar provedor de IA"): settings_dialog()

# ── Upload duplo ──────────────────────────────────────────────────────────────
st.markdown("### 📁 Upload dos arquivos")
st.caption("Exporte do Qualtrics o questionário (.qsf) e os dados numéricos (.xlsx). Ambos são necessários.")

col_qsf, col_xlsx = st.columns(2)
with col_qsf:
    qsf_file = st.file_uploader("📄 Questionário (.qsf)", type=["qsf"], key="qsf_up",
                                 help="Arquivo de definição do questionário exportado do Qualtrics.")
with col_xlsx:
    xlsx_file = st.file_uploader("📊 Dados numéricos (.xlsx)", type=["xlsx"], key="xlsx_up",
                                  help="Dados da pesquisa exportados com valores numéricos e respostas múltiplas já separadas.")

if qsf_file and xlsx_file:
    key = f"{qsf_file.name}_{xlsx_file.name}"
    if st.session_state.upload_key != key:
        st.session_state.upload_key = key
        st.session_state.config_df = None

        tmp_q = tempfile.NamedTemporaryFile(delete=False, suffix=".qsf")
        tmp_q.write(qsf_file.read()); tmp_q.close()
        st.session_state.tmp_qsf = tmp_q.name

        tmp_x = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        tmp_x.write(xlsx_file.read()); tmp_x.close()
        st.session_state.tmp_xlsx = tmp_x.name

    if st.session_state.tmp_xlsx and st.session_state.tmp_qsf and st.session_state.config_df is None:
        provider = build_provider(st.session_state.llm_config)
        real_provider = None if isinstance(provider, MockProvider) else provider

        with st.spinner("🔍 Analisando questionário e dados..."):
            try:
                config, df = build_config(st.session_state.tmp_xlsx, st.session_state.tmp_qsf, real_provider)
                st.session_state.df_data = df
                for c in config:
                    c["revisar"] = "⚠ Revisar" if c["confidence"] == "low" else "✅ OK"
                st.session_state.config_df = pd.DataFrame(config)
                if real_provider:
                    st.success("✅ Questionário analisado com IA. Nomes das variáveis foram gerados automaticamente.")
                else:
                    st.info("💡 Configure um provedor de IA no menu ⚙ para nomes de variáveis mais precisos.")
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivos: {e}")
                import traceback; st.code(traceback.format_exc())

    # ── Tabela de configuração ────────────────────────────────────────────
    if st.session_state.config_df is not None:
        st.divider()
        st.markdown("### 📋 Configuração das colunas")
        st.caption("Revise e edite a configuração. Desmarque 'Incluir' para ignorar colunas. Ajuste grupo, tipo e rótulo conforme necessário.")

        cdf = st.session_state.config_df
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total de colunas", len(cdf))
        c2.metric("Incluídas", int(cdf["include"].sum()))
        c3.metric("Texto livre", int((cdf["type"]=="open_text").sum()))
        c4.metric("⚠ Para revisar", int((cdf["confidence"]=="low").sum()))

        filt = st.radio("Filtrar:", ["Todas","⚠ Para revisar","Incluídas","Excluídas","Texto livre"], horizontal=True, key="filt")
        ddf = cdf.copy()
        if filt=="⚠ Para revisar": ddf = ddf[ddf["confidence"]=="low"]
        elif filt=="Incluídas": ddf = ddf[ddf["include"]==True]
        elif filt=="Excluídas": ddf = ddf[ddf["include"]==False]
        elif filt=="Texto livre": ddf = ddf[ddf["type"]=="open_text"]
        ddf["question_preview"] = ddf["question_text"].apply(_question_preview)

        edited = st.data_editor(ddf, column_config={
            "original_id": st.column_config.TextColumn("ID Qualtrics", disabled=True, width="small"),
            "question_preview": st.column_config.TextColumn("Pergunta", disabled=True, width="medium", help="Use o seletor logo abaixo para abrir o enunciado completo sem alterar a tabela principal."),
            "sample": st.column_config.TextColumn("Amostras", disabled=True, width="small"),
            "include": st.column_config.CheckboxColumn("Incluir", width="small"),
            "group": st.column_config.TextColumn("Grupo", width="small"),
            "type": st.column_config.SelectboxColumn("Tipo", options=VALID_TYPES, width="small"),
            "short_name": st.column_config.TextColumn("Rótulo", width="medium"),
            "subitem": st.column_config.TextColumn("Subitem", width="small"),
            "alternatives": st.column_config.TextColumn("Alternativas", disabled=True, width=None),
            "confidence": st.column_config.TextColumn("Confiança", disabled=True, width=None),
            "revisar": st.column_config.SelectboxColumn("Status", options=["✅ OK","⚠ Revisar"], width="small"),
        }, hide_index=True, use_container_width=True, num_rows="fixed", key="editor",
        column_order=["revisar","include","original_id","question_preview","sample","group","type","short_name","subitem"])

        if edited is not None:
            for idx in edited.index:
                for col in ["include","group","type","short_name","subitem","revisar"]:
                    if col in edited.columns:
                        st.session_state.config_df.at[idx, col] = edited.at[idx, col]

        if not ddf.empty:
            with st.popover("Abrir enunciado completo"):
                selected_question_id = st.selectbox(
                    "Pergunta",
                    options=ddf["original_id"].tolist(),
                    format_func=lambda oid: _question_option_label(ddf.loc[ddf["original_id"] == oid].iloc[0]),
                    key="question_viewer",
                )
                selected_question = ddf.loc[ddf["original_id"] == selected_question_id].iloc[0]
                _render_question_detail(selected_question)

        # ── Seleção de análise por IA ─────────────────────────────────────
        st.divider()
        cdf = st.session_state.config_df
        ot_cols = cdf[(cdf["include"]==True) & (cdf["type"]=="open_text")]

        selected_ids = []
        if len(ot_cols) > 0:
            st.markdown("### 🔬 Análise de sentimento e categorização (opcional)")
            st.caption("Selecione colunas de texto livre para análise automática. Para cada uma, serão criadas duas colunas: sentimento (1-3) e categorias.")
            question_labels = {row["original_id"]: _question_option_label(row) for _, row in ot_cols.iterrows()}
            selected_ids = st.multiselect(
                "Colunas para analisar:",
                options=ot_cols["original_id"].tolist(),
                format_func=lambda oid: question_labels[oid],
                key="ai_sel",
            )
            with st.popover("Abrir enunciado completo da análise"):
                selected_ai_question_id = st.selectbox(
                    "Pergunta de texto livre",
                    options=ot_cols["original_id"].tolist(),
                    format_func=lambda oid: question_labels[oid],
                    key="ai_question_viewer",
                )
                selected_ai_question = ot_cols.loc[ot_cols["original_id"] == selected_ai_question_id].iloc[0]
                _render_question_detail(selected_ai_question)

        # ── Botão de normalização ─────────────────────────────────────────
        st.divider()
        if st.button("🚀 Normalizar", type="primary", use_container_width=True):
            config_list = st.session_state.config_df.to_dict("records")
            provider = build_provider(st.session_state.llm_config)
            is_real = not isinstance(provider, MockProvider)
            ai_headers = [
                build_output_header(cfg["original_id"], cfg.get("short_name", cfg["original_id"]), cfg.get("subitem", ""))
                for cfg in config_list
                if cfg.get("include", True) and cfg.get("type") == "open_text" and cfg["original_id"] in selected_ids
            ]

            with st.spinner("⏳ Normalizando dados..."):
                try:
                    base = Path(xlsx_file.name).stem
                    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx"); tmp_out.close()
                    if ai_headers and is_real:
                        with st.spinner(f"🤖 Analisando sentimento em {len(ai_headers)} coluna(s)..."):
                            result = normalize(
                                st.session_state.tmp_xlsx,
                                tmp_out.name,
                                config_list,
                                st.session_state.df_data,
                                ai_columns=ai_headers,
                                provider=provider,
                            )
                    else:
                        result = normalize(st.session_state.tmp_xlsx, tmp_out.name, config_list, st.session_state.df_data)

                    st.success(f"✅ Concluído! {result['rows']} linhas × {result['columns']} colunas.")

                    ai_gen = [h for h in result["headers"] if "_sentimento" in h or "_categorias" in h]
                    if ai_gen:
                        st.info(f"🔬 Colunas de IA geradas: {', '.join(ai_gen)}")

                    with st.expander("📋 Ver todas as colunas geradas"):
                        for h in result["headers"]:
                            ic = "🔬" if "_sentimento" in h or "_categorias" in h else "📊"
                            st.text(f"  {ic} {h}")

                    with open(tmp_out.name, "rb") as f:
                        st.download_button("📥 Baixar planilha normalizada", f.read(),
                            file_name=f"{base}_normalized.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary", use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Erro na normalização: {e}")
                    import traceback; st.code(traceback.format_exc())
elif qsf_file or xlsx_file:
    missing = "o arquivo de dados (.xlsx)" if qsf_file else "o questionário (.qsf)"
    st.warning(f"⚠ Falta {missing}. Ambos os arquivos são necessários para prosseguir.")
