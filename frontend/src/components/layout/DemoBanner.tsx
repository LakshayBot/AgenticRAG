'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'

export function DemoBanner() {
  const [dismissed, setDismissed] = useState(false)

  if (!IS_DEMO || dismissed) return null

  return (
    <div className={cn(
      'w-full flex items-center gap-3 px-4 py-2.5',
      'bg-[#2d2200] dark:bg-[#2d2200] border-b border-[#7c5c00]/40',
    )}>
      <span
        className="material-symbols-outlined text-[18px] text-[#ffb74d] shrink-0"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        info
      </span>

      <p className="flex-1 text-[12px] text-[#ffcc80] leading-snug">
        <span className="font-semibold text-[#ffb74d]">Demo Hosting</span>
        {' '}— This instance runs on limited resources. The{' '}
        <span className="font-semibold">AI Query</span> feature is disabled to conserve credits.
        To run the full project locally,{' '}
        <a
          href="https://github.com/your-repo-placeholder"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2 hover:text-[#ffe0b2] transition-colors"
        >
          clone the repository →
        </a>
      </p>

      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss banner"
        className="shrink-0 text-[#ffb74d]/60 hover:text-[#ffb74d] transition-colors rounded p-0.5"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  )
}
