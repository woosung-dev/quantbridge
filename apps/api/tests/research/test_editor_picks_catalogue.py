"""동시 정적 검사의 상한·캐시 무결성·수집 중 추가 원문을 검증한다."""

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import catalogue  # noqa: E402
from tools.research.editor_picks.common import read, sha, write  # noqa: E402


def prepare(root, count=8):
    items = []
    for index in range(count):
        source = f"source-{index}".encode()
        source_file = f"sources/{index}.pine"
        (root / "sources").mkdir(exist_ok=True)
        (root / source_file).write_bytes(source)
        items.append(
            {
                "id": str(index),
                "source_file": source_file,
                "source_sha256": sha(source),
                "status": "captured",
            }
        )
    write(root / "catalogue.json", {"items": items})
    return items


def test_screen_bounds_parallelism_reuses_cache_and_rejects_source_tampering(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.setattr(catalogue, "_screen_implementation_hash", lambda: "semantic")
    active = peak = calls = 0
    mutex = threading.Lock()

    def run(args, **kwargs):
        nonlocal active, peak, calls
        with mutex:
            active += 1
            calls += 1
            peak = max(peak, active)
        time.sleep(0.02)
        write(
            tmp_path / "screening" / f"{args[-1]}.json",
            {"id": args[-1], "status": "needs_binding_review"},
        )
        with mutex:
            active -= 1
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(catalogue.subprocess, "run", run)
    assert len(catalogue.screen(tmp_path, workers=2)) == 8
    assert peak == 2
    assert len(catalogue.screen(tmp_path, workers=4)) == 8
    assert calls == 8
    (tmp_path / "sources/0.pine").write_text("tampered")
    with pytest.raises(ValueError, match="SHA256"):
        catalogue.screen(tmp_path)


def test_screen_preserves_new_capture_as_pending_and_does_not_stamp_changed_review(
    tmp_path, monkeypatch
):
    items = prepare(tmp_path, 1)
    monkeypatch.setattr(catalogue, "_screen_implementation_hash", lambda: "semantic")

    def run(args, **kwargs):
        write(tmp_path / "reviews/0.json", {"basis": "changed during scan"})
        write(tmp_path / "catalogue.json", {"items": [*items, {"id": "new"}]})
        write(tmp_path / "screening/0.json", {"id": "0", "status": "static_eligible"})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(catalogue.subprocess, "run", run)
    rows = catalogue.screen(tmp_path)
    assert rows == [
        {"id": "0", "status": "screen_pending"},
        {"id": "new", "status": "screen_pending"},
    ]
    assert "screen_request_sha256" not in read(tmp_path / "screening/0.json")


def test_screen_rejects_duplicate_ids_and_competing_scan(tmp_path, monkeypatch):
    items = prepare(tmp_path, 1)
    monkeypatch.setattr(catalogue, "_screen_implementation_hash", lambda: "semantic")
    write(tmp_path / "catalogue.json", {"items": items * 2})
    with pytest.raises(ValueError, match="같은 게시물"):
        catalogue.screen(tmp_path)
    with catalogue.lock(tmp_path / "screening.lock"), pytest.raises(BlockingIOError):
        catalogue.screen(tmp_path)


def test_cache_semantics_ignore_scheduler_but_include_binding(monkeypatch):
    original = catalogue._screen_implementation_hash()
    monkeypatch.setattr(catalogue, "screen", lambda *args: [])
    assert catalogue._screen_implementation_hash() == original
    monkeypatch.setattr(catalogue, "screen_one", prepare)
    assert catalogue._screen_implementation_hash() != original


def test_screen_records_timeout_and_gives_reviewed_sources_more_time(tmp_path, monkeypatch):
    prepare(tmp_path, 1)
    write(tmp_path / "reviews/0.json", {"basis": "reviewed"})
    monkeypatch.setattr(catalogue, "_screen_implementation_hash", lambda: "semantic")

    def run(args, **kwargs):
        assert kwargs["timeout"] == 21
        raise catalogue.subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(catalogue.subprocess, "run", run)
    assert catalogue.screen(tmp_path, timeout=7)[0]["status"] == "parser_timeout"
