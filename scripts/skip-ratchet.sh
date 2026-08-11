#!/usr/bin/env bash
# skip-ratchet — 무조건 skip 된 pytest 테스트 개수를 래칫으로 동결한다. (2026-08-11 ledger-truth)
#
# 무엇을 재는가
#   대상: `backend/tests/**/*.py` · `backend/src/**/*.py`.
#   위반: **데코레이터 형태의 무조건 skip** — 줄 맨 앞(들여쓰기 허용)에 `@pytest.mark.skip`
#         이 오고 그 뒤가 `(` 또는 줄끝인 것. baseline 초과 시 rc=1.
#
# ★핵심 ① — `skipif` 는 세지 않는다. 조건부 skip 은 정상적인 도구다(플랫폼·픽스처 부재·
#   파일 미생성). 이 래칫이 막으려는 것은 **아무 조건 없이 영구히 꺼진 테스트**다.
#   실측: 이 레포에 `@pytest.mark.skipif` 가 18건 있고 전부 정당하다.
#
# ★핵심 ② — `conftest.py` 가 **프로그램적으로** 만드는 마커 객체는 데코레이터가 아니다.
#   `skip_mutation = pytest.mark.skip(reason=…)` 뒤에 `item.add_marker(...)` 로 주입하는
#   패턴(실측: `tests/conftest.py:138,141` · `tests/real_broker/conftest.py:86`)은 opt-in
#   플래그가 있는 정상 설계다. 그래서 판정은 **줄 맨 앞 `@`** 로 앵커한다.
#   같은 앵커가 문서·독스트링 안에 인용된 `@pytest.mark.skip(` 도 자동으로 배제한다
#   (실측: `tests/health/test_metrics_auth.py` 의 부검 주석이 그 문자열을 품고 있다).
#
# ★핵심 ③ — baseline 이 0 이라 **이 래칫은 스스로를 검증하지 못한다.** 레포가 이미 깨끗해서
#   판정 로직을 통째로 지워도 「초과 0건」이 나온다(BL-569 가 `bl-audit` 에서 겪은 모양).
#   그래서 매 실행마다 ⑴ 패턴 판별력(양성 2 · 음성 3)과 ⑵ 판정 함수(초과/동률/빈입력)를
#   합성 입력으로 자기검사하고, 하나라도 어긋나면 초록 대신 **rc=3 으로 판정을 포기**한다.
#   [LESSON-101] — 검증 명령은 빈 입력을 받으면 「내가 기대한 답」을 낸다.
#
# ★핵심 ④ — 스캔한 파일이 하한 미만이면 rc=3. `grep` 이 아무것도 못 찾은 것과 「위반 0건」은
#   다른 사건이다. 경로 오타·부분 체크아웃이 이 래칫을 조용히 초록으로 만드는 것을 막는다.
#
# baseline 을 올리려면: 왜 무조건 skip 이 필요한지 **BL 번호와 함께** 여기 적고 숫자를 바꿔라.
# 「Sprint NN follow-up」 같은 주인 없는 사유는 3개월 뒤 아무도 못 찾는다 — 그게 이 래칫이
# 생긴 이유다(2026-05-14 에 심긴 5건이 2026-08-11 까지 살아 있었다).
#
# 종료 코드: baseline 이하 → 0 / 초과 → 1 / 자기검사 실패·파일 하한 미달·python3 부재 → 3.
# 인자: 없음 = 요약 + 위반 경로. `--list` = 위반 위치만 한 줄에 하나씩.
#
# 사용법: scripts/skip-ratchet.sh [--list]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# 하네스·수동 대조용 — 검사 대상 트리를 갈아끼운다 (`header-audit.sh` 와 같은 관용구).
[ -n "${QB_SKIP_RATCHET_ROOT:-}" ] && ROOT="$QB_SKIP_RATCHET_ROOT"

LIST=0
case "${1:-}" in
  "") ;;
  --list) LIST=1 ;;
  *) echo "알 수 없는 인자: $1 (지원: --list)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null 2>&1 || {
  echo "✗ python3 를 찾을 수 없다 — 판정을 포기한다 (초록을 내면 거짓 통과가 된다)." >&2
  exit 3
}

ROOT="$ROOT" LIST="$LIST" python3 - <<'PY'
# -*- coding: utf-8 -*-
"""무조건 skip 래칫 — 판정 본체. (2026-08-11 ledger-truth)"""
import os
import re
import sys

ROOT = os.environ["ROOT"]
LIST = os.environ["LIST"] == "1"

# baseline — 이 회차 종료 시점 실측값. 올릴 때는 위 헤더에 BL 번호와 사유를 함께 적어라.
BASELINE = 0
# 스캔 파일 하한 — 실측 721건(2026-08-11). 부분 트리를 초록으로 통과시키지 않기 위한 방벽.
MIN_FILES = 200

TARGETS = ("backend/tests", "backend/src")

# 줄 맨 앞 앵커 + `skip` 직후에 식별자 문자가 없다 ⇒ `skipif` 와 인용문을 배제한다.
# ★2026-08-11 평가자 실측으로 **두 구멍**이 드러나 넓혔다:
#   ⑴ 종전 `[ \t]*(\(|$)` 는 줄끝만 허용해서 `@pytest.mark.skip  # 3개월째 꺼져 있다` 를
#      놓쳤다(CRLF 도 동일). pytest 는 그걸 `unconditional skip` 으로 보고한다 —
#      **사유조차 없는 최악형이 무료 통과**였다.
#   ⑵ `pytestmark = pytest.mark.skip(...)` 모듈 레벨 무조건 skip 은 `@` 앵커에 안 걸렸다.
#      **파일을 통째로 끄는** 더 큰 같은 부채이고, 이 레포는 이미 `pytestmark =
#      pytest.mark.skipif(` 를 2곳에서 쓴다 — 키워드 하나 차이다.
SKIP_DECORATOR = re.compile(r"^[ \t]*@pytest\.mark\.skip(?![A-Za-z_])")
SKIP_MODULE = re.compile(r"^[ \t]*pytestmark[ \t]*=.*pytest\.mark\.skip(?![A-Za-z_])")


def is_unconditional_skip(line):
    """데코레이터 형태 또는 모듈 레벨 형태. 둘 다 「무조건 꺼져 있다」다."""
    return bool(SKIP_DECORATOR.search(line) or SKIP_MODULE.search(line))


def verdict(count, files):
    """(rc, 사유) — 판정은 여기 한 곳에서만 한다. 자기검사가 이 함수를 직접 부른다."""
    if files < MIN_FILES:
        return 3, "스캔 파일 %d건 < 하한 %d건 — 판정 포기" % (files, MIN_FILES)
    if count > BASELINE:
        return 1, "무조건 skip %d건 > baseline %d건" % (count, BASELINE)
    return 0, "무조건 skip %d건 ≤ baseline %d건" % (count, BASELINE)


# ── 자기검사 ① 패턴 판별력 (양성 2 · 음성 3) ──────────────────────
_POSITIVE = (
    '@pytest.mark.skip(reason="x")',
    "    @pytest.mark.skip",
    "@pytest.mark.skip  # 3개월째 꺼져 있다",          # 주석 꼬리 (2026-08-11 구멍 ⑴)
    "@pytest.mark.skip\r",                            # CRLF
    'pytestmark = pytest.mark.skip(reason="모듈 통째")',  # 모듈 레벨 (구멍 ⑵)
    "pytestmark = [pytest.mark.asyncio, pytest.mark.skip]",  # 리스트 형태
)
_NEGATIVE = (
    '@pytest.mark.skipif(not _P.exists(), reason="미생성")',      # 조건부는 정상
    '    skip_mutation = pytest.mark.skip(reason="…")',           # conftest 프로그램적 마커
    'pytestmark = pytest.mark.skipif(_P.exists(), reason="조건부")',  # 모듈 레벨이지만 조건부
    "pytestmark = pytest.mark.real_broker",                        # 다른 마커
    "동안 아래 3건은 `@pytest.mark.skip(...)` 로 죽어 있었다",      # 독스트링 인용
)
_bad = [s for s in _POSITIVE if not is_unconditional_skip(s)]
_bad += [s for s in _NEGATIVE if is_unconditional_skip(s)]
if _bad:
    sys.stderr.write("✗ skip 판별기가 고장났다 — 어긋난 합성 입력:\n")
    for s in _bad:
        sys.stderr.write("    %r\n" % s)
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)

# ── 자기검사 ② 판정 함수 (초과 → 1 · 동률 → 0 · 빈 입력 → 3) ──────
_CASES = (
    (BASELINE + 1, MIN_FILES, 1),
    (BASELINE, MIN_FILES, 0),
    (BASELINE, 0, 3),
)
_bad_v = [(c, f, want, verdict(c, f)[0]) for c, f, want in _CASES if verdict(c, f)[0] != want]
if _bad_v:
    sys.stderr.write("✗ 판정 함수가 고장났다 — (count, files, 기대, 실제): %r\n" % (_bad_v,))
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)

# ── 스캔 ──────────────────────────────────────────────────────────
hits = []
files = 0
per_scope = {}

for scope in TARGETS:
    base_dir = os.path.join(ROOT, scope)
    count = 0
    for dirpath, _dirnames, filenames in os.walk(base_dir):
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            count += 1
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT)
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if is_unconditional_skip(line):
                            hits.append((rel, lineno, line.strip()))
            except OSError as exc:
                sys.stderr.write("✗ 파일을 못 읽었다: %s (%s) — 판정을 포기한다.\n" % (rel, exc))
                sys.exit(3)
    per_scope[scope] = count
    files += count

hits.sort()
rc, why = verdict(len(hits), files)

if LIST:
    for rel, lineno, _text in hits:
        print("%s:%d" % (rel, lineno))
else:
    print("══ skip-ratchet  root=%s ══" % ROOT)
    print("  대상: %s (*.py)" % " + ".join(TARGETS))
    print(
        "  스캔 %d건 (%s) · baseline %d · 무조건 skip %d건"
        % (files, " / ".join("%s %d" % (s, per_scope[s]) for s in TARGETS), BASELINE, len(hits))
    )
    print("")
    print("▶ 무조건 skip — 데코레이터·모듈레벨 (%d건)" % len(hits))
    if not hits:
        print("  없음")
    else:
        for rel, lineno, text in hits:
            print("  %s:%d  %s" % (rel, lineno, text))
    print("")
    if rc == 3:
        print("✗ %s" % why)
    elif rc == 1:
        print("✗ %s — 사유와 BL 번호를 scripts/skip-ratchet.sh 헤더에 적고 baseline 을 올려라." % why)
    else:
        print("✓ %s" % why)
        if len(hits) < BASELINE:
            print("  ↓ baseline 을 %d 로 내려라 — 래칫은 되감기지 않아야 한다." % len(hits))

sys.exit(rc)
PY
