"""LLM 매트릭스 변환기 — Pine → Python.

주어진 .pine 소스를 동일한 시스템 프롬프트 + 유저 메시지로 4개 공급사에 호출하여
generated/e{N}_{model}_{script}.py 로 저장한다.

Usage:
    uv run python scripts/llm_transpile.py --engine e5-sonnet --script corpus/i3_drfx.pine
    uv run python scripts/llm_transpile.py --engine e6-gpt5   --script corpus/i3_drfx.pine
    uv run python scripts/llm_transpile.py --engine e7a-gemini-pro  --script corpus/i3_drfx.pine
    uv run python scripts/llm_transpile.py --engine e7b-gemini-flash --script corpus/i3_drfx.pine
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[4]
load_dotenv(REPO / ".env")

EXP = Path(__file__).resolve().parents[1]
GEN_DIR = EXP / "generated"
LOG_PATH = EXP / "output" / "llm_transpile_log.jsonl"

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("CLAUDE_API_KEY", "") or os.environ.get("CLAUDE_APT_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

ENGINES: dict[str, dict] = {
    "e4-opus":          {"provider": "anthropic", "model": "claude-opus-4-7"},
    "e5-sonnet":        {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "e6-gpt5":          {"provider": "openai",    "model": "gpt-5"},
    "e7a-gemini-pro":   {"provider": "gemini",    "model": "gemini-3.1-pro-preview"},
    "e7a-gemini-25pro": {"provider": "gemini",    "model": "gemini-2.5-pro"},
    "e7b-gemini-flash": {"provider": "gemini",    "model": "gemini-3.1-flash-lite-preview"},
}

SYSTEM_PROMPT = """You are a senior quant engineer. Translate the provided TradingView Pine Script to a self-contained Python backtester.

STRICT RULES:
1. Input: a CSV at sys.argv[1] with columns [timestamp, open, high, low, close, volume]. timestamp is milliseconds epoch UTC. Convert to UTC DatetimeIndex.
2. In-scope Pine constructs to preserve EXACTLY as-is:
   - strategy.entry (long/short)
   - strategy.exit(from_entry=, stop=, limit=)  — TP and SL only
   - strategy.close / strategy.close_all
   - All ta.* and math.* used in the source
   - alert() / alertcondition() — treat as no-op comment
3. Out-of-scope (OMIT with `# [SKIP] <feature>` comment and do NOTHING):
   - strategy.exit trail_points / trail_offset (trailing stop)
   - strategy.exit qty_percent (partial TP)
   - pyramiding (multiple concurrent entries)
   - box.new / line.new / label.new / table.new (rendering objects)
   - request.security (multi-timeframe)
   - bar_magnifier
4. Use pandas + numpy only. No ccxt, no yfinance, no network I/O, no exec, no eval.
5. Config: initial_capital=10000, fee_pct=0.001 per side (applied at each entry and exit).
6. Expose `main(csv_path)` that:
   a. Reads CSV, converts timestamp ms → UTC index.
   b. Runs the strategy bar-by-bar with proper [n] -> df.shift(n) translation for historical refs.
   c. Prints ONE json.dumps() with exactly these keys:
      total_return_pct (float, %), max_drawdown_pct (float, % negative),
      sharpe_ratio (float, annualized with bars_per_year=8760 for 1H),
      profit_factor (float or null if no losers), total_trades (int, closed only),
      winning_trades (int), losing_trades (int), win_rate (float 0..1),
      exit_reasons (dict[str, int], e.g. {"SL": 108, "TP": 37}).
7. `if __name__ == "__main__": main(sys.argv[1])`.
8. Preserve Pine logic with maximum fidelity. Do NOT fix perceived bugs. Do NOT add features.

Respond with ONE Python code block only. No prose. No extra markdown outside the code block."""


def extract_code(text: str) -> tuple[str, str]:
    """응답에서 Python code block 추출. 실패 시 원문 전체 + note 반환."""
    m = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return m.group(1), "fenced"
    return text, "raw"


def log(rec: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def call_anthropic(model: str, user: str) -> dict:
    import anthropic
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC/CLAUDE key missing")
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    t0 = time.time()
    msg = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    dt = time.time() - t0
    text = msg.content[0].text if msg.content else ""
    usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens}
    return {"text": text, "latency_s": dt, "usage": usage, "stop_reason": msg.stop_reason}


def call_openai(model: str, user: str) -> dict:
    from openai import OpenAI
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI key missing")
    client = OpenAI(api_key=OPENAI_KEY)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        max_completion_tokens=16000,
    )
    dt = time.time() - t0
    choice = resp.choices[0]
    text = choice.message.content or ""
    usage = {"input_tokens": resp.usage.prompt_tokens, "output_tokens": resp.usage.completion_tokens}
    return {"text": text, "latency_s": dt, "usage": usage, "stop_reason": choice.finish_reason}


def call_gemini(model: str, user: str) -> dict:
    import google.generativeai as genai
    if not GOOGLE_KEY:
        raise RuntimeError("GOOGLE/GEMINI key missing")
    genai.configure(api_key=GOOGLE_KEY)
    m = genai.GenerativeModel(model_name=model, system_instruction=SYSTEM_PROMPT)
    t0 = time.time()
    resp = m.generate_content(user, generation_config={"max_output_tokens": 16000, "temperature": 0.1})
    dt = time.time() - t0
    text = resp.text if hasattr(resp, "text") and resp.text else ""
    usage_md = resp.usage_metadata if hasattr(resp, "usage_metadata") else None
    usage = {
        "input_tokens": getattr(usage_md, "prompt_token_count", None),
        "output_tokens": getattr(usage_md, "candidates_token_count", None),
    }
    finish = resp.candidates[0].finish_reason.name if resp.candidates else "unknown"
    return {"text": text, "latency_s": dt, "usage": usage, "stop_reason": str(finish)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, choices=list(ENGINES.keys()))
    ap.add_argument("--script", required=True)
    args = ap.parse_args()

    spec = ENGINES[args.engine]
    script_path = (EXP / args.script).resolve() if not Path(args.script).is_absolute() else Path(args.script)
    source = script_path.read_text(encoding="utf-8")

    user_msg = f"""Pine Script ({script_path.name}):

```pine
{source}
```

Translate to Python per the rules. Return ONE code block only."""

    print(f"Engine: {args.engine} | Provider: {spec['provider']} | Model: {spec['model']}")
    print(f"Source: {script_path.name} ({len(source)} chars)")

    caller = {"anthropic": call_anthropic, "openai": call_openai, "gemini": call_gemini}[spec["provider"]]
    try:
        result = caller(spec["model"], user_msg)
    except Exception as e:
        print(f"ERR: {type(e).__name__}: {str(e)[:200]}")
        log({"engine": args.engine, "script": script_path.name, "error": f"{type(e).__name__}: {str(e)[:500]}"})
        sys.exit(1)

    code, block_type = extract_code(result["text"])
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GEN_DIR / f"{args.engine}_{script_path.stem}.py"
    out_path.write_text(code, encoding="utf-8")

    rec = {
        "engine": args.engine,
        "provider": spec["provider"],
        "model": spec["model"],
        "script": script_path.name,
        "source_size": len(source),
        "code_size": len(code),
        "block_type": block_type,
        "latency_s": round(result["latency_s"], 2),
        "usage": result["usage"],
        "stop_reason": result["stop_reason"],
        "out": str(out_path.relative_to(EXP)),
    }
    log(rec)
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"→ {out_path.relative_to(EXP)}")


if __name__ == "__main__":
    main()
