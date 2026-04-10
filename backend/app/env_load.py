"""Load backend/.env once per process. utf-8-sig strips Windows BOM so WSL/Linux see GEMINI_API_KEY."""

from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parent.parent


def load_backend_env() -> None:
    p = _BACKEND / ".env"
    load_dotenv(p, encoding="utf-8-sig")
