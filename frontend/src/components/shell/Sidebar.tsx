import { SIDEBAR_ASSETS } from '../../brand/assets'
import { Check, Gear, LayoutSidebar } from '../icons'

export interface SidebarProps {
  collapsed: boolean
  onCollapse: () => void
  currentStep: 1 | 2 | 3 | 4
  completedSteps: number[]
  onConfigureAI?: () => void
  aiProvider?: string
}

const STEPS = [
  { n: 1, label: 'Upload' },
  { n: 2, label: 'Classificação' },
  { n: 3, label: 'Respostas abertas' },
  { n: 4, label: 'Exportar' },
]

export default function Sidebar({
  collapsed,
  onCollapse,
  currentStep,
  completedSteps,
  onConfigureAI,
  aiProvider,
}: SidebarProps) {
  return (
    <aside
      className="sidebar"
      data-sidebar
      aria-label="Navegação"
      data-collapsed={collapsed}
    >
      {/* Header interno — sidebar é sempre escura; usa variantes "branco-e-citrico" */}
      <div className="sidebar-header">
        {collapsed ? (
          <img
            src={SIDEBAR_ASSETS.logoCompact}
            alt="Localiza&CO"
            className="sidebar-logo-compact"
          />
        ) : (
          <>
            <img
              src={SIDEBAR_ASSETS.logoHorizontal}
              alt="Localiza&CO"
              className="sidebar-logo"
            />
            <button
              className="sidebar-collapse-btn"
              onClick={onCollapse}
              aria-label="Recolher sidebar"
              title="Recolher"
            >
              <LayoutSidebar size={18} aria-hidden />
            </button>
          </>
        )}
      </div>

      {/* Botão de expandir — só aparece quando colapsado, em linha própria centralizada */}
      {collapsed && (
        <div className="sidebar-expand-row">
          <button
            className="sidebar-collapse-btn"
            onClick={onCollapse}
            aria-label="Expandir sidebar"
            title="Expandir"
          >
            <LayoutSidebar size={18} aria-hidden />
          </button>
        </div>
      )}

      <div className="sidebar-divider" />

      {/* Scroll content */}
      <div className="sidebar-scroll">
        {/* Label de seção */}
        {!collapsed && (
          <div className="sidebar-section-label">Progresso</div>
        )}

        {/* Stepper vertical */}
        <nav className="stepper" aria-label="Etapas">
          {STEPS.map((step, idx) => {
            const isCompleted = completedSteps.includes(step.n)
            const isActive = currentStep === step.n
            const prevCompleted = idx > 0 && completedSteps.includes(STEPS[idx - 1].n)

            return (
              <div key={step.n}>
                {/* Conector entre etapas */}
                {idx > 0 && (
                  <div className={`step-connector${prevCompleted ? ' completed' : ''}`} />
                )}

                {/* Item da etapa */}
                <div
                  className={[
                    'step-item',
                    isActive ? 'active' : '',
                    isCompleted ? 'completed' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  aria-current={isActive ? 'step' : undefined}
                  title={collapsed ? step.label : undefined}
                >
                  <div
                    className={`step-circle ${
                      isCompleted ? 'completed' : isActive ? 'active' : 'pending'
                    }`}
                    aria-hidden
                  >
                    {isCompleted ? <Check size={14} aria-hidden /> : step.n}
                  </div>
                  {!collapsed && (
                    <span className="step-label">{step.label}</span>
                  )}
                </div>
              </div>
            )
          })}
        </nav>
      </div>

      {/* Rodapé */}
      <footer className="sidebar-footer">
        {aiProvider && (
          <div className="sidebar-ai-badge" title="IA: Claude">
            <span className="sidebar-ai-badge-dot" aria-hidden />
            {!collapsed && (
              <span className="sidebar-footer-text">IA: Claude</span>
            )}
          </div>
        )}
        <button
          className="sidebar-configure-btn"
          onClick={onConfigureAI}
          title="Configurar IA"
        >
          <Gear size={16} aria-hidden />
          {!collapsed && (
            <span className="sidebar-footer-text">Configurar IA</span>
          )}
        </button>
      </footer>
    </aside>
  )
}
