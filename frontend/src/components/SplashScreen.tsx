import { ArrowRight, Layers3, Sparkles } from 'lucide-react'

type Props = {
  onEnter: () => void
}

export function SplashScreen({ onEnter }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex min-h-screen flex-col bg-[var(--color-surface-0)] text-zinc-100">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-shimmer-opacity absolute -left-1/4 top-0 h-[520px] w-[520px] rounded-full bg-teal-500/15 blur-[120px]" />
        <div className="absolute -right-1/4 bottom-0 h-[480px] w-[480px] rounded-full bg-cyan-600/10 blur-[100px]" />
        <div className="animate-orbit pointer-events-none absolute left-1/2 top-1/2 h-[min(88vw,640px)] w-[min(88vw,640px)] -translate-x-1/2 -translate-y-1/2 rounded-[2.5rem] border border-white/[0.05] shadow-[0_0_80px_-20px_rgba(45,212,191,0.15)]" />
        <div className="animate-orbit-slow pointer-events-none absolute left-1/2 top-1/2 h-[min(72vw,480px)] w-[min(72vw,480px)] -translate-x-1/2 -translate-y-1/2 rounded-[2rem] border border-teal-500/20" />
        <div
          className="absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)`,
            backgroundSize: '64px 64px',
          }}
        />
      </div>

      <header className="relative z-10 flex items-center justify-between px-6 py-6 sm:px-10">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04]">
            <Layers3 className="h-[18px] w-[18px] text-teal-400" strokeWidth={1.75} />
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-200">Briefing Studio</span>
        </div>
        <span className="hidden text-xs font-medium uppercase tracking-[0.2em] text-zinc-500 sm:block">
          FulcrumLATAM
        </span>
      </header>

      <main className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pb-16 pt-4 sm:px-10">
        <div className="animate-splash-fade flex max-w-2xl flex-col items-center text-center">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-1.5 text-xs font-medium text-zinc-400">
            <Sparkles className="h-3.5 w-3.5 text-teal-400/90" strokeWidth={2} />
            AI Engineer assessment · Meeting intelligence POC
          </div>

          <h1 className="font-sans text-4xl font-semibold leading-[1.1] tracking-tight text-white sm:text-5xl sm:leading-[1.08]">
            From transcript to
            <span className="block bg-gradient-to-r from-teal-300 via-cyan-200 to-teal-400 bg-clip-text text-transparent">
              leadership-ready slides
            </span>
          </h1>

          <p className="mt-6 max-w-md text-[15px] leading-relaxed text-zinc-400 sm:max-w-lg sm:text-base">
            Ingest recordings or text, summarize with Gemini on the server, and export a structured deck.
            Real-time progress via Server-Sent Events—built for clarity, not clutter.
          </p>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:gap-5">
            <button
              type="button"
              onClick={onEnter}
              className="group inline-flex items-center justify-center gap-2 rounded-full bg-teal-400 px-8 py-3.5 text-sm font-semibold text-zinc-950 shadow-lg shadow-teal-500/20 transition hover:bg-teal-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/80 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
            >
              Enter workspace
              <ArrowRight
                className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                strokeWidth={2.25}
              />
            </button>
            <p className="max-w-[220px] text-center text-xs leading-relaxed text-zinc-500 sm:max-w-none sm:text-left">
              Keys stay in <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-zinc-400">backend/.env</code>
              — never exposed to the browser.
            </p>
          </div>
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/[0.06] px-6 py-4 text-center text-[11px] text-zinc-600 sm:px-10">
        Main Street AI Advisors · structured outputs for human review before distribution
      </footer>
    </div>
  )
}
