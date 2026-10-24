"""실제 에디터 픽 UI 캡처와 검토한 신호 바인딩을 연결한다."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from tools.research.editor_picks.common import (
    ROOT,
    checked_file,
    immutable,
    now,
    read,
    sha,
    write,
)


def ingest(root: Path) -> dict:
    items = {}
    for path in sorted((root / "captures").glob("*.json")):
        payload = read(path)
        if payload.get("schema_version") != 1:
            raise ValueError("UI 수집 스키마가 다릅니다")
        listings = {row["url"]: row for row in payload["listings"]}
        for row in payload["captures"]:
            listing = listings[row["listing_url"]]
            parsed = urlsplit(listing["url"])
            if (
                parsed.scheme != "https"
                or parsed.hostname != "www.tradingview.com"
                or not re.fullmatch(
                    r"/scripts/editors-picks/(?:page-\d+/)?", parsed.path
                )
                or not any(item["url"] == row["url"] for item in listing["items"])
            ):
                raise ValueError("에디터 픽 목록 관측 근거가 없습니다")
            publication = re.fullmatch(
                r"https://www.tradingview.com/script/([A-Za-z0-9]{8})[^?#]*/",
                row["url"],
            )
            if publication is None or publication[1] != row["id"]:
                raise ValueError("게시물 ID와 URL이 다릅니다")
            item = {key: value for key, value in row.items() if key != "source"}
            item["capture"] = {
                "path": str(path.relative_to(root)),
                "sha256": sha(path.read_bytes()),
            }
            if row["status"] == "captured":
                response = urlsplit(row["source_response_url"])
                if (
                    response.hostname != "pine-facade.tradingview.com"
                    or not response.path.startswith("/pine-facade/get/")
                    or row.get("script_access") not in {"open_no_auth", "open"}
                ):
                    raise ValueError("UI가 받은 공개 원문 응답이 아닙니다")
                source = row["source"].encode()
                source_hash = sha(source)
                target = root / "sources" / f"{row['id']}-{source_hash[:12]}.pine"
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != source:
                    raise ValueError("원문 파일이 변경됐습니다")
                target.write_bytes(source)
                item.update(
                    source_file=str(target.relative_to(root)),
                    source_sha256=source_hash,
                    license_notices=[
                        line
                        for line in row["source"].splitlines()
                        if re.search(
                            r"license|copyright|©|all rights reserved", line, re.I
                        )
                    ],
                )
            previous = items.get(row["id"])
            if previous and previous.get("source_sha256") and item.get("source_sha256"):
                if previous["source_sha256"] != item["source_sha256"]:
                    raise ValueError(
                        "같은 게시물의 원문 버전 변경: 새 실험이 필요합니다"
                    )
            if not previous or not previous.get("source_sha256"):
                items[row["id"]] = item
    seen = {}
    for item in items.values():
        digest = item.get("source_sha256")
        if digest in seen:
            item["duplicate_of"] = seen[digest]
        elif digest:
            seen[digest] = item["id"]

    def order(item):
        match = re.search(r"/page-(\d+)/", item["listing_url"])
        return int(match[1]) if match else 1, item["listing_position"]

    catalogue = {
        "schema_version": 1,
        "observed_at": now(),
        "items": sorted(items.values(), key=order),
    }
    write(root / "catalogue.json", catalogue)
    return catalogue


def screen_one(root: Path, identifier: str) -> dict:
    from scripts.pine_validation.strategy_adapter import adapt_strategy
    from src.strategy.pine_v2.coverage import analyze_coverage

    item = next(
        x for x in read(root / "catalogue.json")["items"] if x["id"] == identifier
    )
    if item.get("duplicate_of") or item["status"] != "captured":
        return {
            "id": identifier,
            "status": "excluded",
            "reason": item.get("duplicate_of", item["status"]),
        }
    source = (
        checked_file(root, item["source_file"], item["source_sha256"])
        .read_bytes()
        .decode()
    )
    coverage = analyze_coverage(source)
    base = {"id": identifier, "source_sha256": item["source_sha256"]}
    if not coverage.is_runnable or coverage.has_degraded:
        return {**base, "status": "unsupported", "detail": str(coverage)}
    review_path = root / "reviews" / f"{identifier}.json"
    if not review_path.exists():
        return {**base, "status": "needs_binding_review"}
    review = read(review_path)
    if (
        review.get("decision") == "exclude"
        and review.get("source_sha256") == item["source_sha256"]
    ):
        return {**base, "status": "excluded", "reason": review["basis"]}
    if (
        review.get("source_sha256") != item["source_sha256"]
        or not review.get("reviewed_by")
        or not review.get("basis")
        or not review.get("family")
        or {b["direction"] for b in review["signal_bindings"]} != {"long", "short"}
        or not 200 <= review.get("warmup_bars", 0) <= 10000
    ):
        raise ValueError("원문 해시·양방향 신호·준비봉·검토 근거가 필요합니다")
    adapted = adapt_strategy(source, review["signal_bindings"], fixed_quantity=None)
    code = adapted.strategy_source
    if not analyze_coverage(code).is_runnable:
        return {**base, "status": "adaptation_unsupported"}
    path = root / "adapted" / f"{identifier}.pine"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(code.encode())
    return {
        **item,
        **review,
        "status": "static_eligible",
        "adapted_file": str(path.relative_to(root)),
        "adapted_sha256": sha(code.encode()),
        "adaptation": adapted.to_dict(),
        "execution_verified": False,
    }


def screen(root: Path, timeout: int = 15) -> list[dict]:
    rows = []
    from tools.research.editor_picks.common import identity

    paths = sorted((ROOT / "apps/api/src/strategy/pine_v2").rglob("*.py"))
    paths += [
        Path(__file__),
        ROOT / "apps/api/scripts/pine_validation/strategy_adapter.py",
    ]
    implementation_hash = identity(
        {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}
    )
    for item in read(root / "catalogue.json")["items"]:
        destination = root / "screening" / f"{item['id']}.json"
        review = root / "reviews" / f"{item['id']}.json"
        effective_timeout = timeout * 3 if review.exists() else timeout
        request_hash = identity(
            {
                "source": item.get("source_sha256"),
                "review": sha(review.read_bytes()) if review.exists() else None,
                "implementation": implementation_hash,
                "timeout": timeout,
            }
        )
        if (
            destination.exists()
            and read(destination).get("screen_request_sha256") == request_hash
        ):
            rows.append(read(destination))
            continue
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.research.editor_picks",
                    "--run-dir",
                    str(root),
                    "screen-one",
                    "--id",
                    item["id"],
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            if completed.returncode:
                row = {
                    "id": item["id"],
                    "status": "screen_failed",
                    "error": completed.stderr[-1500:],
                }
            else:
                row = read(destination)
        except subprocess.TimeoutExpired:
            row = {"id": item["id"], "status": "parser_timeout"}
        row["screen_request_sha256"] = request_hash
        rows.append(row)
        write(destination, row)
    write(root / "screening.json", rows)
    return rows


def seal(root: Path, count: int = 200, pilot: bool = False) -> dict:
    selected = [
        row
        for row in read(root / "screening.json")
        if row["status"] == "static_eligible"
    ][:count]
    if len(selected) != count or len(
        {item["source_sha256"] for item in selected}
    ) != len(selected):
        raise ValueError("중복 없는 검토 원문이 필요합니다")
    cohort = {
        "schema_version": 1,
        "target": count,
        "items": selected,
        "source_count": len(selected),
        "execution_verified": False,
        "selection_policy": "editor_pick_order_then_pine_eligibility_not_returns",
        "complete": False,
    }
    immutable(root / ("pilot-cohort.json" if pilot else "cohort.json"), cohort)
    return cohort
