'use client'

import { useQueries } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { analyticsApi } from '@/lib/api'
import { SidebarTrigger } from '@/components/ui/sidebar'
import type {
  AnalyticsOverview,
  TimelinePoint,
  ResponseTimeStats,
  TypeBreakdown,
  TopQuestion,
  CachePoint,
  EcosystemCount,
  CvssDistributionItem,
  CweCount,
  TrendingAdvisory,
  AdvisoryChunkCountsResult,
} from '@/lib/api'

// ─── Colour palette ───────────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, string> = {
  critical: '#b91c1c',
  high:     '#d97706',
  medium:   '#2563eb',
  low:      '#16a34a',
  unknown:  '#6b7280',
}
const CHART_COLORS = ['#6e1816', '#646100', '#2563eb', '#7c3aed', '#0891b2', '#15803d']
const TYPE_COLORS: Record<string, string> = {
  hybrid:   '#6e1816',
  bm25:     '#646100',
  vector:   '#2563eb',
  agentic:  '#7c3aed',
}

// ─── Tiny helpers ─────────────────────────────────────────────────────────────

function SectionHeading({ icon, title, sub }: { icon: string; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <span
        className="material-symbols-outlined text-primary text-[22px]"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        {icon}
      </span>
      <div>
        <h2 className="font-headline text-lg font-bold text-on-surface leading-tight">{title}</h2>
        {sub && <p className="text-[11px] text-on-surface-variant mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-surface-container rounded-2xl p-5 ${className}`}>
      {children}
    </div>
  )
}

function ChartTitle({ children }: { children: React.ReactNode }) {
  return <p className="text-[12px] font-semibold text-on-surface-variant uppercase tracking-wide mb-4">{children}</p>
}

function Skeleton({ h = 'h-40' }: { h?: string }) {
  return <div className={`${h} rounded-xl bg-surface-container-high animate-pulse`} />
}

function KpiCard({
  label, value, sub, icon, color = 'text-primary',
}: { label: string; value: string | number; sub?: string; icon: string; color?: string }) {
  return (
    <Card className="flex items-start gap-4">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
        <span
          className={`material-symbols-outlined text-[22px] ${color}`}
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          {icon}
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-[11px] text-on-surface-variant uppercase tracking-wide font-semibold">{label}</p>
        <p className="font-numbers text-2xl font-bold text-on-surface mt-0.5 tabular-nums">{value}</p>
        {sub && <p className="text-[11px] text-on-surface-variant mt-0.5">{sub}</p>}
      </div>
    </Card>
  )
}

// ─── Custom tooltip shared style ─────────────────────────────────────────────

const tooltipStyle = {
  contentStyle: {
    background: 'var(--color-surface-container-high)',
    border: 'none',
    borderRadius: 10,
    fontSize: 12,
    color: 'var(--color-on-surface)',
  },
  itemStyle: { color: 'var(--color-on-surface)' },
  labelStyle: { color: 'var(--color-on-surface-variant)', fontWeight: 600 },
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const results = useQueries({
    queries: [
      { queryKey: ['analytics', 'overview'],          queryFn: analyticsApi.overview,                       staleTime: 60_000 },
      { queryKey: ['analytics', 'queryTimeline'],      queryFn: () => analyticsApi.queryTimeline(30),        staleTime: 60_000 },
      { queryKey: ['analytics', 'responseTimes'],      queryFn: analyticsApi.responseTimes,                  staleTime: 60_000 },
      { queryKey: ['analytics', 'queryByType'],        queryFn: analyticsApi.queryByType,                    staleTime: 60_000 },
      { queryKey: ['analytics', 'topQuestions'],       queryFn: () => analyticsApi.topQuestions(20),         staleTime: 60_000 },
      { queryKey: ['analytics', 'cachePerformance'],   queryFn: () => analyticsApi.cachePerformance(30),     staleTime: 60_000 },
      { queryKey: ['analytics', 'advisoryTimeline'],   queryFn: () => analyticsApi.advisoryTimeline(12),     staleTime: 60_000 },
      { queryKey: ['analytics', 'ecosystems'],         queryFn: () => analyticsApi.ecosystems(15),           staleTime: 60_000 },
      { queryKey: ['analytics', 'cvssDistribution'],   queryFn: analyticsApi.cvssDistribution,               staleTime: 60_000 },
      { queryKey: ['analytics', 'cweBreakdown'],       queryFn: () => analyticsApi.cweBreakdown(15),         staleTime: 60_000 },
      { queryKey: ['analytics', 'trending'],           queryFn: () => analyticsApi.trendingAdvisories(10),   staleTime: 60_000 },
      { queryKey: ['analytics', 'chunksPerAdvisory'],  queryFn: () => analyticsApi.chunksPerAdvisory(30),    staleTime: 120_000 },
    ],
  })

  const [
    overviewQ, queryTimelineQ, responseTimesQ, queryByTypeQ,
    topQuestionsQ, cacheQ, advisoryTimelineQ, ecosystemsQ,
    cvssQ, cweQ, trendingQ, chunksQ,
  ] = results

  const overview           = overviewQ.data          as AnalyticsOverview | undefined
  const queryTimeline      = queryTimelineQ.data      as TimelinePoint[] | undefined
  const responseTimes      = responseTimesQ.data      as ResponseTimeStats[] | undefined
  const queryByType        = queryByTypeQ.data        as TypeBreakdown[] | undefined
  const topQuestions       = topQuestionsQ.data       as TopQuestion[] | undefined
  const cachePerf          = cacheQ.data              as CachePoint[] | undefined
  const advisoryTimeline   = advisoryTimelineQ.data   as TimelinePoint[] | undefined
  const ecosystems         = ecosystemsQ.data         as EcosystemCount[] | undefined
  const cvssDistribution   = cvssQ.data               as CvssDistributionItem[] | undefined
  const cweBreakdown       = cweQ.data                as CweCount[] | undefined
  const trending           = trendingQ.data           as TrendingAdvisory[] | undefined
  const chunks             = chunksQ.data             as AdvisoryChunkCountsResult | undefined

  return (
    <main className="flex-1 overflow-y-auto animate-fade-in">
      <div className="max-w-[1400px] mx-auto px-6 py-8 space-y-12">

        {/* ── Page header ───────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="-ml-2" />
            <div>
              <h1 className="font-headline text-3xl font-black text-on-surface">
                Platform Analytics
              </h1>
              <p className="text-sm text-on-surface-variant mt-1">
                Real-time insights into queries, response performance, and advisory intelligence
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-on-surface-variant bg-surface-container px-3 py-1.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Live data
          </div>
        </div>

        {/* ── Section 1: KPI Overview ───────────────────────────────────── */}
        <section>
          <SectionHeading icon="monitoring" title="Overview" sub="Platform-wide key performance indicators" />
          {overviewQ.isLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h="h-24" />)}
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total Queries"
                value={overview?.totalQueries?.toLocaleString() ?? '—'}
                sub="All search & RAG calls"
                icon="search"
              />
              <KpiCard
                label="Avg Response Time"
                value={overview ? `${Math.round(overview.avgResponseTimeMs)} ms` : '—'}
                sub="Mean across all query types"
                icon="timer"
                color="text-secondary"
              />
              <KpiCard
                label="Cache Hit Rate"
                value={overview ? `${overview.cacheHitRate}%` : '—'}
                sub="Redis cache efficiency"
                icon="cached"
                color="text-tertiary"
              />
              <KpiCard
                label="Advisories in DB"
                value={overview?.totalAdvisories?.toLocaleString() ?? '—'}
                sub={overview ? `${overview.indexedAdvisories.toLocaleString()} indexed` : undefined}
                icon="shield"
              />
            </div>
          )}

          {/* Admin-only second row */}
          {overview && (overview.totalUsers != null) && (
            <div className="grid grid-cols-3 gap-4 mt-4">
              <KpiCard
                label="Total Users"
                value={overview.totalUsers?.toLocaleString() ?? '—'}
                sub={`${overview.activeUsers?.toLocaleString()} active`}
                icon="group"
                color="text-secondary"
              />
              <KpiCard
                label="Querying Users"
                value={overview.uniqueQueryingUsers?.toLocaleString() ?? '—'}
                sub="Unique users with query history"
                icon="person_search"
              />
              <KpiCard
                label="Chunks Indexed"
                value={chunks?.totalChunks?.toLocaleString() ?? '—'}
                sub={`Across ${chunks?.totalAdvisories?.toLocaleString() ?? '—'} advisories`}
                icon="database"
                color="text-tertiary"
              />
            </div>
          )}
        </section>

        {/* ── Section 2: Query Volume & Cache ──────────────────────────── */}
        <section>
          <SectionHeading icon="query_stats" title="Query Intelligence" sub="Volume trends and cache efficiency over 30 days" />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

            {/* Query volume line chart */}
            <Card>
              <ChartTitle>Query Volume — Last 30 Days</ChartTitle>
              {queryTimelineQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={queryTimeline ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                    <defs>
                      <linearGradient id="queryGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6e1816" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6e1816" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip {...tooltipStyle} />
                    <Area type="monotone" dataKey="count" stroke="#6e1816" strokeWidth={2} fill="url(#queryGrad)" name="Queries" dot={false} activeDot={{ r: 4 }} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Cache performance stacked area */}
            <Card>
              <ChartTitle>Cache Performance — Last 30 Days</ChartTitle>
              {cacheQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={cachePerf ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                    <defs>
                      <linearGradient id="cachedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#16a34a" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="uncachedGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6e1816" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#6e1816" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip {...tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area type="monotone" dataKey="cached"   stroke="#16a34a" strokeWidth={2} fill="url(#cachedGrad)"   name="Cache Hit"  dot={false} />
                    <Area type="monotone" dataKey="uncached" stroke="#6e1816" strokeWidth={2} fill="url(#uncachedGrad)" name="Cache Miss" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </section>

        {/* ── Section 3: Search Behaviour ──────────────────────────────── */}
        <section>
          <SectionHeading icon="manage_search" title="Search Behaviour" sub="Type distribution, response times, and most-asked questions" />
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

            {/* Search type donut */}
            <Card>
              <ChartTitle>Search Type Distribution</ChartTitle>
              {queryByTypeQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={queryByType ?? []}
                      dataKey="count"
                      nameKey="type"
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={80}
                      paddingAngle={3}
                    >
                      {(queryByType ?? []).map((entry) => (
                        <Cell key={entry.type} fill={TYPE_COLORS[entry.type] ?? '#6b7280'} />
                      ))}
                    </Pie>
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(val, name) => [val, name]}
                    />
                    <Legend
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11 }}
                      formatter={(v) => v.charAt(0).toUpperCase() + v.slice(1)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Response time bar chart */}
            <Card className="xl:col-span-2">
              <ChartTitle>Response Time by Search Type (ms)</ChartTitle>
              {responseTimesQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={responseTimes ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -10 }} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} vertical={false} />
                    <XAxis dataKey="searchType" tick={{ fontSize: 11 }} tickLine={false} axisLine={false}
                      tickFormatter={v => v.charAt(0).toUpperCase() + v.slice(1)} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip {...tooltipStyle} formatter={(v) => [`${v} ms`]} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="avgMs"  name="Avg"  radius={[4,4,0,0]}>
                      {(responseTimes ?? []).map((entry) => (
                        <Cell key={entry.searchType} fill={TYPE_COLORS[entry.searchType] ?? '#6e1816'} />
                      ))}
                    </Bar>
                    <Bar dataKey="p95Ms"  name="P95"  fill="#646100" opacity={0.7} radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          {/* Top questions table */}
          <Card className="mt-5">
            <ChartTitle>Top 20 Most-Asked Questions</ChartTitle>
            {topQuestionsQ.isLoading ? <Skeleton h="h-56" /> : !topQuestions?.length ? (
              <p className="text-sm text-on-surface-variant text-center py-8">No query history yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[12px]">
                  <thead>
                    <tr className="text-on-surface-variant text-left border-b border-outline-variant/30">
                      <th className="pb-2 pr-4 font-semibold w-8">#</th>
                      <th className="pb-2 pr-4 font-semibold">Question</th>
                      <th className="pb-2 pr-4 font-semibold text-right w-20">Count</th>
                      <th className="pb-2 font-semibold text-right w-28">Avg Response</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20">
                    {topQuestions.map((q, i) => (
                      <tr key={i} className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-2 pr-4 text-on-surface-variant tabular-nums">{i + 1}</td>
                        <td className="py-2 pr-4 text-on-surface truncate max-w-[480px]" title={q.question}>{q.question}</td>
                        <td className="py-2 pr-4 text-right font-numbers font-semibold text-on-surface tabular-nums">{q.count}</td>
                        <td className="py-2 text-right font-numbers text-on-surface-variant tabular-nums">
                          {q.avgResponseMs > 0 ? `${Math.round(q.avgResponseMs)} ms` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </section>

        {/* ── Section 4: Advisory Intelligence ─────────────────────────── */}
        <section>
          <SectionHeading icon="security" title="Advisory Intelligence" sub="Publishing trends, CVSS distribution, and vulnerability metadata" />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

            {/* Advisory timeline area */}
            <Card>
              <ChartTitle>Advisories Published — Last 12 Months</ChartTitle>
              {advisoryTimelineQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={advisoryTimeline ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                    <defs>
                      <linearGradient id="advisoryGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#646100" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#646100" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip {...tooltipStyle} />
                    <Area type="monotone" dataKey="count" stroke="#646100" strokeWidth={2} fill="url(#advisoryGrad)" name="Advisories" dot={false} activeDot={{ r: 4 }} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* CVSS distribution bar */}
            <Card>
              <ChartTitle>CVSS Score Distribution</ChartTitle>
              {cvssQ.isLoading ? <Skeleton /> : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={cvssDistribution ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -10 }} barCategoryGap="25%">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} vertical={false} />
                    <XAxis dataKey="range" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip {...tooltipStyle} />
                    <Bar dataKey="count" name="Advisories" radius={[6,6,0,0]}>
                      {(cvssDistribution ?? []).map((entry, i) => (
                        <Cell key={entry.range} fill={CHART_COLORS[i] ?? '#6e1816'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </section>

        {/* ── Section 5: Ecosystem & Weakness Analysis ──────────────────── */}
        <section>
          <SectionHeading icon="hub" title="Ecosystem & Weakness Analysis" sub="Top affected ecosystems and most common CWE weakness types" />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

            {/* Ecosystems horizontal bar */}
            <Card>
              <ChartTitle>Top Affected Ecosystems</ChartTitle>
              {ecosystemsQ.isLoading ? <Skeleton h="h-52" /> : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={ecosystems ?? []}
                    layout="vertical"
                    margin={{ top: 4, right: 12, bottom: 0, left: 0 }}
                    barCategoryGap="20%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="ecosystem" tick={{ fontSize: 11 }} width={64} tickLine={false} axisLine={false} />
                    <Tooltip {...tooltipStyle} />
                    <Bar dataKey="count" name="Advisories" fill="#6e1816" radius={[0,4,4,0]}>
                      {(ecosystems ?? []).map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* CWE horizontal bar */}
            <Card>
              <ChartTitle>Top CWE Weakness Types</ChartTitle>
              {cweQ.isLoading ? <Skeleton h="h-52" /> : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={cweBreakdown ?? []}
                    layout="vertical"
                    margin={{ top: 4, right: 12, bottom: 0, left: 0 }}
                    barCategoryGap="20%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="cweId" tick={{ fontSize: 10 }} width={72} tickLine={false} axisLine={false} />
                    <Tooltip {...tooltipStyle} />
                    <Bar dataKey="count" name="Advisories" radius={[0,4,4,0]}>
                      {(cweBreakdown ?? []).map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[(i + 2) % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </section>

        {/* ── Section 6: Trending & Chunk Depth ────────────────────────── */}
        <section>
          <SectionHeading
            icon="trending_up"
            title="Trending & Chunk Depth"
            sub="Most-queried advisories and OpenSearch chunk distribution"
          />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

            {/* Trending advisories list */}
            <Card>
              <ChartTitle>Most Queried Advisories</ChartTitle>
              {trendingQ.isLoading ? <Skeleton h="h-56" /> : !trending?.length ? (
                <p className="text-sm text-on-surface-variant text-center py-8">
                  No query-to-advisory links found yet. Ask questions with source references to populate this.
                </p>
              ) : (
                <div className="space-y-2.5 overflow-y-auto max-h-[340px] pr-1">
                  {trending.map((item, i) => (
                    <a
                      key={item.ghsaId}
                      href={`/advisories?id=${item.ghsaId}`}
                      className="flex items-start gap-3 p-3 rounded-xl bg-surface-container-high hover:bg-surface-variant transition-colors group"
                    >
                      <span className="text-[12px] font-numbers font-bold text-on-surface-variant tabular-nums w-5 shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-mono text-[11px] text-primary font-semibold">{item.ghsaId}</span>
                          <span
                            className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full"
                            style={{
                              background: `${SEVERITY_COLORS[item.severity] ?? '#6b7280'}20`,
                              color: SEVERITY_COLORS[item.severity] ?? '#6b7280',
                            }}
                          >
                            {item.severity}
                          </span>
                        </div>
                        <p className="text-[12px] text-on-surface truncate">{item.summary}</p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="font-numbers text-sm font-bold text-on-surface tabular-nums">{item.queryCount}</p>
                        <p className="text-[10px] text-on-surface-variant">queries</p>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </Card>

            {/* Chunks per advisory bar chart */}
            <Card>
              <ChartTitle>
                Chunks per Advisory (OpenSearch) — Top {chunks?.counts?.length ?? 30}
              </ChartTitle>
              {chunksQ.isLoading ? <Skeleton h="h-72" /> : !chunks?.counts?.length ? (
                <p className="text-sm text-on-surface-variant text-center py-8">
                  No indexed chunks found. Ingest and index advisories first.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <BarChart
                    data={chunks.counts}
                    margin={{ top: 4, right: 4, bottom: 60, left: -10 }}
                    barCategoryGap="15%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" strokeOpacity={0.4} vertical={false} />
                    <XAxis
                      dataKey="ghsaId"
                      tick={{ fontSize: 9 }}
                      tickLine={false}
                      axisLine={false}
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      height={70}
                      tickFormatter={v => v.replace('GHSA-', '')}
                    />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(v) => [v, 'Chunks']}
                      labelFormatter={(l) => `Advisory: ${l}`}
                    />
                    <Bar dataKey="chunkCount" name="Chunks" radius={[3,3,0,0]}>
                      {(chunks.counts).map((_, i) => (
                        <Cell key={i} fill={`hsl(${(i * 13) % 360}, 55%, 42%)`} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

          </div>
        </section>

      </div>
    </main>
  )
}
