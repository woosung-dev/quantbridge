#!/usr/bin/env bash
# skip-ratchet — 무조건 skip 된 pytest 테스트 개수를 래칫으로 동결한다. (2026-08-11 ledger-truth)
#
# 무엇을 재는가
#   대상: `apps/api/tests/**/*.py` · `apps/api/src/**/*.py`.
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
#   그래서 매 실행마다 ⑴ 패턴 판별력(양성 2 · 음성 3)과 ⑵ 판정 함수(초과/동률/하한 미달/경로
#   부재)를 합성 입력으로 자기검사하고, 하나라도 어긋나면 초록 대신 **rc=3 으로 판정을 포기**한다.
#   [LESSON-101] — 검증 명령은 빈 입력을 받으면 「내가 기대한 답」을 낸다.
#
# ★핵심 ④ — 하한은 **스코프별**이다. `grep` 이 아무것도 못 찾은 것과 「위반 0건」은 다른
#   사건이고, 그 판정을 **합계로 하면 한쪽 스코프가 통째로 사라져도 초록**이 된다([BL-705]).
#   실측 — 수리 전에는 위반이 사는 `apps/api/tests`(505파일)가 통째로 안 스캔돼도
#   `apps/api/src`(217)가 합계 하한 200 을 넘겨 「위반 0건 ✓ rc=0」이었다. `os.walk` 는 없는
#   디렉터리에서 조용히 0 을 내므로 `TARGETS` 두 항목 중 **하나만 오타 나면** 발화한다.
#   ⇒ ⑴ 스코프 경로 부재 → rc=3 ⑵ 스코프별 파일 수 < 그 스코프 하한 → rc=3.
#   하한값은 2026-08-11 실측(tests 505 / src 217)의 **70% 선**이다. 종전 200 은 합계 722 의
#   27.7% 라 **파일 72% 손실까지 초록**이었다. 레포가 정당하게 줄어 rc=3 이 나면 그때
#   숫자를 내리고 **왜 줄었는지 여기 적어라** — 조용히 통과시키지 않는 것이 이 하한의 목적이다.
#
# ★핵심 ⑤ — 위 ③의 자기검사는 **스캔층을 한 줄도 안 덮는다.** 입력이 「한 줄 문자열과 정수」라
#   `TARGETS`·확장자 필터·hit 수집·스코프별 셈이 무검증이다(실측: 자기검사를 `if False:` 로
#   막고 정규식까지 무력화해도 rc=0). 신설 시 「하네스를 따로 두면 또 하나의 고아 스크립트가
#   된다」는 이유로 별도 `-test.sh` 를 뺐는데, **스캔층은 파일 트리 fixture 없이는 검사할 수
#   없다** — 그 판단이 [BL-705] 로 반증됐다. 정본 = `tools/scripts/skip-ratchet-test.sh`(11케이스,
#   `final-gates.sh`·`mise run gate-harnesses`·CI `documentation` 잡에 배선).
#   ★★위 ③의 자기검사는 **정상 상태에서는 절대 발화하지 않으므로 그것을 통째로 지워도
#     게이트가 초록**이다(2026-08-11 실측 — 자기검사 2종을 무력화해도 rc=0). 그 사각은
#     하네스 케이스 ⑩⑪ 이 닫는다: 래칫 **사본**에 변이를 심고 「자기검사가 실제로 우는가」를
#     behavioral 로 잰다. 자기검사를 지우면 그 두 케이스가 red 다.
#
# baseline 을 올리려면: 왜 무조건 skip 이 필요한지 **BL 번호와 함께** 여기 적고 숫자를 바꿔라.
# 「Sprint NN follow-up」 같은 주인 없는 사유는 3개월 뒤 아무도 못 찾는다 — 그게 이 래칫이
# 생긴 이유다(2026-05-14 에 심긴 5건이 2026-08-11 까지 살아 있었다).
#
# 종료 코드: baseline 이하 → 0 / 초과 → 1 /
#            자기검사 실패·스코프 경로 부재·스코프별 하한 미달·python3 부재 → 3.
# 인자: 없음 = 요약 + 위반 경로. `--list` = 위반 위치만 한 줄에 하나씩.
#
# 사용법: tools/scripts/skip-ratchet.sh [--list]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
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

ROOT="$ROOT" LIST="$LIST" OVERRIDE="${QB_SKIP_RATCHET_ROOT:-}" python3 - <<'PY'
# -*- coding: utf-8 -*-
"""무조건 skip 래칫 — 판정 본체. (2026-08-11 ledger-truth · 스코프별 하한 = BL-705)"""
import os
import re
import sys

ROOT = os.environ["ROOT"]
LIST = os.environ["LIST"] == "1"
OVERRIDE = os.environ.get("OVERRIDE", "")

# baseline — 이 회차 종료 시점 실측값. 올릴 때는 위 헤더에 BL 번호와 사유를 함께 적어라.
BASELINE = 0
# 스코프별 스캔 하한 — 2026-08-11 실측(tests 505 / src 217)의 70% 선([BL-705]).
# ★합계로 재지 마라. 합계는 한쪽 스코프가 통째로 사라져도 다른 쪽이 메워 초록을 낸다.
MIN_FILES = {"apps/api/tests": 350, "apps/api/src": 150}

# ★대상은 하한 dict 에서 파생한다 — 두 벌로 두면 하나만 고쳐져 조용히 갈라진다.
TARGETS = tuple(MIN_FILES)

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


def verdict(count, per_scope):
    """(rc, 사유) — 판정은 여기 한 곳에서만 한다. 자기검사가 이 함수를 직접 부른다.

    `per_scope` 는 {스코프: 파일 수}. 값이 None 이면 **그 경로가 없다**(오타·부분 체크아웃).
    ★스코프를 하나씩 본다 — 합계로 재면 [BL-705] 가 돌아온다.
    """
    for scope in TARGETS:
        files = per_scope.get(scope)
        if files is None:
            return 3, "스코프 경로가 없다: %s — 판정 포기" % scope
        if files < MIN_FILES[scope]:
            return 3, "스캔 %s %d건 < 하한 %d건 — 판정 포기" % (scope, files, MIN_FILES[scope])
    if count > BASELINE:
        return 1, "무조건 skip %d건 > baseline %d건" % (count, BASELINE)
    return 0, "무조건 skip %d건 ≤ baseline %d건" % (count, BASELINE)


def scan(root):
    """(hits, per_scope) — 파일 트리를 실제로 훑는 유일한 자리.

    ★이 층은 위 자기검사가 **한 줄도 못 덮는다**(입력이 파일 트리다).
      판별력은 `tools/scripts/skip-ratchet-test.sh` 가 임시 트리로 잰다 — [BL-705].
    """
    hits = []
    per_scope = {}
    for scope in TARGETS:
        base_dir = os.path.join(root, scope)
        if not os.path.isdir(base_dir):
            per_scope[scope] = None  # 「0건 스캔」과 「경로가 없다」는 다른 사건이다.
            continue
        count = 0
        for dirpath, _dirnames, filenames in os.walk(base_dir):
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                count += 1
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root)
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if is_unconditional_skip(line):
                                hits.append((rel, lineno, line.strip()))
                except OSError as exc:
                    sys.stderr.write("✗ 파일을 못 읽었다: %s (%s) — 판정을 포기한다.\n" % (rel, exc))
                    sys.exit(3)
        per_scope[scope] = count
    hits.sort()
    return hits, per_scope


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

# ── 자기검사 ② 판정 함수 ────────────────────────────────────────
# 초과 → 1 · 동률 → 0 · 한 스코프만 비어도 → 3 · 한 스코프만 하한−1 이어도 → 3 · 경로 부재 → 3.
# ★[BL-705] — 종전 케이스는 「빈 입력 → 3」 하나였고, 그것은 **합계**가 0 일 때만 발화했다.
#   한쪽 스코프가 통째로 사라지는 실제 사고는 아래 3·4·5 케이스가 아니면 안 잡힌다.
_FULL = dict(MIN_FILES)
_HEAD, _TAIL = TARGETS[0], TARGETS[-1]
_CASES = (
    (BASELINE + 1, _FULL, 1),
    (BASELINE, _FULL, 0),
    (BASELINE, dict(_FULL, **{_HEAD: 0}), 3),
    (BASELINE, dict(_FULL, **{_TAIL: MIN_FILES[_TAIL] - 1}), 3),
    (BASELINE, dict(_FULL, **{_HEAD: None}), 3),
)
_bad_v = [(c, f, want, verdict(c, f)[0]) for c, f, want in _CASES if verdict(c, f)[0] != want]
if _bad_v:
    sys.stderr.write("✗ 판정 함수가 고장났다 — (count, per_scope, 기대, 실제): %r\n" % (_bad_v,))
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)

# ── 스캔 ──────────────────────────────────────────────────────────
hits, per_scope = scan(ROOT)
files = sum(n for n in per_scope.values() if n is not None)
rc, why = verdict(len(hits), per_scope)

# ★트리 재정의는 **보이게** 한다 — 셸에 남은 export 하나가 판정 대상 트리를 조용히
#   갈아치운다([BL-705] ⑷). `--list` 는 기계 판독 경로라 stderr 로 보낸다.
if OVERRIDE:
    notice = "★QB_SKIP_RATCHET_ROOT 재정의 — 이 트리를 잰다: %s" % OVERRIDE
    (sys.stderr if LIST else sys.stdout).write(notice + "\n")

if LIST:
    for rel, lineno, _text in hits:
        print("%s:%d" % (rel, lineno))
else:
    print("══ skip-ratchet  root=%s ══" % ROOT)
    print("  대상: %s (*.py)" % " + ".join(TARGETS))
    print(
        "  스캔 %d건 (%s) · baseline %d · 무조건 skip %d건"
        % (
            files,
            " · ".join(
                "%s %s/하한 %d"
                % (s, "**없음**" if per_scope[s] is None else per_scope[s], MIN_FILES[s])
                for s in TARGETS
            ),
            BASELINE,
            len(hits),
        )
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
        print("  「스캔 0건」과 「위반 0건」은 다른 사건이다 — 초록을 내지 않는다 ([BL-705]).")
    elif rc == 1:
        print("✗ %s — 사유와 BL 번호를 tools/scripts/skip-ratchet.sh 헤더에 적고 baseline 을 올려라." % why)
    else:
        print("✓ %s" % why)
        if len(hits) < BASELINE:
            print("  ↓ baseline 을 %d 로 내려라 — 래칫은 되감기지 않아야 한다." % len(hits))

sys.exit(rc)
PY
