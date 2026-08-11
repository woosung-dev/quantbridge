#!/usr/bin/env bash
# signal-check — 스킬 게이트 신호의 **신선도** 판정. ([BL-706])
set -uo pipefail

usage() {
  echo "사용법: $0 --run <run> <signal-file-name> | $0 -h|--help" >&2
}

if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
  printf '%s\n' "사용법: $0 --run <run> <signal-file-name> | $0 -h|--help"
  exit 0
fi

if [ "$#" -ne 3 ] || [ "$1" != "--run" ]; then
  usage
  exit 2
fi

RUN="$2"
NAME="$3"
case "$RUN" in
  ""|*..*|*[!A-Za-z0-9._-]*) usage; exit 2 ;;
esac
case "$NAME" in
  ""|*..*|*[!A-Za-z0-9._-]*) usage; exit 2 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
if [ -n "${QB_SIGNAL_ROOT:-}" ]; then
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

[ -e "$SIGNAL_FILE" ] || { CODE="file";  WHY="신호 파일이 없다: $SIGNAL_FILE";     finish 1 "missing" ""; }
[ -s "$SIGNAL_FILE" ] || { CODE="empty"; WHY="신호 파일이 비어 있다: $SIGNAL_FILE"; finish 1 "missing" ""; }

CODE="size"; WHY="비어 있지 않다 — 크기만 봤다(1단계 추출)"
finish 0 "signal" ""
