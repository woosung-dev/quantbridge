#!/usr/bin/env bash
# skip-ratchet 판별력 하네스 — [BL-705]. 전건 통과 = 종료 코드 0.
#
# ★이 파일은 수리보다 **먼저** 쓰였다(G1 수용 기준 동결). 현재 `skip-ratchet.sh` 에 대고
#   돌리면 케이스 ④⑤⑥⑨ 가 red 여야 한다 — 그것이 [BL-705] 의 재현이다.
#   정본 = `docs/reference/operations/workflows/generator-evaluator-pipeline.md` §1.
#
# 무엇을 재는가 — **스캔층**이다.
#   `skip-ratchet.sh` 의 자기검사(패턴 판별력 · 판정 함수)는 입력이 「한 줄 문자열과 정수」라
#   `TARGETS` · 확장자 필터 · 스코프별 하한 · hit 수집을 **한 줄도 안 덮는다.** 신설 시
#   「하네스를 따로 두면 또 하나의 고아 스크립트가 된다」는 이유로 이 파일을 뺐는데,
#   **스캔층은 파일 트리 fixture 없이는 검사할 수 없다** — 그 판단이 [BL-705] 로 반증됐다.
#   (`bl-audit-test.sh` · `header-audit-test.sh` 가 임시 트리를 쓰는 이유가 정확히 이것이다.)
#
# ★★핵심 케이스 = ④⑤ **한쪽 스코프 통째 소실**.
#   수리 전 하한은 **두 스코프 합계**였다. `os.walk` 는 없는 디렉터리에서 조용히 0 을 내므로
#   위반이 사는 `backend/tests` 가 통째로 안 스캔돼도 `backend/src` 혼자 합계 하한을 넘겨
#   **「위반 0건 ✓ rc=0」** 이 나왔다. `TARGETS` 두 항목 중 하나만 오타 나면 발화한다.
#   ⇒ fixture 는 **각 스코프 단독으로도 옛 합계 하한(200)을 넘도록** 크기를 잡는다.
#     그러지 않으면 옛 코드도 rc=3 을 내서 이 케이스가 **재현이 아니라 위장**이 된다.
#
# ★fixture 는 임시 트리에 만든다 — 실제 `backend/` 를 절대 건드리지 않는다.
#   트리 주입은 `skip-ratchet.sh` 가 이미 가진 `QB_SKIP_RATCHET_ROOT` 를 쓴다.
#   ⇒ **기본 ROOT 파생(`dirname $0/..`)은 이 하네스가 안 덮는다.** 그 경로는
#     `final-gates.sh` 의 실물 게이트 실행(인자·env 없음)이 매번 덮는다. 정직한 회계다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: scripts/skip-ratchet-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
RATCHET="$ROOT/scripts/skip-ratchet.sh"
[ -f "$RATCHET" ] || {
  echo "✗ 래칫 스크립트가 없다: $RATCHET" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || {
  echo "✗ python3 가 없다 — fixture 를 만들 수 없다." >&2
  exit 3
}

# ── fixture 크기 ──────────────────────────────────────────────────
# ★이 둘은 `skip-ratchet.sh` 의 `MIN_FILES` 와 **함께 움직인다.**
#   TESTS_N 은 `backend/tests` 하한과 **정확히 같다** — 케이스 ①(하한 = 통과)과
#   ⑥(하한−1 = rc=3)이 경계를 양쪽에서 동시에 재기 때문이다.
#   SRC_N 은 `backend/src` 하한보다 크되 **옛 합계 하한 200 을 단독으로 넘는다**(위 ★★).
#   하한을 올리면 ①이 rc=3 으로 크게 죽는다 — 그때 이 상수를 함께 올려라(조용히 죽지 않는다).
TESTS_N=350
SRC_N=200

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0

# ── base 트리 1회 생성 → 케이스마다 복제 ──────────────────────────
build_base() {
  rm -rf "$TMP/base"
  mkdir -p "$TMP/base/backend/tests" "$TMP/base/backend/src"

  # 깨끗한 트리에도 **음성 대조를 실물로** 심는다. 케이스 ①이 「빈 트리라 조용한 것」이
  # 아니라 「봤는데 셀 것이 없는 것」이 되게 한다.
  cat >"$TMP/base/backend/tests/test_conditional.py" <<'FIX'
# 조건부 skip 은 정상 도구다 — 래칫이 세면 안 된다.
import pytest

pytestmark = pytest.mark.skipif(True, reason="플랫폼 조건")


@pytest.mark.skipif(False, reason="픽스처 부재")
def test_ok() -> None:
    pass
FIX
  cat >"$TMP/base/backend/tests/test_quoted.py" <<'FIX'
# 문서·독스트링 안 인용은 선언이 아니다.
"""과거에 이 파일은 `@pytest.mark.skip(reason="…")` 로 죽어 있었다."""


def test_quoted() -> None:
    pass
FIX
  cat >"$TMP/base/backend/src/marker_factory.py" <<'FIX'
# conftest 가 프로그램적으로 만드는 마커 객체는 데코레이터가 아니다.
import pytest

skip_mutation = pytest.mark.skip(reason="opt-in 플래그")
FIX

  # ★확장자 필터를 재는 미끼 — `*.py` 가 아닌 파일 2종. 하나는 위반 문자열을 **줄 맨 앞**에
  #   품는다. 필터를 지우면 케이스 ①이 rc=1 로, 케이스 ⑥이 rc=0 으로 동시에 뒤집힌다.
  #   (미끼가 없으면 「확장자 필터 제거」 변이가 **무증거**다 — 2026-08-11 실측으로 확인.)
  cat >"$TMP/base/backend/tests/notes.md" <<'FIX'
과거 기록
@pytest.mark.skip(reason="이건 파이썬 파일이 아니다")
FIX
  : >"$TMP/base/backend/tests/fixtures.json"

  # 나머지는 빈 패딩으로 정확한 개수까지 채운다. 10개마다 하위 디렉터리에 둬
  # `os.walk` 재귀 자체도 태운다.
  python3 - "$TMP/base" "$TESTS_N" "$SRC_N" <<'PY'
import os
import sys

base, tests_n, src_n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for scope, want in (("backend/tests", tests_n), ("backend/src", src_n)):
    root = os.path.join(base, scope)
    have = sum(
        1
        for d, _s, fs in os.walk(root)
        for f in fs
        if f.endswith(".py")
    )
    for i in range(want - have):
        sub = os.path.join(root, "sub") if i % 10 == 0 else root
        os.makedirs(sub, exist_ok=True)
        open(os.path.join(sub, "pad_%04d.py" % i), "w").close()
PY
}

new_tree() {
  rm -rf "$TMP/tree"
  cp -a "$TMP/base" "$TMP/tree"
}

put() { # put <상대경로> <본문>
  local p="$TMP/tree/$1"
  mkdir -p "$(dirname "$p")"
  printf '%s\n' "$2" >"$p"
}

run() { # 인자 그대로 래칫에 넘긴다. ★파이프 없음. stdout+stderr 합본.
  OUT="$(QB_SKIP_RATCHET_ROOT="$TMP/tree" bash "$RATCHET" "$@" 2>&1)"
  RC=$?
}

run_stdout() { # 기계 판독 경로(`--list`) 전용 — stderr 를 버린다.
  OUT="$(QB_SKIP_RATCHET_ROOT="$TMP/tree" bash "$RATCHET" "$@" 2>/dev/null)"
  RC=$?
}

# ★래칫 **사본**에 변이를 심고 돌린다 — 원본은 안 건드린다.
#   왜: 래칫의 자기검사(패턴 판별력 · 판정 함수)는 **정상 상태에서는 절대 발화하지 않는다.**
#   그래서 그 둘을 통째로 지워도 게이트도 하네스도 초록이다(2026-08-11 실측 M5). 아래
#   케이스 ⑩⑪ 이 「자기검사가 실제로 발화하는가」를 behavioral 로 잰다 — 자기검사가 사라지면
#   변이가 rc=3 대신 rc=0/1 을 내고 그때 red 가 난다.
#   ★앵커를 못 찾으면 **크게 죽는다**(rc=9). 이름이 바뀌면 조용히 통과하지 않는다.
mutant_run() { # mutant_run <찾을 문자열> <바꿀 문자열>
  python3 - "$RATCHET" "$TMP/mutant.sh" "$1" "$2" <<'PY'
import sys

src, dst, old, new = sys.argv[1:5]
s = open(src, encoding="utf-8").read()
if old not in s:
    sys.stderr.write("✗ 변이 앵커를 못 찾았다: %r\n" % old)
    sys.exit(9)
open(dst, "w", encoding="utf-8").write(s.replace(old, new))
PY
  if [ $? -ne 0 ]; then
    OUT="변이 앵커 소실 — 하네스가 낡았다"
    RC=9
    return
  fi
  OUT="$(QB_SKIP_RATCHET_ROOT="$TMP/tree" bash "$TMP/mutant.sh" 2>&1)"
  RC=$?
}

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-52s %s\n' "$1" "$2"
    printf '%s\n' "$OUT" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-52s\n' "$1"
  fi
}

has() { printf '%s\n' "$OUT" | grep -qF "$1"; }

echo "══ skip-ratchet 하네스 ══"
echo "  fixture: backend/tests $TESTS_N · backend/src $SRC_N (tmp 트리)"
echo ""

build_base

# ① 무변화 — 하한을 정확히 충족하는 깨끗한 트리. **양성 대조 = 일치 시 침묵.**
new_tree
run
why=""
[ "$RC" -eq 0 ] || why="rc=$RC (기대 0) — 하한이 올라갔으면 이 하네스의 TESTS_N/SRC_N 을 함께 올려라"
[ -z "$why" ] && ! has "무조건 skip 0건" && why="깨끗한 트리인데 「0건」을 안 말한다"
report "① 무변화(하한 정확히 충족) → rc=0 · 침묵" "$why"

# ② 데코레이터 위반 1건 → rc=1 + 그 경로가 출력에 있다
new_tree
put "backend/tests/test_dead.py" '# 3개월째 꺼져 있다
import pytest


@pytest.mark.skip(reason="사유 없음")
def test_dead() -> None:
    pass'
run
why=""
[ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
[ -z "$why" ] && ! has "backend/tests/test_dead.py" && why="위반 경로를 출력에 안 적었다"
report "② 데코레이터 위반 1건 → rc=1 + 경로 표기" "$why"

# ③ 모듈 레벨 위반 1건 → rc=1 (형태 축이 2개인지)
new_tree
put "backend/src/dead_module.py" '# 파일을 통째로 끈다.
import pytest

pytestmark = pytest.mark.skip(reason="모듈 통째")'
run
why=""
[ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
[ -z "$why" ] && ! has "backend/src/dead_module.py" && why="위반 경로를 출력에 안 적었다"
report "③ 모듈 레벨 위반 1건 → rc=1" "$why"

# ④ ★BL-705 본체 — `backend/tests` 통째 소실. 옛 코드는 rc=0 이었다.
new_tree
rm -rf "$TMP/tree/backend/tests"
run
why=""
[ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — ★스코프 하나가 통째로 사라졌는데 판정을 냈다"
# 사유까지 잰다 — 「경로가 없다」와 「하한 미달」은 운영자에게 다른 행동을 시킨다(오타 vs 축소).
[ -z "$why" ] && ! has "경로가 없다" && why="rc 는 맞지만 사유가 「경로 부재」가 아니다"
report "④ backend/tests 통째 소실 → rc=3 + 「경로 부재」" "$why"

# ⑤ 반대 축도 대칭인가 — `backend/src` 통째 소실
new_tree
rm -rf "$TMP/tree/backend/src"
run
why=""
[ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — 반대 스코프에는 하한이 없다"
report "⑤ backend/src 통째 소실 → rc=3" "$why"

# ⑥ 경계 — tests 를 하한−1 로. `<` 인가 `<=` 인가.
new_tree
victim="$(find "$TMP/tree/backend/tests" -name 'pad_*.py' | head -1)"
rm -f "$victim"
run
why=""
[ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — 하한−1 을 통과시켰다(부등호가 틀렸다)"
[ -z "$why" ] && ! has "하한" && why="rc 는 맞지만 사유가 「하한 미달」이 아니다"
report "⑥ tests 하한−1 → rc=3 (경계 · 「하한 미달」)" "$why"

# ⑦ 음성 대조 — 조건부 skip 만 늘려도 rc=0. 스캔층을 **지나서** 안 세는가.
new_tree
put "backend/tests/test_more_conditional.py" '# 조건부는 정상이다.
import pytest

pytestmark = pytest.mark.skipif(True, reason="조건부")


@pytest.mark.skipif(True, reason="조건부")
def test_c() -> None:
    pass'
run
why=""
[ "$RC" -eq 0 ] || why="rc=$RC (기대 0) — 조건부 skip 을 셌다"
report "⑦ skipif 만 추가 → rc=0 (음성 대조)" "$why"

# ⑧ `--list` 는 위반 위치만 낸다 — stdout 정확히 1줄
new_tree
put "backend/tests/test_dead.py" 'import pytest


@pytest.mark.skip
def test_dead() -> None:
    pass'
run_stdout --list
why=""
[ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
lines="$(printf '%s' "$OUT" | grep -c .)"
[ -z "$why" ] && [ "$lines" != "1" ] && why="stdout 이 ${lines}줄이다 (기대 1) — 기계 판독 경로가 오염됐다"
[ -z "$why" ] && ! has "backend/tests/test_dead.py:4" && why="위치(파일:줄)를 안 냈다"
report "⑧ --list → rc=1 · stdout 정확히 1줄" "$why"

# ⑨ 트리 재정의는 **보이게** 한다 — 셸 잔여 export 하나가 판정 대상을 조용히 갈아치운다
new_tree
run
why=""
has "QB_SKIP_RATCHET_ROOT" || why="ROOT 재정의를 출력에 안 알린다"
[ -z "$why" ] && ! has "$TMP/tree" && why="어느 트리를 봤는지 출력에 없다"
report "⑨ QB_SKIP_RATCHET_ROOT 재정의를 출력에 알린다" "$why"

# ⑩ 자기검사 ①(패턴 판별력)이 **실제로 발화하는가** — 정규식을 못 맞추게 바꾼 사본
new_tree
mutant_run 'SKIP_DECORATOR = re.compile(r"^[ \t]*@pytest\.mark\.skip(?![A-Za-z_])")' \
  'SKIP_DECORATOR = re.compile(r"^ZZZ_NEVER_MATCHES")'
why=""
[ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — 판별기를 부쉈는데 자기검사가 안 울었다"
[ -z "$why" ] && ! has "판별기가 고장났다" && why="rc 는 맞지만 판별기 고장을 안 말한다"
report "⑩ 패턴 자기검사가 발화한다 (사본 변이)" "$why"

# ⑪ 자기검사 ②(판정 함수)가 **실제로 발화하는가** — 스코프별 하한 비교를 죽인 사본
new_tree
mutant_run '        if files < MIN_FILES[scope]:' '        if False:'
why=""
[ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — 판정 함수를 부쉈는데 자기검사가 안 울었다"
[ -z "$why" ] && ! has "판정 함수가 고장났다" && why="rc 는 맞지만 판정 함수 고장을 안 말한다"
report "⑪ 판정 자기검사가 발화한다 (사본 변이)" "$why"

echo ""
if [ "$FAIL" -ne 0 ]; then
  echo "✗ 하네스 $FAIL/$((PASS + FAIL)) 실패 — 래칫이 스캔층에서 판별력을 잃었다."
  exit 1
fi
echo "✓ 하네스 $PASS/$PASS 전건 통과"
