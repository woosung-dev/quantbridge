"""제공된 TradingView 목록에서 네 상위 집합의 고정 합집합을 만든다."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from pathlib import Path


def select(folder: Path, limit: int = 500) -> dict:
    items, files, summary = [], [], {}
    for kind, pages in (("indicators", 500), ("strategies", 140)):
        records, seen = [], set()
        for page in range(1, pages + 1):
            path = folder / "raw" / f"{kind}_{page:03}.json"
            raw = path.read_bytes()
            payload = json.loads(raw)
            if payload["category"] != kind or payload["page"] != page:
                raise ValueError(f"페이지 출처 불일치: {path.name}")
            files.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
            for position, record in enumerate(payload["items"]):
                publication = re.search(r"/script/([A-Za-z0-9]{8})(?:[-/]|$)", record["chart_url"])
                if publication is None or publication[1] in seen:
                    raise ValueError(f"publication ID 누락·중복: {record['chart_url']}")
                seen.add(publication[1])
                records.append({
                    "id": publication[1], "publication_id": publication[1],
                    "listing_id": record["id"], "kind": kind, "type": kind,
                    "title": record["name"], "author": record["user"]["username"],
                    "summary": " ".join(record["description"].split()),
                    "boosts": record["likes_count"], "comments": record["comments_count"],
                    "url": record["chart_url"], "script_id_part": record["script_id_part"],
                    "listing_version": record["version"], "page": page,
                    "card_position": position + 1, "listing_url": payload["url"],
                    "collected_at": payload["collected_at"], "order": len(records),
                    "source_file": f"sources/{publication[1]}.pine", "source_sha256": None,
                    "review_file": f"reviews/{publication[1]}.json",
                })
        for field, rank_name in (("boosts", "boost_rank"), ("comments", "comment_rank")):
            for rank, row in enumerate(sorted(records, key=lambda r: (-r[field], r["order"])), 1):
                row[rank_name] = rank
        chosen = []
        for record in records:
            record["selected_by"] = [name for name, rank in (("boosts", "boost_rank"), ("comments", "comment_rank")) if record[rank] <= limit]
            if record["selected_by"]:
                chosen.append(record)
        if len({r["id"] for r in chosen}) != len(chosen):
            raise ValueError("선정 집합에 중복 ID")
        summary[kind] = {"collected": len(records), "reported_total": payload["total_reported"], "boost_top": limit, "comment_top": limit, "intersection": sum(len(r["selected_by"]) == 2 for r in chosen), "unique": len(chosen)}
        items.extend(chosen)
    if len({r["id"] for r in items}) != len(items):
        raise ValueError("유형 간 publication 중복")
    return {"schema_version": 1, "selection": "metric_desc_then_page_card_asc", "limit_per_metric": limit, "scope": "provided_download_only", "summary": summary, "input_files": files, "items": items}


def write(folder: Path, output: Path, run: Path) -> dict:
    catalogue = select(folder)
    if catalogue["summary"]["indicators"]["unique"] != 708 or catalogue["summary"]["strategies"]["unique"] != 692:
        raise ValueError("실측한 708/692 코호트와 달라졌습니다. 원본 자료를 확인하세요")
    serialized = json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n"
    for root in (output, run):
        root.mkdir(parents=True, exist_ok=True)
        path = root / "catalogue.json"
        if path.exists() and path.read_text() != serialized:
            raise ValueError(f"기존 다른 코호트를 덮어쓸 수 없습니다: {path}")
        path.write_text(serialized)
    fields = ["kind", "publication_id", "title", "author", "boosts", "comments", "boost_rank", "comment_rank", "selected_by", "url", "page", "card_position", "collected_at"]
    with (output / "선정목록.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in catalogue["items"]:
            writer.writerow({**row, "selected_by": "+".join(row["selected_by"])})
    lines = ["# TradingView 지표·전략 선정 목록", "", "지표 708개 + 전략 692개 = 고유 원본 1,400개.", "", "각 유형에서 로켓/댓글 상위 500개를 선택하고 publication ID로 중복을 제거했다. 동점은 원본 페이지·카드 순서다.", "", "제공된 자료 안의 순위이며 TradingView 전체 순위가 아니다. 전략은 표시 전체 5,760개 중 수집된 3,360개가 대상이다. 숫자는 2026-10-26 수집 시점에 고정했다.", "", "| 유형 | 제목·원문 | 작성자 | 로켓 | 댓글 | 로켓 순위 | 댓글 순위 | 선정 근거 |", "|---|---|---|---:|---:|---:|---:|---|"]
    for row in catalogue["items"]:
        title = row["title"].replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
        lines.append(f"| {'지표' if row['kind'] == 'indicators' else '전략'} | [{title}]({row['url']}) | {row['author']} | {row['boosts']} | {row['comments']} | {row['boost_rank']} | {row['comment_rank']} | {' / '.join(row['selected_by'])} |")
    (output / "선정목록.md").write_text("\n".join(lines) + "\n")
    tree = ast.parse((folder / "build_html.py").read_text())
    template = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "template" for target in node.targets))
    records = [{**r, "summary": f"로켓 순위 {r['boost_rank']} · 댓글 순위 {r['comment_rank']} · 선정: {' + '.join(r['selected_by'])}. {r['summary']}"} for r in catalogue["items"]]
    payload = json.dumps(records, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = template.replace("__DATA__", payload).replace("TradingView 지표·전략 탐색", "TradingView 상위 목록 · 중복 제거 1,400개").replace("지표 12,000개 · 전략 3,360개", "선정 지표 708개 · 선정 전략 692개")
    template = template.replace('<form id="filters"', '<p>각 유형 로켓·댓글 상위 500개 합집합. 제공된 자료 안의 순위이며 사이트 전체 순위가 아닙니다. <a href="선정목록.csv">CSV</a> · <a href="catalogue.json">JSON</a> · <a href="선정목록.md">전체 문서</a></p><form id="filters"')
    template = template.replace('class="table-wrap"', 'class="table-wrap" tabindex="0" role="region" aria-label="선정 목록 스크롤 표"')
    (output / "선정목록.html").write_text(template)
    receipt = {"catalogue_sha256": hashlib.sha256(serialized.encode()).hexdigest(), "total": len(records), "summary": catalogue["summary"]}
    (run / "selection-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write(args.input, args.output, args.run_dir), ensure_ascii=False))
