import { Providers } from '@/app/providers'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <SidebarProvider defaultOpen={false}>
        <AppSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-7 items-center">
            <SidebarTrigger className="opacity-40 hover:opacity-100 transition-opacity" />
          </header>
          <main id="main-content" className="flex-1 overflow-auto animate-fade-in">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </Providers>
  )
}
