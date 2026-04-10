import json
import os
import time
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from openai import OpenAI

from app._version import API_REVISION
from app.demo_data import FALLBACK_SUMMARY
from app.env_load import load_backend_env
from app.transcript_clean import extract_transcript_text


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    s = str(raw).strip().strip('"').strip("'")
    return s or None


def _gemini_api_key() -> str | None:
    """Google AI Studio often documents GOOGLE_API_KEY; we accept both."""
    return _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")


def _gemini_model_id() -> str:
    """Normalize model id for the GenAI SDK (strip optional ``models/`` prefix)."""
    m = (os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    if m.startswith("models/"):
        m = m[len("models/") :]
    return m or "gemini-2.0-flash"


def _gemini_client() -> genai.Client:
    api_key = _gemini_api_key() or ""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is empty after load.")
    try:
        timeout_sec = float(os.environ.get("GEMINI_HTTP_TIMEOUT_SEC", "600"))
    except ValueError:
        timeout_sec = 600.0
    timeout_sec = max(30.0, min(timeout_sec, 3600.0))
    http = types.HttpOptions(timeout=timeout_sec)
    # Same AI Studio key as Firebase / JS SDK: force Developer API, not Vertex (GOOGLE_GENAI_USE_VERTEXAI).
    return genai.Client(api_key=api_key, vertexai=False, http_options=http)


def _reraise_gemini(exc: BaseException) -> None:
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", "?")
        msg = (exc.message or str(exc)).strip() or repr(exc)
        raise RuntimeError(f"Gemini API error (HTTP {code}): {msg}") from exc
    raise exc


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    cands = getattr(response, "candidates", None) or []
    if not cands:
        return ""
    content = getattr(cands[0], "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", None) or []
    return "".join(str(getattr(p, "text", "") or "") for p in parts)


SUMMARY_SCHEMA_HINT = """Return a JSON object with exactly these keys:
{
    "executive_summary": string (2-4 sentences),
    "objectives": array of exactly 3 strings (high-level strategic objectives discussed),
    "actionable_items": array of exactly 3 strings (specific, business-oriented actions),
    "next_steps": array of 3-5 strings (concrete next steps),
    "human_review_notes": string (where a human must verify before sending externally)
}
"""

MIME_BY_EXT = {
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mpeg": "video/mpeg",
    ".mpga": "audio/mpeg",
}


def _merge_partial(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("executive_summary", "objectives", "actionable_items", "next_steps"):
        if key not in data:
            merged = dict(FALLBACK_SUMMARY)
            merged.update({k: v for k, v in data.items() if v})
            return merged
    return data


def _summarize_gemini(cleaned: str) -> dict[str, Any]:
    client = _gemini_client()
    model_name = _gemini_model_id()
    prompt = (
        "You are preparing an internal leadership briefing from a meeting transcript.\n"
        "Be specific and operational; avoid generic advice.\n"
        "Output only valid JSON matching this shape (no markdown):\n"
        f"{SUMMARY_SCHEMA_HINT}\n\nTranscript:\n{cleaned[:120_000]}"
    )
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except genai_errors.APIError as exc:
        _reraise_gemini(exc)
    if not response.candidates:
        reason = getattr(response.prompt_feedback, "block_reason", "unknown")
        raise RuntimeError(f"Gemini returned no candidates (block_reason={reason}).")
    raw = _response_text(response).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini summary was not valid JSON (model={model_name}).") from exc
    return _merge_partial(data)


def _summarize_openai(cleaned: str) -> dict[str, Any]:
    key = _env("OPENAI_API_KEY") or ""
    if not key:
        raise RuntimeError("OPENAI_API_KEY is empty after load.")
    client = OpenAI(api_key=key)
    user_content = (
        "You are preparing an internal leadership briefing from a meeting transcript.\n"
        "Be specific and operational; avoid generic advice.\n\n"
        f"{SUMMARY_SCHEMA_HINT}\n\nTranscript:\n{cleaned[:120_000]}"
    )
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Output only valid JSON. No markdown."},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return _merge_partial(data)


def summarize_transcript(transcript: str, *, use_llm: bool) -> dict[str, Any]:
    cleaned = extract_transcript_text(transcript)
    if not use_llm:
        return dict(FALLBACK_SUMMARY)

    if _gemini_api_key():
        return _summarize_gemini(cleaned)
    if _env("OPENAI_API_KEY"):
        return _summarize_openai(cleaned)
    return dict(FALLBACK_SUMMARY)


def _file_state_name(state: object) -> str:
    return getattr(state, "name", str(state))


def _wait_gemini_file(client: genai.Client, name: str) -> None:
    try:
        wait_sec = int(os.environ.get("GEMINI_FILE_ACTIVE_DEADLINE_SEC", "600"))
    except ValueError:
        wait_sec = 600
    wait_sec = max(60, min(wait_sec, 3600))
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        try:
            f = client.files.get(name=name)
        except genai_errors.APIError as exc:
            _reraise_gemini(exc)
        st = _file_state_name(f.state)
        if st == "ACTIVE":
            return
        if st == "FAILED":
            raise RuntimeError("Gemini file upload failed to process.")
        time.sleep(1)
    raise TimeoutError(
        f"Gemini file did not become ACTIVE within {wait_sec}s (large video?). "
        "Set GEMINI_FILE_ACTIVE_DEADLINE_SEC or use a shorter clip / extract audio."
    )


def _transcribe_gemini(path: str, ext: str | None) -> str:
    client = _gemini_client()
    mime = MIME_BY_EXT.get((ext or "").lower(), "application/octet-stream")
    try:
        uploaded = client.files.upload(
            file=path,
            config=types.UploadFileConfig(mime_type=mime),
        )
    except genai_errors.APIError as exc:
        _reraise_gemini(exc)
    try:
        _wait_gemini_file(client, uploaded.name)
        model_name = _gemini_model_id()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    "Transcribe all spoken dialogue in this file. "
                    "Use plain text only: speaker labels if obvious, no timestamps. "
                    "If the file is video, use the audio track.",
                    uploaded,
                ],
            )
        except genai_errors.APIError as exc:
            _reraise_gemini(exc)
        if not response.candidates:
            reason = getattr(response.prompt_feedback, "block_reason", "unknown")
            raise RuntimeError(f"Gemini transcription blocked (block_reason={reason}).")
        return _response_text(response).strip()
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


def _transcribe_openai(path: str) -> str:
    key = _env("OPENAI_API_KEY") or ""
    if not key:
        raise RuntimeError("OPENAI_API_KEY is empty after load.")
    client = OpenAI(api_key=key)
    model = os.environ.get("OPENAI_WHISPER_MODEL", "whisper-1")
    with open(path, "rb") as audio_file:
        tr = client.audio.transcriptions.create(model=model, file=audio_file)
    return tr.text


def transcribe_media(path: str, ext: str | None) -> str:
    load_backend_env()
    if _gemini_api_key():
        return _transcribe_gemini(path, ext)
    if _env("OPENAI_API_KEY"):
        return _transcribe_openai(path)
    raise RuntimeError(
        f"[{API_REVISION}] No API key for transcription. In backend/.env set GEMINI_API_KEY or "
        "GOOGLE_API_KEY (AI Studio), or OPENAI_API_KEY. Use UTF-8 without BOM issues—we load utf-8-sig. "
        "From WSL: rm -rf app/__pycache__ then restart uvicorn. Check GET /api/health (any_gemini: true). "
        "Or upload a .txt transcript."
    )


def llm_provider_configured() -> str | None:
    if _gemini_api_key():
        return "gemini"
    if _env("OPENAI_API_KEY"):
        return "openai"
    return None
