import { useState } from 'react'
import { api, ApiError } from '../../api/client'
import type { NormalizeResult } from '../../api/client'
import { Check, ChevronDown, ArrowRight } from '../icons'

interface ExportStepProps {
  openTextIds: string[]
  onBack?: () => void
  onRestart?: () => void
}

type Status = 'idle' | 'loading' | 'done' | 'error'

export default function ExportStep({ openTextIds, onBack, onRestart }: ExportStepProps) {
  const [status,        setStatus]        = useState<Status>('idle')
  const [result,        setResult]        = useState<NormalizeResult | null>(null)
  const [errorMsg,      setErrorMsg]      = useState<string | null>(null)
  const [accordionOpen, setAccordionOpen] = useState(false)
  const [downloading,   setDownloading]   = useState(false)

  // ── Normalizar ─────────────────────────────────────────────────────────────
  async function handleNormalize() {
    setStatus('loading')
    setErrorMsg(null)
    try {
      const res = await api.normalize({
        ai_original_ids: openTextIds,
      })
      setResult(res)
      setStatus('done')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Erro ao processar. Tente novamente.')
      setStatus('error')
    }
  }

  // ── Download do .xlsx ──────────────────────────────────────────────────────
  async function handleDownload() {
    setDownloading(true)
    try {
      const res = await api.download()
      if (!res.ok) throw new Error('Resposta inválida do servidor.')
      const blob = await res.blob()
      const disposition = res.headers.get('content-disposition') ?? ''
      const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\r\n]+)/)
      const filename = match ? decodeURIComponent(match[1].trim()) : 'normalizado.xlsx'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // download silently falha — o usuário pode tentar novamente
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="export-step animate-in">
      {/* ── Cabeçalho ── */}
      <div className="step-section-header">
        <p className="step-micro-label">Etapa 4 — Exportar</p>
        <h2 className="step-section-title">Exportar</h2>
        <p className="step-instruction">
          Processe os dados e baixe a planilha normalizada pronta para análise.
        </p>
      </div>

      {/* ── Botão principal (visível até concluir) ── */}
      {status !== 'done' && (
        <div className="export-cta-wrap">
          {/* Linha com Voltar (idle) + Normalizar */}
          <div className={onBack && status === 'idle' ? 'step-cta-row--with-back' : 'step-cta-row'}>
            {onBack && status === 'idle' && (
              <button type="button" className="btn-ghost" onClick={onBack}>
                Voltar
              </button>
            )}
            <button
              type="button"
              className="btn-primary"
              onClick={handleNormalize}
              disabled={status === 'loading'}
            >
              {status === 'loading' ? (
                <>
                  <span className="export-spinner" aria-hidden />
                  <span className="text-shimmer">Processando…</span>
                </>
              ) : (
                'Normalizar e exportar'
              )}
            </button>
          </div>

          {status === 'error' && errorMsg && (
            <div className="export-error-banner" role="alert">
              <span>{errorMsg}</span>
              <button type="button" className="export-retry-btn" onClick={handleNormalize}>
                Tentar novamente
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Resultado (revelado ao concluir) ── */}
      {status === 'done' && result && (
        <>
          {/* Card de sucesso com sombra-carimbo cítrica (§7.7) */}
          <div className="export-success-card">
            <span className="export-success-icon" aria-hidden>
              <Check size={28} />
            </span>
            <div className="export-success-body">
              <p className="export-success-title">Planilha normalizada pronta!</p>
              <p className="export-success-sub">
                Abas <strong>data</strong> e <strong>codebook</strong> geradas com sucesso.
              </p>
            </div>
          </div>

          {/* Cards LINHAS / COLUNAS — mesmo padrão da Etapa 2 (§9.8) */}
          <div className="stat-cards-grid stat-cards-grid--2">
            <div className="stat-card">
              <p className="stat-card-label">LINHAS EXPORTADAS</p>
              <p className="stat-card-number">{result.rows.toLocaleString('pt-BR')}</p>
            </div>
            <div className="stat-card">
              <p className="stat-card-label">COLUNAS EXPORTADAS</p>
              <p className="stat-card-number">{result.columns}</p>
            </div>
          </div>

          {/* Accordion de colunas geradas */}
          <div className="accordion">
            <button
              type="button"
              className={`accordion-header${accordionOpen ? ' accordion-header--open' : ''}`}
              onClick={() => setAccordionOpen(v => !v)}
              aria-expanded={accordionOpen}
            >
              <ChevronDown
                size={16}
                className={`accordion-chevron${accordionOpen ? ' accordion-chevron--open' : ''}`}
                aria-hidden
              />
              Ver todas as colunas geradas
              <span className="accordion-count">({result.headers.length})</span>
            </button>
            {accordionOpen && (
              <div className="accordion-body animate-in">
                <ol className="export-headers-list">
                  {result.headers.map((h, i) => (
                    <li key={i} className="export-header-item">
                      <span className="export-header-index">{i + 1}</span>
                      <span className="export-header-name">{h}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>

          {/* Botão de download */}
          <div className={onBack ? 'step-cta-row--with-back' : 'step-cta-row'}>
            {onBack && (
              <button type="button" className="btn-ghost" onClick={onBack}>
                Voltar
              </button>
            )}
            <button
              type="button"
              className="btn-primary"
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? 'Baixando…' : 'Baixar planilha normalizada'}
              {!downloading && <ArrowRight size={18} aria-hidden />}
            </button>
          </div>

          {/* "Normalizar outro arquivo" — reinicia o fluxo sem fechar o app */}
          {onRestart && (
            <div className="export-restart-row">
              <button type="button" className="btn-ghost" onClick={onRestart}>
                Normalizar outro arquivo
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
