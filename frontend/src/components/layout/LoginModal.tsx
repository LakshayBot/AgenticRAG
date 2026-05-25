'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import type { AuthResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface LoginModalProps {
  /** Whether the modal is visible */
  open: boolean
  /** Called when the modal should close (backdrop click, escape, or cancel) */
  onClose: () => void
  /** Route to navigate to after a successful login */
  redirectTo?: string
}

export function LoginModal({ open, onClose, redirectTo }: LoginModalProps) {
  const router = useRouter()
  const login = useAuthStore((s) => s.login)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Reset form state whenever the modal opens
  useEffect(() => {
    if (open) {
      setEmail('')
      setPassword('')
      setShowPw(false)
      setErrors({})
      setLoading(false)
    }
  }, [open])

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose]
  )
  useEffect(() => {
    if (!open) return
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, handleKeyDown])

  // Lock body scroll while open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [open])

  function validate(): boolean {
    const e: Record<string, string> = {}
    if (!email) e.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Invalid email address'
    if (!password) e.password = 'Password is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      const data = await api.post<AuthResponse>('/api/auth/login', { email, password }, { skipAuth: true })
      login(data)
      onClose()
      if (redirectTo) {
        router.push(redirectTo)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Login failed'
      toast.error(msg)
      setErrors({ _form: msg })
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Sign in"
    >
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative w-full max-w-sm animate-fade-in">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors shadow"
          aria-label="Close"
        >
          <span className="material-symbols-outlined text-[18px]">close</span>
        </button>

        {/* Card */}
        <div className="bg-surface-container-lowest rounded-3xl p-7 shadow-xl">
          {/* Header */}
          <div className="flex flex-col items-center mb-6">
            <div className="w-11 h-11 rounded-2xl bg-primary flex items-center justify-center mb-3">
              <span
                className="material-symbols-outlined text-[22px] text-on-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                lock
              </span>
            </div>
            <h2 className="font-display text-[22px] text-on-surface">Sign in required</h2>
            <p className="text-[12px] text-on-surface-variant mt-1 text-center">
              This section requires an account
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Email */}
            <div>
              <label
                htmlFor="modal-email"
                className="block text-[11px] font-semibold text-on-surface-variant mb-1.5 uppercase tracking-wide"
              >
                Email
              </label>
              <input
                id="modal-email"
                type="email"
                autoComplete="email"
                autoFocus
                value={email}
                onChange={(e) => { setEmail(e.target.value); setErrors((p) => ({ ...p, email: '' })) }}
                className={cn(
                  'w-full px-4 py-2.5 bg-surface-container rounded-2xl text-[14px] text-on-surface',
                  'placeholder:text-on-surface-variant transition-colors',
                  'focus:outline-none focus:ring-2',
                  errors.email ? 'ring-2 ring-error' : 'focus:ring-secondary/40'
                )}
                placeholder="you@example.com"
              />
              {errors.email && (
                <p className="text-[11px] text-error mt-1">{errors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="modal-password"
                className="block text-[11px] font-semibold text-on-surface-variant mb-1.5 uppercase tracking-wide"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="modal-password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: '' })) }}
                  className={cn(
                    'w-full px-4 py-2.5 pr-10 bg-surface-container rounded-2xl text-[14px] text-on-surface',
                    'placeholder:text-on-surface-variant transition-colors',
                    'focus:outline-none focus:ring-2',
                    errors.password ? 'ring-2 ring-error' : 'focus:ring-secondary/40'
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {showPw ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
              {errors.password && (
                <p className="text-[11px] text-error mt-1">{errors.password}</p>
              )}
            </div>

            {errors._form && (
              <p className="text-[12px] text-error bg-error-container rounded-2xl px-3 py-2">
                {errors._form}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className={cn(
                'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-2xl',
                'bg-primary text-on-primary font-semibold text-[14px]',
                'hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed'
              )}
            >
              {loading && (
                <span className="material-symbols-outlined text-[18px] animate-spin">
                  progress_activity
                </span>
              )}
              Sign in
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-outline-variant" />
            <span className="text-[11px] text-on-surface-variant uppercase tracking-wide">or continue with</span>
            <div className="flex-1 h-px bg-outline-variant" />
          </div>

          {/* OAuth buttons */}
          <div className="flex flex-col gap-2">
            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/api/auth/oauth/google`}
              className={cn(
                'w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-2xl',
                'bg-surface-container text-on-surface font-medium text-[14px]',
                'border border-outline-variant hover:bg-surface-container-high transition-colors'
              )}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
                <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
              </svg>
              Continue with Google
            </a>

            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/api/auth/oauth/github`}
              className={cn(
                'w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-2xl',
                'bg-surface-container text-on-surface font-medium text-[14px]',
                'border border-outline-variant hover:bg-surface-container-high transition-colors'
              )}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
              </svg>
              Continue with GitHub
            </a>
          </div>

          <p className="text-center text-[12px] text-on-surface-variant mt-4">
            No account?{' '}
            <Link
              href="/register"
              onClick={onClose}
              className="text-secondary hover:opacity-80 transition-opacity font-medium"
            >
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
