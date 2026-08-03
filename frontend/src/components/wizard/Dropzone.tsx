import { useRef, useState } from 'react'
import { Upload, Document, Spreadsheet, X } from '../icons'

interface DropzoneProps {
  /** Título da coluna: "Questionário" ou "Dados numéricos" */
  title: string
  /** Chip de extensão: ".qsf" ou ".xlsx" */
  extension: string
  /** Hint de formato abaixo do texto principal: "Apenas .qsf • até 200MB" */
  formatHint: string
  /** Ícone do tipo de arquivo: 'document' para .qsf, 'spreadsheet' para .xlsx */
  icon: 'document' | 'spreadsheet'
  /** Atributo accept do input oculto: ".qsf" ou ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" */
  accept: string
  /** Callback chamado quando o usuário seleciona ou solta um arquivo */
  onFile?: (file: File) => void
  /** Arquivo atualmente selecionado — exibe chip quando presente */
  file?: File | null
  /** Callback para remover o arquivo selecionado */
  onRemove?: () => void
}

export default function Dropzone({
  title,
  extension,
  formatHint,
  icon,
  accept,
  onFile,
  file,
  onRemove,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const TypeIcon = icon === 'document' ? Document : Spreadsheet

  /* ── Handlers ─────────────────────────────────────────────────────────── */
  const openPicker = () => inputRef.current?.click()

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openPicker()
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onFile?.(file)
    e.target.value = '' // permite re-selecionar o mesmo arquivo
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    // só sai do drag-over se o cursor deixou o elemento (não um filho)
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setDragOver(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile?.(file)
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="dropzone-wrapper">
      {/* Cabeçalho da coluna: ícone + título + chip de extensão */}
      <div className="dropzone-col-header">
        <TypeIcon size={20} aria-hidden />
        <span className="dropzone-col-title">{title}</span>
        <span className="dropzone-ext-chip">{extension}</span>
      </div>

      {/* Input de arquivo oculto */}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        aria-hidden
        style={{ display: 'none' }}
        tabIndex={-1}
      />

      {file ? (
        /* Chip de arquivo selecionado */
        <div className="dropzone dropzone--filled" role="status" aria-live="polite">
          <TypeIcon size={32} className="dropzone-upload-icon" aria-hidden />
          <p className="dropzone-text-primary dropzone-filename">{file.name}</p>
          <p className="dropzone-text-hint">{formatSize(file.size)}</p>
          <button
            type="button"
            className="dropzone-remove-btn"
            onClick={(e) => { e.stopPropagation(); onRemove?.() }}
            aria-label={`Remover ${file.name}`}
          >
            <X size={14} aria-hidden /> Remover
          </button>
        </div>
      ) : (
        /* Zona de drop — estado vazio */
        <div
          className={`dropzone${dragOver ? ' drag-over' : ''}`}
          role="button"
          tabIndex={0}
          aria-label={`Selecionar arquivo ${title} (${extension})`}
          onClick={openPicker}
          onKeyDown={handleKeyDown}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload size={40} className="dropzone-upload-icon" aria-hidden />
          <p className="dropzone-text-primary">
            <span className="dropzone-text-emphasis">Clique para selecionar</span>{' '}
            ou arraste o arquivo aqui
          </p>
          <p className="dropzone-text-hint">{formatHint}</p>
        </div>
      )}
    </div>
  )
}
