import { Providers } from '@/app/providers'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <SidebarProvider defaultOpen={false}>
        <AppSidebar />
        <SidebarInset>
          <header className="md:hidden sticky top-0 z-50 flex h-10 items-center px-3 bg-background/80 backdrop-blur-sm border-b">
            <SidebarTrigger />
          </header>
          <main id="main-content" className="flex-1 overflow-auto animate-fade-in">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </Providers>
  )
}
