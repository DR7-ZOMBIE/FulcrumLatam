import asyncio
import os
from asyncio import QueueEmpty
from contextlib import asynccontextmanager
from pathlib import Path

from app.env_load import load_backend_env

load_backend_env()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app._version import API_REVISION
from app.pipeline import jobs, register_job, run_pipeline, subscribe

# Stream uploads to disk so large MP4s do not load entirely into RAM (avoids crashes / Failed to fetch).
_UPLOAD_CHUNK = 8 * 1024 * 1024
_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "upload_tmp"


async def _stream_upload_to_disk(job_id: str, upload: UploadFile) -> tuple[Path, str]:
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    raw_name = upload.filename or "upload.bin"
    suffix = Path(raw_name).suffix
    dest = _UPLOAD_DIR / f"{job_id}{suffix}"
    await upload.seek(0)
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(_UPLOAD_CHUNK)
            if not chunk:
                break
            out.write(chunk)
    return dest, raw_name


@asynccontextmanager
async def lifespan(_: FastAPI):
    import logging

    import app.summarizer as summ_mod

    logging.getLogger("uvicorn.error").warning(
        "POC backend revision=%s | summarizer.py=%s",
        API_REVISION,
        summ_mod.__file__,
    )
    yield


app = FastAPI(title="Meeting → Slides POC", lifespan=lifespan)

_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
_extra = [o.strip() for o in os.environ.get("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*_origins, *_extra],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _PrivateNetworkCorsMiddleware(BaseHTTPMiddleware):
    """Chrome: requests from localhost (Vite) to a LAN IP (WSL) need this on the preflight + response."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(_PrivateNetworkCorsMiddleware)


@app.get("/api/health")
def health():
    """Masks keys; useful to confirm `.env` is loaded before transcribing media."""
    g = bool((os.environ.get("GEMINI_API_KEY") or "").strip())
    gg = bool((os.environ.get("GOOGLE_API_KEY") or "").strip())
    o = bool((os.environ.get("OPENAI_API_KEY") or "").strip())
    v = (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower()
    vertex_env = v in ("1", "true", "yes")
    return {
        "status": "ok",
        "api_revision": API_REVISION,
        "gemini_client": {
            "mode": "developer_api",
            "vertexai_forced_false": True,
            "note": "Same AI Studio key as Firebase GEMINI_API_KEY; Vertex env var is ignored for this client.",
        },
        "env_loaded": {
            "gemini_api_key": g,
            "google_api_key": gg,
            "openai_api_key": o,
            "any_gemini": g or gg,
            "GOOGLE_GENAI_USE_VERTEXAI": vertex_env,
        },
    }


@app.post("/api/process")
async def process(
    use_sample_file: bool = Form(False),
    force_demo_summary: bool = Form(False),
    file: UploadFile | None = File(None),
):
    job = register_job()
    upload_path: Path | None = None
    upload_name: str | None = None
    if file is not None and file.filename:
        try:
            upload_path, upload_name = await _stream_upload_to_disk(job.job_id, file)
        except Exception as exc:  # noqa: BLE001 — return JSON instead of 500 before task starts
            jid = job.job_id
            jobs.pop(jid, None)
            return JSONResponse(
                status_code=400,
                content={
                    "error": "upload_failed",
                    "message": str(exc),
                    "api_revision": API_REVISION,
                },
                headers={"X-API-Revision": API_REVISION},
            )

    async def kickoff() -> None:
        try:
            await run_pipeline(
                job,
                upload_name=upload_name,
                upload_path=upload_path,
                use_sample_file=use_sample_file,
                force_demo_summary=force_demo_summary,
            )
        finally:
            if upload_path is not None:
                try:
                    upload_path.unlink(missing_ok=True)
                except OSError:
                    pass

    asyncio.create_task(kickoff())
    return JSONResponse(
        content={"job_id": job.job_id, "api_revision": API_REVISION},
        headers={"X-API-Revision": API_REVISION},
    )


@app.get("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    q = await subscribe(job_id)
    if not q:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    async def gen():
        # Initial snapshot for late subscribers
        yield f"data: {job.event('subscribed', {'status': job.status, 'step': job.step})}\n\n"
        while True:
            try:
                line = await asyncio.wait_for(q.get(), timeout=120.0)
                yield line
                if job.status in ("completed", "failed"):
                    # drain a bit then end
                    try:
                        while True:
                            extra = q.get_nowait()
                            yield extra
                    except QueueEmpty:
                        break
            except TimeoutError:
                yield f"data: {job.event('heartbeat', {})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/jobs/{job_id}/download/transcript")
def download_transcript(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.transcript_path or not job.transcript_path.is_file():
        raise HTTPException(status_code=404, detail="Transcript not ready")
    return FileResponse(
        path=job.transcript_path,
        filename="transcript.txt",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/jobs/{job_id}/download/pptx")
def download_pptx(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.pptx_path or not job.pptx_path.is_file():
        raise HTTPException(status_code=404, detail="Slides not ready")
    return FileResponse(
        path=job.pptx_path,
        filename="meeting_briefing.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.get("/api/jobs/{job_id}/download/json")
def download_json(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.json_path or not job.json_path.is_file():
        raise HTTPException(status_code=404, detail="Summary JSON not ready")
    return FileResponse(path=job.json_path, filename="summary.json", media_type="application/json")
