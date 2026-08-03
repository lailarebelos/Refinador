import { Document, Spreadsheet, Plus } from '../icons'
import '../../styles/wizard.css'

export default function Hero() {
  return (
    <div className="hero-card">
      {/* Texto principal */}
      <div className="hero-body">
        <h2 className="hero-title">
          Transforme exports do Qualtrics em planilhas{' '}
          <span className="hero-accent">prontas para análise.</span>
        </h2>
        <p className="hero-subtitle">
          Envie o questionário e os dados numéricos e gere uma planilha
          normalizada, organizada e pronta para uso.
        </p>
      </div>

      {/* Fluxo .qsf → .xlsx — decorativo, não compete com o título */}
      <div className="hero-flow" aria-hidden>
        <div className="hero-flow-item">
          <Document size={28} />
          <span>.qsf</span>
        </div>
        <Plus size={20} className="hero-flow-arrow" />
        <div className="hero-flow-item">
          <Spreadsheet size={28} />
          <span>.xlsx</span>
        </div>
      </div>
    </div>
  )
}
