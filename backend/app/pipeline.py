import asyncio
import json
import os
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.env_load import load_backend_env

load_backend_env()

from app._version import API_REVISION
from app.slides_builder import build_deck, write_summary_json
from app.summarizer import llm_provider_configured, summarize_transcript, transcribe_media
from app.transcript_clean import extract_transcript_text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSCRIPT = PROJECT_ROOT / "Syntethic_AI_Transcript.txt"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "output"

TEXT_EXT = {".txt", ".text", ".md"}
MEDIA_EXT = {".mp3", ".mp4", ".webm", ".wav", ".m4a", ".mpeg", ".mpga"}


@dataclass
class JobRecord:
    job_id: str
    status: str = "queued"
    step: str = ""
    error: str | None = None
    pptx_path: Path | None = None
    json_path: Path | None = None
    transcript_path: Path | None = None
    transcript_preview: str = ""
    used_llm: bool = False
    subscribers: list[asyncio.Queue[str]] = field(default_factory=list)

    def event(self, event: str, data: dict | None = None) -> str:
        payload = {"event": event, "data": data or {}}
        return json.dumps(payload, ensure_ascii=False)


jobs: dict[str, JobRecord] = {}


async def broadcast(job: JobRecord, event: str, data: dict | None = None) -> None:
    line = f"data: {job.event(event, data)}\n\n"
    dead: list[asyncio.Queue[str]] = []
    for q in job.subscribers:
        try:
            q.put_nowait(line)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        if q in job.subscribers:
            job.subscribers.remove(q)


def register_job() -> JobRecord:
    job_id = str(uuid.uuid4())
    job = JobRecord(job_id=job_id)
    jobs[job_id] = job
    return job


async def subscribe(job_id: str) -> asyncio.Queue[str] | None:
    job = jobs.get(job_id)
    if not job:
        return None
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    job.subscribers.append(q)
    return q


def _suffix(name: str | None) -> str:
    if not name:
        return ""
    return Path(name).suffix.lower()


async def run_pipeline(
    job: JobRecord,
    *,
    upload_name: str | None,
    upload_bytes: bytes | None,
    use_sample_file: bool,
    force_demo_summary: bool,
) -> None:
    emit: Callable[[str, dict | None], Coroutine[None, None, None]] = (
        lambda e, d=None: broadcast(job, e, d)
    )

    try:
        await emit("job_started", {"job_id": job.job_id, "api_revision": API_REVISION})
        job.status = "running"

        transcript_text = ""
        source_label = ""

        # Upload wins over "sample" so API clients and edge-case form order always transcribe media.
        if upload_bytes and upload_name:
            ext = _suffix(upload_name)
            await emit("ingest", {"mode": "upload", "filename": upload_name})
            if ext in TEXT_EXT:
                transcript_text = upload_bytes.decode("utf-8", errors="replace")
                source_label = upload_name
            elif ext in MEDIA_EXT:
                await emit("transcribing", {"detail": "Calling speech-to-text API"})
                loop = asyncio.get_event_loop()

                def write_temp() -> str:
                    with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(upload_bytes)
                        return tmp.name

                tmp_path = await loop.run_in_executor(None, write_temp)
                try:
                    transcript_text = await loop.run_in_executor(
                        None, lambda: transcribe_media(tmp_path, ext)
                    )
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                source_label = upload_name
            else:
                raise ValueError(
                    f"Unsupported file type {ext or 'unknown'}. "
                    "Use .txt transcript or audio/video (mp3, wav, mp4, webm, m4a)."
                )

        elif use_sample_file:
            path = DEFAULT_TRANSCRIPT
            if not path.is_file():
                raise FileNotFoundError(
                    f"Sample transcript not found at {path}. "
                    "Place Syntethic_AI_Transcript.txt next to the backend folder or upload a file."
                )
            await emit("ingest", {"mode": "sample", "path": str(path)})
            transcript_text = path.read_text(encoding="utf-8", errors="replace")
            source_label = path.name

        else:
            raise ValueError("No input: enable 'Use sample transcript' or upload a file.")

        transcript_text = extract_transcript_text(transcript_text)
        job.transcript_preview = transcript_text[:500] + ("…" if len(transcript_text) > 500 else "")
        await emit("transcript_ready", {"chars": len(transcript_text), "source": source_label})

        out_dir = OUTPUT_DIR / job.job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = out_dir / "transcript.txt"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: transcript_path.write_text(transcript_text, encoding="utf-8"),
        )
        job.transcript_path = transcript_path
        await emit(
            "artifact_written",
            {"path": "transcript.txt", "download": f"/api/jobs/{job.job_id}/download/transcript"},
        )

        provider = llm_provider_configured()
        use_llm = not force_demo_summary and provider is not None
        job.used_llm = use_llm
        engine = provider if use_llm else "deterministic_fallback"
        await emit(
            "summarizing",
            {"engine": engine, "model_configured": use_llm},
        )

        summary = await loop.run_in_executor(
            None,
            lambda: summarize_transcript(transcript_text, use_llm=use_llm),
        )

        pptx_path = out_dir / "meeting_briefing.pptx"
        json_path = out_dir / "summary.json"

        await emit("building_slides", {})
        await loop.run_in_executor(
            None,
            lambda: build_deck(
                summary,
                title=f"Source: {source_label}",
                output_path=pptx_path,
            ),
        )
        await loop.run_in_executor(None, lambda: write_summary_json(summary, json_path))

        job.pptx_path = pptx_path
        job.json_path = json_path
        job.status = "completed"
        job.step = "done"
        await emit(
            "completed",
            {
                "transcript": f"/api/jobs/{job.job_id}/download/transcript",
                "pptx": f"/api/jobs/{job.job_id}/download/pptx",
                "json": f"/api/jobs/{job.job_id}/download/json",
                "used_llm": use_llm,
                "api_revision": API_REVISION,
            },
        )
    except Exception as exc:  # noqa: BLE001 — POC boundary
        job.status = "failed"
        job.error = str(exc)
        await emit(
            "error",
            {"message": str(exc), "api_revision": API_REVISION},
        )
