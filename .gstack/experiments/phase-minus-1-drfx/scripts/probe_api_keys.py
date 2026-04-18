"""API 키 가용성 probe.

`.env`에서 OPENAI_API_KEY / GEMINI_API_KEY / CLAUDE_APT_KEY(=ANTHROPIC)를 로드하여
각 제공사의 public 모델 리스트 엔드포인트 호출로 키 유효성 + 가용 모델 확인.

- 키 값은 절대 출력 안 함 (길이만)
- 실패 시 에러 메시지 앞 120자만
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("CLAUDE_API_KEY", "") or os.environ.get("CLAUDE_APT_KEY", "")

TIMEOUT = 15.0


def probe_openai() -> None:
    if not OPENAI_KEY:
        print("OpenAI: KEY unset")
        return
    print(f"OpenAI: key length={len(OPENAI_KEY)} prefix={OPENAI_KEY[:4]}...")
    try:
        r = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        print(f"  ERR: {type(e).__name__}: {str(e)[:120]}")
        return
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {r.text[:180]}")
        return
    data = r.json().get("data", [])
    print(f"  OK — {len(data)} models visible")
    preferred = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o", "o1", "o3", "o4-mini"]
    visible = sorted({m["id"] for m in data})
    matches = [p for p in preferred if any(v.startswith(p) for v in visible)]
    print(f"  plagship hits: {matches}")


def probe_gemini() -> None:
    if not GEMINI_KEY:
        print("Gemini: KEY unset")
        return
    print(f"Gemini: key length={len(GEMINI_KEY)} prefix={GEMINI_KEY[:4]}...")
    try:
        r = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}",
            timeout=TIMEOUT,
        )
    except Exception as e:
        print(f"  ERR: {type(e).__name__}: {str(e)[:120]}")
        return
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {r.text[:180]}")
        return
    data = r.json().get("models", [])
    print(f"  OK — {len(data)} models visible")
    preferred = ["models/gemini-2.5-pro", "models/gemini-2.5-flash", "models/gemini-2.0"]
    visible = sorted({m["name"] for m in data})
    matches = [p for p in preferred if any(v.startswith(p) for v in visible)]
    print(f"  plagship hits: {matches}")


def probe_claude() -> None:
    if not CLAUDE_KEY:
        print("Claude: KEY unset")
        return
    print(f"Claude: key length={len(CLAUDE_KEY)} prefix={CLAUDE_KEY[:4]}...")
    try:
        r = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": CLAUDE_KEY,
                "anthropic-version": "2023-06-01",
            },
            timeout=TIMEOUT,
        )
    except Exception as e:
        print(f"  ERR: {type(e).__name__}: {str(e)[:120]}")
        return
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {r.text[:180]}")
        return
    data = r.json().get("data", [])
    print(f"  OK — {len(data)} models visible")
    preferred = ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"]
    visible = sorted({m["id"] for m in data})
    matches = [p for p in preferred if any(v.startswith(p) for v in visible)]
    print(f"  plagship hits: {matches}")


if __name__ == "__main__":
    print(f"env: {ENV_PATH} exists={ENV_PATH.exists()}")
    print("---")
    probe_openai()
    print()
    probe_gemini()
    print()
    probe_claude()
