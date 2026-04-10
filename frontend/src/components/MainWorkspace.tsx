import {
  ChevronLeft,
  FileJson,
  FileStack,
  FileText,
  Loader2,
  Presentation,
  Radio,
  Square,
  Upload,
} from 'lucide-react'
import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from 'react'

type LogLine = { text: string; kind: 'info' | 'evt' | 'err' }

const apiBase = import.meta.env.VITE_API_URL ?? ''
const uploadTimeoutMs = Number(import.meta.env.VITE_UPLOAD_TIMEOUT_MS ?? 30 * 60 * 1000)

function appendLog(setter: Dispatch<SetStateAction<LogLine[]>>, line: LogLine) {
  setter((prev) => [...prev.slice(-200), line])
}

type WorkspaceProps = {
  onBackToSplash?: () => void
}

export function MainWorkspace({ onBackToSplash }: WorkspaceProps) {
  const [file, setFile] = useState<File | null>(null)
  const [useSample, setUseSample] = useState(true)
  const [forceDemo, setForceDemo] = useState(false)
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<LogLine[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [doneUrls, setDoneUrls] = useState<{
    transcript: string
    pptx: string
    json: string
  } | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const [drag, setDrag] = useState(false)

  const stopStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  const run = async () => {
    stopStream()
    setRunning(true)
    setLogs([])
    setDoneUrls(null)
    setJobId(null)

    const fd = new FormData()
    // If a file is selected, always send it (avoids "sample still on" skipping the upload).
    if (file) {
      fd.append('file', file)
      fd.append('use_sample_file', 'false')
    } else {
      fd.append('use_sample_file', useSample ? 'true' : 'false')
    }
    fd.append('force_demo_summary', forceDemo ? 'true' : 'false')

    appendLog(setLogs, { text: 'POST /api/process', kind: 'info' })

    const url = `${apiBase}/api/process`
    let res: Response
    const ctrl = new AbortController()
    const timer = window.setTimeout(() => ctrl.abort(), uploadTimeoutMs)
    try {
      res = await fetch(url, { method: 'POST', body: fd, signal: ctrl.signal })
    } catch (e) {
      const name = e instanceof Error ? e.name : ''
      const hint =
        'Vite proxy: set VITE_PROXY_API=http://127.0.0.1:8787 (WSL2 port forward). ETIMEDOUT to 192.168… = stale WSL IP. Backend must listen on 0.0.0.0:8787. See npm terminal for [vite] /api proxy target.'
      if (name === 'AbortError') {
        appendLog(setLogs, {
          text: `Upload timed out after ${Math.round(uploadTimeoutMs / 60_000)} min. ${hint}`,
          kind: 'err',
        })
      } else {
        appendLog(setLogs, {
          text: `Network error: ${String(e)}. ${hint}`,
          kind: 'err',
        })
      }
      setRunning(false)
      return
    } finally {
      window.clearTimeout(timer)
    }

    if (!res.ok) {
      let detail = ''
      try {
        const j = (await res.json()) as { message?: string; error?: string }
        detail = j.message || j.error || ''
      } catch {
        /* ignore */
      }
      appendLog(
        setLogs,
        {
          text: detail ? `HTTP ${res.status}: ${detail}` : `HTTP ${res.status} POST ${url}`,
          kind: 'err',
        },
      )
      setRunning(false)
      return
    }

    const data = (await res.json()) as { job_id: string; api_revision?: string }
    const rev = res.headers.get('X-API-Revision') ?? data.api_revision
    setJobId(data.job_id)
    appendLog(
      setLogs,
      {
        text: rev
          ? `job_id ${data.job_id} | api_revision ${rev}`
          : `job_id ${data.job_id} | api_revision MISSING — check VITE_PROXY_API / VITE_USE_WSL_API in frontend/.env.development (POC API port is 8787), restart npm run dev.`,
        kind: rev ? 'evt' : 'err',
      },
    )

    const es = new EventSource(`${apiBase}/api/jobs/${data.job_id}/stream`)
    esRef.current = es

    es.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as { event: string; data: Record<string, unknown> }
        const payload = JSON.stringify(msg.data)
        if (msg.event === 'error') {
          appendLog(setLogs, { text: `${msg.event}: ${payload}`, kind: 'err' })
          setRunning(false)
          es.close()
          return
        }
        appendLog(setLogs, { text: `${msg.event} ${payload}`, kind: 'evt' })
        if (msg.event === 'completed') {
          const d = msg.data as { transcript?: string; pptx?: string; json?: string }
          if (d.pptx && d.json) {
            const base = apiBase || ''
            setDoneUrls({
              transcript: d.transcript ? `${base}${d.transcript}` : '',
              pptx: `${base}${d.pptx}`,
              json: `${base}${d.json}`,
            })
          }
          setRunning(false)
          es.close()
        }
      } catch {
        appendLog(setLogs, { text: ev.data, kind: 'info' })
      }
    }

    es.onerror = () => {
      appendLog(setLogs, { text: 'SSE connection closed or errored', kind: 'err' })
      setRunning(false)
      es.close()
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-surface-0)]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(45,212,191,0.08),transparent)]" />

      <header className="relative z-10 border-b border-white/[0.06] bg-[var(--color-surface-0)]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
              <FileStack className="h-5 w-5 text-teal-400" strokeWidth={1.75} />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-white">Briefing Studio</p>
              <p className="text-xs text-zinc-500">Meeting intelligence to deck</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {onBackToSplash && (
              <button
                type="button"
                onClick={onBackToSplash}
                className="inline-flex items-center gap-1 rounded-lg border border-white/[0.08] px-2.5 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-white/15 hover:text-zinc-200"
              >
                <ChevronLeft className="h-3.5 w-3.5" strokeWidth={2} />
                Welcome
              </button>
            )}
            {running ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-500/25 bg-teal-500/10 px-3 py-1 text-xs font-medium text-teal-300">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Processing
              </span>
            ) : (
              <span className="hidden text-xs text-zinc-500 sm:inline">FulcrumLATAM · POC</span>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-12">
        <div className="mb-10 max-w-2xl">
          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">Pipeline</h1>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400 sm:text-[15px]">
            Transcript or media is summarized with{' '}
            <span className="font-medium text-zinc-300">Gemini</span> (via{' '}
            <code className="rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-xs text-zinc-400">
              GEMINI_API_KEY
            </code>{' '}
            on the server). Each run saves <strong>transcript.txt</strong>, <strong>summary.json</strong>, and{' '}
            <strong>meeting_briefing.pptx</strong> under <code className="font-mono text-xs text-zinc-500">backend/output/&lt;job&gt;/</code> and you can download all three from here when the job finishes.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-12 lg:gap-10">
          <section className="lg:col-span-7">
            <div className="rounded-2xl border border-white/[0.08] bg-[var(--color-surface-2)]/80 p-6 shadow-xl shadow-black/20 backdrop-blur-sm sm:p-8">
              <div className="mb-6 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-500/15 text-xs font-semibold text-teal-400">
                  1
                </span>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Source</h2>
              </div>

              <label
                className={`group relative flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 transition ${
                  drag
                    ? 'border-teal-400/60 bg-teal-500/[0.07]'
                    : 'border-zinc-600/80 bg-zinc-950/40 hover:border-zinc-500 hover:bg-zinc-900/50'
                }`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDrag(true)
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDrag(false)
                  const f = e.dataTransfer.files[0]
                  if (f) {
                    setUseSample(false)
                    setFile(f)
                  }
                }}
              >
                <input
                  type="file"
                  accept=".txt,.md,.mp3,.wav,.mp4,.webm,.m4a"
                  className="absolute inset-0 cursor-pointer opacity-0"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) {
                      setUseSample(false)
                      setFile(f)
                    }
                  }}
                />
                <Upload
                  className={`mb-3 h-10 w-10 transition ${drag ? 'text-teal-400' : 'text-zinc-500 group-hover:text-zinc-400'}`}
                  strokeWidth={1.25}
                />
                <span className="text-center text-sm font-medium text-zinc-300">
                  Drop transcript or media
                </span>
                <span className="mt-1 text-center text-xs text-zinc-500">or click to browse</span>
                {file && (
                  <span className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 font-mono text-xs text-teal-200/90">
                    <FileText className="h-3.5 w-3.5 shrink-0" />
                    {file.name}
                  </span>
                )}
              </label>

              <div className="mt-8 space-y-4">
                <label className="flex cursor-pointer gap-3 rounded-xl border border-white/[0.06] bg-zinc-950/50 p-4 transition hover:border-white/[0.1]">
                  <input
                    type="checkbox"
                    checked={useSample}
                    onChange={() =>
                      setUseSample((v) => {
                        const on = !v
                        if (on) setFile(null)
                        return on
                      })
                    }
                    className="mt-0.5 h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-teal-500 focus:ring-teal-500/40 focus:ring-offset-0"
                  />
                  <span className="text-sm leading-snug text-zinc-400">
                    <span className="font-medium text-zinc-200">Use bundled sample transcript</span>
                    <span className="mt-1 block text-xs text-zinc-500">
                      Turns off when you add a file above; checking this again clears the upload so the
                      run uses{' '}
                      <code className="font-mono text-zinc-400">Syntethic_AI_Transcript.txt</code> only.
                    </span>
                  </span>
                </label>

                <label className="flex cursor-pointer gap-3 rounded-xl border border-white/[0.06] bg-zinc-950/50 p-4 transition hover:border-white/[0.1]">
                  <input
                    type="checkbox"
                    checked={forceDemo}
                    onChange={() => setForceDemo((v) => !v)}
                    className="mt-0.5 h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-teal-500 focus:ring-teal-500/40 focus:ring-offset-0"
                  />
                  <span className="text-sm leading-snug text-zinc-400">
                    <span className="font-medium text-zinc-200">Force deterministic summary</span>
                    <span className="mt-1 block text-xs text-zinc-500">
                      Skip the LLM even if API keys are configured (demo fallback).
                    </span>
                  </span>
                </label>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={running}
                  onClick={() => void run()}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-400 px-5 py-2.5 text-sm font-semibold text-zinc-950 shadow-lg shadow-teal-500/15 transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-45"
                >
                  {running ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Running
                    </>
                  ) : (
                    <>
                      <Presentation className="h-4 w-4" strokeWidth={2} />
                      Run pipeline
                    </>
                  )}
                </button>
                <button
                  type="button"
                  disabled={running}
                  onClick={() => stopStream()}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.12] bg-transparent px-5 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-white/20 hover:bg-white/[0.04] disabled:opacity-40"
                >
                  <Square className="h-4 w-4" strokeWidth={2} />
                  Stop SSE
                </button>
              </div>
            </div>
          </section>

          <section className="lg:col-span-5">
            <div className="lg:sticky lg:top-28">
              <div className="rounded-2xl border border-white/[0.08] bg-[var(--color-surface-2)]/80 p-6 shadow-xl shadow-black/20 backdrop-blur-sm sm:p-8">
                <div className="mb-4 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/15 text-xs font-semibold text-violet-300">
                      2
                    </span>
                    <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                      Live stream
                    </h2>
                  </div>
                  {jobId && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-violet-500/20 bg-violet-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-violet-300">
                      <Radio className="h-3 w-3" />
                      SSE
                    </span>
                  )}
                </div>

                <div className="max-h-[min(52vh,420px)] overflow-y-auto rounded-xl border border-white/[0.06] bg-zinc-950/80 p-4 font-mono text-[11px] leading-relaxed sm:text-xs">
                  {logs.length === 0 ? (
                    <p className="text-zinc-600">Awaiting events…</p>
                  ) : (
                    logs.map((l, i) => (
                      <p
                        key={i}
                        className={
                          l.kind === 'err'
                            ? 'text-red-400/90'
                            : l.kind === 'evt'
                              ? 'text-teal-400/95'
                              : 'text-zinc-500'
                        }
                      >
                        {l.text}
                      </p>
                    ))
                  )}
                </div>

                {doneUrls && (
                  <div className="mt-6 space-y-3">
                    <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Downloads</p>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {doneUrls.transcript ? (
                        <a
                          href={doneUrls.transcript}
                          download="transcript.txt"
                          className="inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-600/80 bg-zinc-900/60 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-teal-500/40 hover:bg-zinc-800/80"
                        >
                          <FileText className="h-4 w-4 text-teal-400/90" />
                          transcript.txt
                        </a>
                      ) : null}
                      <a
                        href={doneUrls.pptx}
                        download="meeting_briefing.pptx"
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-400 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-teal-300"
                      >
                        <Presentation className="h-4 w-4" />
                        .pptx
                      </a>
                      <a
                        href={doneUrls.json}
                        download="summary.json"
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.12] py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/[0.05]"
                      >
                        <FileJson className="h-4 w-4" />
                        summary.json
                      </a>
                    </div>
                    {!apiBase && (
                      <p className="text-[11px] leading-relaxed text-amber-200/70">
                        If downloads fail with connection reset, set{' '}
                        <code className="rounded bg-white/10 px-1 font-mono">VITE_API_URL=http://&lt;WSL-IP&gt;:8787</code> in{' '}
                        <code className="font-mono">frontend/.env.development</code> and restart{' '}
                        <code className="font-mono">npm run dev</code>.
                      </p>
                    )}
                  </div>
                )}
              </div>

              <p className="mt-6 text-xs leading-relaxed text-zinc-600">
                Human review is mandatory before external distribution. Customer-facing copy requires explicit
                approval. API credentials never ship to the client.
              </p>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
