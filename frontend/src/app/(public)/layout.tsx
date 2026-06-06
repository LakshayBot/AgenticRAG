import { Providers } from '@/app/providers'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <SidebarProvider defaultOpen={false}>
        <AppSidebar />
        <SidebarInset>
          <main id="main-content" className="flex-1 overflow-auto animate-fade-in">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </Providers>
  )
}
