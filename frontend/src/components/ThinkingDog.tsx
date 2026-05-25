'use client'

import { useEffect, useState } from 'react'

const FACTS = [
  'The first computer worm (Morris Worm, 1988) infected ~6,000 machines — 10% of the entire internet.',
  'A new CVE is published roughly every 20 minutes — over 25,000 per year.',
  '"Zero-day" means the vendor has had exactly 0 days to patch the vulnerability.',
  'Log4Shell (CVE-2021-44228) potentially affected over 3 billion devices worldwide.',
  'npm has over 2.1 million published packages — more than any other package registry.',
  'CVSS scores range from 0.0 (none) to 10.0 (critical). 9.0+ means patch immediately.',
  'The term "bug" comes from a real moth found trapped in a Harvard Mark II relay in 1947.',
  'Supply chain attacks increased 742% between 2019 and 2022.',
  'The Heartbleed bug (2014) exposed private keys on ~17% of the world\'s HTTPS servers.',
  'PyPI hosts over 500,000 Python packages — and malicious ones are found every week.',
  'Over 80% of breaches involve compromised credentials, not zero-days.',
  'The first CVE (CVE-1999-0001) was published on January 2, 1999.',
  '"GHSA" stands for GitHub Security Advisory — GitHub publishes thousands each year.',
  'The average time to detect a breach is still over 200 days in most organizations.',
]

// 3-frame ASCII dog — each frame is a small multi-line string rendered in a <pre>
const DOG_FRAMES = [
  // trotting: weight on left legs
  [
    ' /\\_/\\ ',
    '( >.< )',
    ' " " " ',
  ],
  // mid-stride: neutral face
  [
    ' /\\_/\\ ',
    '( -.- )',
    '  ""   ',
  ],
  // weight on right legs
  [
    ' /\\_/\\ ',
    '( ^.^ )',
    ' "  "  ',
  ],
]

export default function ThinkingDog() {
  const [frame, setFrame] = useState(0)
  const [factIdx, setFactIdx] = useState(0)
  const [factKey, setFactKey] = useState(0) // force re-mount for animation reset

  // Dog walks at ~2.5 fps — slow enough to be charming, fast enough to look alive
  useEffect(() => {
    const t = setInterval(() => {
      setFrame(f => (f + 1) % DOG_FRAMES.length)
    }, 400)
    return () => clearInterval(t)
  }, [])

  // Rotate facts every 5 seconds
  useEffect(() => {
    const t = setInterval(() => {
      setFactIdx(i => (i + 1) % FACTS.length)
      setFactKey(k => k + 1)
    }, 5000)
    return () => clearInterval(t)
  }, [])

  const lines = DOG_FRAMES[frame]

  return (
    <div className="flex items-center gap-3 py-0.5 select-none">
      {/* ASCII dog — fixed-width so the bubble doesn't jump between frames */}
      <pre
        className="font-mono text-[11px] leading-[1.35] text-md-primary shrink-0 m-0 p-0"
        style={{ fontFamily: 'monospace', whiteSpace: 'pre' }}
        aria-hidden="true"
      >
        {lines[0]}{'\n'}{lines[1]}{'\n'}{lines[2]}
      </pre>

      {/* Fact area */}
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-[10px] font-medium text-md-primary/70 uppercase tracking-wider leading-none">
          Did you know?
        </span>
        {/* key-based remount resets the CSS animation on each fact change */}
        <span
          key={factKey}
          className="text-[12px] text-on-surface-variant leading-snug animate-fact-fade"
          style={{ animationFillMode: 'both' }}
        >
          {FACTS[factIdx]}
        </span>
      </div>
    </div>
  )
}
