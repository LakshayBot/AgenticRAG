import { Providers } from '@/app/providers'
import { Sidebar } from '@/components/layout/Sidebar'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-auto animate-fade-in">
          {children}
        </main>
      </div>
    </Providers>
  )
}
