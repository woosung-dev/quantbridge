"""평가가 끝난 단일 후보의 코드·증거를 검토용으로 내보낸다. 서버에 쓰지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.research.cli import acceptance, exclusive, load_dataset, source_for  # noqa: E402
from tools.research.data import digest, json_write  # noqa: E402


def export_candidate(root: Path, destination: Path) -> dict:
    root, destination = root.resolve(), destination.resolve()
    if not root.is_relative_to(ROOT / "runs") or not destination.is_relative_to(ROOT / "runs"):
        raise ValueError("입력·출력은 저장소 runs/ 안에 있어야 합니다")
    if destination.exists() or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("기존 연구와 분리된 새 출력 디렉터리를 지정하세요")

    with exclusive(root):
        load_dataset(root)
        evidence_names = [
            "dataset.json",
            "batch.json",
            "champion.json",
            "holdout-opened.json",
            "holdout.json",
        ]
        evidence = {name: json.loads((root / name).read_text()) for name in evidence_names}
        batch, champion, opening, holdout = (evidence[name] for name in evidence_names[1:])
        candidate = champion["candidate"]
        source = champion["source"]
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        if (
            batch.get("status") != "completed"
            or batch.get("completed") != 1200
            or holdout.get("status") != "completed"
            or opening["champion_sha256"] != digest(root / "champion.json")
            or champion["dataset_sha256"] != digest(root / "dataset.json")
            or champion["engine"] != batch["engine"]
            or source != source_for(candidate)
        ):
            raise ValueError("동결 후보·데이터·평가 증거가 일치하지 않습니다")

        records = holdout["records"]
        if len(records) != 4 or {
            (row["cell"]["months"], row["cost_multiplier"]) for row in records
        } != {(3, 1), (3, 2), (6, 1), (6, 2)}:
            raise ValueError("최종 3·6개월의 비용 1·2배 평가가 모두 필요합니다")
        result_files = []
        for row in records:
            path = (root / row["result_path"]).resolve()
            if (
                not path.is_relative_to(root)
                or row["status"] != "completed"
                or row["stage"] != "holdout"
                or row["candidate_id"] != candidate["id"]
                or row["source_sha256"] != source_hash
                or row["dataset_sha256"] != champion["dataset_sha256"]
                or row["engine"] != champion["engine"]
                or row["cell"]["symbol"] != champion["symbol"]
                or row["cell"]["timeframe"] != champion["timeframe"]
                or digest(path) != row["result_sha256"]
            ):
                raise ValueError("최종 평가 결과가 유실·변조되었거나 다른 후보입니다")
            result = json.loads(path.read_text())
            for key in (
                "job_hash",
                "candidate_id",
                "source_sha256",
                "dataset_sha256",
                "engine",
                "cell",
                "cost_multiplier",
                "acceptance",
            ):
                if result[key] != row[key]:
                    raise ValueError("평가 요약과 원본 결과가 일치하지 않습니다")
            if (
                any(result["metrics"].get(key) != value for key, value in row["metrics"].items())
                or acceptance(
                    result["metrics"],
                    sum(trade["status"] == "closed" for trade in result["trades"]),
                )
                != row["acceptance"]
            ):
                raise ValueError("원본 손익·거래 수와 평가 판정이 일치하지 않습니다")
            result_files.append(path)
        if holdout["thresholds_passed"] != all(
            row["acceptance"]["passed"] for row in records if row["cost_multiplier"] == 1
        ):
            raise ValueError("최종 평가 통과 요약이 원본과 다릅니다")

        # 검사가 끝나기 전에는 출력 디렉터리도 만들지 않는다.
        destination.mkdir(parents=True)
        (destination / "strategy.py").write_text(source)
        json_write(
            destination / "save-request.json",
            {
                "name": candidate["name"],
                "source": source,
                "params": candidate["params"],
                "warmup_bars": candidate["warmup_bars"],
            },
        )
        evidence_dir = destination / "evidence"
        evidence_dir.mkdir()
        for name in [*evidence_names, "champion-selection-policy.json", "champion-selection.json"]:
            if (root / name).is_file():
                shutil.copyfile(root / name, evidence_dir / name)
        for path in result_files:
            shutil.copyfile(path, evidence_dir / path.name)

        lines = [
            "# Python 연구 후보 검토 묶음",
            "",
            f"후보: {candidate['name']} (`{candidate['id']}`)",
            f"시장: {champion['symbol']} · {champion['timeframe']}",
            "",
            "| 기간 | 비용 배수 | 순수익률 | PF | MDD | 완료 거래 | 수치선 통과 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in records:
            metrics, gate = row["metrics"], row["acceptance"]
            lines.append(
                f"| {row['cell']['months']}개월 | {row['cost_multiplier']} | "
                f"{metrics['total_return']} | {metrics.get('profit_factor')} | "
                f"{metrics['max_drawdown']} | {gate['closed_trades']} | {gate['passed']} |"
            )
        lines.extend(
            [
                "",
                "수익률·MDD는 소수 비율이다. 비용 2배는 참고용이다.",
                "",
                "이 묶음은 검토 자료이며 서버 등록·배포·주문을 실행하지 않는다. 수치선 통과와 별개로",
                "과거 별도 기간은 `retrospective_not_untouched`, 펀딩은 `observed_settlements_only`다.",
                "과거 정산 일정은 독립 입증되지 않았다. 영상 원본 재현이 아닌 프로젝트 연구 가설이다.",
                "`save-request.json`은 Python 연구 API의 저장 요청 형식이며 검증 완료 배지를 부여하지 않는다.",
                "원본 시세 CSV·비밀 설정·영상 파일은 포함하지 않는다. 시세 hash는 evidence/dataset.json에 있다.",
            ]
        )
        (destination / "README.md").write_text("\n".join(lines) + "\n")
        manifest = {
            "candidate_id": candidate["id"],
            "source_sha256": source_hash,
            "review_only": True,
            "automatic_promotion": False,
            "thresholds_passed": holdout["thresholds_passed"],
            "promotion_blockers": holdout["promotion_blockers"],
            "files": {
                str(path.relative_to(destination)): digest(path)
                for path in sorted(destination.rglob("*"))
                if path.is_file()
            },
        }
        json_write(destination / "manifest.json", manifest)
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = export_candidate(args.run_dir, args.output)
    print(
        json.dumps(
            {
                "candidate_id": manifest["candidate_id"],
                "files": len(manifest["files"]),
                "review_only": True,
            }
        )
    )


if __name__ == "__main__":
    main()
