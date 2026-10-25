"""미확보·실패를 제거하지 않는 HTML/CSV/JSON 연구 보고서."""

from __future__ import annotations

import csv
import gzip
import html
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from tools.research.editor_picks.common import ARMS, identity, now, read, write
from tools.research.editor_picks.verification import receipts

METRICS = (
    "total_return",
    "annual_return_pct",
    "max_drawdown",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "win_rate",
    "profit_factor",
    "num_trades",
    "avg_trade_pct",
    "avg_holding_hours",
    "long_win_rate_pct",
    "short_win_rate_pct",
    "open_pnl",
    "total_funding",
    "total_fees",
    "total_slippage",
    "avg_trade_abs",
    "avg_closed_episode_r",
    "closed_episode_win_rate_pct",
    "exposure_minute_pct",
    "closed_episodes",
)


def signal_quality(expected: list[dict], observed: list[dict]) -> dict:
    if [row["timestamp"] for row in expected] != [row["timestamp"] for row in observed]:
        raise ValueError("신호 비교 시각이 다릅니다")
    result = {
        "signal_mismatches": sum(
            a["action"] != b["action"] for a, b in zip(expected, observed, strict=True)
        )
    }
    for action in ("long", "short", "close"):
        actual = sum(row["action"] == action for row in observed)
        reference = sum(row["action"] == action for row in expected)
        true = sum(
            a["action"] == b["action"] == action for a, b in zip(expected, observed, strict=True)
        )
        result.update(
            {
                f"{action}_precision": str(Decimal(true) / actual) if actual else None,
                f"{action}_recall": str(Decimal(true) / reference) if reference else None,
                f"{action}_observed": actual,
                f"{action}_reference": reference,
            }
        )
    return result


def build(root: Path, plan_path: Path) -> dict:
    frozen = read(plan_path)
    completed = receipts(root, frozen)
    rows = []
    for job in frozen["jobs"]:
        evidence = completed.get(identity(job))
        row = {**job, "status": evidence["status"] if evidence else "not_run"}
        if evidence:
            row.update({key: evidence.get("metrics", {}).get(key) for key in METRICS})
            row.update(
                error=evidence.get("error", evidence.get("reason")),
                economic_passed=evidence.get("economic_verdict", {}).get("passed"),
                funding_status=evidence.get("funding_status"),
                duration_seconds=evidence.get("duration_seconds"),
                failure_stage=evidence.get("failure_stage"),
                source_present=evidence.get("source_present"),
                runtime_attempted=evidence.get("runtime_attempted"),
                raw_result_storage=evidence.get("raw_result_storage"),
            )
            pine = completed.get(identity({**job, "arm": "pine"}))
            row["signal_exact"] = (
                evidence["action_sha256"] == pine["action_sha256"]
                if pine and pine["status"] == evidence["status"] == "completed"
                else None
            )
            row["ledger_exact"] = (
                evidence["ledger_sha256"] == pine["ledger_sha256"]
                if pine and pine["status"] == evidence["status"] == "completed"
                else None
            )
            if pine and pine["status"] == evidence["status"] == "completed":
                expected = json.loads(
                    gzip.decompress(
                        (Path(pine["evidence_folder"]) / "signals.json.gz").read_bytes()
                    )
                )
                observed = json.loads(
                    gzip.decompress(
                        (Path(evidence["evidence_folder"]) / "signals.json.gz").read_bytes()
                    )
                )
                row.update(signal_quality(expected, observed))
        rows.append(row)
    cohort = read(root / frozen["cohort_file"])
    available = len(cohort["items"])
    scope = read(root / "scope-audit.json") if (root / "scope-audit.json").exists() else {}
    generation_policy = (
        read(root / "generation-policy.json") if (root / "generation-policy.json").exists() else {}
    )
    runtime_evidence = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        statuses = {}
        for row in arm_rows:
            statuses.setdefault(row["id"], []).append(row["status"])
        runtime_evidence[arm] = {
            "requested_cells": sum(row.get("runtime_attempted") is True for row in arm_rows),
            "requested_originals": len(
                {row["id"] for row in arm_rows if row.get("runtime_attempted") is True}
            ),
            "originals_with_completed_cells": len(
                {row["id"] for row in arm_rows if row["status"] == "completed"}
            ),
            "originals_with_all_cells_completed": sum(
                all(status == "completed" for status in values) for values in statuses.values()
            ),
            "static_preflight_rejected_cells": sum(
                row.get("failure_stage") == "static_preflight" for row in arm_rows
            ),
            "legacy_unknown_request_cells": sum(
                row.get("runtime_attempted") is None
                for row in arm_rows
                if row["status"] != "not_run"
            ),
        }
    summary = {
        "generated_at": now(),
        "phase": frozen["phase"],
        "plan_sha256": identity(frozen),
        "expected_cells": frozen["expected_cells"],
        "observed_cells": len(completed),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "arms": {
            arm: dict(Counter(row["status"] for row in rows if row["arm"] == arm)) for arm in ARMS
        },
        "runtime_evidence": runtime_evidence,
        "raw_result_storage": dict(
            Counter(row["raw_result_storage"] for row in rows if row.get("raw_result_storage"))
        ),
        "complete": len(completed) == frozen["expected_cells"]
        and all(row["status"] != "not_run" for row in rows),
        "target_originals": 200,
        "available_originals": available,
        "source_target_met": available == 200,
        "source_acquisition": {
            **{
                key: scope.get(key)
                for key in (
                    "observed_at",
                    "scope",
                    "inventory_count",
                    "captured_indicator_count",
                    "missing_ids",
                    "indicator_screening_counts",
                )
            },
            "screening_counts_scope": "historical_acquisition_snapshot_not_current_cohort_or_execution",
        },
        "generation_policy": generation_policy,
        "target_full_cells": 21600,
        "holdout_status": "retrospective_not_untouched",
        "promotable": False,
        "limitations": [
            "중첩 6·12·24개월은 독립 holdout이 아닙니다.",
            "현재 관측·선택한 스크립트의 회고 비교이며, 과거 해당 시점에 공개·선택 가능했음을 검증하지 않았습니다.",
            "평균 R·완료 승률은 부분 익절을 합친 episode의 비용 후 손익 기준입니다.",
            "노출은 보유한 1분봉 비율이며 봉 내부 청산 시 해당 분봉을 포함합니다.",
            "LLM Python은 독립 정답 오라클이 아닙니다.",
            "성과는 실제 tick 체결·마크가격 펀딩을 보증하지 않습니다.",
            "펀딩 완전성 UNKNOWN과 경제 수치선 실패를 구분합니다.",
            "파일럿 종결은 200원문·21600셀 종결이 아닙니다.",
            "정적 사전검사 거절은 실제 격리 실행 수에 포함하지 않습니다. 실행 요청은 transport 생성 호출이며 성공 실행과 구분합니다.",
            "authenticated_remote_payload의 전체 원시는 암호화된 원격 분할 파일에 보존됩니다. 원시 SHA를 검증한 인증 증거와 필수 요청·신호·영수증은 로컬에 보존합니다.",
        ],
    }
    output = root / "report" / frozen["phase"]
    write(output / "report.json", {"summary": summary, "rows": rows})
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with (output / "cells.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    def escape(value):
        return html.escape("" if value is None else str(value))

    cells = "".join(
        "<tr>" + "".join(f"<td>{escape(row.get(key))}</td>" for key in columns) + "</tr>"
        for row in rows
    )
    heading = "".join(f"<th>{escape(key)}</th>" for key in columns)
    limits = "".join(f"<li>{escape(text)}</li>" for text in summary["limitations"])
    document = f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>에디터 픽 비교</title>
<style>body{{font:15px system-ui;margin:32px;color:#182526;background:#f4f6f6}}h1{{font-size:28px}}
table{{border-collapse:collapse;background:white}}td,th{{padding:9px;border:1px solid #ccd4d4;white-space:nowrap}}
th{{position:sticky;top:0;background:#dfe9e9}}.scroll{{overflow:auto;max-height:70vh}}input{{padding:10px;width:280px}}</style>
<h1>에디터 픽 · BTC 원문 재현 비교</h1><p>{escape(summary["phase"])} · 관측 {len(completed)} / 계획 {len(rows)}셀</p>
<p>확보한 고유 원문: {available} / 목표 200개 · 실행 종결과 원문 확보 목표 달성은 별개입니다.</p>
<p>전체 목표: Pine 원문 200개 · 3경로 · 1h/4h/1d · 6/12/24개월 · 21,600셀</p>
<ul>{limits}</ul><label>전략·모델·실패 검색 <input id="filter" type="search"></label>
<p><a href="cells.csv">전체 CSV</a> · <a href="report.json">근거 JSON</a></p>
<div class="scroll" tabindex="0" role="region" aria-label="전략 비교 결과"><table><thead><tr>{heading}</tr></thead><tbody>{cells}</tbody></table></div>
<script>document.querySelector('#filter').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();
document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));}});</script></html>"""
    (output / "index.html").write_text(document)
    return summary
