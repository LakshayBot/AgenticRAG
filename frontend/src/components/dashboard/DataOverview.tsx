'use client'

import React from 'react'
import { motion, useMotionValue, useMotionTemplate, useAnimationFrame } from 'framer-motion'
import type { AdvisoryStats, SystemStatsResponse } from '@/lib/types'

// ── Infinite scrolling grid (no colour blobs) ──────────────────────────────
function GridPattern({ offsetX, offsetY }: { offsetX: ReturnType<typeof useMotionValue<number>>; offsetY: ReturnType<typeof useMotionValue<number>> }) {
  return (
    <svg className="w-full h-full">
      <defs>
        <motion.pattern
          id="dov-grid"
          width="40"
          height="40"
          patternUnits="userSpaceOnUse"
          x={offsetX}
          y={offsetY}
        >
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.8" className="text-on-surface" />
        </motion.pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dov-grid)" />
    </svg>
  )
}

function InfiniteGrid() {
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const gridOffsetX = useMotionValue(0)
  const gridOffsetY = useMotionValue(0)

  useAnimationFrame(() => {
    gridOffsetX.set((gridOffsetX.get() + 0.3) % 40)
    gridOffsetY.set((gridOffsetY.get() + 0.3) % 40)
  })

  const maskImage = useMotionTemplate`radial-gradient(320px circle at ${mouseX}px ${mouseY}px, black, transparent)`

  return (
    <div
      className="absolute inset-0 rounded-[32px] overflow-hidden pointer-events-none"
      onMouseMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect()
        mouseX.set(e.clientX - r.left)
        mouseY.set(e.clientY - r.top)
      }}
      // re-enable pointer events just for mouse tracking
      style={{ pointerEvents: 'auto' }}
    >
      {/* Base dim grid — always visible */}
      <div className="absolute inset-0 opacity-[0.04]">
        <GridPattern offsetX={gridOffsetX} offsetY={gridOffsetY} />
      </div>
      {/* Bright grid revealed under cursor */}
      <motion.div
        className="absolute inset-0 opacity-[0.18]"
        style={{ maskImage, WebkitMaskImage: maskImage }}
      >
        <GridPattern offsetX={gridOffsetX} offsetY={gridOffsetY} />
      </motion.div>
    </div>
  )
}

interface DataOverviewProps {
  stats: AdvisoryStats
  systemStats?: SystemStatsResponse
}

// SVG logos for ecosystems — inline so no external deps
function PythonLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 255" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="py-a" x1="12.959%" y1="12.039%" x2="79.639%" y2="78.201%">
          <stop offset="0%" stopColor="#387EB8"/>
          <stop offset="100%" stopColor="#366994"/>
        </linearGradient>
        <linearGradient id="py-b" x1="19.128%" y1="20.579%" x2="90.742%" y2="88.429%">
          <stop offset="0%" stopColor="#FFE052"/>
          <stop offset="100%" stopColor="#FFC331"/>
        </linearGradient>
      </defs>
      <path fill="url(#py-a)" d="M126.916.072c-64.832 0-60.784 28.115-60.784 28.115l.072 29.128h61.868v8.745H41.631S.145 61.355.145 126.77c0 65.417 36.21 63.097 36.21 63.097h21.61v-30.356s-1.165-36.21 35.632-36.21h61.362s34.475.557 34.475-33.319V33.97S194.67.072 126.916.072zM92.802 19.66a11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13 11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.13z"/>
      <path fill="url(#py-b)" d="M128.757 254.126c64.832 0 60.784-28.115 60.784-28.115l-.072-29.127H127.6v-8.745h86.441s41.486 4.705 41.486-60.712c0-65.416-36.21-63.096-36.21-63.096h-21.61v30.355s1.165 36.21-35.632 36.21h-61.362s-34.475-.557-34.475 33.32v56.013s-5.235 33.897 62.519 33.897zm34.114-19.586a11.12 11.12 0 0 1-11.13-11.13 11.12 11.12 0 0 1 11.13-11.13 11.12 11.12 0 0 1 11.13 11.13 11.12 11.12 0 0 1-11.13 11.13z"/>
    </svg>
  )
}

function JavaScriptLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
      <rect width="256" height="256" rx="16" fill="#F7DF1E"/>
      <path d="M67.312 213.932l19.59-11.856c3.78 6.701 7.218 12.371 15.465 12.371 7.905 0 12.89-3.092 12.89-15.12v-81.798h24.057v82.138c0 24.917-14.606 36.259-35.916 36.259-19.245 0-30.416-9.967-36.087-21.994M152.381 211.354l19.588-11.341c5.157 8.421 11.859 14.607 23.715 14.607 9.969 0 16.325-4.984 16.325-11.858 0-8.248-6.53-11.17-17.528-15.98l-6.013-2.58c-17.357-7.393-28.876-16.673-28.876-36.258 0-18.044 13.747-31.792 35.228-31.792 15.294 0 26.292 5.328 34.196 19.247l-18.732 12.03c-4.125-7.389-8.591-10.31-15.465-10.31-7.046 0-11.514 4.468-11.514 10.31 0 7.217 4.468 10.14 14.778 14.608l6.014 2.577c20.45 8.765 31.963 17.7 31.963 37.804 0 21.654-17.012 33.51-39.867 33.51-22.339 0-36.774-10.654-43.816-24.574"/>
    </svg>
  )
}

function NpmLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
      <rect width="256" height="256" rx="16" fill="#CB3837"/>
      <path fill="#fff" d="M48 48h160v160H144v-96H112v96H48z"/>
      <path fill="#CB3837" d="M64 64h128v128H144V96h-32v96H64z" opacity="0"/>
      <rect x="144" y="64" width="48" height="128" fill="#CB3837"/>
    </svg>
  )
}

function GoLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 96" xmlns="http://www.w3.org/2000/svg">
      <g fill="#00ADD8">
        <path d="M16 26.4c-.4 0-.5-.2-.3-.5l2.1-2.7c.2-.3.7-.5 1.1-.5H77c.4 0 .5.3.3.6l-1.7 2.6c-.2.3-.7.6-1 .6L16 26.4z"/>
        <path d="M.5 36.3c-.4 0-.5-.2-.3-.5l2.1-2.7c.2-.3.7-.5 1.1-.5h73.6c.4 0 .6.3.5.6l-.8 2.4c-.1.4-.5.7-.9.7L.5 36.3z"/>
        <path d="M25.6 46.2c-.4 0-.5-.3-.3-.6l1.4-2.5c.2-.3.6-.6 1-.6h32.3c.4 0 .6.3.6.7l-.2 2.4c0 .4-.4.7-.7.7L25.6 46.2z"/>
        <path d="M196.5 23.9c-9.2 2.4-15.5 4.2-24.6 6.6-2.2.6-2.3.7-4.2-1.5-2.1-2.5-3.7-4.1-6.7-5.5-9-4.4-17.7-3.1-25.8 2-9.6 6.1-14.6 15.2-14.4 26.5.1 11.2 7.8 20.4 18.9 21.9 9.5 1.3 17.5-2.1 23.9-9.2.6-.8 1.2-1.6 1.9-2.6h-21.5c-3.1 0-3.8-1.9-2.8-4.4 1.9-4.6 5.4-12.3 7.4-16.2.5-.9 1.5-2.4 3-2.4H232c-.2 2.7-.2 5.4-.6 8.1-1.7 11.3-5.9 21.7-13 30.4-11.5 14-26.2 22.6-44.4 24.9-15.2 1.9-29.3-1.2-41.5-10.2-11.3-8.3-17.8-19.5-19.4-33.4-1.9-16.6 2.8-31.5 12.8-44.7C137.4 2.5 151.8-4.5 169 2.3c11.1 4.4 18.4 12.2 23.1 22.9.5.9.2 1.4-.7 1.7h5.1z"/>
        <path d="M241.8 68.9c-14.1-.3-26.8-4.3-37.5-13.5-8.8-7.7-14.3-17.5-16.3-29-3.1-17.5 1.2-33.1 11.8-46.8C211.2-34.6 228-42 247.7-40.5c17.1 1.3 31.5 8.1 43 20.7 10.6 11.6 15.7 25.4 15.3 41-.5 21-8.2 38.3-23.5 52.1-11.3 10.1-24.6 15.9-39.1 16.2-1.2 0-1.2-.1-.6-.1 0 0 0 0 0 0v-.5h-1zm19.7-76.2c-.1-1.3-.1-2.3-.3-3.3-1.7-9.5-10.3-15.7-19.6-14.1-9.1 1.6-15.4 8.6-16.5 18-.9 7.5 2.7 15.3 9.1 19.7 5.1 3.5 10.6 4.3 16.4 2.4 9.2-3 13.8-10 10.9-22.7z"/>
      </g>
    </svg>
  )
}

function RustLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 106 106" xmlns="http://www.w3.org/2000/svg">
      <circle cx="53" cy="53" r="52" fill="#CE422B"/>
      <path fill="#fff" d="M46.7 68.7v4.6H30.4c0 0-1.7-.1-1.7-1.7 0-1.6 1.6-1.7 1.6-1.7l6.1-.1V55.5h-6c0 0-1.7 0-1.7-1.7 0-1.7 1.7-1.7 1.7-1.7h17.1c0 0 1.7 0 1.7 1.7 0 1.7-1.7 1.7-1.7 1.7h-4.8v13.2h3zm0-24.6c0 2.3-1.9 4.2-4.2 4.2-2.3 0-4.2-1.9-4.2-4.2 0-2.3 1.9-4.2 4.2-4.2 2.3 0 4.2 1.9 4.2 4.2zm28 7c-.2-5.2-4-9-9.3-9H52.2V73.3h6v-8.9h4.5l5.7 8.9H75l-6.3-9.7c3.5-1.4 5.9-4.9 6-9.5zm-9.7 4.7h-7.8v-9h7.8c2.5 0 4.2 1.9 4.2 4.5 0 2.6-1.7 4.5-4.2 4.5z"/>
    </svg>
  )
}

function MavenLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
      <rect width="256" height="256" rx="16" fill="#C71A36"/>
      <path fill="#fff" d="M128 32L80 128l24 8 24-64 24 64 24-8L128 32zm0 128a16 16 0 1 0 0 32 16 16 0 0 0 0-32z"/>
    </svg>
  )
}

function RubyLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 256 255" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="rb-a" x1="84.75%" y1="111.399%" x2="58.254%" y2="64.584%">
          <stop offset="0%" stopColor="#FB7655"/>
          <stop offset="100%" stopColor="#E42B1E"/>
        </linearGradient>
      </defs>
      <path fill="url(#rb-a)" d="M197.467 167.764l-145.334 86.312L256 243.937z"/>
      <path fill="#E42B1E" d="M52.133 254.076L200.85 167.4 256 243.937z" opacity=".5"/>
      <path fill="#fff" d="M128 32c-52.9 0-96 43.1-96 96 0 20.7 6.6 40 17.8 55.8l156.4-92.8C194.6 61.6 163.5 32 128 32z" opacity=".2"/>
      <circle cx="128" cy="128" r="96" fill="none" stroke="#E42B1E" strokeWidth="8"/>
    </svg>
  )
}

export function DataOverview({ stats, systemStats }: DataOverviewProps) {
  const critical = stats.severityBreakdown['critical'] ?? 0
  const total = stats.totalAdvisories || 1

  const critPct = critical / total
  const CIRC = 2 * Math.PI * 40

  // Ecosystem nodes — positioned mathematically on orbit ring
  const ecosystems: {
    label: string
    count: number
    bg: string
    ring: string
    logo: React.ReactNode
  }[] = [
    { label: 'Python',      count: 84, bg: '#EEF6FF', ring: '#3B82F6', logo: <PythonLogo size={22} /> },
    { label: 'npm / JS',    count: 67, bg: '#FEFCE8', ring: '#CA8A04', logo: <JavaScriptLogo size={20} /> },
    { label: 'Go',          count: 31, bg: '#E0F7FA', ring: '#00ACC1', logo: <GoLogo size={18} /> },
    { label: 'Rust',        count: 18, bg: '#FFF3E0', ring: '#CE422B', logo: <RustLogo size={20} /> },
    { label: 'Maven / Java',count: 52, bg: '#FEF2F2', ring: '#C71A36', logo: <MavenLogo size={20} /> },
    { label: 'Ruby Gems',   count: 24, bg: '#FDF4F5', ring: '#CC342D', logo: <RubyLogo size={20} /> },
  ]

  return (
    <div className="bg-surface-container-lowest rounded-[32px] p-6 sm:p-8 shadow-[0_32px_64px_rgba(23,30,13,0.05)] relative overflow-hidden flex flex-col items-center justify-between min-h-[500px] sm:min-h-[600px] h-full w-full">
      {/* Infinite grid background — no colour blobs */}
      <InfiniteGrid />

      {/* Header */}
      <div className="relative z-10 w-full text-left mb-6 self-start">
        <h2 className="font-headline text-3xl sm:text-4xl font-bold text-on-surface tracking-tight">Data Overview</h2>
        <p className="font-body text-sm text-on-surface-variant mt-2">Real-time threat monitoring and resolution status.</p>
      </div>

      {/* Ring Visualization */}
      <div className="relative z-10 w-[280px] h-[280px] sm:w-[360px] sm:h-[360px] md:w-[400px] md:h-[400px] flex items-center justify-center my-auto">

        {/* Single full-size SVG — all rings share the same coordinate space so they're always perfect circles */}
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Outermost slow-spinning solid ring */}
          <circle
            cx="50" cy="50" r="49"
            fill="none"
            stroke="currentColor"
            className="text-outline-variant/20"
            strokeWidth="0.4"
            style={{ transformOrigin: '50px 50px', animation: 'spin 60s linear infinite' }}
          />
          {/* Middle dashed counter-spinning ring */}
          <circle
            cx="50" cy="50" r="46"
            fill="none"
            stroke="currentColor"
            className="text-outline-variant/30"
            strokeWidth="0.4"
            strokeDasharray="2 3"
            style={{ transformOrigin: '50px 50px', animation: 'spin 40s linear infinite reverse' }}
          />
          {/* Track */}
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="currentColor"
            className="text-surface-container-high"
            strokeWidth="8"
          />
          {/* Critical progress arc — revolves continuously */}
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="currentColor"
            className="text-md-primary"
            strokeWidth="8"
            strokeDasharray={`${(critPct * CIRC).toFixed(2)} ${CIRC.toFixed(2)}`}
            strokeLinecap="round"
            style={{ transformOrigin: '50px 50px', animation: 'spin 8s linear infinite' }}
          />
        </svg>

        {/* Center content */}
        <div className="relative z-10 flex flex-col items-center justify-center text-center bg-surface-container-lowest rounded-full w-36 h-36 sm:w-48 sm:h-48 shadow-[0_8px_32px_rgba(23,30,13,0.08)]">
          <div className="font-headline font-light text-4xl sm:text-5xl text-on-surface mb-1 leading-none">
            {critical}
            <span className="text-xl sm:text-2xl text-on-surface-variant/50 font-medium">/{total}</span>
          </div>
          <div className="font-body text-[10px] sm:text-xs font-semibold text-on-surface-variant uppercase tracking-widest px-3 leading-tight mt-1">
            Critical<br />Advisories
          </div>
        </div>

        {/* Orbit ring — rotates as a whole */}
        {/* Each icon counter-rotates at same speed so it stays upright */}
        <style>{`
          @keyframes orbit-cw  { from { transform: rotate(0deg);    } to { transform: rotate(360deg);  } }
          @keyframes orbit-ccw { from { transform: rotate(0deg);    } to { transform: rotate(-360deg); } }
        `}</style>

        {/* Dashed orbit guide ring */}
        <div
          className="absolute rounded-full border border-dashed border-outline-variant/40"
          style={{
            width: '88%', height: '88%',
            top: '6%', left: '6%',
            animation: 'orbit-cw 18s linear infinite',
          }}
        />

        {/* Rotating wrapper — same speed as orbit guide ring */}
        <div
          className="absolute inset-0 w-full h-full z-20"
          style={{ animation: 'orbit-cw 18s linear infinite' }}
        >
          {ecosystems.map(({ label, count, bg, ring, logo }, i) => {
            const angleDeg = (360 / ecosystems.length) * i - 90 // 0 = top
            const angleRad = (angleDeg * Math.PI) / 180
            const orbitR = 44  // % of half-container width (fits inside the 88% guide ring)
            const cx = 50 + orbitR * Math.cos(angleRad)
            const cy = 50 + orbitR * Math.sin(angleRad)
            return (
              <div
                key={label}
                className="absolute group"
                style={{ left: `${cx}%`, top: `${cy}%`, transform: 'translate(-50%, -50%)' }}
              >
                {/* Counter-rotate the bubble + badge so they stay upright while orbiting */}
                <div style={{ animation: 'orbit-ccw 18s linear infinite' }}>
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-30">
                    <div
                      className="text-[10px] font-semibold whitespace-nowrap px-2.5 py-1 rounded-lg shadow-lg text-white"
                      style={{ background: ring }}
                    >
                      {label} · {count} advisories
                    </div>
                  </div>

                  {/* Icon bubble */}
                  <div
                    className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center cursor-pointer relative transition-transform hover:scale-110"
                    style={{
                      background: bg,
                      border: `2.5px solid ${ring}`,
                      boxShadow: `0 2px 8px ${ring}30, 0 0 0 3px ${ring}15`,
                    }}
                  >
                    {logo}
                    {/* Count badge */}
                    <span
                      className="absolute -top-1.5 -right-1.5 text-[8px] font-numbers font-bold text-white rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center shadow-sm leading-none"
                      style={{ background: ring }}
                    >
                      {count}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Bottom charts */}
      <div className="relative z-10 w-full mt-12 sm:mt-16 flex flex-col md:flex-row justify-between items-end gap-6 sm:gap-8 self-end">
        {/* Data Ingestion bar chart */}
        <div className="w-full md:w-5/12">
          <div className="font-body text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-3">
            Data Ingestion
          </div>
          <div className="flex items-end gap-1 sm:gap-1.5 h-12 sm:h-16">
            {[
              { key: 'low',      label: 'Low' },
              { key: 'medium',   label: 'Med' },
              { key: 'high',     label: 'High' },
              { key: 'critical', label: 'Crit' },
            ].map(({ key, label }) => {
              const val = stats.severityBreakdown[key] ?? 0
              const max = Math.max(...Object.values(stats.severityBreakdown), 1)
              const pct = Math.max((val / max) * 100, 6)
              const isCrit = key === 'critical'
              return (
                <div
                  key={key}
                  className={`w-full rounded-t-sm transition-colors hover:opacity-80 relative group ${
                    isCrit ? 'bg-md-primary' : 'bg-surface-container-high'
                  }`}
                  style={{ height: `${pct}%` }}
                  title={`${label}: ${val}`}
                >
                  <span className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-[8px] font-semibold text-on-surface-variant/50 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                    {label}
                  </span>
                </div>
              )
            })}
          </div>
          <div className="flex gap-1 sm:gap-1.5 mt-1">
            {['Low', 'Med', 'High', 'Crit'].map((label) => (
              <div key={label} className="flex-1 text-center text-[8px] font-medium text-on-surface-variant/40 uppercase">
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* Service Status */}
        <div className="w-full md:w-5/12">
          <div className="font-body text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-3 md:text-right">
            Service Status
          </div>
          <div className="flex flex-col gap-2 sm:gap-2.5">
            {(() => {
              const services = systemStats?.services.pythonServices ?? {}
              const entries = Object.entries(services)
              if (entries.length === 0) {
                return [
                  { label: 'API Gateway', healthy: true  },
                  { label: 'Hangfire',    healthy: true  },
                  { label: 'Monitoring',  healthy: true  },
                ].map(({ label, healthy }) => (
                  <div key={label} className="flex items-center gap-3 md:justify-end">
                    <span className="text-[10px] sm:text-xs font-medium text-on-surface-variant whitespace-nowrap">
                      {label}
                    </span>
                    <div className="flex gap-1 sm:gap-1.5 w-full md:w-auto">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <div
                          key={i}
                          className={`flex-1 md:w-6 h-1.5 rounded-full ${
                            healthy === false
                              ? i === 0 ? 'bg-[#d97706] dark:bg-[#ffb77a]' : 'bg-surface-container-high'
                              : healthy === true
                                ? 'bg-emerald-500 dark:bg-emerald-400'
                                : 'bg-surface-container-high'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                ))
              }
              return entries.slice(0, 3).map(([name, svc]) => (
                <div key={name} className="flex items-center gap-3 md:justify-end">
                  <span className="text-[10px] sm:text-xs font-medium text-on-surface-variant whitespace-nowrap capitalize">
                    {name.replace(/-/g, ' ')}
                  </span>
                  <div className="flex gap-1 sm:gap-1.5 w-full md:w-auto">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div
                        key={i}
                        className={`flex-1 md:w-6 h-1.5 rounded-full ${
                          svc.healthy
                            ? 'bg-emerald-500 dark:bg-emerald-400'
                            : i === 0
                              ? 'bg-[#d97706] dark:bg-[#ffb77a]'
                              : 'bg-surface-container-high'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              ))
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}
