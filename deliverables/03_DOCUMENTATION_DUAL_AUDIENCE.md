# Part 4 — Documentation (dual audience)

## A. For the client (non-technical)

### What this does

After an important meeting, your team often needs a **short leadership brief**: what was decided, what matters most, and what to do next. This solution **turns a recording or transcript into a draft presentation** you can edit—so you spend less time writing slides from scratch.

### How it helps the business

- **Saves time** for operations and leadership on weekly reviews.
- **Reduces confusion** about decisions and action owners (when paired with your internal discipline on follow-up).
- **Keeps a paper trail**: transcript and structured summary can be stored alongside the final deck.

### How you would use it (phase-one style)

1. **Record** the meeting (or save the transcript).
2. **Upload** the file to the internal tool (or, in a full rollout, place it in an agreed shared folder).
3. **Wait a few minutes** while the system transcribes (if needed), summarizes, and builds the deck.
4. **Review** the draft carefully—especially any customer-facing language. **Nothing should go external without approval.**
5. **Edit** the deck in PowerPoint or import it into Google Slides, then distribute as you already do.

### What you receive

- A **slide deck** with an executive summary, three high-level objectives, three actionable items, and next steps.
- A **JSON summary** your technical partners can use for automation (optional for you).

### Cadence

For a weekly leadership meeting, expect **one package per meeting**. Seasonal peaks may mean more parallel jobs—your technology partner should watch processing time and cost.

---

## B. For the team (technical)

### Automation structure

1. **Frontend (`frontend/`)** — React + Vite UI. Posts `multipart/form-data` to `POST /api/process`, opens **Server-Sent Events** on `GET /api/jobs/{id}/stream`.
2. **Backend (`backend/app/`)** — FastAPI.
   - `pipeline.py` orchestrates ingest → (optional Whisper) → `summarizer.py` → `slides_builder.py`.
   - Artifacts: `backend/output/<job_id>/meeting_briefing.pptx` and `summary.json`.
3. **LLM path** — **`GEMINI_API_KEY`** in `backend/.env` enables **Gemini** JSON extraction (default model `gemini-2.0-flash`, override with `GEMINI_MODEL`). If Gemini is unset, **`OPENAI_API_KEY`** is optional fallback; otherwise **deterministic fallback** in `demo_data.py` (aligned to the bundled synthetic transcript).
4. **Transcript cleaning** — `transcript_clean.py` removes Gmail/header noise when present.

### API keys & secrets

- Set **`GEMINI_API_KEY`** in **`backend/.env`** (loaded at startup). Never embed keys in the frontend. Optional: `GEMINI_MODEL`. OpenAI vars remain an optional fallback if Gemini is not configured.
- In GCP: **Secret Manager** + Cloud Run secret volumes; rotate on a schedule.

### Environment setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787

cd ..\frontend
npm install
npm run dev
```

Vite dev server proxies `/api` → `http://127.0.0.1:8787` by default (POC port). For production, set `VITE_API_URL` to the public API origin if the UI is hosted separately.

### Troubleshooting

| Symptom | Likely cause | What to check |
|---------|----------------|---------------|
| `404` on download | Job failed or ID wrong | SSE `error` event; server logs |
| Transcription errors | Missing key or unsupported codec | `GEMINI_API_KEY` (or `OPENAI_API_KEY` fallback); convert to WAV/MP3 |
| Empty / generic slides | LLM off + transcript not the synthetic sample | Enable key or use “force demo” with sample file |
| SSE stalls | Proxy buffering | `X-Accel-Buffering: no`; Cloud CDN settings |
| CORS errors | UI and API on different origins | Add origin to `CORSMiddleware` in `main.py` |

### Extending the workflow

- Replace `python-pptx` with **Google Slides API** using a service account (domain-wide delegation if required).
- Add **Pub/Sub** (or SQS) between ingest and workers for retries/backoff.
- Persist jobs in **Postgres/Firestore** instead of the in-memory `jobs` dict.
- Add **evaluation harness**: golden transcripts + expected JSON diff.

### Logging & monitoring (recommended)

- **Structured logs** per `job_id`: ingest metadata, durations for ASR/LLM/slide build, model ids.
- **Metrics**: job success rate, p95 latency, ASR minutes, tokens per job, cost estimate per job.
- **Alerts**: spike in failures, quota errors from ASR/LLM, disk usage on output volume.
- **Tracing**: OpenTelemetry to Cloud Trace / X-Ray for cross-service debugging.

### Known failure points (POC)

- **Poor audio quality** → ASR errors or omissions → downstream hallucination risk.
- **No speaker diarization** in POC → attribution may be fuzzy in summary.
- **Multi-instance API** without shared job store → SSE/download inconsistency.
