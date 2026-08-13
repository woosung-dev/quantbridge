#!/usr/bin/env bash
# signal-check — 스킬 게이트 신호의 **신선도** 판정. ([BL-706])
set -uo pipefail

usage() {
  echo "사용법: $0 [--root <repo>] --run <run> <signal-file-name> | $0 -h|--help" >&2
}

if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
  printf '%s\n' "사용법: $0 [--root <repo>] --run <run> <signal-file-name> | $0 -h|--help"
  exit 0
fi

RUN=""; NAME=""; ROOT_ARG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --run)  [ "$#" -ge 2 ] || { usage; exit 2; }; RUN="$2"; shift 2 ;;
    --root) [ "$#" -ge 2 ] || { usage; exit 2; }; ROOT_ARG="$2"; shift 2 ;;
    -*) usage; exit 2 ;;
    *) [ -z "$NAME" ] || { usage; exit 2; }; NAME="$1"; shift ;;
  esac
done
[ -n "$RUN" ] && [ -n "$NAME" ] || { usage; exit 2; }
case "$RUN" in
  *..*|*[!A-Za-z0-9._-]*) usage; exit 2 ;;
esac
case "$NAME" in
  *..*|*[!A-Za-z0-9._-]*) usage; exit 2 ;;
esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
# ★우선순위: --root 명시 인자 > env > 파생. env 만 열어 두면 셸에 남은 export 하나로
#   빈 신호 디렉터리에서도 PASS 행을 만들 수 있다(콜드 리뷰 P2-1 실증) — 호출부(final-gates)가
#   --root 를 명시해 env 백도어를 닫는다. env 는 하네스 fixture 주입용으로 남긴다.
if [ -n "$ROOT_ARG" ]; then
  if [ -n "${QB_SIGNAL_ROOT:-}" ] && [ "$QB_SIGNAL_ROOT" != "$ROOT_ARG" ]; then
    echo "★QB_SIGNAL_ROOT 는 무시된다 — --root 명시 인자가 이긴다: $ROOT_ARG" >&2
  fi
  ROOT="$ROOT_ARG"
elif [ -n "${QB_SIGNAL_ROOT:-}" ]; then
  ROOT="$QB_SIGNAL_ROOT"
  echo "★QB_SIGNAL_ROOT 재정의 — 이 트리를 잰다: $ROOT" >&2
fi
SIGNAL_FILE="$ROOT/.claude/gates/$RUN/$NAME"
CODE=""; WHY=""

finish() { # finish <rc> <class> <short-sha 또는 "">
  local rc="$1" class="$2" sha="$3"
  if [ -n "$sha" ]; then printf '%s: %s @ %s [%s] — %s\n' "$class" "$NAME" "$sha" "$CODE" "$WHY"
  else                   printf '%s: %s [%s] — %s\n'      "$class" "$NAME" "$CODE" "$WHY"; fi
  exit "$rc"
}
abort() { # 판정 불가. ★초록을 내지 않는다.
  CODE="$1"; WHY="$2"
  finish 3 "abort" ""                                                        # ← 앵커 A8
}

judge_freshness() { # <full-sha> → 0 신선 / 1 낡음 / 3 판정 불가. 사유는 CODE·WHY.
  local sha="$1" anc inmain
  if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then           # ← 앵커 A1
    CODE="no-branch-commits"; WHY="브랜치 커밋이 0개다 (merge-base == HEAD) — 이 회차의 PR 브랜치에서 머지 전에 신호를 다시 취득해라"; return 1
  fi
  if [ "$sha" = "$HEAD_SHA" ]; then                                          # ← 앵커 A2
    CODE="head"; WHY="HEAD 와 동일"; return 0
  fi
  if [ -z "$MERGE_BASE" ]; then                                              # ← 앵커 A3
    CODE="no-origin-main"; WHY="origin/main 이 없어 축약 판정 — HEAD 와 정확히 같을 때만 신선하다"; return 1
  fi
  git -C "$ROOT" merge-base --is-ancestor "$sha" "$HEAD_SHA"; anc=$?
  [ "$anc" -le 1 ] || { CODE="git-error"; WHY="is-ancestor(HEAD) rc=$anc"; return 3; }
  if [ "$anc" -ne 0 ]; then                                                  # ← 앵커 A4
    CODE="not-ancestor"; WHY="HEAD 의 조상이 아니다 — amend·rebase·다른 브랜치의 커밋이다"; return 1
  fi
  git -C "$ROOT" merge-base --is-ancestor "$sha" "$MERGE_BASE"; inmain=$?
  [ "$inmain" -le 1 ] || { CODE="git-error"; WHY="is-ancestor(merge-base) rc=$inmain"; return 3; }
  if [ "$inmain" -eq 0 ]; then                                               # ← 앵커 A5
    CODE="origin-main"; WHY="origin/main 에 이미 있는 커밋 — 앞 회차가 남긴 신호다"; return 1
  fi
  CODE="branch"; WHY="이 브랜치의 커밋 (HEAD-$(git -C "$ROOT" rev-list --count "$sha..$HEAD_SHA" 2>/dev/null || echo '?') · merge-base 이후)"; return 0
}

git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || abort "not-a-repo" "git 저장소가 아니다: $ROOT"
HEAD_SHA="$(git -C "$ROOT" rev-parse --verify --quiet "HEAD^{commit}")" || abort "no-head" "HEAD 를 못 읽었다"
# ★ref 존재와 merge-base 실패는 **다른 사건**이다 (F1). 종전처럼 둘 다 "" 로 뭉개면 초록이 샌다.
#   ref 이름이 아니라 `refs/remotes/origin/main` 을 명시한다 — `origin/main` 은 로컬 브랜치와 모호할 수 있다.
MB_REF="$(git -C "$ROOT" rev-parse --verify --quiet refs/remotes/origin/main)" || MB_REF=""
MERGE_BASE=""
if [ -z "$MB_REF" ]; then
  echo "warn: refs/remotes/origin/main 이 없다 — 축약 판정으로 내려간다 (no-origin-main)" >&2
else
  MERGE_BASE="$(git -C "$ROOT" merge-base "$MB_REF" "$HEAD_SHA" 2>/dev/null)"; mb_rc=$?
  if [ "$mb_rc" -ne 0 ] || [ -z "$MERGE_BASE" ]; then                        # ← 앵커 A14
    abort "git-error" "origin/main 은 있는데 merge-base 가 실패했다 (rc=$mb_rc) — 무관 이력·shallow clone·객체 손상. 판정을 포기한다"
  fi
fi

[ -e "$SIGNAL_FILE" ] || { CODE="file";  WHY="신호 파일이 없다: $SIGNAL_FILE";     finish 1 "missing" ""; }
[ -s "$SIGNAL_FILE" ] || { CODE="empty"; WHY="신호 파일이 비어 있다: $SIGNAL_FILE"; finish 1 "missing" ""; }

FIRST_LINE="$(head -n 1 "$SIGNAL_FILE" | tr -d '\r')"                        # ← 앵커 A6 (M5·M8)
SHA_RAW="$(printf '%s\n' "$FIRST_LINE" | sed -n 's/^[[:blank:]]*commit:[[:blank:]]*\([^[:blank:]]*\)[[:blank:]]*$/\1/p')"
# ★[[:blank:]] 다. [[:space:]] 로 쓰면 CR 을 sed 가 삼켜 `tr -d '\r'` 이 **등가 코드**가 된다(실측 §0-4).
if [ -z "$SHA_RAW" ]; then CODE="commit-line"; WHY="첫 줄이 'commit: <sha>' 가 아니다"; finish 1 "missing" ""; fi
  if ! printf '%s' "$SHA_RAW" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then           # ← 앵커 A7
  CODE="sha-format"; WHY="16진 sha(7~40자)가 아니다: $SHA_RAW — 'HEAD' 같은 심볼릭 ref 는 안 된다"
  finish 1 "invalid" ""
fi
FULL_SHA="$(git -C "$ROOT" rev-parse --verify --quiet "${SHA_RAW}^{commit}")" || FULL_SHA=""
[ -n "$FULL_SHA" ] || { CODE="unknown-sha"; WHY="이 저장소에 없는 커밋(또는 모호한 축약): $SHA_RAW"; finish 1 "invalid" ""; }

judge_freshness "$FULL_SHA"; frc=$?
case "$frc" in
  0) finish 0 "signal" "${FULL_SHA:0:8}" ;;
  3) abort "$CODE" "$WHY" ;;
  *) finish 1 "stale"  "${FULL_SHA:0:8}" ;;
esac
