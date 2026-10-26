"""경계 동점·두 순위 합집합·게시물 식별자의 독립 검증."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.select_tradingview import select


def dataset(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    for kind, pages, prefix in (("indicators", 500, "I"), ("strategies", 140, "S")):
        for page in range(1, pages + 1):
            items = []
            if page <= 3:
                pid = prefix + str(page).zfill(7)
                items = [{
                    "id": page, "name": pid, "user": {"username": "author"},
                    "description": "원본 소개", "likes_count": [100, 50, 50][page - 1],
                    "comments_count": [0, 1, 20][page - 1],
                    "chart_url": f"https://www.tradingview.com/script/{pid}-slug/",
                    "script_id_part": f"PUB;{pid}", "version": "1",
                }]
            (raw / f"{kind}_{page:03}.json").write_text(json.dumps({
                "category": kind, "page": page, "url": f"https://www.tradingview.com/{kind}/{page}",
                "collected_at": "2026-10-26T02:00:00Z", "total_reported": 3, "items": items,
            }))
    return tmp_path


def test_union_preserves_both_ranks_and_ties_follow_page_order(tmp_path):
    result = select(dataset(tmp_path), limit=2)
    rows = {item["id"]: item for item in result["items"]}
    assert len(rows) == 6
    assert rows["I0000002"]["boost_rank"] == 2
    assert rows["I0000003"]["boost_rank"] == 3
    assert rows["I0000002"]["selected_by"] == ["boosts", "comments"]
    assert rows["I0000001"]["selected_by"] == ["boosts"]
    assert rows["I0000003"]["selected_by"] == ["comments"]
    assert result["summary"]["indicators"]["intersection"] == 1


def test_slug_or_numeric_listing_id_does_not_create_another_publication(tmp_path):
    folder = dataset(tmp_path)
    path = folder / "raw/indicators_002.json"
    value = json.loads(path.read_text())
    value["items"][0]["chart_url"] = "https://www.tradingview.com/script/I0000001-new-title/"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="publication ID 누락·중복"):
        select(folder, limit=2)


def test_page_mismatch_is_not_silently_used(tmp_path):
    folder = dataset(tmp_path)
    path = folder / "raw/indicators_002.json"
    value = json.loads(path.read_text())
    value["page"] = 1
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="페이지 출처 불일치"):
        select(folder, limit=2)
