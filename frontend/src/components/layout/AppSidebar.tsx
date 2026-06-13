'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/authStore'
import { useTheme } from '@/hooks/useTheme'
import { LoginModal } from '@/components/layout/LoginModal'
import { conversationsApi } from '@/lib/api'
import { cn } from '@/lib/utils'
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
  useSidebar,
} from '@/components/ui/sidebar'
import { Shield, Search, Brain, BarChart3, LayoutDashboard, ShieldAlert, Cog, LogIn, Sun, Moon, Plus, MessageSquare, PanelLeftClose, PanelLeft } from 'lucide-react'
import { formatDistanceToNow, parseISO } from 'date-fns'

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

function ChatHistoryList() {
  const pathname = usePathname()
  const { isAuthenticated } = useAuthStore()
  const queryClient = useQueryClient()
  const { setOpenMobile, state } = useSidebar()

  const [activeId, setActiveId] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    setActiveId(pathname.startsWith('/ask') ? params.get('c') : null)
  }, [pathname])

  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
    staleTime: 30_000,
    enabled: isAuthenticated,
  })

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    await conversationsApi.delete(id)
    queryClient.invalidateQueries({ queryKey: ['conversations'] })
  }

  if (!isAuthenticated) return null

  const isCollapsed = state === 'collapsed'
  const items = conversations?.slice(0, 20) ?? []

  // --- Collapsed state: compact icon with count badge ---
  if (isCollapsed) {
    return (
      <SidebarGroup>
        <SidebarGroupLabel className="justify-center">
          {items.length > 0 ? (
            <Link href="/ask" className="relative" title="Chat History">
              <MessageSquare className="size-4 text-muted-foreground" />
              <span className="absolute -top-1.5 -right-2.5 flex items-center justify-center min-w-[14px] h-[14px] rounded-full bg-sidebar-primary text-[8px] font-bold text-sidebar-primary-foreground leading-none px-0.5">
                {items.length}
              </span>
            </Link>
          ) : (
            <MessageSquare className="size-4 text-muted-foreground/50" />
          )}
        </SidebarGroupLabel>
        <SidebarGroupContent />
      </SidebarGroup>
    )
  }

  // --- Expanded state: full chat list ---
  return (
    <SidebarGroup className="flex-1 min-h-0 overflow-hidden">
      <SidebarGroupLabel>
        <span className="flex-1">Chat History</span>
        <Link
          href="/ask"
          onClick={() => setOpenMobile(false)}
          className="text-[10px] text-muted-foreground hover:text-sidebar-primary transition-colors flex items-center gap-0.5 shrink-0"
        >
          <Plus className="size-3" />
        </Link>
      </SidebarGroupLabel>
      <SidebarGroupContent className="flex-1 min-h-0">
        {isLoading ? (
          <div className="space-y-2 px-1 py-1">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-1.5 rounded-md px-2 py-1.5">
                <div className="h-3 bg-sidebar-accent/60 rounded animate-pulse w-full" />
                <div className="h-3 bg-sidebar-accent/60 rounded animate-pulse w-2/3" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="px-2 py-3 text-[11px] text-muted-foreground text-center">
            Start a new chat to investigate threats
          </p>
        ) : (
          <div className="overflow-y-auto flex-1 min-h-0">
            {items.map((conv) => {
              const active = activeId === conv.id
              const timeStr = formatDistanceToNow(parseISO(conv.updatedAt), { addSuffix: true })
              return (
                <Link
                  key={conv.id}
                  href={`/ask?c=${conv.id}`}
                  onClick={() => setOpenMobile(false)}
                  className={cn(
                    'group relative flex flex-col px-2 py-1.5 rounded-[4px] transition-colors',
                    'border-l-2',
                    active
                      ? 'border-l-sidebar-primary bg-sidebar-accent/50'
                      : 'border-l-transparent hover:bg-sidebar-accent/30'
                  )}
                >
                  <span className="text-[12px] leading-snug text-sidebar-foreground line-clamp-2 font-medium">
                    {conv.title}
                  </span>
                  <span className="mt-0.5 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground leading-none">
                      {timeStr}
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, conv.id)}
                      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity text-muted-foreground hover:text-red-500 shrink-0"
                      aria-label={`Delete "${conv.title}"`}
                    >
                      <svg width="12" height="12" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" className="size-3">
                        <path d="M5.5 1C5.22386 1 5 1.22386 5 1.5V3H1.5C1.22386 3 1 3.22386 1 3.5C1 3.77614 1.22386 4 1.5 4H2V13.5C2 13.7761 2.22386 14 2.5 14H12.5C12.7761 14 13 13.7761 13 13.5V4H13.5C13.7761 4 14 3.77614 14 3.5C14 3.22386 13.7761 3 13.5 3H10V1.5C10 1.22386 9.77614 1 9.5 1H5.5ZM6 2.5V3H9V2.5C9 2.22386 8.77614 2 8.5 2H6.5C6.22386 2 6 2.22386 6 2.5ZM3 4H12V13H3V4Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd" />
                      </svg>
                    </button>
                  </span>
                </Link>
              )
            })}
          </div>
        )}
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

export function AppSidebar() {
  const pathname        = usePathname()
  const { user, isAuthenticated, logout } = useAuthStore()
  const { isDark, toggle: toggleTheme } = useTheme()
  const isAdmin         = user?.role === 'admin'
  const [apiVersion, setApiVersion] = useState<string>('')
  const [modalOpen, setModalOpen] = useState(false)
  const [pendingHref, setPendingHref] = useState<string | undefined>(undefined)
  const { setOpenMobile, state, setOpen, isMobile } = useSidebar()
  const [lockedOpen, setLockedOpen] = useState(false)
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleMouseEnter = useCallback(() => {
    if (isMobile || lockedOpen) return
    if (leaveTimerRef.current) {
      clearTimeout(leaveTimerRef.current)
      leaveTimerRef.current = null
    }
    setOpen(true)
  }, [isMobile, lockedOpen, setOpen])

  const handleMouseLeave = useCallback(() => {
    if (isMobile || lockedOpen) return
    leaveTimerRef.current = setTimeout(() => {
      setOpen(false)
    }, 400)
  }, [isMobile, lockedOpen, setOpen])

  const handleToggleClick = useCallback(() => {
    if (state === 'collapsed') {
      setOpen(true)
      setLockedOpen(true)
    } else if (lockedOpen) {
      setLockedOpen(false)
      setOpen(false)
    } else {
      setLockedOpen(true)
    }
  }, [state, lockedOpen, setOpen])

  useEffect(() => {
    return () => {
      if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current)
    }
  }, [])

  const isExpanded = state === 'expanded'

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
      <Sidebar collapsible="icon" variant="sidebar" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
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
                            setOpenMobile(false)
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

          <SidebarGroup>
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
                            setOpenMobile(false)
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

          <ChatHistoryList />
        </SidebarContent>

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
                    setOpenMobile(false)
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
            <SidebarMenuItem>
              <SidebarMenuButton onClick={handleToggleClick} tooltip={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'}>
                {isExpanded ? <PanelLeftClose className="size-4" /> : <PanelLeft className="size-4" />}
                <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
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
