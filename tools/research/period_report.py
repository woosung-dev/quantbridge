"""고정 연구 원장으로 인터넷 없이 열리는 한국어 진행 보고서를 만든다."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from tools.research.pine_first import build_pine_first_view  # noqa: E402

DEFAULT_RUN = Path("runs/indicator-strategy-period-study-20261026")
DEFAULT_OUTPUT = Path("/Users/woosung/Downloads/QuantBridge-기간별-비교연구-20261026")
KST = timezone(timedelta(hours=9))
METRICS = (
    "total_return",
    "max_drawdown",
    "closed_episode_win_rate_pct",
    "closed_episodes",
    "episode_count",
    "fill_count",
    "profit_factor",
    "sharpe_ratio",
    "total_fees",
    "total_slippage",
    "total_funding",
    "open_pnl",
    "long_closed_episode_net_pnl",
    "short_closed_episode_net_pnl",
)
IDENTITY = (
    "publication_id",
    "code_path",
    "timeframe",
    "period",
    "policy",
    "signal_mode",
)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_bytes())


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def local_file(root: Path, relative: object, expected: object = None) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return None
    if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        return None
    return path


def json_script(value) -> str:
    """원문 제목의 HTML·스크립트 종결 문자열이 실행 문맥을 벗어나지 못하게 한다."""
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # CSV를 스프레드시트에서 열어도 원문 제목을 수식으로 실행하지 않는다.
            writer.writerow(
                {
                    key: (
                        "'" + value
                        if isinstance(value, str) and value.startswith(("=", "+", "@"))
                        else value
                    )
                    for key, value in row.items()
                }
            )


def records(root: Path, pattern: str) -> list[dict]:
    return [read_json(path) for path in sorted(root.glob(pattern)) if path.is_file()]


def file_stage(root: Path, items: list[dict], status: str, file_key: str, hash_key: str) -> int:
    return sum(
        item.get("status") == status
        and bool(item.get(hash_key))
        and local_file(root, item.get(file_key), item.get(hash_key)) is not None
        for item in items
    )


def evidence_counts(root: Path) -> dict:
    native = records(root, "native-verification/*.json")
    registration = records(root, "registration/*.json")
    # 파일 보유·판정 텍스트를 기술 검증이나 실제 GET 재조회 성공으로 승격하지 않는다.
    native_pass = sum(
        item.get("status") == "passed"
        and item.get("evidence_verified") is True
        and isinstance(item.get("evidence"), list)
        and bool(item["evidence"])
        and all(
            isinstance(proof, dict)
            and proof.get("sha256")
            and local_file(root, proof.get("path"), proof["sha256"]) is not None
            for proof in item["evidence"]
        )
        for item in native
    )
    registered = sum(
        item.get("status") == "registered" and item.get("get_verified") is True
        for item in registration
    )
    return {
        "native_records": len(native),
        "native_passed": native_pass,
        "native_statuses": dict(Counter(item.get("status", "UNKNOWN") for item in native)),
        "registered": registered,
        "registration_records": len(registration),
        "registration_statuses": dict(
            Counter(item.get("status", "UNKNOWN") for item in registration)
        ),
    }


def derived_activity(
    fills: list[dict], start: str, end: str, closed_episodes: int, minute_count: int
) -> dict:
    """분봉 포함 규칙을 명시한 시간 노출과 30일당 완료 episode 빈도."""
    left, right = datetime.fromisoformat(start), datetime.fromisoformat(end)
    if left.utcoffset() is None or right.utcoffset() is None:
        raise ValueError("평가 경계의 시간대가 필요합니다")
    seconds = int((right - left).total_seconds())
    if seconds <= 0 or seconds % 60 or minute_count != seconds // 60:
        raise ValueError("노출 분모의 연속된 전체 1분 평가 곡선이 필요합니다")
    if type(closed_episodes) is not int or closed_episodes < 0:
        raise ValueError("완료 episode 수가 필요합니다")
    active, intervals = {}, []
    for fill in fills:
        episode = fill.get("episode_id", fill.get("generation"))
        timestamp = datetime.fromisoformat(fill["timestamp"])
        if timestamp.utcoffset() is None or fill.get("phase") not in {
            "bar_open",
            "intrabar_scenario",
        }:
            raise ValueError("체결의 시간대와 실행 phase가 필요합니다")
        timestamp = timestamp.replace(second=0, microsecond=0)
        quantity = Decimal(str(fill["quantity"]))
        if not quantity.is_finite() or quantity <= 0 or episode is None:
            raise ValueError("체결 수량과 episode ID가 필요합니다")
        if fill["kind"] == "entry":
            if episode in active:
                raise ValueError("같은 episode의 중복 진입 체결입니다")
            active[episode] = (timestamp, quantity)
        else:
            if episode not in active or quantity > active[episode][1]:
                raise ValueError("진입 없는 체결 또는 잔량 초과 청산입니다")
            entered, remaining = active[episode]
            remaining -= quantity
            if remaining == 0:
                finished = timestamp + (
                    timedelta(minutes=1) if fill["phase"] == "intrabar_scenario" else timedelta()
                )
                intervals.append((max(left, entered), min(right, finished)))
                del active[episode]
            else:
                active[episode] = (entered, remaining)
    intervals.extend((max(left, entered), right) for entered, _quantity in active.values())
    merged = []
    for entered, finished in sorted(intervals):
        if finished <= entered:
            continue
        if merged and entered <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], finished))
        else:
            merged.append((entered, finished))
    held = sum(int((finished - entered).total_seconds()) // 60 for entered, finished in merged)
    return {
        "trade_frequency_30d": str(
            Decimal(closed_episodes) * Decimal(30 * 86400) / Decimal(seconds)
        ),
        "exposure_pct": str(Decimal(held) * Decimal(100) / Decimal(minute_count)),
        "exposure_held_minutes": held,
        "exposure_total_minutes": minute_count,
        "activity_convention": "completed_episodes_per_30_calendar_days;minute_union_bar_open_exclusive_intrabar_inclusive_v1",
    }


def export_ledgers(root: Path, output: Path, rows: list[dict]) -> dict:
    episodes, fills, links = [], [], {}
    integrity = Counter()
    trace_path = output / "ledgers" / "trace.jsonl.gz"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(trace_path, "wt", encoding="utf-8") as trace_stream:
        for row in rows:
            if row.get("status") != "completed":
                continue
            path = local_file(root, row.get("result_file"), row.get("result_sha256"))
            if (
                path is None
                or not row.get("result_sha256")
                or path.relative_to(root.resolve()).parts[0] != "cells"
            ):
                row["result_integrity"] = "missing_or_hash_mismatch"
                integrity["missing_or_hash_mismatch"] += 1
                continue
            raw = path.read_bytes()
            result = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
            row["result_integrity"] = "verified"
            integrity["verified"] += 1
            relative = Path("evidence") / path.relative_to(root.resolve())
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            row["evidence_link"] = quote(relative.as_posix())
            identity = {key: row.get(key) for key in IDENTITY}
            for trade in result.get("trades", []):
                episodes.append({**identity, **trade})
            timestamps, cell_fills = [], []
            for event in result.get("trace", []):
                trace_stream.write(
                    json.dumps({**identity, "event": event}, ensure_ascii=False) + "\n"
                )
                if event.get("type") == "fill":
                    fills.append({**identity, **event})
                    cell_fills.append(event)
                    if isinstance(event.get("timestamp"), str):
                        timestamps.append(event["timestamp"])
            row["first_fill_utc"] = min(timestamps) if timestamps else None
            row["last_fill_utc"] = max(timestamps) if timestamps else None
            for key in ("first_fill_utc", "last_fill_utc"):
                row[key.replace("_utc", "_kst")] = (
                    datetime.fromisoformat(row[key]).astimezone(KST).isoformat()
                    if row[key]
                    else None
                )
            row["funding_data_incomplete"] = result.get("metrics", {}).get(
                "funding_data_incomplete"
            )
            row["sharpe_convention"] = result.get("metrics", {}).get("sharpe_convention")
            curve = result.get("equity_curve")
            encoding = result.get("curve_encoding", {})
            if isinstance(curve, list):
                minute_count = len(curve)
                row["curve_storage"] = "raw_minute_curves"
            elif (
                encoding.get("kind") == "event_ledger_recipe_v1"
                and encoding.get("restoration_verified") is True
            ):
                minute_count = encoding.get("row_count")
                row["curve_storage"] = "event_ledger_recipe_v1_verified_restoration"
            else:
                minute_count = None
                row["curve_storage"] = "unverified_or_missing"
            try:
                row.update(
                    derived_activity(
                        cell_fills,
                        row["start_utc"],
                        row["end_exclusive_utc"],
                        row["closed_episodes"],
                        minute_count,
                    )
                )
            except (ValueError, KeyError, TypeError, InvalidOperation) as error:
                row.update(
                    trade_frequency_30d=None,
                    exposure_pct=None,
                    activity_unavailable_reason=str(error),
                )
    for name, entries in (("episodes", episodes), ("fills", fills)):
        fields = list(IDENTITY) + sorted({key for item in entries for key in item} - set(IDENTITY))
        write_csv(output / "ledgers" / f"{name}.csv", entries, fields)
        write_json(output / "ledgers" / f"{name}.json", entries)
        links[name] = f"ledgers/{name}.csv"
    return {
        "integrity": dict(integrity),
        "episodes": len(episodes),
        "fills": len(fills),
        "links": links,
    }


def prepare(run: Path, output: Path) -> dict:
    catalogue = read_json(run / "catalogue.json", {"items": []})
    manifest = read_json(run / "manifest.json", {})
    exported = read_json(run / "report-input.json", {})
    dataset = read_json(run / "data/dataset.json", {})
    receipts = records(run, "source_receipts/*.json")
    reviews = records(run, "reviews/*.json")
    generations = records(run, "generation/*/status.json")
    source_audit = read_json(run / "source-capture-audit.json", {})
    audited_failures = {
        item["publication_id"]: item for item in source_audit.get("failed_sources", [])
    }
    rows = exported.get("cells", [])
    source_target = manifest.get("source_count", len(catalogue["items"]))
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("report-input.cells는 객체 목록이어야 합니다")
    keys = [tuple(row.get(name) for name in IDENTITY[:5]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("금융 셀 식별자가 중복됩니다")
    ledger = export_ledgers(run, output, rows)
    sources = {item.get("id", item.get("publication_id")): item for item in receipts}
    review_by_id = {item.get("id", item.get("publication_id")): item for item in reviews}
    source_rows = []
    for item in catalogue["items"]:
        pid = item.get("publication_id", item.get("id"))
        source = sources.get(pid, {})
        review = review_by_id.get(pid, {})
        audited = audited_failures.get(pid, {})
        source_rows.append(
            {
                "publication_id": pid,
                "title": item.get("title"),
                "kind": item.get("kind"),
                "author": item.get("author"),
                "url": item.get("url"),
                "source_status": source.get("status", "pending"),
                "source_sha256": source.get("source_sha256"),
                "source_reason": source.get("error", source.get("reason")),
                "source_attempts": len(source.get("attempts", [])),
                "source_audit_classification": audited.get("classification"),
                "source_audit_reason": audited.get("reason"),
                "review_status": review.get("status", "UNKNOWN" if review else "pending"),
                "signal_mode": review.get("signal_mode"),
                "native_verification": "reported_separately",
            }
        )
    write_json(output / "sources-status.json", source_rows)
    write_csv(
        output / "sources-status.csv",
        source_rows,
        list(source_rows[0]) if source_rows else ["publication_id"],
    )
    source_by_id = {item["publication_id"]: item for item in source_rows}
    for row in rows:
        source = source_by_id.get(row.get("publication_id"), {})
        row["url"] = source.get("url")
        row["author"] = source.get("author")
        row["signal_mode"] = row.get("signal_mode") or source.get("signal_mode")
    review_statuses = Counter(item.get("status", "UNKNOWN") for item in reviews)
    generation_reviews = Counter()
    for item in generations:
        path = local_file(run, item.get("generated_file"), item.get("generated_sha256"))
        if item.get("status") != "completed" or not item.get("generated_sha256") or path is None:
            continue
        reviewed = read_json(path.parent / "code-review.json", {})
        source = sources.get(item.get("publication_id", item.get("id")), {})
        approved = (
            reviewed.get("status") == "reviewed_for_isolated_execution"
            and reviewed.get("generated_sha256") == item["generated_sha256"]
            and reviewed.get("original_source_sha256") == source.get("source_sha256")
            and bool(source.get("source_sha256"))
            and bool(reviewed.get("reviewer"))
            and bool(reviewed.get("checks"))
        )
        generation_reviews[
            "approved"
            if approved
            else "rejected"
            if reviewed.get("status") == "rejected"
            else "pending"
        ] += 1
    pine_first = build_pine_first_view(run, rows)
    selected_rows = pine_first["rows"]
    selected_progress = pine_first["progress"]
    required_progress = {
        "financial_target",
        "financial_recorded",
        "financial_statuses",
        "financial_pending",
        "pine_completed",
        "python_fallback_completed",
        "legacy_financial_target",
        "legacy_financial_recorded",
        "legacy_financial_statuses",
        "legacy_python_completed_excluded",
    }
    if not required_progress <= selected_progress.keys():
        raise ValueError("Pine 우선 보고서의 현재·과거 분모와 경로별 집계가 필요합니다")
    selected_counts = selected_progress["financial_statuses"]
    if (
        sum(selected_counts.get(key, 0) for key in ("completed", "failed", "not_run", "pending"))
        != selected_progress["financial_target"]
        or selected_progress["pine_completed"] + selected_progress["python_fallback_completed"]
        != selected_counts.get("completed", 0)
        or selected_progress["financial_pending"] != selected_counts.get("pending", 0)
    ):
        raise ValueError("Pine 우선 보고서의 상태 분모 또는 성공 경로 합계가 다릅니다")
    generated_at = datetime.now(UTC).isoformat()
    progress = {
        "source_target": source_target,
        "source_captured_verified": file_stage(
            run, receipts, "captured", "source_file", "source_sha256"
        ),
        "source_statuses": dict(Counter(item.get("status", "UNKNOWN") for item in receipts)),
        "source_receipts": len(receipts),
        "review_records": len(reviews),
        "review_completed": sum(
            item.get("status") in {"reviewed", "ready", "supported", "ok"}
            and bool(item.get("reviewer", item.get("reviewed_by")))
            and bool(item.get("basis"))
            and isinstance(item.get("signal_bindings"), list)
            and bool(item["signal_bindings"])
            and item.get("source_sha256")
            == sources.get(item.get("id", item.get("publication_id")), {}).get("source_sha256")
            for item in reviews
        ),
        "review_statuses": dict(review_statuses),
        "review_pending": review_statuses["pending_review"],
        "review_not_comparable": review_statuses["not_comparable"],
        "generation_verified": file_stage(
            run, generations, "completed", "generated_file", "generated_sha256"
        ),
        "generation_statuses": dict(Counter(item.get("status", "UNKNOWN") for item in generations)),
        "generation_review_statuses": dict(generation_reviews),
        "generation_review_approved": generation_reviews["approved"],
        "reported_models": dict(
            Counter(item.get("provider_reported_model") or "UNKNOWN" for item in generations)
        ),
        "registration_target_max": source_target * 2 * 3,
        "legacy_registration_target_max": source_target * 2 * 2 * 3,
        **selected_progress,
        **evidence_counts(run),
    }
    periods = []
    for period in manifest.get("periods", []):
        periods.append(
            {
                **period,
                "start_kst": datetime.fromisoformat(period["start"]).astimezone(KST).isoformat(),
                "end_exclusive_kst": datetime.fromisoformat(period["end_exclusive"])
                .astimezone(KST)
                .isoformat(),
            }
        )
    summary = {
        "schema_version": 1,
        "report_kind": "progress",
        "generated_at_utc": generated_at,
        "generated_at_kst": datetime.fromisoformat(generated_at).astimezone(KST).isoformat(),
        "controller_observed_at": exported.get("progress", {}).get("observed_at"),
        "progress": progress,
        "periods": periods,
        "units": {
            **exported.get("units", {}),
            "trade_frequency_30d": "episodes_per_30_calendar_days",
            "exposure_pct": "percent_0_100",
        },
        "source_summary": catalogue.get("summary", {}),
        "source_audit": source_audit.get("summary", {}),
        "costs": manifest.get("costs", {}),
        "ledger": ledger,
        "dataset": {
            "symbol": dataset.get("symbol"),
            "funding_status": dataset.get("funding_status", "UNKNOWN"),
            "historical_schedule_independently_verified": dataset.get(
                "historical_schedule_independently_verified", False
            ),
            "files": dataset.get("files", {}),
        },
        "deployment_status": "awaiting_review_and_deployment",
        "scope": "provided_download_only_current_popularity_retrospective",
        "execution_policy": pine_first["policy"],
        "cells": selected_rows,
    }
    write_json(
        output / "study-summary.json",
        {key: value for key, value in summary.items() if key != "cells"},
    )
    write_json(output / "financial-cells.json", {"units": summary["units"], "cells": rows})
    write_json(
        output / "selected-financial-cells.json",
        {"units": summary["units"], "policy": pine_first["policy"], "cells": selected_rows},
    )
    fields = list(
        dict.fromkeys(
            [
                *IDENTITY,
                "title",
                "kind",
                "symbol",
                "market",
                "status",
                "reason",
                "start_utc",
                "end_exclusive_utc",
                "start_kst",
                "end_exclusive_kst",
                *METRICS,
                "signal_hash",
                "first_fill_utc",
                "last_fill_utc",
                "first_fill_kst",
                "last_fill_kst",
                "trade_frequency_30d",
                "exposure_pct",
                "exposure_held_minutes",
                "exposure_total_minutes",
                "activity_convention",
                "sharpe_convention",
                "curve_storage",
                "result_file",
                "result_sha256",
                "result_integrity",
                "evidence_link",
            ]
        )
    )
    write_csv(output / "financial-cells.csv", rows, fields)
    write_csv(
        output / "selected-financial-cells.csv",
        selected_rows,
        [*fields, "selection_reason", "recovery_pending", "failed_terminal", "execution_attempt",
         "original_path_status", "original_path_reason"],
    )
    write_json(
        output / "provenance.json",
        {
            "inputs": {
                str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (
                    run / name
                    for name in (
                        "catalogue.json",
                        "manifest.json",
                        "report-input.json",
                        "data/dataset.json",
                        "source-capture-audit.json",
                    )
                )
                if path.exists()
            },
            "generated_at_utc": generated_at,
            "scope": summary["scope"],
            "units": summary["units"],
        },
    )
    if source_audit:
        write_json(output / "source-capture-audit.json", source_audit)
    return summary


CORE_JS = r"""
const ReportCore = (() => {
 const number = value => {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
  const n = Number(value); return Number.isFinite(n) ? n : null;
 };
 const scaled = (value, unit) => {
  const n = number(value); if (n === null || !unit) return null;
  return unit === 'ratio' || unit === 'ratio_negative' ? n * 100 : n;
 };
 const value = (row, metric, units) => {
  if (!row || row.status !== 'completed') return null;
  const unit = units[metric] ?? (['episode_count','closed_episodes','fill_count'].includes(metric) ? 'count' : metric === 'sharpe_ratio' ? 'number' : null);
  return scaled(row[metric], unit);
 };
 const groups = rows => {
  const map = new Map();
  for (const row of rows) {
   const key = JSON.stringify(['publication_id','code_path','timeframe','period','signal_mode'].map(k => row[k] ?? null));
   if (!map.has(key)) map.set(key, {key, ...row, A:null, B:null});
   map.get(key)[row.policy] = row;
  }
  return [...map.values()];
 };
 const matches = (group, filters, units) => {
  if (filters.query && ![group.title,group.publication_id,group.author].join(' ').toLowerCase().includes(filters.query.toLowerCase())) return false;
  for (const key of ['kind','code_path','period','timeframe','signal_mode']) if (filters[key] && filters[key] !== group[key]) return false;
  let selected = filters.policy ? [group[filters.policy]].filter(Boolean) : [group.A,group.B].filter(Boolean);
  if (filters.status) selected = selected.filter(row => filters.status === 'recovery_pending' ? row.recovery_pending === true : row.status === filters.status && !(filters.status === 'pending' && row.recovery_pending));
  if (!selected.length) return false;
  if (filters.min !== null || filters.max !== null) {
   return selected.some(row => { const n = value(row,filters.metric,units); return n !== null && (filters.min === null || n >= filters.min) && (filters.max === null || n <= filters.max); });
  }
  return true;
 };
 const compare = (left,right,key,direction,units) => {
  const [policy,metric] = key.split('.');
  const a = value(left[policy],metric,units), b = value(right[policy],metric,units);
  if (a === null || b === null) return a === b ? left.key.localeCompare(right.key) : a === null ? 1 : -1;
  return (a-b)*(direction === 'desc' ? -1:1) || left.key.localeCompare(right.key);
 };
 return {number,scaled,value,groups,matches,compare};
})();
if (typeof module !== 'undefined') module.exports = ReportCore;
"""

CSS = r"""
:root{color-scheme:light;--ink:#17263b;--muted:#526277;--back:#f3f5f8;--paper:#fff;--line:#d7dee8;--blue:#194da2;--green:#12623c;--red:#a72e36;--tint:#e9f0fb;--amber:#805100}*{box-sizing:border-box}body{margin:0;background:var(--back);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}a{color:var(--blue);text-underline-offset:3px}button,input,select{font:inherit}button,select{cursor:pointer}button,input,select{min-height:44px;border:1px solid #aab8ca;border-radius:6px;background:var(--paper);color:var(--ink);padding:8px 12px}input,select{width:100%;min-width:0}button:hover{background:var(--tint)}button:disabled{opacity:.45;cursor:default}:is(a,button,input,select,[tabindex]):focus-visible{outline:3px solid #155ed0;outline-offset:3px}header{background:#17263b;color:#fff;padding:36px max(20px,calc((100vw - 1560px)/2))}header p{color:#d6e0ee;margin:8px 0}h1{font-size:clamp(25px,3.6vw,38px);line-height:1.25;letter-spacing:-1px;margin:8px 0 14px}h2{font-size:22px;line-height:1.35;margin:0 0 16px}.eyebrow{font-size:13px;letter-spacing:1.2px;font-weight:700}.status{display:inline-block;background:#fff2c6;color:#634200;padding:4px 10px;border-radius:4px;font-size:13px;font-weight:700}main{max-width:1600px;margin:0 auto;padding:24px 20px 60px}section{margin:0 0 24px}.panel{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:22px}.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.stage{padding:18px;background:var(--paper);border:1px solid var(--line);border-radius:8px}.stage h2{font-size:14px;color:var(--muted);margin:0 0 8px}.stage strong{display:block;font-size:27px;font-variant-numeric:tabular-nums}.stage p{font-size:13px;color:var(--muted);margin:6px 0 0}progress{width:100%;height:8px;accent-color:var(--blue)}.meta{font-size:13px;color:var(--muted)}.notice{border-left:4px solid #b67b16;background:#fff9e9;padding:16px 20px;color:#5c440f}.links{display:flex;flex-wrap:wrap;gap:12px 22px}.links a{min-height:44px;display:inline-flex;align-items:center}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.field label{font-size:13px;font-weight:700;display:block;margin:0 0 5px;color:var(--muted)}.search{grid-column:span 2}.range{display:grid;grid-template-columns:1fr 1fr;gap:10px}.toolbar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;margin:18px 0 10px}.toolbar p{margin:0}.table-region{overflow:auto;background:var(--paper);border:1px solid var(--line);border-radius:8px}table{border-collapse:separate;border-spacing:0;width:100%;min-width:1550px;font-size:13px}caption{text-align:left;padding:14px;font-weight:700;color:var(--muted)}th,td{padding:12px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top;font-variant-numeric:tabular-nums}th{background:#e9eef6;color:#233c5c;white-space:nowrap}th button{border:0;background:transparent;padding:6px 4px;font-size:13px;min-height:44px;white-space:nowrap}th:first-child,td:first-child{text-align:left;min-width:230px;max-width:320px}td:nth-child(2),td:nth-child(3){text-align:left;min-width:110px}tbody tr:hover{background:#f8faff}.positive{color:var(--green)}.negative{color:var(--red)}.unavailable{color:var(--muted)}.small{display:block;font-size:12px;color:var(--muted);white-space:normal}.pill{display:inline-block;border-radius:4px;padding:2px 6px;background:#edf1f7;color:#42536b;font-size:11px}.error{color:var(--red)}.detail td{text-align:left;background:#f8fafc;padding:0 16px 10px}.detail summary{cursor:pointer;min-height:44px;display:flex;align-items:center;color:var(--blue);font-size:13px}.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.detail pre{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;font-size:13px;margin:4px 0}.detail h3{font-size:14px}.empty{padding:45px 20px;text-align:center}.empty p{margin:6px 0 18px}.pager{display:flex;justify-content:center;align-items:center;gap:18px;margin:18px 0}.periods{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.periods article{border-left:3px solid #d5deed;padding:0 12px;font-size:13px}.periods strong{display:block}.periods time{display:block;font-variant-numeric:tabular-nums;font-size:12px}.limits{display:grid;grid-template-columns:1fr 1fr;gap:24px}.limits p{margin:0 0 12px}footer{font-size:13px;color:var(--muted);padding-top:8px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}[hidden]{display:none!important}@media(max-width:1100px){.stages{grid-template-columns:repeat(3,minmax(0,1fr))}.periods{grid-template-columns:repeat(3,minmax(0,1fr))}.filters{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:700px){header{padding:26px 16px}main{padding:16px 12px 40px}.panel{padding:16px}.stages{grid-template-columns:repeat(2,minmax(0,1fr))}.stage:last-child:nth-child(odd){grid-column:1/-1}.stage strong{font-size:24px}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.search{grid-column:1/-1}.periods{grid-template-columns:1fr}.limits,.detail-grid{grid-template-columns:1fr}.toolbar{align-items:flex-start}.pager{gap:10px}.pager button{padding-inline:10px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
"""

UI_JS = r"""
const report=JSON.parse(document.getElementById('report-data').textContent);
const $=id=>document.getElementById(id), core=ReportCore, units=report.units, all=core.groups(report.cells);
const labels={completed:'완료',failed:'최종 실패',not_run:'명시적 미실행',running:'실행 중',pending:'대기'};
const statusLabel=row=>row.recovery_pending?'복구 대기':(labels[row.status]??row.status);
const metrics=[['total_return','총수익률'],['max_drawdown','최대 낙폭'],['closed_episode_win_rate_pct','완료 승률'],['episode_count','episode'],['fill_count','fill']];
let sortKey='A.total_return',direction='desc',page=1,filtered=[],timer;
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nf=new Intl.NumberFormat('ko-KR',{maximumFractionDigits:2});
function num(row,key){const n=core.value(row,key,units);if(n===null)return '<span class="unavailable">미산출</span>';const pct=['total_return','max_drawdown','closed_episode_win_rate_pct'].includes(key);const color=key==='total_return'?(n<0?'negative':n>0?'positive':''):'';return '<span class="'+color+'">'+nf.format(n)+(pct?'%':'')+'</span>'}
function bounds(id){return $(id).value===''?null:core.number($(id).value)}
function filters(){return Object.fromEntries(['kind','code_path','policy','period','timeframe','signal_mode','status','metric'].map(k=>[k,$(k).value]).concat([['query',$('query').value.trim()],['min',bounds('min')],['max',bounds('max')]]))}
function apply(){clearTimeout(timer);const f=filters(),invalid=(f.min!==null&&f.max!==null&&f.min>f.max)||['min','max'].some(k=>!$(k).validity.valid);$('filter-error').hidden=!invalid;$('filter-error').textContent=invalid?'숫자 범위와 최솟값 ≤ 최댓값을 확인하세요.':'';filtered=invalid?[]:all.filter(g=>core.matches(g,f,units));filtered.sort((a,b)=>core.compare(a,b,sortKey,direction,units));page=1;render()}
function evidence(row){if(!row)return '정책 기록 대기';const parts=['상태: '+statusLabel(row),'실행 결과 근거: '+(row.result_integrity==='verified'?'파일 SHA256 확인':row.result_integrity??'해당 없음')];for(const [key,label] of [['profit_factor','Profit factor'],['sharpe_ratio','샤프'],['total_fees','수수료 USDT'],['total_slippage','슬리피지 USDT'],['total_funding','펀딩 USDT'],['open_pnl','미청산 평가손익 USDT'],['long_closed_episode_net_pnl','롱 완료 순손익 USDT'],['short_closed_episode_net_pnl','숏 완료 순손익 USDT']]){const n=key==='sharpe_ratio'&&!['tv_monthly_rfr2','tv_daily_rfr2'].includes(row.sharpe_convention)?null:core.number(row[key]);parts.push(label+': '+(row.status==='completed'&&n!==null?nf.format(n):'미산출'))}parts.push('곡선 저장: '+(row.curve_storage==='raw_minute_curves'?'원시 1분 곡선':row.curve_storage==='event_ledger_recipe_v1_verified_restoration'?'원장·데이터 SHA 기반 재현 recipe · 전량 복원 검증 기록':'저장·복원 미확인'));parts.push('샤프 관례: '+(row.sharpe_convention??'UNKNOWN'));parts.push('거래 빈도: '+(core.number(row.trade_frequency_30d)===null?'미산출':nf.format(Number(row.trade_frequency_30d))+' 완료 episode / 30일'));parts.push('보유 시간 노출: '+(core.number(row.exposure_pct)===null?'미산출':nf.format(Number(row.exposure_pct))+'%')+' · 분봉 포함 가정');if(row.activity_unavailable_reason)parts.push('빈도·노출 미산출 사유: '+row.activity_unavailable_reason);parts.push('R 통계: '+(row.policy==='A'?'해당 없음':'개별 fill 계획·SL 변화 원장 참고'));parts.push('펀딩 완전성: '+(row.funding_data_incomplete===true?'누락 관측':row.funding_data_incomplete===false?'노출 없음 또는 해당 실행 완전':'UNKNOWN'));parts.push('최초 체결 UTC / KST: '+(row.first_fill_utc??'미산출')+' / '+(row.first_fill_kst??'미산출'));parts.push('최종 체결 UTC / KST: '+(row.last_fill_utc??'미산출')+' / '+(row.last_fill_kst??'미산출'));parts.push('신호 해시: '+(row.signal_hash??'미산출'));if(row.reason)parts.push('사유: '+row.reason);return '<pre>'+esc(parts.join('\n'))+'</pre>'+(row.evidence_link?'<a download href="'+esc(row.evidence_link)+'">전체 결과·재현 기록 JSON.GZ</a>':'')}
function render(){const size=50,pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.max(1,Math.min(page,pages));const start=(page-1)*size;
 $('rows').innerHTML=filtered.slice(start,start+size).map(g=>{let title=esc(g.title||g.publication_id);if(typeof g.url==='string'&&/^https:\/\/(?:www\.)?tradingview\.com\/script\//.test(g.url))title='<a href="'+esc(g.url)+'" target="_blank" rel="noopener noreferrer">'+title+'</a>';const mode=g.signal_mode==='shared_events'?'공통 신호 · 청산 차이':g.signal_mode==='position_feedback'?'포지션 반영 · 매수·청산 변화':'신호 모드 미확인';let cells='<td>'+title+'<span class="small">'+esc(g.publication_id)+' · '+esc(g.kind==='strategies'?'전략':'지표')+' · '+esc(g.code_path==='python'?'Python · 대체':'Pine')+'</span></td><td>'+esc(g.period)+' · '+esc(g.timeframe)+'<span class="small">UTC ['+esc(g.start_utc)+' , '+esc(g.end_exclusive_utc)+')</span></td><td>'+esc(mode)+'</td>';for(const p of ['A','B'])for(const [key] of metrics){const row=g[p];cells+='<td>'+num(row,key)+(key==='total_return'?'<span class="small">'+esc(row?statusLabel(row):'기록 대기')+'</span>':key==='episode_count'&&row?'<span class="small">완료 '+esc(row.closed_episodes??'미산출')+'</span>':'')+'</td>'}return '<tr>'+cells+'</tr><tr class="detail"><td colspan="13"><details><summary>비용·롱/숏·실제 체결 시각·근거 보기</summary><p class="meta">평가 KST ['+esc(g.start_kst)+' , '+esc(g.end_exclusive_kst)+') · 종료 미포함</p><div class="detail-grid"><div><h3>A · 신호 청산</h3>'+evidence(g.A)+'</div><div><h3>B · 손절·반익절·추적</h3>'+evidence(g.B)+'</div></div></details></td></tr>'}).join('');
 $('count').textContent=filtered.length.toLocaleString('ko-KR')+'개 A/B 비교행 · 금융 기록 '+report.cells.length.toLocaleString('ko-KR')+' / '+report.progress.financial_target.toLocaleString('ko-KR')+'셀';$('empty').hidden=filtered.length!==0;$('page-info').textContent=filtered.length?page+' / '+pages+' 페이지':'0 / 0 페이지';$('prev').disabled=page<=1||!filtered.length;$('next').disabled=page>=pages||!filtered.length;
 document.querySelectorAll('[data-sort]').forEach(b=>{const active=b.dataset.sort===sortKey;b.querySelector('span').textContent=active?(direction==='desc'?'↓':'↑'):'↕';b.closest('th').setAttribute('aria-sort',active?(direction==='desc'?'descending':'ascending'):'none')});$('sort-state').textContent=sortKey.replace('total_return','총수익률').replace('max_drawdown','최대 낙폭').replace('closed_episode_win_rate_pct','완료 승률').replace('episode_count','episode').replace('fill_count','fill')+' '+(direction==='desc'?'내림차순':'오름차순')+' · 미산출은 마지막';
}
for(const p of ['A','B'])for(const [key,label] of metrics){const th=document.createElement('th');th.scope='col';th.innerHTML='<button type="button" data-sort="'+p+'.'+key+'" aria-label="'+p+' '+label+' 정렬">'+label+' <span aria-hidden="true">↕</span></button>';$('metric-head').appendChild(th)}
 document.querySelectorAll('[data-sort]').forEach(b=>b.addEventListener('click',()=>{direction=sortKey===b.dataset.sort&&direction==='desc'?'asc':'desc';sortKey=b.dataset.sort;apply()}));
$('filters').addEventListener('submit',e=>{e.preventDefault();apply()});for(const id of ['kind','code_path','policy','period','timeframe','signal_mode','status','metric','min','max'])$(id).addEventListener('input',apply);$('query').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(apply,180)});function reset(){$('filters').reset();sortKey='A.total_return';direction='desc';apply()}$('reset-filters').addEventListener('click',reset);$('empty-reset').addEventListener('click',reset);$('prev').addEventListener('click',()=>{page--;render()});$('next').addEventListener('click',()=>{page++;render()});apply();
"""


def render(summary: dict) -> str:
    p = summary["progress"]

    def esc(value):
        return html.escape(str(value), quote=True)

    recovery = p.get("financial_recovery_pending", 0)
    native_deferred = (
        summary.get("execution_policy", {}).get("native_verification")
        == "deferred_until_after_financial_research"
    )
    status_text = (
        f"최종 실패 {p['financial_statuses'].get('failed', 0):,} · "
        f"복구 대기 {recovery:,} · "
        f"미실행 {p['financial_statuses'].get('not_run', 0):,} · "
        f"일반 대기 {p['financial_pending'] - recovery:,}"
    )
    stages = [
        (
            "1. 원문 확보",
            p["source_captured_verified"],
            p["source_target"],
            "실제 소스 파일·SHA 일치. 목록 확보와 구분",
        ),
        (
            "2. 원문 신호 매핑",
            p["review_completed"],
            p["source_target"],
            "Pine 우선 · Python은 필요한 대체 범위만 검토",
        ),
        (
            "3. 원본 신호 대조",
            p["native_passed"],
            p["source_target"] * 3,
            f"원본·시간봉 조합. 판정 {p['native_records']:,}건 · 파일 보유와 통과 구분",
        ),
        (
            "4. 금융 셀 · 언어 중복 제외",
            p["financial_statuses"].get("completed", 0),
            p["financial_target"],
            f"Pine {p['pine_completed']:,} · Python 대체 {p['python_fallback_completed']:,} · {status_text}",
        ),
        (
            "5. 등록·GET 재조회",
            p["registered"],
            p["registration_target_max"],
            "최대 원본·선택 경로·A/B·시간봉 조합. 전체 연구 후 마지막 단계",
        ),
    ]
    if native_deferred:
        stages = [stage for stage in stages if stage[0] != "3. 원본 신호 대조"]
        stages = [
            (f"{index}. {title.split('. ', 1)[1]}", done, total, note)
            for index, (title, done, total, note) in enumerate(stages, 1)
        ]
    cards = "".join(
        f'<article class="stage"><h2>{esc(title)}</h2><strong>{done:,} <span class="meta">/ {total:,}</span></strong><progress value="{done}" max="{max(total, 1)}" aria-label="{esc(title)} {done} / {total}"></progress><p>{esc(note)}</p></article>'
        for title, done, total, note in stages
    )
    periods = "".join(
        f"<article><strong>{esc(period['id'])}</strong><time>UTC {esc(period['start'])}<br>≤ 평가 &lt; {esc(period['end_exclusive'])}</time><time>KST {esc(period['start_kst'])}<br>≤ 평가 &lt; {esc(period['end_exclusive_kst'])}</time></article>"
        for period in summary["periods"]
    )

    def select(name, label, options):
        values = '<option value="">전체</option>' + "".join(
            f'<option value="{esc(value)}">{esc(text)}</option>' for value, text in options
        )
        return f'<div class="field"><label for="{name}">{label}</label><select id="{name}">{values}</select></div>'

    controls = "".join(
        [
            select("kind", "원본 분류", [("indicators", "지표"), ("strategies", "전략")]),
            select(
                "code_path",
                "코드 경로",
                [("pine", "Pine"), ("python", "Python · 대체")],
            ),
            select(
                "policy",
                "기록된 정책",
                [("A", "A · 신호 청산"), ("B", "B · 보호 청산")],
            ),
            select(
                "signal_mode",
                "신호 비교 방식",
                [
                    ("shared_events", "공통 신호 · 청산 효과"),
                    ("position_feedback", "포지션 반영 · 매수·청산 변화"),
                ],
            ),
            select(
                "period",
                "평가 기간",
                [(period["id"], period["id"]) for period in summary["periods"]],
            ),
            select(
                "timeframe",
                "신호 시간봉",
                [("1h", "1시간"), ("4h", "4시간"), ("1d", "1일")],
            ),
            select(
                "status",
                "금융 실행 상태",
                [
                    ("completed", "완료"),
                    ("failed", "최종 실패"),
                    ("recovery_pending", "복구 대기"),
                    ("pending", "일반 대기"),
                    ("not_run", "명시적 미실행"),
                ],
            ),
        ]
    )
    dataset_files = summary["dataset"]["files"]
    data_ranges = "".join(
        f"<li>{esc(period)} · {len(files)}개 주기/펀딩 파일 · "
        + esc(
            ", ".join(
                f"{key}: {value.get('rows', '?'):,}행"
                if isinstance(value.get("rows"), int)
                else f"{key}: 행 수 미확인"
                for key, value in files.items()
            )
        )
        + "</li>"
        for period, files in dataset_files.items()
    )
    audit = summary["source_audit"]
    failures = audit.get("failure_classifications", {})
    source_failure_note = (
        f"소스 미확보 {audit.get('capture_failed', 0):,}건: 최초 수집은 Source code 버튼 8초 대기 실패입니다. "
        f"현재 공개 페이지·ID 기본 URL의 404 확인 {failures.get('current_publication_not_found_404', 0):,}건, "
        f"소스 탭 확인 {failures.get('current_source_tab_available', 0):,}건, "
        f"미확인 {failures.get('unconfirmed', 0):,}건입니다. 보호 스크립트 실증 {audit.get('protected_proven', 0):,}건. "
        "404만으로 삭제·비공개·일시 상태를 구분할 수 없습니다."
        if audit
        else "소스 미확보 사유의 독립 감사는 아직 없습니다. 수집 실패를 보호 스크립트로 판정하지 않습니다."
    )
    audit_link = (
        '<a href="source-capture-audit.json" download>소스 미확보·전량 SHA 감사 JSON</a>'
        if audit
        else ""
    )
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"><link rel="icon" href="data:,"><title>QuantBridge 기간별 A/B 비교 연구 · 진행 보고서</title><style>{CSS}</style></head>
<body><header><div class="eyebrow">QUANTBRIDGE / RESEARCH NOTE 2026.10.26</div><h1>Pine 우선 기간별 연구,<br>두 청산 정책 비교</h1><span class="status">진행 보고서 · 연구 미완료</span><p>작성 UTC {esc(summary["generated_at_utc"])}<br>KST {esc(summary["generated_at_kst"])}</p><p>작성 시점 스냅샷입니다. 실행 중인 작업의 완료를 뜻하지 않으며 이 파일은 자동 갱신되지 않습니다.</p></header>
<main><section class="stages" aria-label="단계별 완료 분모">{cards}</section>
<section class="notice"><strong>금융 실행 성공 ≠ TradingView 원본 일치 ≠ 수익성 검증 ≠ 실서버 등록</strong><br>정적 분류 기록 {p["review_records"]:,} / {p["source_target"]:,}원본: 매핑 확정 {p["review_completed"]:,} · 검토 대기 {p["review_pending"]:,} · 비교 불가 {p["review_not_comparable"]:,}. 현재 정책은 Pine 우선이며 Pine 성공 원본의 Python 생성·중복 금융 실행을 생략합니다. Python은 Pine 실행 실패 중 변환 가능한 범위에서 명시 근거를 확인한 대체만 포함합니다. 수익·승률을 보고 대체 경로를 선택하지 않습니다. Pine만 실패한 셀은 복구 대기이며, 검증된 Python 대체 금융 실행의 허용 재시도까지 소진한 경우만 최종 실패입니다. 생성 시간 초과·원문 또는 데이터 부재는 최종 금융 실패로 세지 않습니다.<br>현재 금융 분모 {p["financial_target"]:,}셀 · 과거 양언어 계획 {p["legacy_financial_target"]:,}셀. 기존 경로별 기록 {p["legacy_financial_recorded"]:,}셀과 현재 미선택 Python 완료 {p["legacy_python_completed_excluded"]:,}셀은 감사 자료로 보존합니다. 기존 Python 생성 파일 {p["generation_verified"]:,}개 · 명시 리뷰 승인 {p["generation_review_approved"]:,}개는 현재 실행 목표와 별도입니다.<br>{"원본 대조는 사용자 요청으로 금융 연구 뒤 후속 수행합니다. 기존 관측·검증 기록과 재개 목록을 보존합니다." if native_deferred else "원본 대조는 실제 캡처 근거를 검증한 범위만 통과로 셉니다."} 실서버 전략 등록은 전체 연구가 끝난 뒤 마지막에 진행하며 데모 활성화·주문은 포함하지 않습니다.</section>
<section class="panel"><h2>고정된 평가 기간</h2><div class="periods">{periods}</div><p class="meta">UTC 시작 포함·종료 미포함. 준비 이력은 거래 금지이며 기간 말 미청산 손익은 평가액에 포함합니다. 가상 종료 청산으로 비용을 추가하지 않습니다. 신호 주기 1h/4h/1d와 체결 계산 1분봉을 구분합니다.</p></section>
<section class="panel"><h2>결과 탐색</h2><form id="filters"><div class="filters"><div class="field search"><label for="query">원본 제목·작성자·publication ID</label><input id="query" type="search" placeholder="원본 검색" autocomplete="off"></div>{controls}<div class="field"><label for="metric">수치 필터 항목</label><select id="metric"><option value="total_return">총수익률 (%)</option><option value="max_drawdown">최대 낙폭 (%)</option><option value="closed_episode_win_rate_pct">완료 episode 승률 (%)</option><option value="episode_count">episode 수</option><option value="fill_count">fill 수</option></select></div><div class="field search"><label for="min">수치 범위 · 미산출은 범위 필터에서 제외</label><div class="range"><input id="min" type="number" step="any" placeholder="최소" aria-label="최솟값"><input id="max" type="number" step="any" placeholder="최대" aria-label="최댓값"></div></div><button id="reset-filters" type="button">필터·정렬 초기화</button></div><p id="filter-error" class="error" role="alert" hidden></p></form><p class="meta">A/B는 동일 원본·코드 경로·시간봉·평가 기간·신호 모드를 나란히 비교합니다. 정책 필터는 해당 정책 기록이 있는 비교행을 고릅니다. 공통 신호는 청산 효과, 포지션 반영 신호는 진입까지 달라지는 전체 전략 비교입니다.</p></section>
<section aria-label="A/B 성과 비교"><div class="toolbar"><p id="count" role="status" aria-live="polite"></p><p id="sort-state" class="meta" role="status"></p></div><div class="table-region" role="region" aria-label="가로 스크롤 가능한 A/B 성과 표" tabindex="0"><table><caption>표 제목을 누르면 정렬합니다. 단위가 없거나 실패·미실행인 셀은 미산출입니다.</caption><thead><tr><th rowspan="2" scope="col">원본 / 경로</th><th rowspan="2" scope="col">기간 / 신호 주기</th><th rowspan="2" scope="col">비교 해석</th><th colspan="5" scope="colgroup">A · 신호 청산</th><th colspan="5" scope="colgroup">B · 손절·반익절·추적</th></tr><tr id="metric-head"></tr></thead><tbody id="rows"></tbody></table><div id="empty" class="empty" hidden><strong>표시할 금융 결과가 없습니다.</strong><p>아직 실행되지 않았거나 현재 필터에 맞는 기록이 없습니다. 미실행을 수익률 0%로 표시하지 않습니다.</p><button id="empty-reset" type="button">조건 초기화</button></div></div><nav class="pager" aria-label="결과 페이지"><button id="prev" type="button">이전 50개</button><span id="page-info" role="status"></span><button id="next" type="button">다음 50개</button></nav></section>
<section class="panel"><h2>원장·근거 다운로드</h2><div class="links"><a href="selected-financial-cells.csv" download>현재 정책 금융 셀 CSV</a><a href="selected-financial-cells.json" download>현재 정책 금융 셀 JSON</a><a href="financial-cells.csv" download>기존 전체 경로 CSV · 감사</a><a href="financial-cells.json" download>기존 전체 경로 JSON · 감사</a><a href="ledgers/episodes.csv" download>전체 episode CSV</a><a href="ledgers/episodes.json" download>episode JSON</a><a href="ledgers/fills.csv" download>전체 체결 fill CSV</a><a href="ledgers/fills.json" download>fill JSON</a><a href="ledgers/trace.jsonl.gz" download>SL·신호·펀딩 이벤트 원장</a><a href="sources-status.csv" download>원본별 진행 CSV</a><a href="sources-status.json" download>원본별 진행 JSON</a><a href="provenance.json" download>입력 SHA256·단위 근거</a><a href="study-summary.json" download>연구 진행 JSON</a><a href="native-resume-manifest.json" download>후속 원본 대조 재개 목록</a><a href="failure-classification-audit.json" download>실패·복구 분류 근거</a>{audit_link}<a href="{quote("선정목록.html")}">최초 선정 목록</a></div><p class="meta">전체 경로 감사 원장: episode {summary["ledger"]["episodes"]:,}행 · fill {summary["ledger"]["fills"]:,}행. 현재 정책 선택 여부와 별도로 기존 실행 증거를 보존합니다. 비어 있는 CSV는 데이터가 없다는 뜻입니다. 개별 완료 셀의 전체 결과 JSON.GZ는 표의 근거에서 내려받습니다. HTML과 상대 폴더를 함께 보관하세요. 결과의 곡선은 원시 저장 또는 검증된 원장 재현 recipe이며 각 셀에 구분 표시합니다. recipe 전량 복원에는 해당 SHA의 연구 데이터와 encoding.restore가 필요합니다.</p></section>
<section class="panel limits"><div><h2>읽을 때 필요한 가정</h2><p>Bybit BTCUSDT 무기한 선물 · 초기 자본 10,000 USDT · 1배 · 자본 배분 100%. taker {esc(summary["costs"].get("taker", "UNKNOWN"))}, maker {esc(summary["costs"].get("maker", "UNKNOWN"))}, 슬리피지 {esc(summary["costs"].get("slippage", "UNKNOWN"))}는 비율 단위이며 이번 연구의 고정 가정입니다.</p><p>A는 원문 신호 청산만, B는 고정 2봉 swing 손절·1.5R 절반 익절·2R 본절/추적입니다. 둘 다 새로운 같은 방향 신호에서도 잔량 청산 후 다시 진입합니다. B의 반익절 fill은 독립 승리 episode가 아닙니다.</p><p>완료 episode가 0개면 승률은 미산출입니다. A의 R 통계는 해당 없음입니다. 승률은 예측 정확도가 아니며 native precision/recall 미산출을 100%로 표시하지 않습니다. 샤프는 평가곡선의 월간·표본 부족 시 일간 리샘플 관례이며 연율화하지 않습니다. 셀별 관례를 근거에서 확인하세요. 거래 빈도는 완료 episode / UTC 평가 일수 곱하기 30입니다. 보유 시간 노출은 전체 1분봉 중 포지션 보유 분봉의 합집합 비율입니다. 시가 청산 분봉은 제외하고 봉 내부 청산 분봉은 포함하며, 실제 틱 체결 시각이 아닌 분봉 포함 가정입니다.</p></div><div><h2>자료 범위와 미확인</h2><p>{esc(source_failure_note)}</p><p>제공된 지표 12,000개·전략 3,360개 안에서 현재 로켓/댓글 상위를 선정한 회고 분석입니다. TradingView 전체 상위나 과거 당시 선정 가능성을 뜻하지 않습니다. 전략 목록의 표시 총수 5,760개 중 일부만 수집됐으며 인기 선정 편향이 있습니다.</p><p>펀딩 상태: {esc(summary["dataset"]["funding_status"])}. 과거 정산 일정의 독립 검증: {"확인" if summary["dataset"]["historical_schedule_independently_verified"] else "UNKNOWN"}. 관측 정산 데이터와 완전성 보증을 구분합니다. 실제 틱 순서를 재현하지 않으며 1분 OHLC의 불리한 경로 가정을 사용합니다.</p><details><summary>기간별 데이터 수집 범위</summary><ul>{data_ranges or "<li>동결 데이터 미확보</li>"}</ul></details><p>보존한 Python 생성 기록의 요청 모델은 gpt-6.1-sol/high입니다. 실제 응답 모델 보고: {esc(summary["progress"]["reported_models"] or "UNKNOWN · 생성 기록 없음")}. 코드 생성 성공과 원문 의미 일치는 별도 판정입니다.</p></div></section><footer>인터넷 없이 필터·정렬·페이지 이동·상대 파일 다운로드가 동작합니다. TradingView 원문 링크를 열 때만 인터넷이 필요합니다. 외부 폰트·CDN·추적 요청을 사용하지 않습니다.</footer></main><script id="report-data" type="application/json">{json_script(summary)}</script><script>{CORE_JS}\n{UI_JS}</script></body></html>'''


def generate(run: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    summary = prepare(run.resolve(), output.resolve())
    target = output / "report.html"
    target.write_text(render(summary), encoding="utf-8")
    return {
        "report": str(target),
        "report_kind": summary["report_kind"],
        "cells": len(summary["cells"]),
        "progress": summary["progress"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(generate(args.run_root, args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
