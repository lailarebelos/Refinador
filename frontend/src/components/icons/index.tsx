// Set de ícones funcionais — 24×24, currentColor, stroke 1.5px
// Regra: NUNCA misturar com bibliotecas externas (lucide, heroicons etc.)

interface IconProps {
  size?: number
  className?: string
  'aria-hidden'?: boolean
}

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none' as const,
  stroke: 'currentColor' as const,
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
})

export function Sun({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="2" x2="12" y2="4" />
      <line x1="12" y1="20" x2="12" y2="22" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="2" y1="12" x2="4" y2="12" />
      <line x1="20" y1="12" x2="22" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

export function Moon({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

export function Upload({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  )
}

export function Document({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

export function Spreadsheet({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="9" x2="9" y2="21" />
    </svg>
  )
}

export function Check({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

export function AlertTriangle({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

export function Info({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
      <line x1="12" y1="12" x2="12" y2="16" />
    </svg>
  )
}

export function ArrowRight({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

export function Plus({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

export function X({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

export function ChevronDown({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}

export function ChevronRight({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

export function ChevronLeft({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

export function Gear({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function LayoutSidebar({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  )
}

export function Trash({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  )
}

export function Refresh({ size = 24, className, 'aria-hidden': ah }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden={ah}>
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  )
}
