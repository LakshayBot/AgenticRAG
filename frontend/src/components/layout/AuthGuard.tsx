'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { getAccessToken } from '@/lib/api'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const hasHydrated     = useAuthStore((s) => s._hasHydrated)

  useEffect(() => {
    // Only redirect AFTER the store has rehydrated from localStorage.
    // Without this guard, a page refresh briefly sees isAuthenticated=false
    // (pre-hydration default) and wrongly redirects to /login.
    if (!hasHydrated) return

    const token = getAccessToken()
    if (!isAuthenticated || !token) {
      router.replace('/login')
    }
  }, [hasHydrated, isAuthenticated, router])

  // Show spinner while store is rehydrating
  if (!hasHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <span className="material-symbols-outlined text-4xl text-outline animate-spin">
          progress_activity
        </span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <span className="material-symbols-outlined text-4xl text-outline animate-spin">
          progress_activity
        </span>
      </div>
    )
  }

  return <>{children}</>
}
