'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { useTheme } from '@/hooks/useTheme'
import { LoginModal } from '@/components/layout/LoginModal'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from '@/components/ui/sidebar'
import { Shield, Search, Brain, BarChart3, LayoutDashboard, ShieldAlert, Cog, LogIn, Sun, Moon } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const TOP_NAV = [
  { label: 'Overview',      href: '/dashboard',  icon: LayoutDashboard, isPublic: true  },
  { label: 'Threat Intel',  href: '/advisories', icon: ShieldAlert,   isPublic: false },
  { label: 'Analytics',     href: '/analytics',  icon: BarChart3,     isPublic: false },
]

const BOTTOM_NAV = [
  { label: 'AI Query',          href: '/ask',     icon: Brain,          isPublic: false },
  { label: 'Search Incidents',  href: '/search',  icon: Search,         isPublic: false },
]

const ADMIN_ITEM = { label: 'System Health', href: '/admin', icon: Cog, isPublic: false }

export function AppSidebar() {
  const pathname        = usePathname()
  const { user, isAuthenticated, logout } = useAuthStore()
  const { isDark, toggle: toggleTheme } = useTheme()
  const isAdmin         = user?.role === 'admin'
  const [apiVersion, setApiVersion] = useState<string>('')
  const [modalOpen, setModalOpen] = useState(false)
  const [pendingHref, setPendingHref] = useState<string | undefined>(undefined)

  useEffect(() => {
    fetch(`${API_BASE}/version`)
      .then((r) => r.json())
      .then((data) => setApiVersion(data.version ?? ''))
      .catch(() => setApiVersion(''))
  }, [])

  const topItems    = isAdmin ? [...TOP_NAV, ADMIN_ITEM] : TOP_NAV
  const bottomItems = BOTTOM_NAV

  return (
    <>
      <Sidebar collapsible="icon" variant="sidebar">
        {/* ── Header ─────────────────────────────────────────────── */}
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Shield className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">CyberGuard</span>
                  {apiVersion && (
                    <span className="text-[10px] text-muted-foreground">v{apiVersion}</span>
                  )}
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        {/* ── Top Nav ────────────────────────────────────────────── */}
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Main</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {topItems.map(({ label, href, icon: Icon, isPublic }) => {
                  const active = pathname === href || (href !== '/dashboard' && (pathname ?? '').startsWith(href))
                  const locked = !isPublic && !isAuthenticated

                  if (locked) {
                    return (
                      <SidebarMenuItem key={href}>
                        <SidebarMenuButton
                          onClick={() => {
                            setPendingHref(href)
                            setModalOpen(true)
                          }}
                          tooltip={label}
                        >
                          <Icon />
                          <span>{label}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    )
                  }

                  return (
                    <SidebarMenuItem key={href}>
                      <SidebarMenuButton isActive={active} tooltip={label} render={<Link href={href} />}>
                        <Icon />
                        <span>{label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarGroup className="mt-auto">
            <SidebarGroupLabel>Tools</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {bottomItems.map(({ label, href, icon: Icon, isPublic }) => {
                  const active = pathname === href || (pathname ?? '').startsWith(href)
                  const locked = !isPublic && !isAuthenticated

                  if (locked) {
                    return (
                      <SidebarMenuItem key={href}>
                        <SidebarMenuButton
                          onClick={() => {
                            setPendingHref(href)
                            setModalOpen(true)
                          }}
                          tooltip={label}
                        >
                          <Icon />
                          <span>{label}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    )
                  }

                  return (
                    <SidebarMenuItem key={href}>
                      <SidebarMenuButton isActive={active} tooltip={label} render={<Link href={href} />}>
                        <Icon />
                        <span>{label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        {/* ── Footer ─────────────────────────────────────────────── */}
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              {isAuthenticated && user ? (
                <SidebarMenuButton
                  onClick={logout}
                  tooltip="Sign out"
                >
                  <div className="flex aspect-square size-6 items-center justify-center rounded-md bg-sidebar-primary/10 text-sidebar-primary text-[10px] font-bold">
                    {user.firstName?.[0] ?? user.email?.[0]?.toUpperCase() ?? 'U'}
                  </div>
                  <span className="truncate">
                    {user.firstName ? `${user.firstName} ${user.lastName ?? ''}`.trim() : user.email}
                  </span>
                </SidebarMenuButton>
              ) : (
                <SidebarMenuButton
                  onClick={() => {
                    setPendingHref(undefined)
                    setModalOpen(true)
                  }}
                  tooltip="Sign in"
                >
                  <LogIn className="size-4" />
                  <span>Sign in</span>
                </SidebarMenuButton>
              )}
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton onClick={toggleTheme} tooltip={isDark ? 'Light mode' : 'Dark mode'}>
                {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
                <span>{isDark ? 'Light' : 'Dark'} mode</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      <LoginModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        redirectTo={pendingHref}
      />
    </>
  )
}
