import { useState, useEffect, useRef } from 'react'
import { api, ApiError } from '../../api/client'
import type { EligibilityColumn } from '../../api/client'
import { ChevronDown, X, ArrowRight, Check } from '../icons'

interface OpenTextStepProps {
  onNext: (selectedIds: string[]) => void
  onBack?: () => void
}

const ANALYSIS_DESCRIPTION =
  'Para cada coluna selecionada, o sistema envia amostras de respostas a um modelo de ' +
  'linguagem (LLM) configurado e solicita a classificação do sentimento de cada resposta ' +
  'como Negativo, Neutro ou Positivo, além de uma categoria temática. O resultado é ' +
  'acrescentado à planilha exportada em colunas adicionais de sentimento e categoria.'

export default function OpenTextStep({ onNext, onBack }: OpenTextStepProps) {
  const [columns,      setColumns]      = useState<EligibilityColumn[]>([])
  const [selectedIds,  setSelectedIds]  = useState<Set<string>>(new Set())
  const [menuOpen,     setMenuOpen]     = useState(false)
  const [accord1Open,  setAccord1Open]  = useState(false)
  const [accord2Open,  setAccord2Open]  = useState(false)
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState<string | null>(null)
  const [continuing,   setContinuing]   = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)

  // Carrega colunas elegíveis ao montar
  useEffect(() => {
    api.eligibility.get()
      .then(res => {
        setColumns(res.columns)
        // Pré-seleciona as elegíveis
        setSelectedIds(new Set(res.columns.filter(c => c.eligible).map(c => c.original_id)))
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Erro ao carregar colunas.')
      })
      .finally(() => setLoading(false))
  }, [])

  // Fecha o menu ao clicar fora
  useEffect(() => {
    if (!menuOpen) return
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [menuOpen])

  function toggleColumn(id: string) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function removeChip(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }

  function handleContinue() {
    setContinuing(true)
    onNext(Array.from(selectedIds))
  }

  const selectedColumns = columns.filter(c => selectedIds.has(c.original_id))
  const label = (c: EligibilityColumn) =>
    c.question_text.length > 60 ? c.question_text.slice(0, 58) + '…' : c.question_text

  return (
    <div className="opentext-step animate-in">
      <div className="step-section-header">
        <p className="step-micro-label">Etapa 3 — Respostas abertas</p>
        <h2 className="step-section-title">
          Análise de respostas abertas{' '}
          <span className="step-title-optional">(opcional)</span>
        </h2>
        <p className="step-instruction">
          Selecione colunas com texto opinativo para análise de sentimento e categorização por IA.
        </p>
      </div>

      {/* ── Multiselect ── */}
      <div className="multiselect-field-wrap" ref={containerRef}>
        <label id="ms-label" className="multiselect-label" htmlFor="ms-trigger">
          Colunas para analisar
        </label>

        {loading ? (
          <p className="opentext-loading" role="status">Carregando colunas…</p>
        ) : error ? (
          <p className="opentext-error" role="alert">{error}</p>
        ) : columns.length === 0 ? (
          <p className="opentext-empty">Nenhuma coluna de texto aberto encontrada.</p>
        ) : (
          <>
            {/* Campo com chips */}
            <div
              id="ms-trigger"
              className={`multiselect-field${menuOpen ? ' multiselect-field--open' : ''}`}
              role="combobox"
              aria-expanded={menuOpen}
              aria-haspopup="listbox"
              aria-labelledby="ms-label"
              tabIndex={0}
              onClick={() => setMenuOpen(v => !v)}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setMenuOpen(v => !v) } }}
            >
              <div className="multiselect-chips">
                {selectedColumns.length === 0 ? (
                  <span className="multiselect-placeholder">Escolha as colunas…</span>
                ) : (
                  selectedColumns.map(c => (
                    <span key={c.original_id} className="multiselect-chip">
                      <span className="multiselect-chip-label">{c.original_id}</span>
                      <button
                        type="button"
                        className="multiselect-chip-remove"
                        aria-label={`Remover ${c.original_id}`}
                        onClick={e => removeChip(c.original_id, e)}
                      >
                        <X size={12} aria-hidden />
                      </button>
                    </span>
                  ))
                )}
              </div>
              <ChevronDown
                size={16}
                className={`multiselect-chevron${menuOpen ? ' multiselect-chevron--open' : ''}`}
                aria-hidden
              />
            </div>

            {/* Menu flutuante */}
            {menuOpen && (
              <div className="multiselect-menu" role="listbox" aria-multiselectable="true">
                {columns.map(c => {
                  const checked = selectedIds.has(c.original_id)
                  return (
                    <label
                      key={c.original_id}
                      className={`multiselect-option${checked ? ' multiselect-option--selected' : ''}`}
                      role="option"
                      aria-selected={checked}
                    >
                      <input
                        type="checkbox"
                        className="multiselect-option-checkbox"
                        checked={checked}
                        onChange={() => toggleColumn(c.original_id)}
                      />
                      <span className={`multiselect-option-check${checked ? ' multiselect-option-check--checked' : ''}`}>
                        {checked && <Check size={12} aria-hidden />}
                      </span>
                      <span className="multiselect-option-body">
                        <span className="multiselect-option-id">{c.original_id}</span>
                        <span className="multiselect-option-text" title={c.question_text}>
                          {label(c)}
                        </span>
                      </span>
                      {c.eligible && (
                        <span className="multiselect-option-badge">Elegível</span>
                      )}
                    </label>
                  )
                })}
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Accordion 1: enunciado completo da análise ── */}
      <div className="accordion">
        <button
          type="button"
          className={`accordion-header${accord1Open ? ' accordion-header--open' : ''}`}
          onClick={() => setAccord1Open(v => !v)}
          aria-expanded={accord1Open}
        >
          <ChevronDown
            size={16}
            className={`accordion-chevron${accord1Open ? ' accordion-chevron--open' : ''}`}
            aria-hidden
          />
          Ver enunciado completo da análise
        </button>
        {accord1Open && (
          <div className="accordion-body animate-in">
            <p className="accordion-analysis-text">{ANALYSIS_DESCRIPTION}</p>
          </div>
        )}
      </div>

      {/* ── Accordion 2: classificação de elegibilidade ── */}
      <div className="accordion">
        <button
          type="button"
          className={`accordion-header${accord2Open ? ' accordion-header--open' : ''}`}
          onClick={() => setAccord2Open(v => !v)}
          aria-expanded={accord2Open}
        >
          <ChevronDown
            size={16}
            className={`accordion-chevron${accord2Open ? ' accordion-chevron--open' : ''}`}
            aria-hidden
          />
          Ver classificação de elegibilidade de todas as colunas open text
          {columns.length > 0 && (
            <span className="accordion-count">({columns.length})</span>
          )}
        </button>
        {accord2Open && (
          <div className="accordion-body animate-in">
            {loading ? (
              <p className="opentext-loading">Carregando…</p>
            ) : (
              <div className="eligibility-list">
                {columns.map(c => (
                  <div key={c.original_id} className="eligibility-row">
                    <div className="eligibility-row-header">
                      <span className="col-id-text">{c.original_id}</span>
                      <span className={`status-badge status-badge--${c.eligible ? 'ok' : 'review'}`}>
                        {c.eligible ? 'Elegível' : 'Não elegível'}
                      </span>
                      <span className="eligibility-score">score {c.score.toFixed(2)}</span>
                    </div>
                    <p className="eligibility-question" title={c.question_text}>{c.question_text}</p>
                    {c.summary && (
                      <p className="eligibility-summary">{c.summary}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── CTA ── */}
      <div className={onBack ? 'step-cta-row--with-back' : 'step-cta-row'}>
        {onBack && (
          <button type="button" className="btn-ghost" onClick={onBack} disabled={continuing}>
            Voltar
          </button>
        )}
        <button
          type="button"
          className="btn-primary"
          onClick={handleContinue}
          disabled={continuing}
        >
          {continuing ? 'Aguarde…' : 'Continuar para exportação'}
          {!continuing && <ArrowRight size={18} aria-hidden />}
        </button>
      </div>
    </div>
  )
}
