'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AdvisoryStats, SystemStatsResponse, JobsStatusResponse } from '@/lib/types'
import { useAuthStore } from '@/stores/authStore'
import { AlertsBlock } from '@/components/dashboard/AlertsBlock'
import { AutomationBlock } from '@/components/dashboard/AutomationBlock'
import { DataOverview } from '@/components/dashboard/DataOverview'
import { OpenIncidents } from '@/components/dashboard/OpenIncidents'
import { LiveFeed } from '@/components/dashboard/LiveFeed'

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`rounded-3xl animate-pulse ${className ?? ''}`}
      style={{ background: 'var(--surface-container)' }}
    />
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const { data: advisoryStats, isLoading: loadingAdvisory } = useQuery({
    queryKey: ['advisory-stats'],
    queryFn: () => api.get<AdvisoryStats>('/api/advisories/stats'),
    staleTime: 60_000,
  })

  const { data: systemStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: () => api.get<SystemStatsResponse>('/api/admin/stats'),
    staleTime: 60_000,
    enabled: isAdmin,
  })

  const { data: jobsStatus } = useQuery({
    queryKey: ['jobs-status'],
    queryFn: () => api.get<JobsStatusResponse>('/api/jobs/status'),
    staleTime: 30_000,
  })

  return (
    <div className="p-4 md:p-6 lg:p-8 overflow-x-hidden min-h-screen relative z-10 w-full">

      <div className="flex flex-col xl:flex-row xl:items-stretch gap-6 lg:gap-8 mt-2">
        {/* LEFT COLUMN */}
        <div className="w-full xl:w-64 flex flex-col md:flex-row xl:flex-col gap-6 relative z-10 shrink-0 xl:self-stretch">
          {loadingAdvisory ? (
            <Skeleton className="h-64 flex-1" />
          ) : advisoryStats ? (
            <AlertsBlock stats={advisoryStats} />
          ) : (
            <div className="rounded-3xl bg-primary/10 p-6 text-sm text-on-surface-variant flex-1 flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">warning</span>
              Advisory stats unavailable
            </div>
          )}

          <AutomationBlock systemStats={systemStats} jobsStatus={jobsStatus} />
        </div>

        {/* CENTER COLUMN */}
        <div className="flex-1 flex flex-col gap-6 relative z-10 w-full min-w-0">
          {loadingAdvisory ? (
            <Skeleton className="min-h-[500px] sm:min-h-[600px] flex-1" />
          ) : advisoryStats ? (
            <DataOverview stats={advisoryStats} systemStats={systemStats} />
          ) : (
            <div className="rounded-[32px] bg-surface-container-lowest p-8 min-h-[500px] flex items-center justify-center text-on-surface-variant">
              <span className="material-symbols-outlined text-[18px] mr-2">analytics</span>
              No data available
            </div>
          )}
        </div>

        {/* RIGHT COLUMN */}
        <div className="w-full xl:w-64 flex flex-col md:flex-row xl:flex-col gap-6 relative z-10 shrink-0">
          {loadingAdvisory ? (
            <>
              <Skeleton className="h-48 flex-1" />
              <Skeleton className="h-52 flex-1" />
            </>
          ) : advisoryStats ? (
            <>
              <OpenIncidents stats={advisoryStats} />
              <LiveFeed stats={advisoryStats} />
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
