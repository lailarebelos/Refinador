import { useState, useEffect, useRef } from 'react'
import Hero from './Hero'
import Dropzone from './Dropzone'
import { api, ApiError, ProcessResult } from '../../api/client'

interface UploadStepProps {
  onBothFiles?: (qsf: File, xlsx: File, result: ProcessResult) => void
}

export default function UploadStep({ onBothFiles }: UploadStepProps) {
  const [qsfFile, setQsfFile] = useState<File | null>(null)
  const [xlsxFile, setXlsxFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onBothFilesRef = useRef(onBothFiles)
  useEffect(() => { onBothFilesRef.current = onBothFiles })

  useEffect(() => {
    if (!qsfFile || !xlsxFile) return
    let cancelled = false

    setLoading(true)
    setError(null)

    api.process(qsfFile, xlsxFile)
      .then((result) => {
        if (cancelled) return
        setLoading(false)
        onBothFilesRef.current?.(qsfFile, xlsxFile, result)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoading(false)
        setError(err instanceof ApiError ? err.message : 'Erro ao processar arquivos.')
      })

    return () => { cancelled = true }
  }, [qsfFile, xlsxFile])

  return (
    <div className="upload-step animate-in">
      <Hero />

      <div className="step-section-header">
        <p className="step-micro-label">Etapa 1 — Upload</p>
        <h2 className="step-section-title">Upload dos arquivos</h2>
        <p className="step-instruction">
          Exporte do Qualtrics o questionário (.qsf) e os dados numéricos
          (.xlsx). Ambos são necessários para continuar.
        </p>
      </div>

      <div className="dropzone-grid">
        <Dropzone
          title="Questionário"
          extension=".qsf"
          formatHint="Apenas .qsf • até 200 MB"
          icon="document"
          accept=".qsf"
          onFile={setQsfFile}
          file={qsfFile}
          onRemove={() => setQsfFile(null)}
        />
        <Dropzone
          title="Dados numéricos"
          extension=".xlsx"
          formatHint="Apenas .xlsx • até 200 MB"
          icon="spreadsheet"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onFile={setXlsxFile}
          file={xlsxFile}
          onRemove={() => setXlsxFile(null)}
        />
      </div>

      {loading && (
        <div className="upload-processing-card" role="status" aria-live="polite">
          <div className="upload-processing-dots" aria-hidden="true">
            <span className="upload-dot" style={{ animationDelay: '0s' }} />
            <span className="upload-dot" style={{ animationDelay: '0.20s' }} />
            <span className="upload-dot" style={{ animationDelay: '0.40s' }} />
          </div>
          <p className="upload-processing-label text-shimmer">Processando arquivos…</p>
          <p className="upload-processing-sub">Isso pode levar alguns segundos.</p>
        </div>
      )}
      {error && (
        <p className="upload-status upload-status--error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
