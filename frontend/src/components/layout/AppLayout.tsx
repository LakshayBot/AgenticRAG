import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'

interface Props {
  children: React.ReactNode
}

export function AppLayout({ children }: Props) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  // Auto-collapse sidebar on small screens
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 768px)')
    const handler = (e: MediaQueryListEvent) => {
      setSidebarCollapsed(e.matches)
    }
    setSidebarCollapsed(mql.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
      {/* Skip to main */}
      <a href="#main-content" className="skip-to-main">
        Skip to main content
      </a>

      {/* Sidebar — hidden on mobile, toggled via hamburger */}
      <div className="hidden md:block relative shrink-0">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((v) => !v)}
        />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-40 md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 md:hidden">
            <Sidebar
              collapsed={false}
              onToggle={() => setMobileSidebarOpen(false)}
            />
          </div>
        </>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile header */}
        <div className="md:hidden flex items-center h-12 px-4 border-b border-[var(--border)] bg-[var(--bg-surface)] shrink-0">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            aria-label="Open navigation"
            className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        <main
          id="main-content"
          className="flex-1 overflow-y-auto"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
