import { useState, useEffect, type ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header, { type StatusBadgeState } from './Header'
import '../../styles/shell.css'

const SIDEBAR_KEY = 'normalizer:sidebar_collapsed'

interface AppShellProps {
  currentStep: 1 | 2 | 3 | 4
  completedSteps: number[]
  title?: string
  status?: StatusBadgeState
  aiProvider?: string
  hasContent?: boolean
  onConfigureAI?: () => void
  onHelp?: () => void
  children: ReactNode
}

export default function AppShell({
  currentStep,
  completedSteps,
  title,
  status,
  aiProvider,
  hasContent = false,
  onConfigureAI,
  onHelp,
  children,
}: AppShellProps) {
  const [collapsed,   setCollapsed]   = useState<boolean>(() => {
    return localStorage.getItem(SIDEBAR_KEY) === 'true'
  })
  const [drawerOpen,  setDrawerOpen]  = useState(false)

  const handleCollapse = () => {
    setCollapsed(c => {
      const next = !c
      localStorage.setItem(SIDEBAR_KEY, String(next))
      return next
    })
  }

  // Fecha o drawer ao redimensionar acima do breakpoint mobile
  useEffect(() => {
    const close = () => { if (window.innerWidth >= 768) setDrawerOpen(false) }
    window.addEventListener('resize', close)
    return () => window.removeEventListener('resize', close)
  }, [])

  const shellClass = [
    'app-shell',
    collapsed   ? 'sidebar-collapsed' : '',
    drawerOpen  ? 'drawer-open'        : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={shellClass} aria-label="Refinador">
      {/* Overlay do drawer (só em mobile) */}
      <div
        className="drawer-overlay"
        aria-hidden
        onClick={() => setDrawerOpen(false)}
      />

      <Sidebar
        collapsed={collapsed}
        onCollapse={handleCollapse}
        currentStep={currentStep}
        completedSteps={completedSteps}
        onConfigureAI={onConfigureAI}
        aiProvider={aiProvider}
      />

      <div className="main-area">
        <Header title={title} status={status} onHelp={onHelp} onOpenDrawer={() => setDrawerOpen(true)} />

        <main className="content-area">
          <div className="content-column">
            {children}
          </div>

          {/* Marca-d'água "&" sangrando a borda direita (§7.4) */}
          <img
            src="/brand/grafismos/grafismo-ampersand-contorno-citrico.svg"
            alt=""
            aria-hidden
            className={`watermark${hasContent ? ' has-content' : ''}`}
          />
        </main>
      </div>
    </div>
  )
}
