// ── Tipos espelhando os modelos Pydantic do backend ──────────────────────────

export interface SessionStatus {
  step: 1 | 2 | 3 | 4
  has_config: boolean
  classification_confirmed: boolean
  has_result: boolean
  has_download: boolean
}

export interface ConfigRow {
  original_id: string
  short_name: string
  type: string
  subitem: string
  include: boolean
  group: string | null
  revisar?: boolean
  question_text: string
  sample: string
  confidence: 'high' | 'low'
  alternatives: string
}

export interface ConfigStats {
  total: number
  included: number
  open_text: number
  to_review: number
}

export interface ProcessResult {
  config: ConfigRow[]
  stats: ConfigStats
  ai_used: boolean
  base_name: string
}

export interface ConfigResponse {
  config: ConfigRow[]
  stats: ConfigStats
  classification_confirmed: boolean
  valid_types: string[]
}

export interface ConfigRowUpdate {
  original_id: string
  include?: boolean
  group?: string | null
  type?: string
  short_name?: string
  subitem?: string
  revisar?: boolean
}

export interface PatchResponse {
  ok: boolean
  stats: ConfigStats
}

export interface EligibilityColumn {
  original_id: string
  question_text: string
  eligible: boolean
  score: number
  reasons_for: string[]
  reasons_against: string[]
  summary: string
}

export interface EligibilityResponse {
  columns: EligibilityColumn[]
}

export interface NormalizeRequest {
  ai_original_ids: string[]
}

export interface NormalizeResult {
  rows: number
  columns: number
  headers: string[]
}

export interface LLMConfig {
  provider: string | null
  model: string | null
  has_key: boolean
  base_url: string | null
}

export interface LLMConfigUpdate {
  provider?: string
  model?: string
  api_key?: string
  base_url?: string
  persist?: boolean
}

export interface TestResult {
  ok: boolean
  message: string
}

// ── Utilitário de request ─────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { credentials: 'include', ...init })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    let detail = text
    try {
      const json = JSON.parse(text) as { detail?: string }
      if (json.detail) detail = json.detail
    } catch {
      /* mantém text original */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

// ── Cliente tipado ────────────────────────────────────────────────────────────

export const api = {
  session: {
    status: () => request<SessionStatus>('/api/session/status'),
    reset: () => request<{ ok: boolean }>('/api/session', { method: 'DELETE' }),
  },

  process: (qsfFile: File, xlsxFile: File) => {
    const form = new FormData()
    form.append('qsf_file', qsfFile)
    form.append('xlsx_file', xlsxFile)
    return request<ProcessResult>('/api/process', { method: 'POST', body: form })
  },

  config: {
    get: () => request<ConfigResponse>('/api/config'),
    patch: (rows: ConfigRowUpdate[]) =>
      request<PatchResponse>('/api/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows }),
      }),
    confirm: () =>
      request<{ ok: boolean }>('/api/config/confirm', { method: 'POST' }),
  },

  eligibility: {
    get: () => request<EligibilityResponse>('/api/eligibility'),
  },

  normalize: (req: NormalizeRequest) =>
    request<NormalizeResult>('/api/normalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),

  // Retorna Response bruto para o caller gerenciar o blob
  download: () => fetch('/api/download', { credentials: 'include' }),

  llm: {
    get: () => request<LLMConfig>('/api/llm-config'),
    update: (config: LLMConfigUpdate) =>
      request<{ ok: boolean }>('/api/llm-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      }),
    test: (config: LLMConfigUpdate) =>
      request<TestResult>('/api/llm-config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      }),
  },
}
