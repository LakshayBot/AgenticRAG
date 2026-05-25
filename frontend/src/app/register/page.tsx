'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import type { AuthResponse } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Providers } from '@/app/providers'

function passwordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++

  if (score <= 1) return { score, label: 'Weak', color: 'var(--sev-critical)' }
  if (score <= 2) return { score, label: 'Fair', color: 'var(--sev-high)' }
  if (score <= 3) return { score, label: 'Good', color: 'var(--sev-medium)' }
  return { score, label: 'Strong', color: 'var(--sev-low)' }
}

function RegisterForm() {
  const router = useRouter()
  const login = useAuthStore((s) => s.login)
  const [form, setForm] = useState({ email: '', password: '', firstName: '', lastName: '' })
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const pwStrength = passwordStrength(form.password)

  function setField(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setErrors((prev) => ({ ...prev, [field]: '', _form: '' }))
  }

  function validate(): boolean {
    const e: Record<string, string> = {}
    if (!form.email) e.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Invalid email'
    if (!form.password) e.password = 'Password is required'
    else if (form.password.length < 8) e.password = 'Minimum 8 characters'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      const data = await api.post<AuthResponse>('/api/auth/register', form, { skipAuth: true })
      login(data)
      router.replace('/dashboard')
      toast.success('Account created')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed'
      toast.error(msg)
      setErrors({ _form: msg })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center mb-4">
            <span
              className="material-symbols-outlined text-[26px] text-on-primary"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              security
            </span>
          </div>
          <h1 className="font-display text-[26px] text-on-surface">Create account</h1>
          <p className="text-[13px] text-on-surface-variant mt-1">CyberGuard Intelligence Platform</p>
        </div>

        <div className="bg-surface-container-lowest rounded-3xl p-6 shadow-sm">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Name row */}
            <div className="grid grid-cols-2 gap-3">
              {(['firstName', 'lastName'] as const).map((field) => (
                <div key={field}>
                  <label htmlFor={field} className="block text-[12px] font-semibold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                    {field === 'firstName' ? 'First' : 'Last'}
                    <span className="text-on-surface-variant/50 ml-1 normal-case tracking-normal">(opt)</span>
                  </label>
                  <input
                    id={field}
                    type="text"
                    value={form[field]}
                    onChange={(e) => setField(field, e.target.value)}
                    className="w-full px-3 py-2.5 bg-surface-container rounded-2xl text-[14px] text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-secondary/40"
                    placeholder={field === 'firstName' ? 'Jane' : 'Doe'}
                  />
                </div>
              ))}
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-[12px] font-semibold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => setField('email', e.target.value)}
                className={cn(
                  'w-full px-4 py-2.5 bg-surface-container rounded-2xl text-[14px] text-on-surface',
                  'placeholder:text-on-surface-variant focus:outline-none focus:ring-2',
                  errors.email ? 'ring-2 ring-error' : 'focus:ring-secondary/40'
                )}
                placeholder="you@example.com"
              />
              {errors.email && <p className="text-[11px] text-error mt-1">{errors.email}</p>}
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-[12px] font-semibold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => setField('password', e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 pr-10 bg-surface-container rounded-2xl text-[14px] text-on-surface',
                    'placeholder:text-on-surface-variant focus:outline-none focus:ring-2',
                    errors.password ? 'ring-2 ring-error' : 'focus:ring-secondary/40'
                  )}
                  placeholder="Min 8 characters"
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
              {errors.password && <p className="text-[11px] text-error mt-1">{errors.password}</p>}

              {/* Strength meter */}
              {form.password.length > 0 && (
                <div className="mt-2">
                  <div className="flex gap-1 mb-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className="h-1 flex-1 rounded-full transition-all"
                        style={{
                          background: i <= pwStrength.score ? pwStrength.color : 'var(--outline-variant)',
                        }}
                      />
                    ))}
                  </div>
                  <p className="text-[11px]" style={{ color: pwStrength.color }}>{pwStrength.label}</p>
                </div>
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
              Create account
            </button>
          </form>
        </div>

        <p className="text-center text-[12px] text-on-surface-variant mt-4">
          Already have an account?{' '}
          <Link href="/login" className="text-secondary hover:opacity-80 transition-opacity font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Providers>
      <RegisterForm />
    </Providers>
  )
}
