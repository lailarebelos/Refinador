import { useTheme } from '../../contexts/ThemeContext'
import { THEMED_ASSETS } from '../../brand/assets'
import { Sun, Moon } from '../icons'

export type StatusBadgeState = 'waiting' | 'processing' | 'ready' | 'review'

const STATUS_LABELS: Record<StatusBadgeState, string> = {
  waiting:    'Aguardando arquivos',
  processing: 'Processando',
  ready:      'Pronto para exportar',
  review:     'Revisar classificação',
}

export interface HeaderProps {
  title?: string
  status?: StatusBadgeState
  onHelp?: () => void
  onOpenDrawer?: () => void
}

export default function Header({ title = 'Refinador', status = 'waiting', onHelp, onOpenDrawer }: HeaderProps) {
  const { theme, toggleTheme } = useTheme()
  const assets = THEMED_ASSETS[theme]

  return (
    <header className="header">
      {/* Esquerda: hamburguer (mobile) + título + badge de status */}
      <div className="header-left">
        <button
          className="icon-btn header-hamburger"
          onClick={onOpenDrawer}
          aria-label="Abrir menu de navegação"
          title="Navegação"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <line x1="3" y1="6"  x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <h1 className="header-title">{title}</h1>
        <span className={`status-badge ${status}`} role="status" aria-live="polite">
          {STATUS_LABELS[status]}
        </span>
      </div>

      {/* Direita: tema → compartilhar → ajuda → logo compacto */}
      <div className="header-right">
        {/* Toggle de tema (lua/sol) */}
        <button
          className="icon-btn"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'}
          title={theme === 'light' ? 'Modo escuro' : 'Modo claro'}
        >
          {theme === 'light' ? <Moon size={20} aria-hidden /> : <Sun size={20} aria-hidden />}
        </button>

        {/* Ajuda */}
        <button
          className="icon-btn"
          onClick={onHelp}
          aria-label="Ajuda — como usar"
          title="Como usar"
        >
          <img
            src={assets.iconQuestion}
            alt=""
            aria-hidden
            width={20}
            height={20}
            style={{ objectFit: 'contain' }}
          />
        </button>

        {/* Separador visual */}
        <div style={{ width: 1, height: 24, background: 'var(--lds-color-neutral-border-low)', margin: '0 4px' }} aria-hidden />

        {/* Selo L&CO compacto */}
        <img
          src={assets.logoCompact}
          alt="Localiza&CO"
          className="header-logo"
        />
      </div>
    </header>
  )
}
