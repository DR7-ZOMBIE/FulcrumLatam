# Meeting → Slides POC (FulcrumLATAM / Main Street AI Advisors)

Proof of concept: ingest meeting **transcript or media**, summarize into executive summary + 3 objectives + 3 actions + next steps, emit an editable **PowerPoint** file (uploadable to Google Slides) and **JSON** sidecar. The UI streams **SSE** progress events from a **Python (FastAPI)** backend. A **deterministic fallback** works without API keys for the bundled synthetic transcript.

## Assumptions (explicit)

- **Synthetic input file** is `Syntethic_AI_Transcript.txt` at the repo root (filename spelling as provided). The first lines may be Gmail noise; the backend strips content before the `Synthetic Transcript` marker or first `[mm:ss]` cue.
- **Google Slides**: native API OAuth scope is not implemented in the 2-hour POC; **`.pptx` is the interchange format** (File → Import to Google Slides).
- **Privacy**: media and transcripts are processed in memory / ephemeral temp files; outputs land under `backend/output/<job_id>/`. A production design would use per-tenant buckets, encryption at rest, retention policies, and audit logs (see `deliverables/`).
- **Firebase**: **Firebase Hosting** serves the static Vite build. **SSE + multipart uploads** are a better fit for **Cloud Run** (or similar) behind Hosting rewrites, not classic short-lived Functions-only stacks.

## Local run

**Terminal A — backend**

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Optional: create `backend/.env` with **`GEMINI_API_KEY`** (recommended) for summarization and for transcribing audio/video uploads. If Gemini is unset, **`OPENAI_API_KEY`** is used as a fallback for both. Never commit real keys.

**Terminal B — frontend**

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Enable “Use bundled sample” and run, or upload `.txt` / audio / video.

**POC API port is `8787`** (not 8000) to avoid clashes with other tools. Scripts `run_backend_wsl.sh` / `run_dev_wsl.sh` use it by default; override with **`PORT=9000 ./run_backend_wsl.sh`**.

**Windows + WSL gotcha:** If you run **`npm run dev` on Windows** but **`uvicorn` only inside WSL**, the default proxy hits **`127.0.0.1:8787` on Windows** — wrong if the API is only in WSL. You will see `api_revision MISSING`.

Fix (pick one):

1. **`VITE_PROXY_API=http://<WSL-LAN-IP>:8787`** in `frontend/.env.development` (mirrored networking: IP from `ip a`, e.g. `192.168.1.x`). The repo ships an example; adjust the IP if DHCP changes.
2. **`VITE_USE_WSL_API=true`** — Vite picks the WSL IP and uses port **8787** (or **`VITE_API_PORT`**).
3. Run uvicorn **on Windows** from `backend/` on **8787** so `127.0.0.1:8787` matches the default Vite proxy.

If everything runs on Windows only, you can delete `frontend/.env.development` or point `VITE_PROXY_API` at `http://127.0.0.1:8787`.

**WSL uvicorn must bind `0.0.0.0`**, not only `127.0.0.1`, or the Windows→WSL proxy gets **`Failed to fetch` / `ERR_CONNECTION_RESET`**. The `run_backend_wsl.sh` script already uses `--host 0.0.0.0`.

**This is not a curl/CORS bug:** the browser talks to Vite (`localhost:5173`), and Vite proxies `/api`. Curl to `127.0.0.1:8787` only hits **Windows**, not WSL. Compare:

```powershell
curl.exe -s http://127.0.0.1:8787/api/health
curl.exe -s http://192.168.REPLACE.WSL.IP:8787/api/health
```

If the first JSON has no `api_revision` (or wrong behavior) and the second matches your WSL logs, the proxy fix above is what you need.

### WSL / Linux

Uvicorn must be started with **`backend` as the current directory** (so `app` resolves to `backend/app`). The system `python3` in WSL usually does not have this project’s packages; use a **Linux venv** (`backend/.venv-wsl`).

On **Kali / Debian**, bare `pip install` hits **PEP 668** (“externally-managed-environment”). Use **`.venv-wsl/bin/pip`** after `source .venv-wsl/bin/activate`, or run **`./run_dev_wsl.sh`** (it syncs `requirements.txt` into the venv on every start).

From the **repo root** (creates `.venv-wsl` if missing; `run_dev_wsl.sh` keeps deps in sync):

```bash
chmod +x run_backend_wsl.sh
./run_backend_wsl.sh
```

Or manually:

```bash
cd Proof_AILatam_20260410_DPJP/backend
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8787
```

Use **`--host 0.0.0.0`** when the browser/Vite runs on **Windows** and proxies to the **WSL IP**. With **`127.0.0.1`** only, Linux listens on loopback and Windows gets **`ERR_CONNECTION_RESET`**.

**`Address already in use` (port 8787):** free it with `fuser -k 8787/tcp` or use **`PORT=9000 ./run_backend_wsl.sh`** and set **`VITE_PROXY_API=http://<WSL-IP>:9000`** in `frontend/.env.development`.

Running `uvicorn app.main:app` from the repo root causes `ModuleNotFoundError: No module named 'app'`. `ImportError: cannot import name 'genai' from 'google'` means **`google-genai` is not installed in `.venv-wsl`** (often: system `pip` was used instead of the venv). Fix: `backend/.venv-wsl/bin/pip install -r requirements.txt` or run `./run_dev_wsl.sh` again.

## Production-shaped deploy (outline)

1. `npm run build` in `frontend/`.
2. Deploy API container to **Cloud Run** with **`GEMINI_API_KEY`** (and optionally `GEMINI_MODEL`) as secrets.
3. Point **Firebase Hosting** `rewrites` for `/api/**` to that Cloud Run service (or put the API URL in `VITE_API_URL` and use CORS).
4. Confirm **SSE** works through your CDN (disable buffering; this repo sets `X-Accel-Buffering: no`).

## Deliverables for submission

See the `deliverables/` folder: architecture, cost estimate, and dual-audience documentation. Record a 2–3 minute screen capture showing upload → SSE → downloads.

## Transcript source

The scenario transcript is the **“Synthetic Transcript – Retail AI Automation Discovery Call”** (BrightLane Retail) embedded in `Syntethic_AI_Transcript.txt`.
