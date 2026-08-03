import { useState } from 'react'
import type { ProcessResult, ConfigRow, ConfigStats } from '../../api/client'
import { api, ApiError } from '../../api/client'
import { Check, ChevronDown, ArrowRight, AlertTriangle, X } from '../icons'

const TYPE_PT: Record<string, string> = {
  single_choice:   'Escolha única',
  multiple_choice: 'Escolha múltipla',
  dichotomous:     'Dicotômica',
  likert:          'Escala Likert',
  ranking:         'Ranking',
  nps:             'NPS',
  open_text:       'Campo aberto',
  numeric:         'Quantitativa',
  date:            'Data',
  metadata:        'Metadado externo',
}

const VALID_TYPES = Object.keys(TYPE_PT)

type Filter = 'all' | 'review' | 'included' | 'excluded' | 'open_text'
type EditingCell = { id: string; field: 'type' | 'short_name' } | null

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all',       label: 'Todas' },
  { key: 'review',    label: 'Para revisar' },
  { key: 'included',  label: 'Incluídas' },
  { key: 'excluded',  label: 'Excluídas' },
  { key: 'open_text', label: 'Texto livre' },
]

interface ClassificationStepProps {
  result: ProcessResult
  onNext: () => void
  onBack?: () => void
}

export default function ClassificationStep({ result, onNext, onBack }: ClassificationStepProps) {
  const [filter,        setFilter]       = useState<Filter>('all')
  const [rows,          setRows]         = useState<ConfigRow[]>(result.config)
  const [localStats,    setLocalStats]   = useState<ConfigStats>(result.stats)
  const [editingCell,   setEditingCell]  = useState<EditingCell>(null)
  const [draftValue,    setDraftValue]   = useState('')
  const [accordionOpen, setAccordionOpen] = useState(false)
  const [continuing,    setContinuing]   = useState(false)
  const [patchError,    setPatchError]   = useState<string | null>(null)
  const [continueError, setContinueError] = useState<string | null>(null)

  // ── Patch helper — atualiza stats com a resposta do backend ────────────────
  async function patch(updates: Parameters<typeof api.config.patch>[0]) {
    setPatchError(null)
    try {
      const res = await api.config.patch(updates)
      setLocalStats(res.stats)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erro ao salvar alteração. Verifique se o backend está acessível.'
      setPatchError(msg)
      throw err // re-lança para o caller (ex: revert do checkbox)
    }
  }

  // ── Checkbox Incluir ───────────────────────────────────────────────────────
  function handleToggleInclude(row: ConfigRow) {
    const next = !row.include
    // Atualização otimista
    setRows(prev =>
      prev.map(r => r.original_id === row.original_id ? { ...r, include: next } : r)
    )
    patch([{ original_id: row.original_id, include: next }]).catch(() => {
      // Reverte se o backend rejeitar
      setRows(prev =>
        prev.map(r => r.original_id === row.original_id ? { ...r, include: row.include } : r)
      )
    })
  }

  // ── Tipo (select) ──────────────────────────────────────────────────────────
  function handleTypeChange(row: ConfigRow, newType: string) {
    setRows(prev =>
      prev.map(r => r.original_id === row.original_id ? { ...r, type: newType } : r)
    )
    setEditingCell(null)
    patch([{ original_id: row.original_id, type: newType }])
  }

  // ── Rótulo (input) ─────────────────────────────────────────────────────────
  function startEditing(id: string, field: 'type' | 'short_name', current: string) {
    setEditingCell({ id, field })
    setDraftValue(current)
  }

  function handleRotuloBlur(row: ConfigRow) {
    const trimmed = draftValue.trim()
    if (trimmed && trimmed !== row.short_name) {
      setRows(prev =>
        prev.map(r => r.original_id === row.original_id ? { ...r, short_name: trimmed } : r)
      )
      patch([{ original_id: row.original_id, short_name: trimmed }])
    }
    setEditingCell(null)
  }

  // ── Continuar (confirma config + avança stepper) ──────────────────────────
  async function handleContinue() {
    setContinuing(true)
    setContinueError(null)
    try {
      await api.config.confirm()
      onNext()
    } catch (err) {
      setContinueError(err instanceof ApiError ? err.message : 'Erro ao confirmar. Verifique se o backend está acessível.')
      setContinuing(false)
    }
  }

  // ── Dados derivados ────────────────────────────────────────────────────────
  const statCards = [
    { label: 'TOTAL',        value: localStats.total,     highlight: false },
    { label: 'INCLUÍDAS',    value: localStats.included,  highlight: false },
    { label: 'TEXTO LIVRE',  value: localStats.open_text, highlight: false },
    { label: 'PARA REVISAR', value: localStats.to_review, highlight: localStats.to_review > 0 },
  ]

  const filteredRows = rows.filter(row => {
    switch (filter) {
      case 'review':    return row.confidence === 'low'
      case 'included':  return row.include
      case 'excluded':  return !row.include
      case 'open_text': return row.type === 'open_text'
      default:          return true
    }
  })

  return (
    <div className="classification-step animate-in">
      <div className="step-section-header">
        <p className="step-micro-label">Etapa 2 — Classificação</p>
        <h2 className="step-section-title">Classificação das colunas</h2>
        <p className="step-instruction">
          Revise e edite. Desmarque "Incluir" para ignorar colunas. Ajuste tipo e rótulo
          conforme necessário.
        </p>
      </div>

      <div className="stat-cards-grid">
        {statCards.map(({ label, value, highlight }) => (
          <div
            key={label}
            className={`stat-card${highlight ? ' stat-card--highlight' : ''}`}
          >
            <p className="stat-card-label">{label}</p>
            <p className="stat-card-number">{value}</p>
          </div>
        ))}
      </div>

      {/* Banner de erro de patch (salvar edições) */}
      {patchError && (
        <div className="step-error-banner" role="alert">
          <AlertTriangle size={16} aria-hidden />
          <span>{patchError}</span>
          <button type="button" className="step-error-dismiss" onClick={() => setPatchError(null)} aria-label="Fechar">
            <X size={14} aria-hidden />
          </button>
        </div>
      )}

      <div className="filter-pills-row">
        <span className="filter-pills-label">Filtrar:</span>
        <div className="filter-pills" role="group" aria-label="Filtrar colunas">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className={`filter-pill${filter === key ? ' filter-pill--active' : ''}`}
              onClick={() => setFilter(key)}
              aria-pressed={filter === key}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="col-table-wrap">
        <div className="col-table-scroll">
          <table className="col-table" aria-label="Classificação das colunas do questionário">
            <thead>
              <tr>
                <th scope="col" className="col-th col-th--status">Status</th>
                <th scope="col" className="col-th col-th--include">Incluir</th>
                <th scope="col" className="col-th col-th--id">ID Qualtrics</th>
                <th scope="col" className="col-th col-th--pergunta">Pergunta</th>
                <th scope="col" className="col-th col-th--tipo">Tipo</th>
                <th scope="col" className="col-th col-th--rotulo">Rótulo</th>
                <th scope="col" className="col-th col-th--sample">Amostras</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, i) => {
                const isReview    = row.confidence === 'low'
                const editingType = editingCell?.id === row.original_id && editingCell.field === 'type'
                const editingRot  = editingCell?.id === row.original_id && editingCell.field === 'short_name'

                return (
                  <tr
                    key={row.original_id}
                    className={`col-tr${i % 2 === 1 ? ' col-tr--alt' : ''}`}
                  >
                    {/* Status */}
                    <td className="col-td col-td--status">
                      <span className={`status-badge status-badge--${isReview ? 'review' : 'ok'}`}>
                        {isReview ? 'Revisar' : 'OK'}
                      </span>
                    </td>

                    {/* Incluir — checkbox interativo */}
                    <td className="col-td col-td--include">
                      <button
                        type="button"
                        className={`col-checkbox${row.include ? ' col-checkbox--checked' : ''}`}
                        onClick={() => handleToggleInclude(row)}
                        aria-label={row.include ? 'Excluir coluna da exportação' : 'Incluir coluna na exportação'}
                        aria-pressed={row.include}
                      >
                        {row.include && <Check size={12} aria-hidden />}
                      </button>
                    </td>

                    {/* ID */}
                    <td className="col-td col-td--id">
                      <span className="col-id-text">{row.original_id}</span>
                    </td>

                    {/* Pergunta truncada */}
                    <td className="col-td col-td--pergunta">
                      <span className="col-pergunta-text" title={row.question_text}>
                        {row.question_text}
                      </span>
                    </td>

                    {/* Tipo — select inline */}
                    <td className="col-td col-td--editable">
                      {editingType ? (
                        <select
                          className="col-select"
                          value={row.type}
                          autoFocus
                          aria-label={`Tipo da coluna ${row.original_id}`}
                          onChange={e => handleTypeChange(row, e.target.value)}
                          onBlur={() => setEditingCell(null)}
                        >
                          {VALID_TYPES.map(t => (
                            <option key={t} value={t}>{TYPE_PT[t]}</option>
                          ))}
                        </select>
                      ) : (
                        <button
                          type="button"
                          className="col-editable-trigger"
                          onClick={() => startEditing(row.original_id, 'type', row.type)}
                          aria-label={`Editar tipo da coluna ${row.original_id}`}
                        >
                          <span className="col-editable-text">{TYPE_PT[row.type] ?? row.type}</span>
                          <ChevronDown size={14} className="col-edit-chevron" aria-hidden />
                        </button>
                      )}
                    </td>

                    {/* Rótulo — input inline */}
                    <td className="col-td col-td--editable">
                      {editingRot ? (
                        <input
                          className="col-input"
                          type="text"
                          value={draftValue}
                          autoFocus
                          aria-label={`Rótulo da coluna ${row.original_id}`}
                          onChange={e => setDraftValue(e.target.value)}
                          onBlur={() => handleRotuloBlur(row)}
                          onKeyDown={e => {
                            if (e.key === 'Enter')  (e.target as HTMLInputElement).blur()
                            if (e.key === 'Escape') setEditingCell(null)
                          }}
                        />
                      ) : (
                        <button
                          type="button"
                          className="col-editable-trigger"
                          onClick={() => startEditing(row.original_id, 'short_name', row.short_name)}
                          aria-label={`Editar rótulo da coluna ${row.original_id}`}
                        >
                          <span className="col-editable-text">{row.short_name}</span>
                        </button>
                      )}
                    </td>

                    {/* Amostras */}
                    <td className="col-td col-td--sample">
                      <span className="col-sample-text" title={row.sample}>
                        {row.sample}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {filteredRows.length === 0 && (
          <p className="col-table-empty">
            Nenhuma coluna corresponde ao filtro selecionado.
          </p>
        )}
      </div>

      {/* ── Accordion "Ver enunciado completo" (§9.6) ── */}
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
          Ver enunciado completo
          <span className="accordion-count">({filteredRows.length})</span>
        </button>

        {accordionOpen && (
          <div className="accordion-body animate-in">
            <dl className="accordion-question-list">
              {filteredRows.map(row => (
                <div key={row.original_id} className="accordion-question-item">
                  <dt className="accordion-question-id">{row.original_id}</dt>
                  <dd className="accordion-question-text">{row.question_text}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      {/* Banner de erro ao confirmar */}
      {continueError && (
        <div className="step-error-banner" role="alert">
          <AlertTriangle size={16} aria-hidden />
          <span>{continueError}</span>
          <button type="button" className="step-error-dismiss" onClick={() => setContinueError(null)} aria-label="Fechar">
            <X size={14} aria-hidden />
          </button>
        </div>
      )}

      {/* ── Botão Continuar (§7.11) ── */}
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
          {continuing ? 'Confirmando…' : 'Continuar para análise de respostas abertas'}
          {!continuing && <ArrowRight size={18} aria-hidden />}
        </button>
      </div>
    </div>
  )
}
