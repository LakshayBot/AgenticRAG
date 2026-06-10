import { Providers } from '@/app/providers'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { AuthGuard } from '@/components/layout/AuthGuard'
import { DemoBanner } from '@/components/layout/DemoBanner'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <AuthGuard>
        <div className="flex flex-col min-h-screen bg-background">
          <DemoBanner />
          <SidebarProvider defaultOpen={false}>
            <AppSidebar />
            <SidebarInset>
              <main id="main-content" className="flex-1 overflow-auto animate-fade-in relative">
                <SidebarTrigger className="absolute top-3 left-1.5 z-20 opacity-40 hover:opacity-100 transition-opacity" />
                {children}
              </main>
            </SidebarInset>
          </SidebarProvider>
        </div>
      </AuthGuard>
    </Providers>
  )
}
