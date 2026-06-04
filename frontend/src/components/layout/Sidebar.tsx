'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'
import { LoginModal } from '@/components/layout/LoginModal'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const TOP_NAV = [
  { label: 'Overview',      href: '/dashboard',  icon: 'dashboard',  public: true  },
  { label: 'Threat Intel',  href: '/advisories', icon: 'security',   public: false },
  { label: 'Analytics',     href: '/analytics',  icon: 'bar_chart',  public: false },
]

const BOTTOM_NAV = [
  { label: 'AI Query',          href: '/ask',     icon: 'psychology', public: false },
  { label: 'Search Incidents',  href: '/search',  icon: 'history',    public: false },
]

const ADMIN_ITEM = { label: 'System Health', href: '/admin', icon: 'analytics', public: false }

export function Sidebar() {
  const pathname   = usePathname()
  const { user, isAuthenticated, logout } = useAuthStore()
  const { isDark, toggle: toggleTheme } = useTheme()
  const isAdmin    = user?.role === 'admin'
  const [collapsed, setCollapsed] = useState(false)
  const [apiVersion, setApiVersion] = useState<string>('')

  useEffect(() => {
    fetch(`${API_BASE}/version`)
      .then((r) => r.json())
      .then((data) => setApiVersion(data.version ?? ''))
      .catch(() => setApiVersion(''))
  }, [])

  // Login modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [pendingHref, setPendingHref] = useState<string | undefined>(undefined)

  const topItems = isAdmin ? [...TOP_NAV, ADMIN_ITEM] : TOP_NAV
  const bottomItems = BOTTOM_NAV

  function handleProtectedClick(href: string) {
    setPendingHref(href)
    setModalOpen(true)
  }

  return (
    <>
      <aside
        className={cn(
          'shrink-0 h-screen sticky top-0 flex flex-col bg-surface-container-low overflow-y-auto transition-all duration-300',
          collapsed ? 'w-[72px]' : 'w-64'
        )}
      >
        {/* Logo + collapse toggle */}
        {collapsed ? (
          <div className="py-4 flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded bg-primary flex items-center justify-center shrink-0">
              <span
                className="material-symbols-outlined text-on-primary"
                style={{ fontSize: '20px', fontVariationSettings: "'FILL' 1" }}
              >
                shield
              </span>
            </div>
            <button
              onClick={() => setCollapsed(false)}
              className="text-on-surface hover:text-primary transition-colors rounded-full p-1.5 hover:bg-surface-container bg-surface-container-high"
              title="Expand sidebar"
            >
              <span className="material-symbols-outlined text-[20px]">chevron_right</span>
            </button>
          </div>
        ) : (
          <div className="px-4 py-5 flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-primary flex items-center justify-center shrink-0">
              <span
                className="material-symbols-outlined text-on-primary"
                style={{ fontSize: '20px', fontVariationSettings: "'FILL' 1" }}
              >
                shield
              </span>
            </div>
            <div className="flex-1 overflow-hidden">
              <h1 className="font-headline text-lg font-black text-tertiary dark:text-on-surface uppercase tracking-tight leading-none">
                CyberGuard
              </h1>
              <span className="text-[10px] text-on-surface-variant font-medium tracking-normal">
                Tactical Curator{apiVersion ? ` v${apiVersion}` : ''}
              </span>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              className="text-on-surface-variant hover:text-on-surface transition-colors rounded-full p-1 hover:bg-surface-container"
              title="Collapse sidebar"
            >
              <span className="material-symbols-outlined text-[20px]">chevron_left</span>
            </button>
          </div>
        )}

        {/* Top nav links */}
        <nav className={cn('py-2 space-y-0.5', collapsed ? 'px-1' : 'pr-4')}>
          {topItems.map(({ label, href, icon, public: isPublic }) => {
            const active = pathname === href || (href !== '/dashboard' && (pathname ?? '').startsWith(href))
            const locked = !isPublic && !isAuthenticated

            if (locked) {
              return (
                <button
                  key={href}
                  onClick={() => handleProtectedClick(href)}
                  title={collapsed ? `${label} (sign in required)` : undefined}
                  className={cn(
                    'w-full flex items-center gap-3 py-3 text-[13px] font-semibold transition-all duration-200',
                    'text-on-surface-variant/50 hover:text-on-surface-variant hover:bg-surface-container/30',
                    collapsed
                      ? 'justify-center px-2 rounded-full mx-1'
                      : 'px-6 rounded-r-full'
                  )}
                >
                  <span
                    className="material-symbols-outlined text-[20px] shrink-0"
                    style={{ fontVariationSettings: "'FILL' 0" }}
                  >
                    {icon}
                  </span>
                  {!collapsed && (
                    <span className="flex-1 text-left">{label}</span>
                  )}
                  {!collapsed && (
                    <span
                      className="material-symbols-outlined text-[14px] text-on-surface-variant/40"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      lock
                    </span>
                  )}
                </button>
              )
            }

            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? label : undefined}
                className={cn(
                  'flex items-center gap-3 py-3 text-[13px] font-semibold transition-all duration-200 hover:translate-x-0.5',
                  collapsed
                    ? 'justify-center px-2 rounded-full mx-1'
                    : 'px-6 rounded-r-full',
                  active
                    ? 'text-on-surface'
                    : 'text-on-surface-variant hover:bg-surface-container/50'
                )}
                style={active ? { backgroundColor: 'var(--nav-active-bg)' } : undefined}
              >
                <span
                  className="material-symbols-outlined text-[20px] shrink-0"
                  style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}
                >
                  {icon}
                </span>
                {!collapsed && label}
              </Link>
            )
          })}
        </nav>

        {/* Spacer — pushes bottom nav items to the bottom */}
        <div className="flex-1" />

        {/* Bottom nav links */}
        <nav className={cn('py-2 space-y-0.5', collapsed ? 'px-1' : 'pr-4')}>
          {bottomItems.map(({ label, href, icon, public: isPublic }) => {
            const active = pathname === href || (pathname ?? '').startsWith(href)
            const locked = !isPublic && !isAuthenticated

            if (locked) {
              return (
                <button
                  key={href}
                  onClick={() => handleProtectedClick(href)}
                  title={collapsed ? `${label} (sign in required)` : undefined}
                  className={cn(
                    'w-full flex items-center gap-3 py-3 text-[13px] font-semibold transition-all duration-200',
                    'text-on-surface-variant/50 hover:text-on-surface-variant hover:bg-surface-container/30',
                    collapsed
                      ? 'justify-center px-2 rounded-full mx-1'
                      : 'px-6 rounded-r-full'
                  )}
                >
                  <span
                    className="material-symbols-outlined text-[20px] shrink-0"
                    style={{ fontVariationSettings: "'FILL' 0" }}
                  >
                    {icon}
                  </span>
                  {!collapsed && (
                    <span className="flex-1 text-left">{label}</span>
                  )}
                  {!collapsed && (
                    <span
                      className="material-symbols-outlined text-[14px] text-on-surface-variant/40"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      lock
                    </span>
                  )}
                </button>
              )
            }

            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? label : undefined}
                className={cn(
                  'flex items-center gap-3 py-3 text-[13px] font-semibold transition-all duration-200 hover:translate-x-0.5',
                  collapsed
                    ? 'justify-center px-2 rounded-full mx-1'
                    : 'px-6 rounded-r-full',
                  active
                    ? 'text-on-surface'
                    : 'text-on-surface-variant hover:bg-surface-container/50'
                )}
                style={active ? { backgroundColor: 'var(--nav-active-bg)' } : undefined}
              >
                <span
                  className="material-symbols-outlined text-[20px] shrink-0"
                  style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}
                >
                  {icon}
                </span>
                {!collapsed && label}
              </Link>
            )
          })}
        </nav>

        {/* User row */}
        <div className={cn('pb-4 pt-2 border-t border-outline-variant/30', collapsed ? 'px-1' : 'px-4')}>
          {isAuthenticated && user ? (
            /* Authenticated: show user info + logout */
            collapsed ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center text-[12px] font-semibold text-on-tertiary-container">
                  {user.firstName?.[0] ?? user.email?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <button
                  onClick={toggleTheme}
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                  className="text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {isDark ? 'light_mode' : 'dark_mode'}
                  </span>
                </button>
                <button
                  onClick={logout}
                  title="Sign out"
                  className="text-on-surface-variant hover:text-primary transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">logout</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center shrink-0 text-[12px] font-semibold text-on-tertiary-container">
                  {user.firstName?.[0] ?? user.email?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <div className="overflow-hidden flex-1">
                  <p className="text-[13px] font-medium text-on-surface truncate">
                    {user.firstName ? `${user.firstName} ${user.lastName ?? ''}`.trim() : user.email}
                  </p>
                  <p className="text-[11px] text-on-surface-variant capitalize">{user.role}</p>
                </div>
                <button
                  onClick={toggleTheme}
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                  className="text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {isDark ? 'light_mode' : 'dark_mode'}
                  </span>
                </button>
                <button
                  onClick={logout}
                  title="Sign out"
                  className="text-on-surface-variant hover:text-primary transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">logout</span>
                </button>
              </div>
            )
          ) : (
            /* Unauthenticated: show Login button */
            collapsed ? (
              <div className="flex flex-col items-center gap-2">
                <button
                  onClick={() => { setPendingHref(undefined); setModalOpen(true) }}
                  title="Sign in"
                  className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary hover:opacity-90 transition-opacity"
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    login
                  </span>
                </button>
                <button
                  onClick={toggleTheme}
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                  className="text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {isDark ? 'light_mode' : 'dark_mode'}
                  </span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setPendingHref(undefined); setModalOpen(true) }}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-2xl bg-primary text-on-primary text-[13px] font-semibold hover:opacity-90 transition-opacity"
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    login
                  </span>
                  Sign in
                </button>
                <button
                  onClick={toggleTheme}
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                  className="text-on-surface-variant hover:text-on-surface transition-colors p-1"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {isDark ? 'light_mode' : 'dark_mode'}
                  </span>
                </button>
              </div>
            )
          )}
        </div>
      </aside>

      {/* Login modal — rendered outside aside so it can cover full viewport */}
      <LoginModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        redirectTo={pendingHref}
      />
    </>
  )
}
