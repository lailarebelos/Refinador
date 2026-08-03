import { useEffect, useRef } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { THEMED_ASSETS } from '../../brand/assets'
import { X } from '../icons'

interface HelpModalProps {
  onClose: () => void
}

const STEPS = [
  {
    n: 1,
    icon: '/brand/icones/passo1-enviar-nuvem-v3.svg',
    title: 'Envie os dois arquivos do Qualtrics',
    desc: 'Faça upload do questionário (.qsf) e dos dados (.xlsx) exportados do Qualtrics.',
  },
  {
    n: 2,
    icon: '/brand/icones/passo2-revisar-checklist-v2.svg',
    title: 'Revise a classificação das colunas',
    desc: 'Ajuste tipo e rótulo; desmarque "Incluir" nas colunas que não devem ir para a planilha.',
  },
  {
    n: 3,
    icon: '/brand/icones/passo3-analisar-chatduplo-v2.svg',
    title: 'Analise respostas abertas (opcional)',
    desc: 'Selecione colunas com texto opinativo para análise de sentimento e categorias por IA.',
  },
  {
    n: 4,
    icon: '/brand/icones/passo4-baixar-exportar-v2.svg',
    title: 'Normalize e baixe',
    desc: 'Gere e baixe a planilha normalizada com as abas data e codebook.',
  },
]

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function HelpModal({ onClose }: HelpModalProps) {
  const { theme } = useTheme()
  const assets = THEMED_ASSETS[theme]
  const dialogRef = useRef<HTMLDivElement>(null)

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

  return (
    <div
      className="modal-overlay modal-overlay--help"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className="modal-card modal-card--help"
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-modal-title"
      >
        {/* Cabeçalho */}
        <div className="modal-header">
          <img src={assets.logoHorizontal} alt="Localiza&CO" className="modal-logo" />
          <button className="modal-close" onClick={onClose} aria-label="Fechar">
            <X size={18} aria-hidden />
          </button>
        </div>

        {/* Corpo */}
        <div className="modal-body">
          <h2 className="modal-title" id="help-modal-title">Como usar o Refinador</h2>

          <ol className="help-steps" aria-label="Passos de uso">
            {STEPS.map(step => (
              <li key={step.n} className="help-step" data-step={step.n}>
                <div className="help-step-circle" aria-hidden="true">{step.n}</div>
                <div className="help-step-icon-box" aria-hidden="true">
                  <img src={step.icon} alt="" className="help-step-icon" />
                </div>
                <div className="help-step-content">
                  <strong className="help-step-title">{step.title}</strong>
                  <p className="help-step-desc">{step.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        {/* Rodapé */}
        <div className="modal-footer">
          <button className="btn-primary btn-primary--full" onClick={onClose}>
            Entendi
          </button>
        </div>
      </div>
    </div>
  )
}
