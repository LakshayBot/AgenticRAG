'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from 'sonner'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: 1,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'var(--surface-container-lowest)',
              border: '1px solid var(--outline-variant)',
              color: 'var(--on-surface)',
              fontFamily: 'var(--font-body)',
            },
          }}
        />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
