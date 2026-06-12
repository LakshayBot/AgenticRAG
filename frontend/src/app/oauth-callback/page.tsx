'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'
import type { AuthResponse } from '@/lib/types'
import { Providers } from '@/app/providers'

const BACKEND = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

function OAuthCallbackInner() {
  const router = useRouter()
  const login = useAuthStore((s) => s.login)
  const handled = useRef(false)

  useEffect(() => {
    if (handled.current) return
    handled.current = true

    async function finalize() {
      const params = new URLSearchParams(window.location.search)
      const token = params.get('token')
      const refreshToken = params.get('refreshToken')
      const expiresAt = params.get('expiresAt')

      if (!token || !refreshToken || !expiresAt) {
        toast.error('OAuth login failed - missing tokens')
        router.replace('/login?error=oauth_failed')
        return
      }

      try {
        // Exchange the refresh token for a full AuthResponse (which includes the user object)
        const res = await fetch(`${BACKEND}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken }),
        })

        if (!res.ok) throw new Error('Token exchange failed')

        const data: AuthResponse = await res.json()
        login(data)

        const redirect = sessionStorage.getItem('redirectAfterLogin') ?? '/dashboard'
        sessionStorage.removeItem('redirectAfterLogin')
        router.replace(redirect)
      } catch {
        toast.error('OAuth login failed - please try again')
        router.replace('/login?error=oauth_failed')
      }
    }

    finalize()
  }, [login, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <span className="material-symbols-outlined text-[40px] text-primary animate-spin">
          progress_activity
        </span>
        <p className="text-[14px] text-on-surface-variant">Completing sign-in…</p>
      </div>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Providers>
      <OAuthCallbackInner />
    </Providers>
  )
}
