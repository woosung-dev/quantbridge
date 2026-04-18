"""E3 — 현재 QB 파서 baseline 측정.

corpus/ 내 6개 .pine을 QB의 Pine AST 인터프리터 단계별로 돌려 어느 단계에서 깨지는지 기록한다.

실행: backend uv 환경에서 직접 호출 (QB `src` 패키지 import 필요)
  cd backend && uv run python ../.gstack/experiments/phase-minus-1-drfx/scripts/parse_qb.py
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / ".gstack/experiments/phase-minus-1-drfx/corpus"
OUT = REPO / ".gstack/experiments/phase-minus-1-drfx/output/e3_qb_parser_baseline"

# backend src 패키지 로드 (cwd가 backend여야 함)
import sys  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))

from src.strategy.pine.errors import PineError  # noqa: E402
from src.strategy.pine.lexer import tokenize  # noqa: E402
from src.strategy.pine.parser import parse as pine_parse  # noqa: E402
from src.strategy.pine.stdlib import validate_functions  # noqa: E402
from src.strategy.pine.v4_to_v5 import detect_version, normalize  # noqa: E402

# __init__ 에 있는 허용 structural set 복제 (순환 import 회피)
ALLOWED_STRUCTURAL = {
    "strategy", "strategy.entry", "strategy.close", "strategy.exit",
    "indicator", "input", "input.int", "input.float", "input.bool", "input.string",
    "plot", "plotshape", "bgcolor", "barcolor", "fill",
    "alert", "alertcondition", "timestamp",
    "color.new", "color.red", "color.green", "color.blue", "color.white", "color.black",
}


def run_one(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    rec: dict = {"file": path.name, "size": len(source), "stages": {}}

    # 1. detect_version
    try:
        ver = detect_version(source)
        rec["stages"]["version"] = {"ok": True, "value": ver}
    except Exception as e:
        rec["stages"]["version"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec

    # 2. normalize (v4 → v5)
    try:
        normalized = normalize(source)
        rec["stages"]["normalize"] = {"ok": True}
    except PineError as e:
        rec["stages"]["normalize"] = {"ok": False, "kind": "unsupported", "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec
    except Exception as e:
        rec["stages"]["normalize"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec

    # 3. lex
    try:
        tokens = tokenize(normalized)
        rec["stages"]["lex"] = {"ok": True, "token_count": len(tokens)}
    except PineError as e:
        rec["stages"]["lex"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec
    except Exception as e:
        rec["stages"]["lex"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec

    # 4. parse
    try:
        program = pine_parse(tokens)
        rec["stages"]["parse"] = {"ok": True, "statement_count": len(program.statements) if hasattr(program, "statements") else -1}
    except PineError as e:
        rec["stages"]["parse"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}"}
        return rec
    except Exception as e:
        rec["stages"]["parse"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:200]}", "trace": traceback.format_exc().splitlines()[-3:]}
        return rec

    # 5. stdlib validate
    try:
        report = validate_functions(program, allowed_structural=ALLOWED_STRUCTURAL)
        rec["stages"]["stdlib"] = {"ok": True, "report_keys": list(report.keys())[:10] if isinstance(report, dict) else None}
    except PineError as e:
        rec["stages"]["stdlib"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:300]}"}
        return rec
    except Exception as e:
        rec["stages"]["stdlib"] = {"ok": False, "err": f"{type(e).__name__}: {str(e)[:300]}"}
        return rec

    rec["all_stages_passed"] = True
    return rec


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = [run_one(f) for f in sorted(CORPUS.glob("*.pine"))]

    (OUT.with_suffix(".json")).write_text(json.dumps(results, indent=2, ensure_ascii=False))

    lines = ["# E3 — 현재 QB 파서 baseline 커버리지", "", "| 파일 | 크기 | version | normalize | lex | parse | stdlib | 실패 단계 |", "|------|:---:|:--:|:--:|:--:|:--:|:--:|------|"]
    for r in results:
        st = r["stages"]
        def mark(name: str) -> str:
            if name not in st:
                return "—"
            return "✅" if st[name].get("ok") else "❌"
        failed = next((k for k, v in st.items() if not v.get("ok")), "— (all pass)")
        err = st.get(failed, {}).get("err", "") if failed != "— (all pass)" else ""
        lines.append(f"| {r['file']} | {r['size']}B | {mark('version')} | {mark('normalize')} | {mark('lex')} | {mark('parse')} | {mark('stdlib')} | `{failed}` {err[:80]} |")

    lines.append("")
    lines.append("## 단계별 실패 상세")
    for r in results:
        for stage_name, stage in r["stages"].items():
            if not stage.get("ok"):
                lines.append(f"\n### {r['file']} @ `{stage_name}`\n```\n{stage.get('err', '')}\n```")
                break

    OUT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT.with_suffix('.md')}")
    for r in results:
        st = r["stages"]
        passed = [k for k, v in st.items() if v.get("ok")]
        failed = [k for k, v in st.items() if not v.get("ok")]
        status = "✅" if not failed else "❌ " + failed[0]
        print(f"  {r['file']:30} passed={len(passed)}/{len(st)} {status}")


if __name__ == "__main__":
    main()
