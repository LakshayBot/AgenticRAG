import type { ApiError, AuthResponse, Conversation, ConversationDetail } from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// ─── Token helpers ────────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('accessToken')
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('refreshToken')
}

export function setTokens(accessToken: string, refreshToken: string, expiresAt: string): void {
  localStorage.setItem('accessToken', accessToken)
  localStorage.setItem('refreshToken', refreshToken)
  localStorage.setItem('tokenExpiresAt', expiresAt)
}

export function clearTokens(): void {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
  localStorage.removeItem('tokenExpiresAt')
}

export function isTokenExpired(): boolean {
  const expiresAt = localStorage.getItem('tokenExpiresAt')
  if (!expiresAt) return true
  return new Date(expiresAt) < new Date(Date.now() + 30_000) // 30s buffer
}

// ─── JWT decode (no verification — client-side only) ─────────────────────────

export function decodeJwt<T = Record<string, unknown>>(token: string): T | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as T
  } catch {
    return null
  }
}

// ─── Refresh token flow ───────────────────────────────────────────────────────

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) throw new Error('No refresh token')

    const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })

    if (!res.ok) {
      clearTokens()
      window.location.href = '/login'
      throw new Error('Refresh failed')
    }

    const data: AuthResponse = await res.json()
    setTokens(data.accessToken, data.refreshToken, data.expiresAt)
    return data.accessToken
  })()

  try {
    return await refreshPromise
  } finally {
    refreshPromise = null
  }
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

interface FetchOptions extends RequestInit {
  skipAuth?: boolean
}

export async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, headers: extraHeaders, ...rest } = options

  let token = getAccessToken()

  // Proactively refresh if near expiry
  if (!skipAuth && token && isTokenExpired()) {
    try {
      token = await refreshAccessToken()
    } catch {
      throw new ApiClientError('Unauthorized', 401)
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  }

  if (!skipAuth && token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...rest, headers })

  // Auto-retry once on 401 after fresh token
  if (res.status === 401 && !skipAuth) {
    try {
      token = await refreshAccessToken()
      headers['Authorization'] = `Bearer ${token}`
      const retried = await fetch(`${BASE_URL}${path}`, { ...rest, headers })
      if (!retried.ok) await throwApiError(retried)
      if (retried.status === 204) return undefined as T
      return retried.json() as Promise<T>
    } catch (err) {
      if (err instanceof ApiClientError) throw err
      throw new ApiClientError('Unauthorized', 401)
    }
  }

  if (!res.ok) await throwApiError(res)
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

async function throwApiError(res: Response): Promise<never> {
  let body: ApiError = {}
  try {
    body = await res.json()
  } catch {
    // ignore
  }
  throw new ApiClientError(
    body.message ?? body.title ?? `Request failed: ${res.status}`,
    res.status,
    body
  )
}

export class ApiClientError extends Error {
  readonly status: number
  readonly body?: ApiError

  constructor(message: string, status: number, body?: ApiError) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.body = body
  }
}

// ─── Streaming fetch (returns Response for SSE) ───────────────────────────────

export async function apiStream(
  path: string,
  body: unknown
): Promise<Response> {
  let token = getAccessToken()

  if (token && isTokenExpired()) {
    token = await refreshAccessToken()
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) await throwApiError(res)
  return res
}

// ─── Convenience methods ──────────────────────────────────────────────────────

// ─── Analytics Types ──────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  totalQueries: number
  avgResponseTimeMs: number
  cacheHitRate: number
  totalAdvisories: number
  indexedAdvisories: number
  totalUsers?: number
  activeUsers?: number
  uniqueQueryingUsers?: number
}

export interface TimelinePoint {
  date: string
  count: number
}

export interface ResponseTimeStats {
  searchType: string
  avgMs: number
  p95Ms: number
  minMs: number
  maxMs: number
  count: number
}

export interface TypeBreakdown {
  type: string
  count: number
}

export interface TopQuestion {
  question: string
  count: number
  avgResponseMs: number
}

export interface CachePoint {
  date: string
  cached: number
  uncached: number
}

export interface EcosystemCount {
  ecosystem: string
  count: number
}

export interface CvssDistributionItem {
  range: string
  min: number
  max: number
  count: number
}

export interface CweCount {
  cweId: string
  count: number
}

export interface TrendingAdvisory {
  ghsaId: string
  queryCount: number
  severity: string
  summary: string
}

export interface AdvisoryChunkCount {
  ghsaId: string
  chunkCount: number
}

export interface AdvisoryChunkCountsResult {
  counts: AdvisoryChunkCount[]
  totalAdvisories: number
  totalChunks: number
}

// ─── Analytics API helpers ────────────────────────────────────────────────────

export const analyticsApi = {
  overview: () =>
    apiFetch<AnalyticsOverview>('/api/analytics/overview'),
  queryTimeline: (days = 30) =>
    apiFetch<TimelinePoint[]>(`/api/analytics/queries/timeline?days=${days}`),
  responseTimes: () =>
    apiFetch<ResponseTimeStats[]>('/api/analytics/queries/response-times'),
  queryByType: () =>
    apiFetch<TypeBreakdown[]>('/api/analytics/queries/by-type'),
  topQuestions: (limit = 20) =>
    apiFetch<TopQuestion[]>(`/api/analytics/queries/top?limit=${limit}`),
  cachePerformance: (days = 30) =>
    apiFetch<CachePoint[]>(`/api/analytics/queries/cache-performance?days=${days}`),
  advisoryTimeline: (months = 12) =>
    apiFetch<TimelinePoint[]>(`/api/analytics/advisories/timeline?months=${months}`),
  ecosystems: (limit = 15) =>
    apiFetch<EcosystemCount[]>(`/api/analytics/advisories/ecosystems?limit=${limit}`),
  cvssDistribution: () =>
    apiFetch<CvssDistributionItem[]>('/api/analytics/advisories/cvss-distribution'),
  cweBreakdown: (limit = 15) =>
    apiFetch<CweCount[]>(`/api/analytics/advisories/cwe-breakdown?limit=${limit}`),
  trendingAdvisories: (limit = 10) =>
    apiFetch<TrendingAdvisory[]>(`/api/analytics/advisories/trending?limit=${limit}`),
  chunksPerAdvisory: (limit = 30) =>
    apiFetch<AdvisoryChunkCountsResult>(`/api/analytics/chunks/per-advisory?limit=${limit}`),
}

export const api = {
  get: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { method: 'GET', ...opts }),

  post: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  patch: <T>(path: string, body?: unknown, opts?: FetchOptions) =>
    apiFetch<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  delete: <T>(path: string, opts?: FetchOptions) =>
    apiFetch<T>(path, { method: 'DELETE', ...opts }),
}

export const conversationsApi = {
  list: () =>
    api.get<Conversation[]>('/api/conversations'),

  create: () =>
    api.post<Conversation>('/api/conversations'),

  get: (id: string) =>
    api.get<ConversationDetail>(`/api/conversations/${id}`),

  rename: (id: string, title: string) =>
    api.patch<Conversation>(`/api/conversations/${id}`, { title }),

  delete: (id: string) =>
    api.delete<void>(`/api/conversations/${id}`),
}
