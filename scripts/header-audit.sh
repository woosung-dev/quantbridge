#!/usr/bin/env bash
# header-audit — 소스 파일 첫 3줄 안에 "한국어 주석"이 있는지 감사한다. [BL-307]
#
# 무엇을 재는가
#   대상: `backend/src/**/*.py` · `frontend/src/**/*.{ts,tsx}` (다른 확장자는 대상 아님).
#   위반: 파일 첫 3줄 안, **주석/독스트링 영역**에 한글(`[가-힣]`)이 1자 이상 없다.
#   근거: 루트 `AGENTS.md:23` (「사고/계획/대화/문서/주석 = 한국어」).
#
# ★핵심 — 한글 "존재" 검사가 아니라 한글 "주석" 검사다.
#   `MESSAGE = "백테스트 실패"` 처럼 한글이 문자열 리터럴에만 있으면 그건 위반이다.
#   그래서 각 줄이 주석/독스트링 **시작 토큰**(py: `#` `"""` `'''` / ts·tsx: `//` `/*`)으로
#   시작할 때만 그 줄(또는 블록 주석·독스트링이 열린 뒤 이어지는 줄)을 검사 대상으로 본다.
#   코드 줄은 절대 들여다보지 않는다 — `head -3 | grep '[가-힣]'` 로 짜면 이 구분이 사라진다.
#
# 면제 (검사 대상에서 제외, `docs/backlog.md` BL-307 원장의 exempt list)
#   경로에 `/tests/`·`/__tests__/`·`config`·`/generated/` 포함, 또는
#   파일명이 `test_*.py`·`*_test.py`·`conftest.py`·`*.test.ts(x)`·`*.spec.ts(x)`·
#   `__init__.py`·`index.ts`·`index.tsx`·`*.d.ts`·`*.generated.*`.
#
# 종료 코드: 위반 0건 → 0 / 1건 이상 → 1.
# 인자: 없음 = 사람이 읽는 요약 + 위반 경로. `--list` = 위반 경로만 한 줄에 하나씩(그 외 출력 없음).
#
# ★이 레포 실측 함정
#   - zsh/bash 단어분할: 파일 목록은 배열 + `find -print0` + `while IFS= read -r -d ''` 로만 돈다.
#   - 경로에 공백·괄호가 있다 (`frontend/src/app/(dashboard)/...`) — 전부 배열/인용으로 다룬다.
#   - 파이프가 `$?` 를 가린다 — 종료 코드 판정에 파이프를 끼우지 않는다.
#   - macOS 기본 `bash` 는 3.2 다. `set -u` + 빈 배열 `"${arr[@]}"` 전개는 3.2 에서 unbound
#     variable 로 죽는다(4.4 에서 고쳐진 버그) — `"${arr[@]+"${arr[@]}"}"` 가드로 우회한다.
#
# 사용법: scripts/header-audit.sh [--list]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

# ── 판별력 자기검사 ──────────────────────────────────────────────
# ★이 감사기의 전부는 `grep '[가-힣]'` 한 줄에 걸려 있다. 그런데 그 범위가 제대로 도는지는
#   **로케일에 달렸다.** CI 러너(리눅스 GNU grep)와 개발 머신(macOS BSD grep)이 다르고,
#   `LC_ALL=C` 로 떨어지면 멀티바이트 범위가 바이트로 해석될 수 있다.
#   ⇒ 깨진 환경에서 이 스크립트는 **모든 파일을 「한글 없음」으로 읽어 전건 위반**을 내거나,
#     반대로 아무거나 매치해 **전건 통과**를 낸다. 둘 다 조용하다.
#   그래서 매 실행마다 양성·음성 한 쌍으로 판별력을 먼저 확인하고, 안 되면 **판정하지 않는다.**
#   (판정할 수 없을 때 초록을 내는 것이 이 레포가 반복해 밟은 함정이다.)
if ! printf '한' | grep -q '[가-힣]' || printf 'a' | grep -q '[가-힣]'; then
  echo "✗ 이 환경의 grep 이 한글 범위 '[가-힣]' 를 판별하지 못한다 (로케일: LANG=${LANG:-unset} LC_ALL=${LC_ALL:-unset})." >&2
  echo "  판정을 포기한다 — 초록을 내면 거짓 통과가 된다. UTF-8 로케일에서 다시 실행해라." >&2
  exit 3
fi

LIST=0
case "${1:-}" in
  "") ;;
  --list) LIST=1 ;;
  *) echo "알 수 없는 인자: $1 (지원: --list)" >&2; exit 1 ;;
esac

# ── 면제 판정 ────────────────────────────────────────────────────
# rel = ROOT 기준 상대경로. 경로 부분 문자열 검사와 파일명(basename) 검사를 나눈다.
is_exempt() {
  local rel="$1" base="${1##*/}"
  case "$rel" in
    */tests/*|*/__tests__/*|*config*|*/generated/*) return 0 ;;
  esac
  case "$base" in
    test_*.py|*_test.py|conftest.py) return 0 ;;
    *.test.ts|*.test.tsx|*.spec.ts|*.spec.tsx) return 0 ;;
    __init__.py|index.ts|index.tsx) return 0 ;;
    *.d.ts) return 0 ;;
    *.generated.*) return 0 ;;
  esac
  return 1
}

# ── 헤더 판정 ────────────────────────────────────────────────────
# 첫 3줄을 순서대로 읽는다. 블록 주석/독스트링이 열려 있으면 그 줄 전체가 주석 영역이고
# (⑦ — 본문 줄도 통과 대상), 아니면 그 줄이 주석 시작 토큰으로 시작할 때만 검사한다(⑨ 방어).
# 한글을 찾으면 즉시 0(발견)을 반환하고, 첫 3줄을 다 봐도 없으면 1(미발견)을 반환한다.
has_korean_header() {
  local file="$1" lineno=0 line trimmed rest before q
  local in_block=0 block_end=""
  while [ "$lineno" -lt 3 ] && IFS= read -r line; do
    lineno=$((lineno + 1))

    if [ "$in_block" -eq 1 ]; then
      if [[ "$line" == *"$block_end"* ]]; then
        before="${line%%"$block_end"*}"
        printf '%s' "$before" | grep -q '[가-힣]' && return 0
        in_block=0
      else
        printf '%s' "$line" | grep -q '[가-힣]' && return 0
      fi
      continue
    fi

    # 선행 공백 제거 (순수 bash 관용구 — 서브프로세스 없음)
    trimmed="${line#"${line%%[![:space:]]*}"}"

    if [[ "$trimmed" == '#'* ]]; then
      printf '%s' "$trimmed" | grep -q '[가-힣]' && return 0
    elif [[ "$trimmed" == '"""'* || "$trimmed" == "'''"* ]]; then
      q="${trimmed:0:3}"; rest="${trimmed:3}"
      if [[ "$rest" == *"$q"* ]]; then
        before="${rest%%"$q"*}"
        printf '%s' "$before" | grep -q '[가-힣]' && return 0
      else
        printf '%s' "$rest" | grep -q '[가-힣]' && return 0
        in_block=1; block_end="$q"
      fi
    elif [[ "$trimmed" == '//'* ]]; then
      printf '%s' "$trimmed" | grep -q '[가-힣]' && return 0
    elif [[ "$trimmed" == '/*'* ]]; then
      rest="${trimmed:2}"
      if [[ "$rest" == *'*/'* ]]; then
        before="${rest%%\*/*}"
        printf '%s' "$before" | grep -q '[가-힣]' && return 0
      else
        printf '%s' "$rest" | grep -q '[가-힣]' && return 0
        in_block=1; block_end='*/'
      fi
    fi
    # 그 외는 코드 줄 — 문자열 리터럴 안 한글은 여기서 절대 보지 않는다.
  done < "$file"
  return 1
}

# ── 대상 수집 ────────────────────────────────────────────────────
be_files=()
while IFS= read -r -d '' f; do be_files+=("$f"); done \
  < <(find "$ROOT/backend/src" -type f -name '*.py' -print0 2>/dev/null)
fe_files=()
while IFS= read -r -d '' f; do fe_files+=("$f"); done \
  < <(find "$ROOT/frontend/src" \( -type f -name '*.ts' -o -type f -name '*.tsx' \) -print0 2>/dev/null)

total_be=${#be_files[@]}
total_fe=${#fe_files[@]}
total=$((total_be + total_fe))

violations=()
checked=0
exempted=0

for f in "${be_files[@]+"${be_files[@]}"}" "${fe_files[@]+"${fe_files[@]}"}"; do
  rel="${f#"$ROOT"/}"
  if is_exempt "$rel"; then
    exempted=$((exempted + 1))
    continue
  fi
  checked=$((checked + 1))
  has_korean_header "$f" || violations+=("$rel")
done

n_violations=${#violations[@]}

# ── 출력 ─────────────────────────────────────────────────────────
if [ "$LIST" -eq 1 ]; then
  for v in "${violations[@]+"${violations[@]}"}"; do printf '%s\n' "$v"; done
else
  printf '══ header-audit  root=%s ══\n' "$ROOT"
  printf '  대상: backend/src/**/*.py + frontend/src/**/*.{ts,tsx}\n'
  printf '  스캔 %d건 (BE .py %d + FE .ts/.tsx %d) · 면제 %d건 · 검사 %d건\n' \
    "$total" "$total_be" "$total_fe" "$exempted" "$checked"
  if [ "$total" -eq 0 ]; then
    printf '  ⚠ 대상 확장자 파일이 0건이다 — ROOT 판정이 잘못됐을 수 있다 (ROOT=%s)\n' "$ROOT"
  fi
  printf '\n▶ 위반 — 첫 3줄에 한국어 주석 없음 (%d건)\n' "$n_violations"
  if [ "$n_violations" -eq 0 ]; then
    printf '  없음\n'
  else
    for v in "${violations[@]+"${violations[@]}"}"; do printf '  %s\n' "$v"; done
  fi
  echo
  if [ "$n_violations" -eq 0 ]; then
    printf '✓ 위반 0건\n'
  else
    printf '✗ 위반 %d건\n' "$n_violations"
  fi
fi

[ "$n_violations" -eq 0 ] && exit 0
exit 1
