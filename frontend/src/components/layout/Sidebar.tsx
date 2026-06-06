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
  { label: 'Overview',      href: '/dashboard',  icon: 'dashboard',  isPublic: true  },
  { label: 'Threat Intel',  href: '/advisories', icon: 'security',   isPublic: false },
  { label: 'Analytics',     href: '/analytics',  icon: 'bar_chart',  isPublic: false },
]

const BOTTOM_NAV = [
  { label: 'AI Query',          href: '/ask',     icon: 'psychology', isPublic: false },
  { label: 'Search Incidents',  href: '/search',  icon: 'history',    isPublic: false },
]

const ADMIN_ITEM = { label: 'System Health', href: '/admin', icon: 'analytics', isPublic: false }

function NavLink({
  label,
  href,
  icon,
  isPublic,
  active,
  collapsed,
  isAuthenticated,
  onProtectedClick,
}: {
  label: string
  href: string
  icon: string
  isPublic: boolean
  active: boolean
  collapsed: boolean
  isAuthenticated: boolean
  onProtectedClick: (href: string) => void
}) {
  const locked = !isPublic && !isAuthenticated

  if (locked) {
    return (
      <button
        onClick={() => onProtectedClick(href)}
        title={collapsed ? `${label} (sign in required)` : undefined}
        className={cn(
          'w-full flex items-center gap-3 py-2.5 text-[13px] font-medium transition-all duration-200 rounded-xl',
          'text-on-surface-variant/40 hover:text-on-surface-variant hover:bg-surface-container-highest/40',
          collapsed ? 'justify-center px-2' : 'px-3'
        )}
      >
        <span className="material-symbols-outlined text-[20px] shrink-0" style={{ fontVariationSettings: "'FILL' 0" }}>
          {icon}
        </span>
        {!collapsed && <span className="flex-1 text-left">{label}</span>}
        {!collapsed && (
          <span className="material-symbols-outlined text-[14px] opacity-30" style={{ fontVariationSettings: "'FILL' 1" }}>
            lock
          </span>
        )}
      </button>
    )
  }

  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      className={cn(
        'flex items-center gap-3 py-2.5 text-[13px] font-medium transition-all duration-200 rounded-xl',
        collapsed ? 'justify-center px-2' : 'px-3',
        active
          ? 'bg-primary text-on-primary shadow-sm'
          : 'text-on-surface-variant hover:bg-surface-container-highest/40 hover:text-on-surface'
      )}
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
}

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
          'shrink-0 h-screen sticky top-0 flex flex-col bg-surface-container border-r border-outline-variant/10 overflow-y-auto transition-all duration-300',
          collapsed ? 'w-[68px]' : 'w-60'
        )}
      >
        {/* ── Logo ─────────────────────────────────────────────────────── */}
        <div className={cn(
          'border-b border-outline-variant/10',
          collapsed ? 'py-4 flex flex-col items-center gap-3' : 'px-4 py-4'
        )}>
          {collapsed ? (
            <>
              <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shrink-0 shadow-sm">
                <span className="material-symbols-outlined text-on-primary text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                  shield
                </span>
              </div>
              <button
                onClick={() => setCollapsed(false)}
                className="text-on-surface-variant hover:text-on-surface transition-colors rounded-full p-1.5 hover:bg-surface-container-highest"
                title="Expand sidebar"
              >
                <span className="material-symbols-outlined text-[18px]">chevron_right</span>
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shrink-0 shadow-sm">
                  <span className="material-symbols-outlined text-on-primary text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    shield
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="font-headline text-base font-black text-tertiary dark:text-on-surface uppercase tracking-tight leading-none">
                    CyberGuard
                  </h1>
                  {apiVersion && (
                    <span className="text-[9px] font-semibold text-on-surface-variant/50 tracking-wider uppercase">
                      v{apiVersion}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setCollapsed(true)}
                  className="text-on-surface-variant hover:text-on-surface transition-colors rounded-full p-1 hover:bg-surface-container-highest"
                  title="Collapse sidebar"
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                </button>
              </div>
              <p className="text-[10px] text-on-surface-variant/50 font-medium mt-1.5 truncate">
                Tactical Curator
              </p>
            </>
          )}
        </div>

        {/* ── Top Navigation ────────────────────────────────────────────── */}
        <nav className={cn('py-3 space-y-0.5', collapsed ? 'px-2' : 'px-3')}>
          {topItems.map((item) => {
            const active = pathname === item.href || (item.href !== '/dashboard' && (pathname ?? '').startsWith(item.href))
            return (
              <NavLink
                key={item.href}
                {...item}
                active={active}
                collapsed={collapsed}
                isAuthenticated={isAuthenticated}
                onProtectedClick={handleProtectedClick}
              />
            )
          })}
        </nav>

        {/* ── Spacer ────────────────────────────────────────────────────── */}
        <div className="flex-1" />

        {/* ── Section label ─────────────────────────────────────────────── */}
        {!collapsed && (
          <div className="px-4 pb-1">
            <span className="text-[9px] font-semibold text-on-surface-variant/40 uppercase tracking-widest">
              Tools
            </span>
          </div>
        )}

        {/* ── Bottom Navigation ─────────────────────────────────────────── */}
        <nav className={cn('py-2 space-y-0.5', collapsed ? 'px-2' : 'px-3')}>
          {bottomItems.map((item) => {
            const active = pathname === item.href || (pathname ?? '').startsWith(item.href)
            return (
              <NavLink
                key={item.href}
                {...item}
                active={active}
                collapsed={collapsed}
                isAuthenticated={isAuthenticated}
                onProtectedClick={handleProtectedClick}
              />
            )
          })}
        </nav>

        {/* ── User Row ──────────────────────────────────────────────────── */}
        <div className={cn(
          'border-t border-outline-variant/10 bg-surface-container-highest/30',
          collapsed ? 'py-3 flex flex-col items-center gap-2.5' : 'p-3'
        )}>
          {isAuthenticated && user ? (
            collapsed ? (
              <>
                <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center text-[11px] font-bold text-primary">
                  {user.firstName?.[0] ?? user.email?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <button onClick={toggleTheme} title={isDark ? 'Light mode' : 'Dark mode'} className="text-on-surface-variant/60 hover:text-on-surface transition-colors">
                  <span className="material-symbols-outlined text-[16px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
                </button>
                <button onClick={logout} title="Sign out" className="text-on-surface-variant/60 hover:text-primary transition-colors">
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0 text-[11px] font-bold text-primary">
                  {user.firstName?.[0] ?? user.email?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <div className="overflow-hidden flex-1">
                  <p className="text-[12px] font-semibold text-on-surface truncate">
                    {user.firstName ? `${user.firstName} ${user.lastName ?? ''}`.trim() : user.email}
                  </p>
                  <p className="text-[10px] text-on-surface-variant/60 capitalize">{user.role}</p>
                </div>
                <button onClick={toggleTheme} title={isDark ? 'Light mode' : 'Dark mode'} className="text-on-surface-variant/60 hover:text-on-surface transition-colors">
                  <span className="material-symbols-outlined text-[18px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
                </button>
                <button onClick={logout} title="Sign out" className="text-on-surface-variant/60 hover:text-primary transition-colors">
                  <span className="material-symbols-outlined text-[18px]">logout</span>
                </button>
              </div>
            )
          ) : (
            collapsed ? (
              <>
                <button
                  onClick={() => { setPendingHref(undefined); setModalOpen(true) }}
                  title="Sign in"
                  className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary hover:opacity-90 transition-opacity shadow-sm"
                >
                  <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>login</span>
                </button>
                <button onClick={toggleTheme} title={isDark ? 'Light mode' : 'Dark mode'} className="text-on-surface-variant/60 hover:text-on-surface transition-colors">
                  <span className="material-symbols-outlined text-[16px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setPendingHref(undefined); setModalOpen(true) }}
                  className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-primary text-on-primary text-[12px] font-semibold hover:opacity-90 transition-opacity shadow-sm"
                >
                  <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>login</span>
                  Sign in
                </button>
                <button onClick={toggleTheme} title={isDark ? 'Light mode' : 'Dark mode'} className="text-on-surface-variant/60 hover:text-on-surface transition-colors p-1">
                  <span className="material-symbols-outlined text-[18px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
                </button>
              </div>
            )
          )}
        </div>
      </aside>

      <LoginModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        redirectTo={pendingHref}
      />
    </>
  )
}
