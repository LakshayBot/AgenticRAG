// ─── All TypeScript types derived from FRONTEND_INTEGRATION_GUIDE.md ───────

export interface UserDto {
  id: string
  email: string
  firstName?: string
  lastName?: string
  role: 'user' | 'admin'
  createdAt: string
}

export interface AuthResponse {
  accessToken: string
  refreshToken: string
  expiresAt: string
  user: UserDto
}

// ─── RAG ─────────────────────────────────────────────────────────────────────

export interface SourceDocument {
  sourceId: string
  title: string
  authors?: string
  chunkText?: string
  chunkIndex: number
  score: number
}

export interface RAGResponse {
  question: string
  answer: string
  sources: SourceDocument[]
  chunksUsed: number
  searchMode: 'hybrid' | 'bm25' | 'vector'
  reasoningSteps: string[] | null
  responseTimeMs: number
  fromCache: boolean
}

export interface RAGRequest {
  question: string
  topK?: number
  useHybrid?: boolean
  useAgentic?: boolean
  model?: string
  advisoryId?: string
}

// ─── Search ──────────────────────────────────────────────────────────────────

export interface SearchResult {
  id: string
  sourceId: string
  title: string
  abstract?: string
  authors?: string
  publishedDate?: string
  score: number
  snippet?: string
  chunkText?: string
  chunkIndex?: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  totalResults: number
  searchType: 'hybrid' | 'bm25' | 'vector'
  queryTimeMs: number
}

export interface SearchRequest {
  query: string
  topK?: number
  useHybrid?: boolean
  category?: string
  dateFrom?: string
  dateTo?: string
}

// ─── Advisories ───────────────────────────────────────────────────────────────

export interface Advisory {
  id: string
  ghsaId: string
  cveId?: string
  summary: string
  description?: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  cvssScore?: number
  type?: string
  affectedEcosystems?: string[]
  affectedPackages?: string[]
  vulnerabilities?: object[]
  cweIds?: string[]
  cwes?: object[]
  referenceUrls?: string[]
  githubUrl?: string
  publishedAt?: string
  updatedAt?: string
  withdrawnAt?: string
  indexed: boolean
  indexedAt?: string
  createdAt: string
  modifiedAt?: string
}

export interface AdvisorySummary {
  ghsaId: string
  severity: string
  summary: string
  publishedAt?: string
}

export interface AdvisoryStats {
  totalAdvisories: number
  severityBreakdown: Record<string, number>
  recentAdvisories: AdvisorySummary[]
}

export interface AdvisoryAskRequest {
  query: string
  useHybrid?: boolean
  topK?: number
}

export interface AdvisoryAskResponse {
  query: string
  answer: string
  sources: string[]
  chunksUsed: number
  searchMode: string
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export interface ServiceHealth {
  name: string
  healthy: boolean
  responseTimeMs: number
  errorMessage?: string
}

export interface SystemStatsResponse {
  database: {
    totalUsers: number
    totalAdvisories: number
    totalUploadedFiles: number
    totalSearches: number
  }
  search: {
    todaySearches: number
    averageResponseTimeMs: number
    searchTypeDistribution: Record<string, number>
  }
  cache: {
    totalKeys: number
    usedMemoryBytes: number
    hitRate: number
  }
  services: {
    pythonServices: Record<string, ServiceHealth>
    databaseHealthy: boolean
    cacheHealthy: boolean
  }
}

export interface UserAdminDto {
  id: string
  email: string
  firstName?: string
  lastName?: string
  role: 'user' | 'admin'
  isActive: boolean
  createdAt: string
  lastLoginAt?: string
  uploadCount: number
  searchCount: number
}

export interface AdminUsersResponse {
  users: UserAdminDto[]
  totalCount: number
}

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export interface RecurringJobInfo {
  id: string
  cron: string
  nextExecution?: string
  lastExecution?: string
  lastJobState?: string
  lastJobId?: string
  queue?: string
  error?: string
}

export interface RecentJobInfo {
  jobId: string
  state: string
  succeededAt?: string
}

export interface JobsStatusResponse {
  queued: number
  scheduled: number
  processing: number
  succeeded: number
  failed: number
  recurringJobs: RecurringJobInfo[]
  recentSucceeded: RecentJobInfo[]
}

// ─── SSE Streaming ────────────────────────────────────────────────────────────

export interface StreamMetadataEvent {
  sources: SourceDocument[]
  chunksUsed: number
  searchMode: string
}

export interface StreamChunkEvent {
  chunk: string
}

export interface StreamDoneEvent {
  answer: string
  done: true
}

export interface StreamErrorEvent {
  error: string
}

export type StreamEvent = StreamMetadataEvent | StreamChunkEvent | StreamDoneEvent | StreamErrorEvent

// ─── API Error ────────────────────────────────────────────────────────────────

export interface ApiError {
  message?: string
  detail?: string
  status?: number
  title?: string
  errors?: Record<string, string[]>
}
