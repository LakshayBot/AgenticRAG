'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SystemStatsResponse, AdminUsersResponse, JobsStatusResponse, UserAdminDto } from '@/lib/types'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { SidebarTrigger } from '@/components/ui/sidebar'

type Tab = 'overview' | 'users' | 'jobs'

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: string }) {
  return (
    <div className="rounded-2xl bg-surface-container-lowest p-4 space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-on-surface-variant uppercase tracking-widest font-numbers">{label}</span>
        <span className="material-symbols-outlined text-[18px] text-on-surface-variant">{icon}</span>
      </div>
      <p className="font-numbers text-[28px] font-bold text-on-surface">{value}</p>
    </div>
  )
}

function OverviewTab({ stats, jobs }: { stats: SystemStatsResponse; jobs: JobsStatusResponse }) {
  const services = [
    ...Object.entries(stats.services.pythonServices).map(([name, svc]) => ({
      name,
      healthy: svc.healthy,
      ms: svc.responseTimeMs,
    })),
    { name: 'PostgreSQL', healthy: stats.services.databaseHealthy, ms: 0 },
    { name: 'Redis', healthy: stats.services.cacheHealthy, ms: 0 },
  ]

  return (
    <div className="space-y-6">
      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Users" value={stats.database.totalUsers} icon="group" />
        <StatCard label="Advisories" value={stats.database.totalAdvisories} icon="security" />
        <StatCard label="Files" value={stats.database.totalUploadedFiles} icon="description" />
        <StatCard label="Searches" value={stats.database.totalSearches} icon="manage_search" />
      </div>

      {/* Services */}
      <div>
        <h3 className="font-display text-[16px] text-on-surface mb-3">Service Health</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {services.map(({ name, healthy, ms }) => (
            <div
              key={name}
              className="rounded-2xl bg-surface-container-lowest p-3 flex items-center gap-2"
            >
              <span
                className="material-symbols-outlined text-[18px]"
                style={{
                  color: healthy ? 'var(--sev-low)' : 'var(--sev-critical)',
                  fontVariationSettings: "'FILL' 1",
                }}
              >
                {healthy ? 'check_circle' : 'error'}
              </span>
              <span className="text-[13px] font-medium text-on-surface flex-1 truncate">{name}</span>
              {ms > 0 && (
                <span className="text-[11px] font-numbers text-on-surface-variant">{ms.toFixed(0)}ms</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Search stats */}
      <div>
        <h3 className="font-display text-[16px] text-on-surface mb-3">Search Activity</h3>
        <div className="grid grid-cols-3 gap-3">
          <StatCard label="Today" value={stats.search.todaySearches} icon="today" />
          <StatCard label="Avg Response" value={`${stats.search.averageResponseTimeMs.toFixed(0)}ms`} icon="timer" />
          <StatCard label="Cache Keys" value={stats.cache.totalKeys} icon="storage" />
        </div>
      </div>

      {/* Jobs */}
      <div>
        <h3 className="font-display text-[16px] text-on-surface mb-3">Job Queue</h3>
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Queued', value: jobs.queued, color: 'var(--sev-medium)' },
            { label: 'Processing', value: jobs.processing, color: 'var(--secondary)' },
            { label: 'Succeeded', value: jobs.succeeded, color: 'var(--sev-low)' },
            { label: 'Failed', value: jobs.failed, color: 'var(--sev-critical)' },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-2xl bg-surface-container-lowest p-3 text-center">
              <p className="font-numbers text-[22px] font-bold" style={{ color }}>{value}</p>
              <p className="text-[11px] text-on-surface-variant uppercase tracking-wide">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function UsersTab({ users }: { users: UserAdminDto[] }) {
  const queryClient = useQueryClient()

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api.post(`/api/admin/users/${id}/${active ? 'enable' : 'disable'}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User updated')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="rounded-2xl bg-surface-container-lowest overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-outline-variant">
            {['User', 'Role', 'Status', 'Searches', 'Uploads', 'Joined', ''].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-on-surface-variant"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant">
          {users.map((u) => (
            <tr key={u.id} className="hover:bg-surface-container transition-colors">
              <td className="px-4 py-3">
                <p className="text-[13px] font-medium text-on-surface">
                  {u.firstName ? `${u.firstName} ${u.lastName ?? ''}`.trim() : u.email}
                </p>
                <p className="text-[11px] text-on-surface-variant">{u.email}</p>
              </td>
              <td className="px-4 py-3">
                <span className={cn(
                  'text-[11px] px-2 py-0.5 rounded-full uppercase tracking-wide font-semibold',
                  u.role === 'admin'
                    ? 'bg-primary-container text-on-primary-container'
                    : 'bg-surface-container text-on-surface-variant'
                )}>
                  {u.role}
                </span>
              </td>
              <td className="px-4 py-3">
                <span
                  className="material-symbols-outlined text-[18px]"
                  style={{
                    color: u.isActive ? 'var(--sev-low)' : 'var(--sev-critical)',
                    fontVariationSettings: "'FILL' 1",
                  }}
                >
                  {u.isActive ? 'check_circle' : 'cancel'}
                </span>
              </td>
              <td className="px-4 py-3 text-[13px] font-numbers text-on-surface-variant">{u.searchCount}</td>
              <td className="px-4 py-3 text-[13px] font-numbers text-on-surface-variant">{u.uploadCount}</td>
              <td className="px-4 py-3 text-[12px] text-on-surface-variant">
                {formatDistanceToNow(new Date(u.createdAt))} ago
              </td>
              <td className="px-4 py-3">
                <button
                  onClick={() => toggleMutation.mutate({ id: u.id, active: !u.isActive })}
                  className="text-[12px] text-secondary hover:opacity-80 transition-opacity"
                >
                  {u.isActive ? 'Disable' : 'Enable'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function AdminPage() {
  const { user } = useAuthStore()
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('overview')

  useEffect(() => {
    if (user && user.role !== 'admin') {
      router.replace('/dashboard')
    }
  }, [user, router])

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: () => api.get<SystemStatsResponse>('/api/admin/stats'),
    staleTime: 60_000,
    enabled: user?.role === 'admin',
  })

  const { data: usersData } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get<AdminUsersResponse>('/api/admin/users'),
    staleTime: 60_000,
    enabled: user?.role === 'admin' && tab === 'users',
  })

  const { data: jobs } = useQuery({
    queryKey: ['jobs-status'],
    queryFn: () => api.get<JobsStatusResponse>('/api/jobs/status'),
    staleTime: 30_000,
    enabled: user?.role === 'admin',
  })

  const triggerMutation = useMutation({
    mutationFn: () => api.post('/api/jobs/advisory-ingestion/trigger'),
    onSuccess: () => toast.success('Advisory ingestion job triggered'),
    onError: (err: Error) => toast.error(err.message),
  })

  if (user?.role !== 'admin') return null

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SidebarTrigger className="-ml-2" />
          <div>
            <h1 className="font-display text-[26px] text-on-surface">System Health</h1>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Admin dashboard — infrastructure and user management
            </p>
          </div>
        </div>

        <button
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-secondary text-on-secondary text-[13px] font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[18px]">play_circle</span>
          Run Ingestion
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface-container rounded-2xl p-1 mb-6 w-fit">
        {(['overview', 'users', 'jobs'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'px-4 py-2 rounded-xl text-[13px] font-medium capitalize transition-colors',
              tab === t
                ? 'bg-surface-container-lowest text-on-surface shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {loadingStats ? (
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-20 rounded-2xl animate-skeleton" />
          ))}
        </div>
      ) : (
        <>
          {tab === 'overview' && stats && jobs && (
            <OverviewTab stats={stats} jobs={jobs} />
          )}
          {tab === 'users' && usersData && (
            <UsersTab users={usersData.users} />
          )}
          {tab === 'jobs' && jobs && (
            <div className="space-y-4">
              <h3 className="font-display text-[16px] text-on-surface">Recurring Jobs</h3>
              {jobs.recurringJobs.length === 0 ? (
                <p className="text-[13px] text-on-surface-variant">No recurring jobs configured.</p>
              ) : (
                <div className="space-y-2">
                  {jobs.recurringJobs.map((job) => (
                    <div key={job.id} className="rounded-2xl bg-surface-container-lowest p-4 space-y-1">
                      <p className="text-[14px] font-medium text-on-surface font-numbers">{job.id}</p>
                      <div className="flex gap-4">
                        <span className="text-[12px] font-numbers text-on-surface-variant">
                          CRON: {job.cron}
                        </span>
                        {job.nextExecution && (
                          <span className="text-[12px] text-on-surface-variant">
                            Next: {formatDistanceToNow(new Date(job.nextExecution))} from now
                          </span>
                        )}
                        {job.lastJobState && (
                          <span className={cn(
                            'text-[11px] px-2 py-0.5 rounded-full uppercase tracking-wide font-semibold',
                            job.lastJobState === 'Succeeded'
                              ? 'bg-surface-container text-sev-low'
                              : 'bg-error-container text-error'
                          )}>
                            {job.lastJobState}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
