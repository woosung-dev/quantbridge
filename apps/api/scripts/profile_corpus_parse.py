"""[BL-598] 코퍼스 첫-접촉 파싱 비용의 정체를 재는 프로파일러.

배경: `tests/strategy/pine_v2/test_ast_classifier.py::test_classify_script_matches_baseline`
가 단독 실행 시 `i3_drfx` 하나에 40초대를 쓰는데 전체 스위트 안에서는 4초대다. 이 비용이
프로세스 전역이라 CI 를 샤딩하면 샤드마다 중복된다.

판별할 두 가설:
- (a) **import 시점 워밍업** — `pynescript`/`src.strategy.pine_v2` import 자체가 비싸다.
      참이면 처방은 테스트 픽스처 캐시이고 `apps/api/src` 수정이 불필요하다.
- (b) **파서의 입력 크기 비선형** — 파싱 시간이 입력 크기에 초선형으로 자란다.
      참이면 처방은 파서 구간 수정이다.

측정 축:
1. import 비용 — 서브프로세스에서 `classify_script` import 만. ANTLR DFA 상태 수도 함께 센다.
2. 코퍼스 cold 1회차 — 한 프로세스에서 9벌을 순서대로 최초 파싱.
3. 코퍼스 warm 2회차 — 같은 프로세스에서 재파싱. `cold - warm` = 첫-접촉 프리미엄.
4. cold 램프(`--ramp`) — `i3_drfx` 를 1/8~8/8 로 자르고 **조각마다 새 프로세스**로 최초 파싱.
   시간이 「글자 수」와 「DFA 상태 수」 중 어느 축을 따라가는지 log-log 기울기로 가른다.
   ★한 프로세스에서 이어 돌리면 뒤 조각이 앞 조각의 DFA 를 물려받아 cold 가 아니게 된다.
5. warm 램프(`--ramp`) — 같은 조각들을 DFA 포화 상태에서 재파싱.
6. solo(`--solo`) — 서브프로세스 1개당 파일 1개만 파싱. 워밍업의 파일 간 전이량(=샤딩 중복분).
7. cProfile(`--cprofile`) — cold 파싱의 누적시간 상위 함수.
8. **인과 대조(기본 포함)** — 같은 프로세스·같은 입력에서 ANTLR 캐시**만** 비운다. cold 비용이
   되돌아오면 원인이 캐시 상태임이 상관이 아니라 인과로 확정된다. 이어서 성분(`parser_dfa` /
   `shared_ctx` / `lexer_dfa`)을 **하나씩** 비워 어느 것이 비용을 지는지까지 좁힌다.
   ★단 이 성분 루프는 회차마다 다시 데우므로 **independent 하지 않다** — [9] 를 봐라.
9. 성분 independent control(`--components`) — 성분마다 **새 프로세스**에서 배경 워밍 이력을
   똑같이 맞춘 뒤 그 성분만 비운다. [8] 성분 루프의 순서 의존을 없앤 판이다.

★[5] 의 log-log 기울기는 **보조 증거일 뿐이다**. 잘린 조각마다 문법 구성이 달라 값이 울퉁불퉁
하고(꼬리 구간은 오히려 sublinear), 기울기가 1 을 넘더라도 warm 합계 자체가 단독 실행 비용을
설명하지 못하면 (b) 는 기각된다. 판정의 주 근거는 [1]·[3]·[8] 이다.

사용:
    cd apps/api && uv run python scripts/profile_corpus_parse.py            # 기본 1·2·3·8 (~3분)
    cd apps/api && uv run python scripts/profile_corpus_parse.py --ramp     # + 크기 램프
    cd apps/api && uv run python scripts/profile_corpus_parse.py --solo     # + 파일별 격리 프로세스
    cd apps/api && uv run python scripts/profile_corpus_parse.py --all      # 전부 ([7] 포함, ~16분)
    cd apps/api && uv run python scripts/profile_corpus_parse.py --cprofile # [7] 만 (cold 상위 함수)
    cd apps/api && uv run python scripts/profile_corpus_parse.py --components # [9] 만 (~4분)

DB·환경변수 불필요 — `classify_script` 는 순수 함수다.
★절대시간은 머신 부하에 민감하다(같은 cold 파싱이 41~68s 로 흔들린 실측이 있다). 결론은
배수·순위·[8] 의 되돌아옴으로 읽어라, 절대초로 읽지 마라.

★**zero-touch 계약과의 관계.** 이 스크립트는 `apps/api/src` 를 **읽기 전용으로 import** 한다 —
쓰기도 생성도 없고, 부수효과는 `__pycache__/` 바이트코드뿐이다. 그 디렉터리는
`.gitignore:57` · `apps/api/.gitignore:1` 에 등재돼 있고 소크 스택은 `.soak/src` **스냅샷을
mount** 하므로, 이 스크립트를 돌려도 커밋되는 `apps/api/src` 변경은 0줄이고 소크 창에도
닿지 않는다(계약이 사는 자리는 커밋 diff 이지 파일시스템이 아니다).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_CORPUS_DIR = _BACKEND_DIR / "tests" / "fixtures" / "pine_corpus_v2"
_HEADLINE = "i3_drfx"
_RAMP_FRACTIONS = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)


def _dfa_state_count() -> int:
    """ANTLR ALL(*) 어댑티브 예측이 쌓아 둔 DFA 상태 총수.

    `PinescriptParser.decisionsToDFA` 는 **클래스 속성**이라 프로세스 전역이다
    (`pynescript/ast/grammar/antlr4/generated/PinescriptParser.py:346`).
    이 값이 곧 「워밍업이 얼마나 진행됐나」다.
    """
    from pynescript.ast.grammar.antlr4.generated.PinescriptParser import (
        PinescriptParser,
    )

    return sum(len(dfa.states) for dfa in PinescriptParser.decisionsToDFA)


def _corpus_files() -> list[Path]:
    return sorted(_CORPUS_DIR.glob("*.pine"))


def _read(name: str) -> str:
    return (_CORPUS_DIR / f"{name}.pine").read_text()


def _run_child(program: str, *args: str) -> Any:
    """apps/api/ 를 cwd 로 자식 파이썬을 띄우고 마지막 줄 JSON 을 회수한다.

    `program` 은 이 파일 안의 리터럴 상수만 들어온다 (외부 입력 아님) — S603 면제 근거.
    """
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program, *args],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _fmt_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    head = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "  ".join("-" * w for w in widths)
    body = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows]
    return "\n".join([head, sep, *body])


def _loglog_slope(points: list[tuple[int, float]]) -> float:
    """(size, seconds) 점들의 log-log 최소제곱 기울기. 1.0 = 선형, >1 = 초선형."""
    usable = [(size, secs) for size, secs in points if size > 0 and secs > 0]
    if len(usable) < 2:
        return float("nan")
    xs = [math.log(size) for size, _ in usable]
    ys = [math.log(secs) for _, secs in usable]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else float("nan")


def _reset_antlr_caches(scope: str = "all") -> None:
    """ANTLR 의 프로세스 전역 워밍업 상태를 import 직후로 되돌린다.

    `decisionsToDFA` / `sharedContextCache` 는 generated 파서·렉서의 **클래스 속성**이고,
    파서 인스턴스는 생성 시점에 이 클래스 속성을 읽는다 (`PinescriptParser.__init__` →
    `ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)`).
    따라서 클래스 속성을 새 객체로 갈아끼우면 다음 파싱부터 워밍업이 처음부터 다시 일어난다.

    `scope` 로 **성분을 하나씩** 비울 수 있다. 셋을 한꺼번에 비우면 「ANTLR 캐시 상태가
    원인」까지만 말할 수 있고 어느 성분인지는 못 가른다 — 성분 분리가 있어야 결론을
    `parser_dfa` 로 좁힐 수 있다 (2026-08-08 codex 평가 지적을 받아 추가).

    - `"parser_dfa"`  — `PinescriptParser.decisionsToDFA` 만
    - `"shared_ctx"`  — `PinescriptParser.sharedContextCache` 만
    - `"lexer_dfa"`   — `PinescriptLexer.decisionsToDFA` 만
    - `"all"`         — 셋 전부

    ★드리프트 경고 — 같은 리셋 로직이 `_COMPONENT_CHILD` 안에 **verbatim 재구현**돼 있다
    (child 는 별도 프로세스의 문자열 프로그램이라 import 로 공유가 구조적으로 불가능하다).
    리셋 방식을 바꾸면 **두 곳을 함께 고쳐라.**
    """
    from antlr4.dfa.DFA import DFA
    from antlr4.PredictionContext import PredictionContextCache
    from pynescript.ast.grammar.antlr4.generated.PinescriptLexer import PinescriptLexer
    from pynescript.ast.grammar.antlr4.generated.PinescriptParser import (
        PinescriptParser,
    )

    if scope not in {"all", "parser_dfa", "shared_ctx", "lexer_dfa"}:
        raise ValueError(f"unknown reset scope: {scope}")

    if scope in {"all", "parser_dfa"}:
        PinescriptParser.decisionsToDFA = [
            DFA(state, index) for index, state in enumerate(PinescriptParser.atn.decisionToState)
        ]
    if scope in {"all", "shared_ctx"}:
        PinescriptParser.sharedContextCache = PredictionContextCache()
    if scope in {"all", "lexer_dfa"}:
        PinescriptLexer.decisionsToDFA = [
            DFA(state, index) for index, state in enumerate(PinescriptLexer.atn.decisionToState)
        ]


# --------------------------------------------------------------------------- #
# [1] import 비용
# --------------------------------------------------------------------------- #

_IMPORT_CHILD = """
import json, sys, time
sys.path.insert(0, ".")
start = time.perf_counter()
from src.strategy.pine_v2.ast_classifier import classify_script
elapsed = time.perf_counter() - start
from pynescript.ast.grammar.antlr4.generated.PinescriptParser import PinescriptParser
dfa = sum(len(d.states) for d in PinescriptParser.decisionsToDFA)
print(json.dumps({"import_s": elapsed, "dfa_after_import": dfa}))
"""


def section_import(repeats: int = 3) -> dict[str, Any]:
    print(f"\n[1] import 비용 — 서브프로세스 {repeats} 회 (bytecode 컴파일 편향 제거)")
    # 첫 회는 .pyc 컴파일이 섞이므로 버린다 (첫 실행이 17s, 이후 0.26s 로 관측됐다).
    # ★**여기서 나오는 수치는 warm 프로세스 한정이다** (2026-08-08 codex 평가 지적).
    #   버려지는 첫 회 17s 는 bytecode 컴파일 + OS 파일 캐시 워밍이고, **CI 는 cold 다** —
    #   `.pyc` 가 없는 새 러너에서 샤드마다 이 17s 계열을 다시 무는지는 **이 도구가 안 잰다**.
    #   따라서 「import 는 cold 합계의 0.4% 라 무시 가능」은 [BL-598] 이 재는 현상(같은 머신
    #   warm 프로세스에서 42.66s vs 4.58s)에 대해서만 참이고, cold CI 축으로 일반화하면
    #   안 된다. cold 축 = [BL-652] 미측정.
    _run_child(_IMPORT_CHILD)
    samples = [_run_child(_IMPORT_CHILD) for _ in range(repeats)]
    times = sorted(sample["import_s"] for sample in samples)
    dfas = sorted({sample["dfa_after_import"] for sample in samples})
    median = times[len(times) // 2]
    print(
        f"    classify_script import: "
        f"min={times[0]:.3f}s  median={median:.3f}s  max={times[-1]:.3f}s"
    )
    print(f"    import 직후 ANTLR DFA 상태 수: {dfas}  <- 0 이면 import 는 워밍업이 아니다")
    return {"import_min_s": times[0], "dfa_after_import": dfas}


# --------------------------------------------------------------------------- #
# [2][3] 코퍼스 cold / warm
# --------------------------------------------------------------------------- #


def section_corpus() -> dict[str, Any]:
    from src.strategy.pine_v2.ast_classifier import classify_script

    files = _corpus_files()
    print("\n[2] 코퍼스 cold 1회차 + [3] warm 2회차 (단일 프로세스, 알파벳 순)")

    cold: dict[str, float] = {}
    dfa_after: dict[str, int] = {}
    for path in files:
        source = path.read_text()
        start = time.perf_counter()
        classify_script(source)
        cold[path.stem] = time.perf_counter() - start
        dfa_after[path.stem] = _dfa_state_count()

    warm: dict[str, float] = {}
    for path in files:
        source = path.read_text()
        start = time.perf_counter()
        classify_script(source)
        warm[path.stem] = time.perf_counter() - start

    rows: list[list[str]] = []
    for path in files:
        name = path.stem
        size = len(path.read_text())
        rows.append(
            [
                name,
                str(size),
                f"{cold[name]:.3f}",
                f"{warm[name]:.3f}",
                f"{cold[name] - warm[name]:.3f}",
                f"{1e6 * warm[name] / size:.1f}",
                str(dfa_after[name]),
            ]
        )
    print(
        _fmt_table(
            ["script", "chars", "cold_s", "warm_s", "premium_s", "warm_us/ch", "dfa"],
            rows,
        )
    )
    total_cold = sum(cold.values())
    total_warm = sum(warm.values())
    premium = total_cold - total_warm
    share = 100.0 * premium / total_cold if total_cold else 0.0
    print(
        f"    합계 cold={total_cold:.2f}s  warm={total_warm:.2f}s  "
        f"첫-접촉 프리미엄={premium:.2f}s ({share:.1f}%)"
    )
    return {"cold": cold, "warm": warm, "dfa_after": dfa_after}


# --------------------------------------------------------------------------- #
# [4][5] 크기 램프
# --------------------------------------------------------------------------- #


def _ramp_slices(name: str) -> list[tuple[float, str]]:
    lines = _read(name).splitlines(keepends=True)
    slices: list[tuple[float, str]] = []
    for frac in _RAMP_FRACTIONS:
        count = max(1, int(len(lines) * frac))
        slices.append((frac, "".join(lines[:count])))
    return slices


# ★조각 하나당 프로세스 하나다. 한 프로세스에서 조각들을 이어서 돌리면 두 번째 행부터
#   앞 조각이 만들어 둔 DFA 를 물려받아 **cold 측정이 아니게 되고**, 그 값으로 「크기와
#   무관하다」를 주장하면 워밍업 효과를 크기 효과로 오인한다 (2026-08-08 codex 평가 지적).
_COLD_RAMP_CHILD = """
import json, sys, time
sys.path.insert(0, ".")
from pathlib import Path
from src.strategy.pine_v2.ast_classifier import classify_script
from pynescript.ast.grammar.antlr4.generated.PinescriptParser import PinescriptParser

name = sys.argv[1]
frac = float(sys.argv[2])
path = Path("tests/fixtures/pine_corpus_v2") / (name + ".pine")
lines = path.read_text().splitlines(keepends=True)
count = max(1, int(len(lines) * frac))
source = "".join(lines[:count])
start = time.perf_counter()
try:
    classify_script(source)
    ok = True
except Exception:
    ok = False
elapsed = time.perf_counter() - start
dfa = sum(len(d.states) for d in PinescriptParser.decisionsToDFA)
print(json.dumps({"frac": frac, "chars": len(source), "s": elapsed, "ok": ok, "dfa": dfa}))
"""


def section_cold_ramp(name: str = _HEADLINE) -> dict[str, Any]:
    print(f"\n[4] cold 램프 — {name} 를 1/8~8/8 로 자르고 **조각마다 새 프로세스**로 최초 파싱")
    samples = [_run_child(_COLD_RAMP_CHILD, name, repr(frac)) for frac in _RAMP_FRACTIONS]
    rows = [
        [
            f"{s['frac']:.3f}",
            str(s["chars"]),
            f"{s['s']:.3f}",
            str(s["dfa"]),
            "ok" if s["ok"] else "PARSE-FAIL",
        ]
        for s in samples
    ]
    print(_fmt_table(["frac", "chars", "cold_s", "dfa_total", "parse"], rows))
    ok = [s for s in samples if s["ok"]]
    result: dict[str, Any] = {"samples": samples}
    if len(ok) >= 2:
        by_chars = _loglog_slope([(s["chars"], s["s"]) for s in ok])
        by_dfa = _loglog_slope([(s["dfa"], s["s"]) for s in ok])
        result["slope_by_chars"] = by_chars
        result["slope_by_dfa"] = by_dfa
        print(f"    log-log 기울기: 시간~글자수 = {by_chars:.2f} · 시간~DFA상태수 = {by_dfa:.2f}")
        print(
            f"    크기 {ok[-1]['chars'] / ok[0]['chars']:.1f} 배 → "
            f"cold 시간 {ok[-1]['s'] / ok[0]['s']:.1f} 배 · "
            f"DFA 상태 {ok[-1]['dfa'] / ok[0]['dfa']:.1f} 배"
        )
        print("      ★어느 축의 기울기가 1 에 가까운가가 「무엇이 비용을 지배하는가」다.")
    return result


def section_warm_ramp(name: str = _HEADLINE) -> dict[str, Any]:
    from src.strategy.pine_v2.ast_classifier import classify_script

    print("\n[5] warm 램프 — 같은 조각들을 DFA 포화 뒤 재파싱 (선형성 보조 증거)")
    slices = _ramp_slices(name)
    for _, source in slices:
        # 먼저 전량 1회 파싱해 DFA 를 포화시킨다. 잘린 조각의 문법 오류는 여기서 무시.
        with contextlib.suppress(Exception):
            classify_script(source)

    rows: list[list[str]] = []
    points: list[tuple[int, float]] = []
    for frac, source in slices:
        start = time.perf_counter()
        try:
            classify_script(source)
            ok = True
        except Exception:  # 잘린 조각은 문법 오류일 수 있다 — 실패도 한 행으로 남긴다
            ok = False
        elapsed = time.perf_counter() - start
        if ok:
            points.append((len(source), elapsed))
        rows.append(
            [
                f"{frac:.3f}",
                str(len(source)),
                f"{elapsed:.3f}",
                f"{1e6 * elapsed / len(source):.1f}",
                "ok" if ok else "PARSE-FAIL",
            ]
        )
    print(_fmt_table(["frac", "chars", "warm_s", "us/ch", "parse"], rows))
    slope = _loglog_slope(points)
    print(f"    log-log 기울기 = {slope:.2f}  (1.00=선형)")
    if len(points) >= 2:
        size_ratio = points[-1][0] / points[0][0]
        time_ratio = points[-1][1] / points[0][1]
        print(f"    양 끝: 크기 {size_ratio:.1f} 배 → 시간 {time_ratio:.1f} 배")
        mid = points[len(points) // 2]
        tail_size = points[-1][0] / mid[0]
        tail_time = points[-1][1] / mid[1]
        print(f"    꼬리 절반(중간→끝): 크기 {tail_size:.1f} 배 → 시간 {tail_time:.1f} 배")
        print("      ★꼬리가 sublinear 면 기울기는 성장법칙이 아니라 구문 밀도의 얼룩이다.")
    return {"slope": slope, "points": points}


# --------------------------------------------------------------------------- #
# [6] solo — 워밍업의 파일 간 전이량
# --------------------------------------------------------------------------- #

_SOLO_CHILD = """
import json, sys, time
sys.path.insert(0, ".")
from pathlib import Path
from src.strategy.pine_v2.ast_classifier import classify_script
from pynescript.ast.grammar.antlr4.generated.PinescriptParser import PinescriptParser

path = Path("tests/fixtures/pine_corpus_v2") / (sys.argv[1] + ".pine")
start = time.perf_counter()
classify_script(path.read_text())
elapsed = time.perf_counter() - start
dfa = sum(len(d.states) for d in PinescriptParser.decisionsToDFA)
print(json.dumps({"s": elapsed, "dfa": dfa}))
"""


def section_solo(cold_in_batch: dict[str, float]) -> dict[str, Any]:
    print("\n[6] solo — 프로세스당 파일 1개만 파싱 (워밍업의 파일 간 전이량 = 샤딩 중복분)")
    rows: list[list[str]] = []
    solo: dict[str, float] = {}
    for path in _corpus_files():
        name = path.stem
        result = _run_child(_SOLO_CHILD, name)
        solo[name] = result["s"]
        batch = cold_in_batch.get(name)
        rows.append(
            [
                name,
                str(len(path.read_text())),
                f"{result['s']:.3f}",
                "-" if batch is None else f"{batch:.3f}",
                "-" if batch is None else f"{result['s'] - batch:+.3f}",
                str(result["dfa"]),
            ]
        )
    print(_fmt_table(["script", "chars", "solo_s", "batch_cold_s", "delta", "dfa"], rows))
    print(
        f"    solo 합계={sum(solo.values()):.2f}s — 프로세스 9 개로 쪼갰을 때의 총비용 (샤딩 최악)"
    )
    return {"solo": solo}


# --------------------------------------------------------------------------- #
# [7] cProfile
# --------------------------------------------------------------------------- #


def section_cprofile(name: str = _HEADLINE, top: int = 15) -> None:
    import cProfile
    import io
    import pstats

    from src.strategy.pine_v2.ast_classifier import classify_script

    print(
        f"\n[7] cProfile — cold {name}, 누적시간 상위 {top} (프로파일러가 절대시간을 3~4배 부풀린다)"
    )
    profiler = cProfile.Profile()
    profiler.enable()
    classify_script(_read(name))
    profiler.disable()
    buffer = io.StringIO()
    pstats.Stats(profiler, stream=buffer).sort_stats("cumulative").print_stats(top)
    print(buffer.getvalue())


# --------------------------------------------------------------------------- #
# [8] 인과 대조 — 이 스크립트에서 가장 강한 증거
# --------------------------------------------------------------------------- #


def section_dfa_control(name: str = _HEADLINE) -> dict[str, float]:
    """같은 프로세스·같은 입력에서 ANTLR 캐시를 비우면 cold 비용이 돌아오는가.

    돌아온다면 원인은 import 도, 입력 크기도 아니고 **캐시의 상태**다.
    ★뒤이어 성분을 **하나씩** 비워, 셋 중 어느 것이 비용을 지고 있는지까지 가른다.
    """
    from src.strategy.pine_v2.ast_classifier import classify_script

    print(f"\n[8] 인과 대조 — 같은 프로세스·같은 입력({name}), ANTLR 캐시만 비운다")
    source = _read(name)
    rows: list[list[str]] = []
    measured: dict[str, float] = {}

    def measure(label: str) -> None:
        start = time.perf_counter()
        classify_script(source)
        elapsed = time.perf_counter() - start
        measured[label] = elapsed
        rows.append([label, f"{elapsed:.3f}", str(_dfa_state_count())])

    # 앞 섹션이 이미 DFA 를 데워 놨을 수 있으므로 먼저 비운다 — 라벨을 정직하게 유지한다.
    _reset_antlr_caches()
    rows.append(["0 reset all", "-", str(_dfa_state_count())])
    measure("1 cold")
    measure("2 warm")
    measure("3 warm")
    _reset_antlr_caches()
    rows.append(["4 reset all", "-", str(_dfa_state_count())])
    measure("5 post-reset")
    measure("6 warm again")

    # ── 성분 분리 ──────────────────────────────────────────────
    # 셋을 한꺼번에 비우면 「ANTLR 캐시가 원인」까지만 말할 수 있다. 하나씩 비워야
    # 「parser DFA 가 원인」으로 좁혀진다 (2026-08-08 codex 평가 지적을 받아 추가).
    #
    # ★★**이 루프는 independent control 이 아니다** (2026-08-08 2차 codex 평가 지적).
    #   매 회차 끝에 `measure("  → warm")` 로 **다시 데우므로**, `shared_ctx` 차례가 왔을 때
    #   parser DFA 는 이미 워밍돼 있다. 그래서 여기 나오는 1.0배는
    #     「shared_ctx 는 무관하다」가 아니라
    #     「**parser DFA 가 데워져 있으면** shared_ctx 는 추가 비용을 안 진다」
    #   만 말한다. 성분의 **단독** 기여는 이 루프가 답하지 않는다.
    #   답하는 것은 [9] `--components` — 성분마다 **새 프로세스**를 띄워 워밍 이력을 같게 맞춘다.
    for scope in ("parser_dfa", "shared_ctx", "lexer_dfa"):
        _reset_antlr_caches(scope)
        rows.append([f"reset {scope} only", "-", str(_dfa_state_count())])
        measure(f"  → after {scope}")
        measure("  → warm")

    print(_fmt_table(["단계", "seconds", "dfa"], rows))
    warm = measured["2 warm"]
    if warm > 0:
        print("    성분별 배수 (warm 대비):")
        for scope in ("parser_dfa", "shared_ctx", "lexer_dfa"):
            ratio = measured[f"  → after {scope}"] / warm
            verdict = "★비용을 진다" if ratio > 2 else "이 상태에서는 추가 비용 없음"
            print(f"      {scope:12s} {ratio:5.1f} 배  {verdict}")
        print(
            "      ★위 세 줄은 **직전 성분이 다시 데워진 상태**에서 잰 값이다 — "
            "성분의 단독 기여가 아니다 ([9] `--components` 참조)."
        )
        print(
            f"    ★워밍업 배수: cold/warm = {measured['1 cold'] / warm:.1f} 배, "
            f"리셋 직후/warm = {measured['5 post-reset'] / warm:.1f} 배"
        )
        print("      입력도 프로세스도 그대로인데 비용이 되돌아온다 → 원인은 캐시 상태다.")
    return measured


# --------------------------------------------------------------------------- #
# [9] 성분 independent control — 성분마다 새 프로세스
# --------------------------------------------------------------------------- #

# 한 프로세스 안에서 성분을 순서대로 비우면 뒤 성분은 앞 성분이 **다시 데워진** 상태에서
# 측정된다([8] 주석). 여기서는 성분 하나당 프로세스 하나를 띄워, 리셋 직전 상태를
# 「cold 1회 + warm 1회」로 **셋 다 똑같이** 맞춘다. 그래야 세 배수를 서로 비교할 수 있다.
_COMPONENT_CHILD = """
import json, sys, time
sys.path.insert(0, ".")
from pathlib import Path
from antlr4.dfa.DFA import DFA
from antlr4.PredictionContext import PredictionContextCache
from src.strategy.pine_v2.ast_classifier import classify_script
from pynescript.ast.grammar.antlr4.generated.PinescriptLexer import PinescriptLexer
from pynescript.ast.grammar.antlr4.generated.PinescriptParser import PinescriptParser

name = sys.argv[1]
scope = sys.argv[2]
source = (Path("tests/fixtures/pine_corpus_v2") / (name + ".pine")).read_text()

def dfa_total():
    return sum(len(d.states) for d in PinescriptParser.decisionsToDFA)

def timed():
    start = time.perf_counter()
    classify_script(source)
    return time.perf_counter() - start

cold = timed()      # 이 프로세스의 첫 접촉 — 셋 다 여기서 같은 이력을 갖는다
warm = timed()

# ★드리프트 경고 — 아래 리셋 3분기는 부모의 `_reset_antlr_caches()` 를 **verbatim 재구현**한 것이다.
#   child 는 별도 프로세스에서 도는 **문자열 프로그램**이라 부모 함수를 import 로 공유할 수 없다.
#   ⇒ ANTLR 리셋 방식이 바뀌면 **두 곳을 함께 고쳐라** (여기 + `_reset_antlr_caches`).
#   한쪽만 고치면 [9] 의 independent control 과 [8] 의 성분 루프가 **서로 다른 것을 재고도**
#   둘 다 초록으로 보인다.
if scope == "parser_dfa":
    PinescriptParser.decisionsToDFA = [
        DFA(s, i) for i, s in enumerate(PinescriptParser.atn.decisionToState)
    ]
elif scope == "shared_ctx":
    PinescriptParser.sharedContextCache = PredictionContextCache()
elif scope == "lexer_dfa":
    PinescriptLexer.decisionsToDFA = [
        DFA(s, i) for i, s in enumerate(PinescriptLexer.atn.decisionToState)
    ]
else:
    raise SystemExit("unknown scope: " + scope)

after = timed()
rewarm = timed()
print(json.dumps({
    "scope": scope, "cold_s": cold, "warm_s": warm,
    "after_reset_s": after, "rewarm_s": rewarm, "dfa": dfa_total(),
}))
"""


def section_components(name: str = _HEADLINE) -> dict[str, Any]:
    """성분마다 **새 프로세스**에서 재는 independent control.

    [8] 의 성분 루프는 회차마다 `→ warm` 으로 다시 데우므로, 두 번째·세 번째 성분은
    「parser DFA 가 이미 워밍된 상태」를 배경으로 측정된다. 그 배치에서 나온 1.0배는
    **성분의 단독 기여가 아니다.** 여기서는 프로세스를 갈아 배경을 셋 다 동일하게
    (cold 1회 + warm 1회) 맞춘 뒤 그 성분만 비운다.

    ★이 섹션이 답하는 것과 아닌 것.
      - 답한다: 「배경 워밍 이력이 같을 때, 어느 성분을 비워야 비용이 되돌아오는가」
      - 안 답한다: 「완전 cold 첫 파싱에서 각 성분이 몇 초씩 나눠 갖는가」. 셋 다 비어
        있는 상태를 성분별로 쪼갤 방법이 없다 — 캐시를 「끈」 채로 파싱할 수 없기 때문이다.
        그 분해는 **미측정**이다.
    """
    print(f"\n[9] 성분 independent control — 성분마다 **새 프로세스** ({name})")
    print("    배경을 cold 1회 + warm 1회로 셋 다 동일하게 맞춘 뒤 그 성분만 비운다.")
    rows: list[list[str]] = []
    out: dict[str, Any] = {}
    for scope in ("parser_dfa", "shared_ctx", "lexer_dfa"):
        sample = _run_child(_COMPONENT_CHILD, name, scope)
        out[scope] = sample
        ratio = sample["after_reset_s"] / sample["warm_s"] if sample["warm_s"] else float("nan")
        rows.append(
            [
                scope,
                f"{sample['cold_s']:.3f}",
                f"{sample['warm_s']:.3f}",
                f"{sample['after_reset_s']:.3f}",
                f"{sample['rewarm_s']:.3f}",
                f"{ratio:.1f}x",
            ]
        )
    print(_fmt_table(["scope", "cold_s", "warm_s", "after_reset_s", "rewarm_s", "배수"], rows))
    print("    ★배수 = after_reset / warm. 같은 프로세스 안 비교라 머신 부하에 강하다.")
    return out


# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description="[BL-598] 코퍼스 첫-접촉 파싱 비용 프로파일")
    parser.add_argument("--ramp", action="store_true", help="[4][5] 크기 램프 (cold+warm)")
    parser.add_argument("--solo", action="store_true", help="[6] 파일별 격리 프로세스")
    parser.add_argument(
        "--cprofile", action="store_true", help="[7] cold 파싱 상위 함수 (단독 지정 시 [7]만)"
    )
    parser.add_argument(
        "--components",
        action="store_true",
        help="[9] 성분마다 새 프로세스로 재는 independent control (단독 지정 시 [9]만, ~4분)",
    )
    parser.add_argument("--all", action="store_true", help="[1]~[9] 전부 ([7] 포함, ~16분)")
    args = parser.parse_args()

    print("=" * 78)
    print("[BL-598] 코퍼스 첫-접촉 파싱 비용 프로파일")
    print(f"코퍼스: {_CORPUS_DIR}")
    print(f"python: {sys.version.split()[0]}")
    print("=" * 78)

    # `--cprofile` / `--components` 단독 = 그 섹션만. `--all` 과 함께면 전 구간을 돈다.
    if args.cprofile and not args.all:
        section_cprofile()
        return 0
    if args.components and not args.all:
        section_components()
        return 0

    section_import()
    corpus = section_corpus()
    if args.ramp or args.all:
        section_cold_ramp()
        section_warm_ramp()
    if args.solo or args.all:
        section_solo(corpus["cold"])
    if args.all:
        # ★[7] 은 프로세스를 데우므로 [8] 의 라벨을 오염시키지 않도록 [8] 앞에 둔다
        #   ([8] 은 첫 단계에서 캐시를 통째로 비우므로 안전하다).
        section_cprofile()
    section_dfa_control()
    if args.components or args.all:
        section_components()

    print("\n" + "=" * 78)
    print("판별 규칙")
    print("  (a) import 워밍업  — [1] import 가 [2] cold 합계 대비 무시할 수준이고 DFA=0 이면 기각")
    print("  (b) 입력크기 비선형 — [3] warm 합계가 단독 실행 비용을 설명 못 하면 기각")
    print("                        (--ramp 의 log-log 기울기는 보조 증거일 뿐이다)")
    print("  둘 다 기각이고 [8] 에서 DFA 리셋만으로 cold 비용이 되돌아오면, 정체는")
    print("  「파싱이 유발하는 프로세스 전역 ANTLR ALL(*) DFA 워밍업」이다.")
    print("  ⇒ 처방은 테스트가 파싱 자체를 안 하게 만드는 것(디스크 캐시) — apps/api/src 불필요.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
