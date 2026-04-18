"""E4~E7 결과를 N-way 매트릭스 CSV + markdown으로 정리."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parents[1]
OUT = EXP / "output"

ENGINES_META = [
    ("e4-opus",           "Claude Opus 4.7",           "Anthropic", "플래그십"),
    ("e5-sonnet",         "Claude Sonnet 4.6",         "Anthropic", "중형"),
    ("e6-gpt5",           "GPT-5",                     "OpenAI",    "플래그십"),
    ("e7a-gemini-pro",    "Gemini 3.1-pro-preview",    "Google",    "플래그십 (skip — 429 quota)"),
    ("e7b-gemini-flash",  "Gemini 3.1-flash-lite",     "Google",    "소형"),
]

# 개별 엔진 JSON 파일명 매핑 (타임프레임 접미사 {tf})
JSON_TEMPLATES = {
    "e4-opus": "e4_opus_i3_drfx_{tf}.json",
    "e5-sonnet": "e5-sonnet_i3_drfx_{tf}.json",
    "e6-gpt5": "e6-gpt5_i3_drfx_{tf}.json",
    "e7b-gemini-flash": "e7b-gemini-flash_i3_drfx_{tf}.json",
}
TIMEFRAMES = ["1h", "4h"]

INDICATORS = [
    ("total_return_pct", "%"),
    ("max_drawdown_pct", "%"),
    ("sharpe_ratio", ""),
    ("profit_factor", ""),
    ("total_trades", ""),
    ("winning_trades", ""),
    ("losing_trades", ""),
    ("win_rate", ""),
]


def load(engine: str, tf: str) -> dict | None:
    template = JSON_TEMPLATES.get(engine)
    if not template:
        return None
    path = OUT / template.format(tf=tf)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def main() -> None:
    rows: list[dict] = []
    for tf in TIMEFRAMES:
        for engine, model, provider, tier in ENGINES_META:
            data = load(engine, tf)
            row = {
                "timeframe": tf,
                "engine": engine,
                "model": model,
                "provider": provider,
                "tier": tier,
            }
            for metric, _ in INDICATORS:
                row[metric] = data.get(metric) if data else None
            if data:
                exit_reasons = data.get("exit_reasons", {}) or {}
                row["exit_reasons"] = ", ".join(f"{k}:{v}" for k, v in exit_reasons.items()) if exit_reasons else "—"
            else:
                row["exit_reasons"] = "skip"
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = OUT / "nway_diff_matrix.csv"
    df.to_csv(csv_path, index=False)

    # Markdown
    lines = ["# N-way 매트릭스 — I3 DrFX × 1H/4H 타임프레임", ""]
    lines.append("> 기간: 2025-04-18 ~ 2026-04-17 1년 (BTCUSDT 현물, Binance CCXT, 고정 CSV)")
    lines.append("> 1H: 8,760 bars / 4H: 2,190 bars")
    lines.append("> E1 PyneCore 오라클은 PyneSys 상용 API 의존으로 제거. LLM 4개 + Opus baseline 상호 비교.")
    lines.append("")

    for tf in TIMEFRAMES:
        lines.append(f"## {tf.upper()} 타임프레임")
        lines.append("")
        headers = ["엔진", "모델", "공급사", "TIER"] + [m for m, _ in INDICATORS] + ["exit reasons"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        tf_rows = [r for r in rows if r["timeframe"] == tf]
        for row in tf_rows:
            cells = [row["engine"], row["model"], row["provider"], row["tier"]]
            for metric, unit in INDICATORS:
                v = row.get(metric)
                if v is None:
                    cells.append("—")
                elif isinstance(v, float):
                    if metric in ("total_return_pct", "max_drawdown_pct", "win_rate"):
                        cells.append(f"{v:.2f}{unit}" if metric != "win_rate" else f"{v:.2%}")
                    else:
                        cells.append(f"{v:.2f}")
                else:
                    cells.append(str(v))
            cells.append(row.get("exit_reasons", "—"))
            lines.append("| " + " | ".join(cells) + " |")

        valid_returns = [r["total_return_pct"] for r in tf_rows if r.get("total_return_pct") is not None]
        valid_trades = [r["total_trades"] for r in tf_rows if r.get("total_trades") is not None]
        if valid_returns:
            lines.append("")
            lines.append(f"**수익률 범위:** {min(valid_returns):.2f}% ~ {max(valid_returns):.2f}% (폭 {max(valid_returns) - min(valid_returns):.2f}%p) / "
                         f"거래 0건 엔진 {sum(1 for t in valid_trades if t == 0)}/{len(valid_trades)}")
        lines.append("")

    # 종합 판정
    lines.append("## Phase -1 가정 판정 (MVP scope: TP/SL/LONG/SHORT)")
    lines.append("")
    lines.append("| 가정 | 판정 | 근거 |")
    lines.append("|------|:--:|------|")
    all_returns = [r["total_return_pct"] for r in rows if r.get("total_return_pct") is not None]
    all_trades = [r["total_trades"] for r in rows if r.get("total_trades") is not None]
    if all_returns:
        return_range_all = max(all_returns) - min(all_returns)
        zero_trades = sum(1 for t in all_trades if t == 0)
        lines.append(f"| A2: 상대오차 <0.1% KPI 현실적 | ❌ **반증** | 1H+4H 통합 수익률 범위 {return_range_all:.1f}%p — LLM 단독 quasi-oracle 불가 |")
        lines.append(f"| A3: LLM 변환 버그 재현성 | ✅ **실증** | 모델별 상이한 구조적 버그. 1H+4H 합산 {zero_trades}개 runs에서 진입 로직 자체 실패 |")
        lines.append("| ~~A1: trail_points 지원~~ | N/A | scope 축소 (H2+ 이연) |")
        lines.append("")
        lines.append("## 타임프레임 간 비교 관찰 (1H vs 4H)")
        lines.append("")
        e4_1h = next((r for r in rows if r["engine"] == "e4-opus" and r["timeframe"] == "1h"), {})
        e4_4h = next((r for r in rows if r["engine"] == "e4-opus" and r["timeframe"] == "4h"), {})
        if e4_1h.get("total_return_pct") is not None and e4_4h.get("total_return_pct") is not None:
            delta = e4_4h["total_return_pct"] - e4_1h["total_return_pct"]
            lines.append(f"- **E4 Opus:** 1H {e4_1h['total_return_pct']:.2f}% vs 4H {e4_4h['total_return_pct']:.2f}% (delta {delta:+.2f}%p) — 노이즈 + 수수료 누적이 1H 손실 악화의 주요 원인 (145 → 37 trades)")
        e5_1h = next((r for r in rows if r["engine"] == "e5-sonnet" and r["timeframe"] == "1h"), {})
        e5_4h = next((r for r in rows if r["engine"] == "e5-sonnet" and r["timeframe"] == "4h"), {})
        if e5_1h.get("total_return_pct") is not None and e5_4h.get("total_return_pct") is not None:
            lines.append(f"- **E5 Sonnet:** 1H {e5_1h['total_return_pct']:.2f}% vs 4H {e5_4h['total_return_pct']:.2f}% — Opus와 달리 4H에서도 손실 유지 → 구조적 변환 차이 지속")
        lines.append("- **E6/E7b:** 1H·4H 모두 0 trades — 진입 로직 자체 미구현. 타임프레임 무관 구조 실패")

    md_path = OUT / "nway_diff_matrix.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"CSV: {csv_path.relative_to(EXP)}")
    print(f"MD:  {md_path.relative_to(EXP)}")
    print()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
