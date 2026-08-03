import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { THEMED_ASSETS } from '../../brand/assets'
import { X, Check, AlertTriangle } from '../icons'
import { api } from '../../api/client'
import type { LLMConfig, LLMConfigUpdate } from '../../api/client'

interface LlmConfigModalProps {
  onClose: () => void
}

type TestStatus = { ok: true; message: string } | { ok: false; message: string } | null

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function LlmConfigModal({ onClose }: LlmConfigModalProps) {
  const { theme } = useTheme()
  const assets = THEMED_ASSETS[theme]
  const dialogRef = useRef<HTMLDivElement>(null)

  const [loading,     setLoading]     = useState(true)
  const [saving,      setSaving]      = useState(false)
  const [testing,     setTesting]     = useState(false)
  const [loadError,   setLoadError]   = useState<string | null>(null)
  const [saveError,   setSaveError]   = useState<string | null>(null)
  const [testResult,  setTestResult]  = useState<TestStatus>(null)
  const [currentCfg,  setCurrentCfg]  = useState<LLMConfig | null>(null)

  // Campos do formulário
  const [provider, setProvider] = useState('')
  const [model,    setModel]    = useState('')
  const [apiKey,   setApiKey]   = useState('')
  const [baseUrl,  setBaseUrl]  = useState('')
  const [persist,  setPersist]  = useState(true)

  // Carrega config atual ao abrir
  useEffect(() => {
    api.llm.get()
      .then((cfg) => {
        setCurrentCfg(cfg)
        setProvider(cfg.provider ?? '')
        setModel(cfg.model ?? '')
        setBaseUrl(cfg.base_url ?? '')
        // api_key nunca vem do backend; campo fica vazio intencionalmente
      })
      .catch((err: Error) => setLoadError(err.message))
      .finally(() => setLoading(false))
  }, [])

  // Trap de foco + fechar no Esc
  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    el.querySelector<HTMLElement>('.modal-close')?.focus()

    const trap = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key !== 'Tab') return
      const focusables = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE))
      if (!focusables.length) return
      const first = focusables[0]
      const last  = focusables[focusables.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus()
      }
    }
    document.addEventListener('keydown', trap)
    return () => document.removeEventListener('keydown', trap)
  }, [onClose])

  // Monta o objeto de atualização com só os campos preenchidos
  function buildUpdate(): LLMConfigUpdate {
    const update: LLMConfigUpdate = { persist }
    if (provider.trim()) update.provider = provider.trim()
    if (model.trim())    update.model    = model.trim()
    if (apiKey.trim())   update.api_key  = apiKey.trim()
    if (baseUrl.trim())  update.base_url = baseUrl.trim()
    return update
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    setSaveError(null)
    try {
      const res = await api.llm.test(buildUpdate())
      setTestResult({ ok: res.ok, message: res.message })
    } catch (err: unknown) {
      setTestResult({ ok: false, message: err instanceof Error ? err.message : 'Erro ao testar conexão.' })
    } finally {
      setTesting(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    setSaveError(null)
    setTestResult(null)
    try {
      await api.llm.update(buildUpdate())
      onClose()
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Erro ao salvar configuração.')
    } finally {
      setSaving(false)
    }
  }

  const isWorking = loading || saving || testing

  return (
    <div
      className="modal-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="llm-modal-title"
        aria-busy={loading}
      >
        {/* Cabeçalho */}
        <div className="modal-header">
          <img src={assets.logoHorizontal} alt="Localiza&CO" className="modal-logo" />
          <button
            className="modal-close"
            onClick={onClose}
            aria-label="Fechar"
            disabled={saving}
          >
            <X size={18} aria-hidden />
          </button>
        </div>

        {/* Corpo */}
        <div className="modal-body">
          <h2 className="modal-title" id="llm-modal-title">Configurar IA</h2>
          <p className="modal-subtitle">
            Defina o provedor e o modelo de linguagem para análise de respostas abertas.
          </p>

          {loading && (
            <p style={{ color: 'var(--lds-color-neutral-foreground-low)', fontSize: 'var(--lds-font-size-sm)' }}>
              Carregando configuração atual...
            </p>
          )}

          {loadError && (
            <div className="modal-error" role="alert">
              <AlertTriangle size={16} aria-hidden />
              {loadError}
            </div>
          )}

          {!loading && !loadError && (
            <form
              className="modal-form"
              onSubmit={(e) => { e.preventDefault(); handleSave() }}
              noValidate
            >
              {/* Provedor */}
              <div className="form-group">
                <label htmlFor="llm-provider" className="form-label">Provedor</label>
                <input
                  id="llm-provider"
                  className="form-input"
                  type="text"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  placeholder="ex: anthropic, openai"
                  disabled={isWorking}
                  autoComplete="off"
                />
              </div>

              {/* Modelo */}
              <div className="form-group">
                <label htmlFor="llm-model" className="form-label">Modelo</label>
                <input
                  id="llm-model"
                  className="form-input"
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="ex: claude-sonnet-4-6, gpt-4o"
                  disabled={isWorking}
                  autoComplete="off"
                />
              </div>

              {/* Chave de API — campo de senha, nunca exibe valor salvo */}
              <div className="form-group">
                <label htmlFor="llm-api-key" className="form-label">
                  Chave de API
                  <span className="form-label-optional">(opcional)</span>
                </label>
                <input
                  id="llm-api-key"
                  className="form-input"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    currentCfg?.has_key
                      ? 'Chave salva — deixe em branco para manter'
                      : 'Insira a chave de API'
                  }
                  disabled={isWorking}
                  autoComplete="new-password"
                />
                {currentCfg?.has_key && (
                  <span className="form-hint">
                    Uma chave de API ja esta salva. Preencha apenas se quiser substituí-la.
                  </span>
                )}
              </div>

              {/* URL base — campo opcional para endpoints customizados */}
              <div className="form-group">
                <label htmlFor="llm-base-url" className="form-label">
                  URL base
                  <span className="form-label-optional">(opcional)</span>
                </label>
                <input
                  id="llm-base-url"
                  className="form-input"
                  type="url"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="ex: https://api.openai.com/v1"
                  disabled={isWorking}
                  autoComplete="off"
                />
                <span className="form-hint">
                  Necessário apenas para provedores com endpoint customizado ou proxies.
                </span>
              </div>

              {/* Persistir nas variáveis de ambiente */}
              <div className="form-group">
                <label className="form-checkbox-row">
                  <input
                    id="llm-persist"
                    className="form-checkbox"
                    type="checkbox"
                    checked={persist}
                    onChange={(e) => setPersist(e.target.checked)}
                    disabled={isWorking}
                  />
                  <span className="form-checkbox-label">
                    Salvar nas variáveis de ambiente (.env)
                  </span>
                </label>
                <span className="form-hint" style={{ marginLeft: '24px' }}>
                  Mantém a configuração entre reinicializações do servidor.
                </span>
              </div>
            </form>
          )}

          {/* Resultado do teste de conexão */}
          {testResult && (
            <div
              className={`modal-test-result ${testResult.ok ? 'ok' : 'fail'}`}
              role="status"
            >
              {testResult.ok
                ? <Check size={15} aria-hidden />
                : <AlertTriangle size={15} aria-hidden />
              }
              {testResult.message}
            </div>
          )}

          {/* Erro ao salvar */}
          {saveError && (
            <div className="modal-error" role="alert" style={{ marginTop: '8px' }}>
              <AlertTriangle size={15} aria-hidden />
              {saveError}
            </div>
          )}
        </div>

        {/* Rodapé */}
        <div className="modal-footer modal-footer--split">
          {/* Testar conexão — fica à esquerda */}
          <button
            type="button"
            className="btn-secondary"
            onClick={handleTest}
            disabled={isWorking || loading || !!loadError}
            aria-busy={testing}
          >
            {testing ? 'Testando...' : 'Testar conexão'}
          </button>

          {/* Cancelar + Salvar — ficam à direita */}
          <div className="modal-footer-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={saving}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSave}
              disabled={isWorking || !!loadError}
              aria-busy={saving}
            >
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
