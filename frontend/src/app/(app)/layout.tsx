import { Providers } from '@/app/providers'
import { Sidebar } from '@/components/layout/Sidebar'
import { AuthGuard } from '@/components/layout/AuthGuard'
import { DemoBanner } from '@/components/layout/DemoBanner'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <AuthGuard>
        <div className="flex flex-col min-h-screen bg-background">
          <DemoBanner />
          <div className="flex flex-1">
            <Sidebar />
            <main id="main-content" className="flex-1 overflow-auto animate-fade-in">
              {children}
            </main>
          </div>
        </div>
      </AuthGuard>
    </Providers>
  )
}
