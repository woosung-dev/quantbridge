#!/usr/bin/env bash
# signal-check 판별력 하네스 — [BL-706]. 전건 통과 = 종료 코드 0.
#
# ★이 파일은 수리보다 **먼저** 쓰였다(G1 수용 기준 동결 — skip-ratchet-test.sh 와 같은 규율).
#   1단계(행위 불변 추출 = 판정이 `[ -s ]` 뿐)에 대고 돌리면 **정확히 16건이 red** 여야 한다:
#   ③④⑦⑨⑩⑪⑫⑬⑭⑮⑲⑳㉒㉓㉔㉕. 전건 red 면 추출이 틀린 것(재현이 아니라 위장)이고,
#   green 이 12건 이상이면 케이스가 무디다. ⑬ 의 red 사유는 rc 가 아니라 **경고 부재**다.
#   (케이스 ㉔㉕·⑩ 형태·앵커는 G1 직후 codex 플랜 검증 F1~F5·H1~H9 를 채택해 개정했다 —
#    특히 ㉕ 는 [치명적] F1(merge-base 실패가 초록으로 새는 경로) 수리의 유일한 증인이다.)
#
# ★정직한 한계 하나 더 (H9) — ㉑㉒㉓ 의 wire 스텁은 ROOT 에 **실 레포**를 넘긴다. 그래서
#   안내문의 `git rev-parse HEAD` 와 「신호 파일:」 경로는 실 레포 것으로 찍히고, ㉒ 는 문구
#   존재만 보므로 **경로 조립 오류는 못 잡는다** — 그것은 G4 의 실물 대조 2회가 잡는다.
#
# 무엇을 재는가 — 신호 **신선도** 판정(scripts/signal-check.sh)과 check_signal 배선이다.
#   fixture = 임시 git 저장소 4벌(브랜치 지형·merge-base==HEAD·origin/main 부재·비저장소).
#   본체 케이스 ③ = 「낡은 신호(origin/main 에 이미 있는 sha, 파일은 비어 있지 않음)」 —
#   구 판정 `[ -s ]` 가 PASS 하던 바로 그 형상이다(2026-08-11 실측: eod/ 4종 전부 남의 회차).
#
# ★안 덮는 것 (정직한 회계 — skip-ratchet-test.sh:24-25 와 같은 헤더 규율):
#   · 기본 ROOT 파생(`dirname $0/..`) — final-gates.sh 의 실물 실행이 매번 덮는다
#   · 빈 저장소(커밋 0개 → abort[no-head]) · git 자체 실패(is-ancestor rc>1 → abort[git-error])
#   · final-gates.sh 게이트 체인 전체 경로 — G4 의 실물 대조 2회가 정본 증거다
#
# ★이 하네스가 final-gates.sh 를 부르고(케이스 ⑩) final-gates.sh 가 이 하네스를 부른다 —
#   재귀가 아니다: 내부 호출은 `--run eod` 인자 검증에서 즉사한다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (pipefail 없는 셸에서 `| tail` 이 $? 를
#   가린 실측 사고 이력 — pipefail 하에서는 보존되지만 규율은 유지한다).
#
# 사용법: scripts/signal-check-test.sh            # 25케이스 (상시 — final-gates 가 돌린다)
#         scripts/signal-check-test.sh --mutants  # + 변이 M1~M10 · 음성 대조 N1~N3 (G4 에서 1회)

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
CHECK="$ROOT/scripts/signal-check.sh"
GATES="$ROOT/scripts/final-gates.sh"
[ -f "$CHECK" ] || { echo "✗ 판정 스크립트가 없다: $CHECK" >&2; exit 1; }
[ -f "$GATES" ] || { echo "✗ final-gates.sh 가 없다: $GATES" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "✗ git 이 없다 — 판정을 포기한다." >&2; exit 3; }
command -v python3 >/dev/null 2>&1 || { echo "✗ python3 가 없다 — fixture 를 만들 수 없다." >&2; exit 3; }
command -v shasum >/dev/null 2>&1 || { echo "✗ shasum 이 없다 — 원본 오염 감시(P4)를 세울 수 없다." >&2; exit 3; }

MODE="${1:-}"

TMP="$(mktemp -d)"
# P4 — 원본 오염 감시. 변이는 사본에만 심는다.
SUM_BEFORE="$(shasum -a 256 "$CHECK" "$GATES")"
[ -n "$SUM_BEFORE" ] || { echo "✗ 원본 sha256 을 못 얻었다 — P4 를 세울 수 없다." >&2; rm -rf "$TMP"; exit 3; }
finish_trap() {
  local rc=$?
  rm -rf "$TMP"
  local after
  after="$(shasum -a 256 "$CHECK" "$GATES")"
  if [ "$after" != "$SUM_BEFORE" ]; then
    echo "✗✗ 원본이 실행 중 바뀌었다 — 변이가 샜다. 수동 복구가 필요하다." >&2
    exit 3
  fi
  exit "$rc"
}
trap finish_trap EXIT

# fixture git 을 사용자 전역 설정에서 격리한다 (gpgsign·hooksPath·defaultBranch).
# ★상속된 GIT_DIR 하나가 P2 를 거짓 초록으로 만든다 — 리다이렉션 env 도 전부 걷어낸다 (F10).
export HOME="$TMP/home"
mkdir -p "$HOME"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=qb GIT_AUTHOR_EMAIL=qb@example.invalid
export GIT_COMMITTER_NAME=qb GIT_COMMITTER_EMAIL=qb@example.invalid
# ★GIT_CONFIG_GLOBAL 은 HOME 재정의를 통째로 무력화한다 (H4) — 리다이렉션 env 전량을 걷는다.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_CEILING_DIRECTORIES \
  GIT_CONFIG_GLOBAL GIT_CONFIG GIT_CONFIG_SYSTEM GIT_TEMPLATE_DIR GIT_NAMESPACE GIT_ALTERNATE_OBJECT_DIRECTORIES \
  2>/dev/null || true

# P2 — TMPDIR 이 어떤 저장소 안이면 케이스 ⑨ 가 거짓 초록이 된다.
if git -C "$TMP" rev-parse --git-dir >/dev/null 2>&1; then
  echo "✗ TMPDIR($TMP) 이 git 저장소 안이다 — 케이스 ⑨ 를 잴 수 없다." >&2
  exit 3
fi

# ── fixture 지형 ──────────────────────────────────────────────────
# repo:        c1─c2─c3─c4 (branch work, HEAD=c4) · sibling 브랜치에 c5(c2 의 자식) · origin/main=c2
# repo-mbhead: 같은 지형, origin/main=c4  (merge-base == HEAD — 경계 (b))
# repo-noorig: 같은 지형, origin/main 없음 (경계 (a))
# norepo:      git 아닌 평범한 디렉터리
build_repo() { # build_repo <dir> → C1..C5 전역
  local d="$1"
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" symbolic-ref HEAD refs/heads/work
  git -C "$d" -c commit.gpgsign=false commit -q --allow-empty -m c1; C1="$(git -C "$d" rev-parse HEAD)"
  git -C "$d" -c commit.gpgsign=false commit -q --allow-empty -m c2; C2="$(git -C "$d" rev-parse HEAD)"
  git -C "$d" -c commit.gpgsign=false commit -q --allow-empty -m c3; C3="$(git -C "$d" rev-parse HEAD)"
  git -C "$d" -c commit.gpgsign=false commit -q --allow-empty -m c4; C4="$(git -C "$d" rev-parse HEAD)"
  # c5 = c2 의 자식, HEAD 조상 아님. checkout 없이 commit-tree 로 만들고 브랜치로 살려 둔다(gc 방지).
  C5="$(git -C "$d" commit-tree "${C2}^{tree}" -p "$C2" -m c5)"
  git -C "$d" branch -q sibling "$C5"
  mkdir -p "$d/.claude/gates/t-run"
}

build_repo "$TMP/repo";        A_C2="$C2"; A_C3="$C3"; A_C4="$C4"; A_C5="$C5"
git -C "$TMP/repo" update-ref refs/remotes/origin/main "$A_C2"
build_repo "$TMP/repo-mbhead"; B_C4="$C4"
git -C "$TMP/repo-mbhead" update-ref refs/remotes/origin/main "$B_C4"
build_repo "$TMP/repo-noorig"; N_C3="$C3"; N_C4="$C4"
# repo-unrel — origin/main 이 **무관 이력**(orphan)이다: ref 존재 + merge-base rc=1 + 빈 출력.
# F1 [치명적](merge-base 실패가 no-origin-main 으로 뭉개져 초록)의 유일한 fixture 다 (케이스 ㉕).
build_repo "$TMP/repo-unrel";  U_C1="$C1"; U_C4="$C4"
ORPH="$(git -C "$TMP/repo-unrel" commit-tree "${U_C1}^{tree}" -m orphan)"
git -C "$TMP/repo-unrel" update-ref refs/remotes/origin/main "$ORPH"
mkdir -p "$TMP/norepo/.claude/gates/t-run"

# P3 — 지형 대조. fixture 가 깨지면 ③⑲ 가 엉뚱한 이유로 통과한다.
# ★is-ancestor 는 rc=128 이 에러다 — 「조상 아님(rc=1)」과 구분해서 재야 미상 sha 가 안 샌다 (F7).
p3_fail() { echo "✗ fixture 지형이 어긋났다: $1" >&2; exit 3; }
p3_rc=0
[ "$A_C2" != "$A_C4" ] || p3_fail "c2 == c4"
git -C "$TMP/repo" rev-parse --verify --quiet "${A_C5}^{commit}" >/dev/null || p3_fail "c5 를 resolve 못 한다"
[ "$(git -C "$TMP/repo" merge-base origin/main HEAD)" = "$A_C2" ] || p3_fail "merge-base != c2"
git -C "$TMP/repo" merge-base --is-ancestor "$A_C3" HEAD; p3_rc=$?
[ "$p3_rc" -eq 0 ] || p3_fail "c3 HEAD 조상 판정 rc=$p3_rc (기대 0)"
git -C "$TMP/repo" merge-base --is-ancestor "$A_C3" "$A_C2"; p3_rc=$?
[ "$p3_rc" -eq 1 ] || p3_fail "c3-in-c2 판정 rc=$p3_rc (기대 1 = 조상 아님)"
git -C "$TMP/repo" merge-base --is-ancestor "$A_C5" HEAD; p3_rc=$?
[ "$p3_rc" -eq 1 ] || p3_fail "c5-in-HEAD 판정 rc=$p3_rc (기대 1 = 조상 아님)"
# P3′ — 나머지 3벌 (H5). F1 이후 ⓐ/ⓑ 갈래가 ref 존재 여부에 걸리므로 전제를 재야 ⑬⑭㉕ 가 유효하다.
[ "$(git -C "$TMP/repo-mbhead" merge-base origin/main HEAD)" = "$B_C4" ] || p3_fail "mbhead: mb != HEAD"
git -C "$TMP/repo-noorig" rev-parse --verify --quiet refs/remotes/origin/main >/dev/null && p3_fail "noorig 에 origin/main 이 있다"
git -C "$TMP/repo-unrel" rev-parse --verify --quiet refs/remotes/origin/main >/dev/null || p3_fail "unrel 에 origin/main 이 없다"
git -C "$TMP/repo-unrel" merge-base refs/remotes/origin/main HEAD >/dev/null 2>&1; p3_rc=$?
[ "$p3_rc" -eq 1 ] || p3_fail "unrel merge-base rc=$p3_rc (기대 1 = 무관 이력)"

# ── 러너 ──────────────────────────────────────────────────────────
CHECK_BIN="$CHECK"   # 변이 모드에서 사본으로 바뀐다
ARGPARSE_SRC=""      # 변이 M7 전용 — 채워지면 케이스 ⑩ 이 prologue 추출본을 돈다
QUIET=0
PASS=0; FAIL=0; RED_IDS=""

run_sig() { # run_sig <tree> <이름 또는 원시 인자...>  — stdout=OUT / stderr=ERR / rc=RC. 파이프 없음.
  local tree="$1"; shift
  OUT="$(QB_SIGNAL_ROOT="$tree" bash "$CHECK_BIN" "$@" 2>"$TMP/err")"
  RC=$?
  ERR="$(cat "$TMP/err")"
}

sig() { # sig <tree> <본문...>  — t-run/g9.ok 에 신호 파일을 쓴다
  local tree="$1"; shift
  printf '%s\n' "$@" >"$tree/.claude/gates/t-run/g9.ok"
}

has() { printf '%s\n' "$OUT" | grep -qF "$1"; }
has_err() { printf '%s\n' "$ERR" | grep -qF "$1"; }

report() { # report <id> <label> <why(빈 문자열이면 통과)>
  if [ -n "$3" ]; then
    FAIL=$((FAIL + 1)); RED_IDS="$RED_IDS$1"
    if [ "$QUIET" -eq 0 ]; then
      printf '  ✗ %s %-50s %s\n' "$1" "$2" "$3"
      printf '%s\n' "$OUT" | sed 's/^/        | /'
    fi
  else
    PASS=$((PASS + 1))
    [ "$QUIET" -eq 0 ] && printf '  ✓ %s %-50s\n' "$1" "$2"
  fi
}

# check_signal 배선 스텁 — record/skip_gate 를 가짜로 두고 추출된 check_signal 만 실행한다.
cat >"$TMP/wire.sh" <<'WIRE'
#!/usr/bin/env bash
# check_signal 배선 시험용 스텁 — signal-check-test.sh 가 생성. (하네스 케이스 ㉑㉒㉓)
set -u
ROOT="$1"; RUN="$2"; REQ="$3"; NAME="$4"; CS="$5"
record()    { printf 'REC|%s|%s|%s\n' "$1" "$2" "$3"; }
skip_gate() { printf 'SKIP|%s|%s\n' "$1" "$2"; }
. "$CS"
check_signal "테스트게이트" "$NAME" "$REQ" "fe diff 0"
WIRE

run_wire() { # run_wire <tree> <req 0|1>  — 추출된 check_signal 을 스텁 위에서 돈다
  sed -n '/^check_signal() {/,/^}/p' "$GATES" >"$TMP/cs.sh"
  if ! grep -qF 'check_signal()' "$TMP/cs.sh"; then
    OUT="check_signal 추출 실패 — final-gates.sh 형태가 바뀌었다"; RC=9; ERR=""; return
  fi
  OUT="$(QB_SIGNAL_ROOT="$1" bash "$TMP/wire.sh" "$ROOT" t-run "$2" g9.ok "$TMP/cs.sh" 2>"$TMP/err")"
  RC=$?
  ERR="$(cat "$TMP/err")"
}

# ── 케이스 23건 (번호·기대값 = G1 동결 §2.3 그대로) ────────────────
run_suite() {
  PASS=0; FAIL=0; RED_IDS=""
  local why rec_line

  # ① 신선 sha == HEAD — 양성 대조: 수리가 정상 신호를 죽이지 않는다
  sig "$TMP/repo" "commit: $A_C4" "화면 검증 근거 본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && ! has "signal:" && why="stdout 에 signal: 토큰이 없다"
  report "①" "신선 sha==HEAD → rc0 signal:" "$why"

  # ② 신선 = 브랜치 중간 커밋 — 신호 뒤에 커밋을 더 해도 살아야 한다
  sig "$TMP/repo" "commit: $A_C3" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && ! has "signal:" && why="signal: 토큰이 없다"
  report "②" "신선 브랜치 중간 커밋 → rc0" "$why"

  # ③ ★본체 — sha ∈ origin/main + 비어 있지 않은 파일(미끼 20줄). 구 판정은 PASS 했다.
  {
    printf 'commit: %s\n' "$A_C2"
    for i in $(seq 1 20); do printf '앞 회차가 남긴 산문 근거 %d줄 — 크기 판정은 이걸 초록으로 삼켰다\n' "$i"; done
  } >"$TMP/repo/.claude/gates/t-run/g9.ok"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — ★남의 회차 신호가 통과했다"
  [ -z "$why" ] && ! has "[origin-main]" && why="[origin-main] 코드가 없다"
  report "③" "★낡음 sha∈origin/main → rc1 [origin-main]" "$why"

  # ④ commit 줄 없음 — 현 eod 파일 형식이 그대로 떨어진다
  sig "$TMP/repo" "# G9 — 계획 vs 실제 구현 (2026-08-11 ledger-truth)" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
  [ -z "$why" ] && ! has "[commit-line]" && why="[commit-line] 코드가 없다"
  report "④" "commit 줄 없음(현 eod 형식) → rc1" "$why"

  # ⑤ 파일 없음 — 종전 FAIL 유지(회귀 방지)
  rm -f "$TMP/repo/.claude/gates/t-run/g9.ok"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
  [ -z "$why" ] && ! has "[file]" && why="[file] 코드가 없다"
  report "⑤" "파일 없음 → rc1 [file]" "$why"

  # ⑥ 빈 파일 — 「없음」과 「빔」은 사람에게 다른 행동을 시킨다
  : >"$TMP/repo/.claude/gates/t-run/g9.ok"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
  [ -z "$why" ] && ! has "[empty]" && why="[empty] 코드가 없다"
  report "⑥" "빈 파일 → rc1 [empty]" "$why"

  # ⑦ 미상 sha — resolve 실패를 초록으로 삼키지 않는다
  sig "$TMP/repo" "commit: 0123456789012345678901234567890123456789" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1)"
  [ -z "$why" ] && ! has "[unknown-sha]" && why="[unknown-sha] 코드가 없다"
  report "⑦" "미상 sha → rc1 [unknown-sha]" "$why"

  # ⑧ 축약 sha 7자 — 문자열 비교가 아니라 rev-parse 로 푸는가
  sig "$TMP/repo" "commit: ${A_C4:0:7}" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && ! has "signal:" && why="signal: 토큰이 없다"
  report "⑧" "축약 sha 7자 신선 → rc0" "$why"

  # ⑨ git 저장소 아님 — 초록도 낡음도 아닌 rc=3
  sig "$TMP/norepo" "commit: $A_C4" "본문"
  run_sig "$TMP/norepo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — 판정 불가가 다른 것으로 위장됐다"
  [ -z "$why" ] && ! has "[not-a-repo]" && why="[not-a-repo] 코드가 없다"
  report "⑨" "git 저장소 아님 → rc3 [not-a-repo]" "$why"

  # ⑩ final-gates --run eod — 입구 거부. ★실물 체인을 돌리지 않도록 prologue(ROOT= 이전)만
  #   추출해 돈다 — 실물 경로엔 DB drop/create 가 있다 (F4). 거부가 ROOT= 아래로 내려가면
  #   추출본에서 빠져 rc 0 → red = 위치 집행. 실물 전체 경로는 §6-4 실물 대조가 정본 증거다.
  #   임의의 조기 실패를 정답으로 세지 않도록 거부 사유 문구까지 잰다 (F3).
  local eod_src="${ARGPARSE_SRC:-$GATES}"
  if ! grep -qF 'ROOT="' "$eod_src"; then
    OUT="prologue 앵커(ROOT=)를 못 찾았다"; RC=9
  else
    sed '/^ROOT="/,$d' "$eod_src" >"$TMP/argparse.sh"
    OUT="$(bash "$TMP/argparse.sh" --run eod 2>&1)"; RC=$?
  fi
  why=""
  [ "$RC" -ne 0 ] || why="rc=0 — eod 가 거부되지 않았다"
  [ -z "$why" ] && ! has "eod 는 금지다" && why="거부 사유 문구가 없다 — 임의의 조기 실패는 정답이 아니다"
  [ -z "$why" ] && has "══ final-gates" && why="헤더가 찍혔다 — 거부가 인자 검증보다 아래에 있다"
  report "⑩" "--run eod 즉시 거부(prologue 추출) → rc≠0" "$why"

  # ⑪ commit: HEAD 리터럴 — 안내문이 rev-parse 를 포함하므로 리터럴 붙여넣기는 예정된 사건
  sig "$TMP/repo" "commit: HEAD" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — 심볼릭 ref 가 통과했다"
  [ -z "$why" ] && ! has "[sha-format]" && why="[sha-format] 코드가 없다"
  report "⑪" "commit: HEAD 리터럴 → rc1 [sha-format]" "$why"

  # ⑫ 경계(b) merge-base == HEAD — FF 머지 뒤 앞 회차 신호가 HEAD 를 가리킬 수 있다
  sig "$TMP/repo-mbhead" "commit: $B_C4" "본문"
  run_sig "$TMP/repo-mbhead" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — 브랜치 커밋 0개인데 통과했다"
  [ -z "$why" ] && ! has "[no-branch-commits]" && why="[no-branch-commits] 코드가 없다"
  report "⑫" "경계(b) mb==HEAD → rc1 [no-branch-commits]" "$why"

  # ⑬ 경계(a) origin/main 부재 + sha==HEAD — 축약 판정으로 내려가되 **소리 내는가**
  sig "$TMP/repo-noorig" "commit: $N_C4" "본문"
  run_sig "$TMP/repo-noorig" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && ! has "signal:" && why="signal: 토큰이 없다"
  [ -z "$why" ] && ! has_err "no-origin-main" && why="★경고 부재 — rc 는 맞지만 조용한 축약이다 (red 사유는 rc 가 아니라 이것)"
  report "⑬" "경계(a) noorig+HEAD → rc0 + stderr 경고" "$why"

  # ⑭ 경계(a) 의 엄격 축 — fallback 이 느슨해지지 않았는가
  sig "$TMP/repo-noorig" "commit: $N_C3" "본문"
  run_sig "$TMP/repo-noorig" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — 축약 판정이 조상까지 통과시켰다"
  [ -z "$why" ] && ! has "[no-origin-main]" && why="[no-origin-main] 코드가 없다"
  report "⑭" "경계(a) noorig+조상 → rc1 [no-origin-main]" "$why"

  # ⑮ commit 줄이 첫 줄이 아님 — 파일 전체 grep 구현 차단(독스트링 인용 함정과 동류)
  sig "$TMP/repo" "부검 산문 첫 줄" "둘째 줄" "commit: $A_C4"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — 3줄째 commit 이 근거가 됐다"
  [ -z "$why" ] && ! has "[commit-line]" && why="[commit-line] 코드가 없다"
  report "⑮" "commit 줄이 3줄째 → rc1 (첫 줄만 본다)" "$why"

  # ⑯ CRLF 첫 줄 — CR 이 붙으면 신선한 신호가 낡음으로 오판돼 사람이 게이트를 우회한다
  printf 'commit: %s\r\n본문\n' "$A_C4" >"$TMP/repo/.claude/gates/t-run/g9.ok"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0) — CR 하나에 신선이 죽었다"
  [ -z "$why" ] && ! has "signal:" && why="signal: 토큰이 없다"
  report "⑯" "CRLF 첫 줄 신선 → rc0" "$why"

  # ⑰ QB_SIGNAL_ROOT 고지 — 셸에 남은 export 하나가 판정 대상을 조용히 바꾼다
  sig "$TMP/repo" "commit: $A_C4" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && ! has_err "QB_SIGNAL_ROOT" && why="stderr 에 재정의 고지가 없다"
  [ -z "$why" ] && ! has_err "$TMP/repo" && why="고지에 대상 트리 경로가 없다"
  report "⑰" "QB_SIGNAL_ROOT 재정의 고지(stderr)" "$why"

  # ⑱ 사용법 오류 — 「잘못 불렀다」(rc2)와 「낡았다」(rc1)를 분리한다. 경로 탈출 이름도 rc2 (F11).
  run_sig "$TMP/repo" --bogus g9.ok
  why=""
  [ "$RC" -eq 2 ] || why="rc=$RC (기대 2)"
  [ -z "$why" ] && [ -n "$OUT" ] && why="사용법 오류인데 stdout 이 침묵하지 않았다: $OUT"
  if [ -z "$why" ]; then
    run_sig "$TMP/repo" --run t-run "../escape.ok"
    [ "$RC" -eq 2 ] || why="경로 탈출 이름이 rc=2 가 아니다 (rc=$RC)"
  fi
  report "⑱" "모르는 플래그·경로 탈출 이름 → rc2" "$why"

  # ⑲ HEAD 조상 아님(형제/amend) — 신호 뒤 --amend 하면 sha 는 살고 트리는 다르다
  sig "$TMP/repo" "commit: $A_C5" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 1 ] || why="rc=$RC (기대 1) — 형제 브랜치 커밋이 통과했다"
  [ -z "$why" ] && ! has "[not-ancestor]" && why="[not-ancestor] 코드가 없다"
  report "⑲" "형제 브랜치 sha → rc1 [not-ancestor]" "$why"

  # ⑳ 변이·배선 앵커 14종이 규정 횟수로 원본에 존재 — 이름이 바뀌면 §3 변이가 조용히 무증거가
  #   되고, 배선(호출부·run_gate·Makefile)이 사라지면 고아 하네스가 된다 (F2 — 텍스트 앵커로 집행,
  #   행위 증거는 §6-4 실물 대조가 맡는다). ★A12 는 `check_signal "` **x4** — 특정 1줄만 세면
  #   나머지 3 호출을 지워도 초록이다 (H2). ★A13 은 순서 결합 false red 를 피해 regex 다 (H6).
  # ★heredoc 을 $( ) **안에 두지 마라** — /bin/bash 3.2 는 명령 치환 안의 quoted heredoc 에서
  #   ⑴ 달러+작은따옴표 인접을 ANSI-C 인용으로 오인해 **달러를 삼키고**(A7 이 x0 이 됐고,
  #   생성자가 그 훼손 앵커에 맞춘 미끼 주석으로 이 케이스를 통과시킨 사고가 실제로 있었다 —
  #   2026-08-11 최소 재현 실측) ⑵ heredoc 본문의 따옴표·백틱에 $() 파서가 걸려 EOF 로 죽는다.
  #   평범한 명령 + 파일 리다이렉트는 make_mutant 가 증명하듯 둘 다 안전하다.
  python3 - "$CHECK" "$GATES" "$ROOT/Makefile" >"$TMP/anchors.out" 2>&1 <<'PY'
import re
import sys

sc = open(sys.argv[1], encoding="utf-8").read()
fg = open(sys.argv[2], encoding="utf-8").read()
mk = open(sys.argv[3], encoding="utf-8").read()
anchors = [
    ("A1", sc, '  if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then', 1),
    ("A2", sc, '  if [ "$sha" = "$HEAD_SHA" ]; then', 1),
    ("A3", sc, '  if [ -z "$MERGE_BASE" ]; then', 1),
    ("A4", sc, '  if [ "$anc" -ne 0 ]; then', 1),
    ("A5", sc, '  if [ "$inmain" -eq 0 ]; then', 1),
    ("A6", sc, '''head -n 1 "$SIGNAL_FILE" | tr -d '\\r' '''.strip(), 1),
    ("A7", sc, '''  if ! printf '%s' "$SHA_RAW" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then''', 1),
    ("A8", sc, '  finish 3 "abort" ""', 1),
    ("A9", sc, r"sed -n 's/^[[:blank:]]*commit:[[:blank:]]*\([^[:blank:]]*\)[[:blank:]]*$/\1/p'", 1),
    ("A14", sc, '  if [ "$mb_rc" -ne 0 ] || [ -z "$MERGE_BASE" ]; then', 1),
    ("A10", fg, 'case "$RUN" in eod)', 1),
    ("A11", fg, 'run_gate "신호 신선도 하네스" "scripts/signal-check.sh" bash "$ROOT/scripts/signal-check-test.sh"', 1),
    ("A12", fg, 'check_signal "', 4),
]
bad = ["%s x%d(기대%d)" % (n, s.count(a), w) for n, s, a, w in anchors if s.count(a) != w]
if not re.search(r"for h in [^;]*\bsignal-check\b", mk):
    bad.append("A13 (Makefile gate-harnesses 목록에 signal-check 부재)")
if bad:
    print("앵커 이탈: " + " · ".join(bad))
    sys.exit(1)
PY
  RC=$?
  OUT="$(cat "$TMP/anchors.out")"
  why=""
  [ "$RC" -eq 0 ] || why="$OUT"
  report "⑳" "변이·배선 앵커 14종 규정 횟수 존재" "$why"

  # ㉑ 배선: 신선 → record rc=0 + note 가 signal: 로 시작
  sig "$TMP/repo" "commit: $A_C4" "본문"
  run_wire "$TMP/repo" 1
  why=""
  [ "$(printf '%s\n' "$OUT" | grep -c '^REC|')" -eq 1 ] || why="record 호출이 1회가 아니다"
  [ -z "$why" ] && [ "$(printf '%s\n' "$OUT" | grep -c '^SKIP|')" -eq 0 ] || { [ -n "$why" ] || why="skip_gate 가 불렸다"; }
  [ -z "$why" ] && ! printf '%s\n' "$OUT" | grep -q '^REC|테스트게이트|0|signal:' && why="record 가 rc=0·signal: note 가 아니다"
  report "㉑" "배선: 신선 → PASS 행 + note 전달" "$why"

  # ㉒ 배선: 낡음 + req=1 → FAIL 행 + 안내문. ★`local out=$(...)` rc 삼킴을 잡는 유일한 자리.
  sig "$TMP/repo" "# 앞 회차 산문 — commit 줄 없음" "본문"
  run_wire "$TMP/repo" 1
  why=""
  rec_line="$(printf '%s\n' "$OUT" | grep '^REC|' || true)"
  [ -n "$rec_line" ] || why="record 가 불리지 않았다"
  [ -z "$why" ] && [ "$(printf '%s' "$rec_line" | cut -d'|' -f3)" != "0" ] || { [ -n "$why" ] || why="★record rc=0 — 낡은 신호가 PASS 됐다 (rc 삼킴?)"; }
  [ -z "$why" ] && ! has '첫 줄에 `commit:' && why="안내문(첫 줄에 commit: …)이 없다"
  report "㉒" "배선: 낡음+req=1 → FAIL 행 + 안내문" "$why"

  # ㉓ 배선: 낡음 + req=0 → skip 강등 (vercel.ok, fe diff 0 를 FAIL 로 올리지 않는다)
  run_wire "$TMP/repo" 0
  why=""
  [ "$(printf '%s\n' "$OUT" | grep -c '^SKIP|')" -eq 1 ] || why="skip_gate 호출이 1회가 아니다"
  [ -z "$why" ] && [ "$(printf '%s\n' "$OUT" | grep -c '^REC|')" -eq 0 ] || { [ -n "$why" ] || why="record 가 불렸다 — req=0 인데 FAIL 로 올렸다"; }
  report "㉓" "배선: 낡음+req=0 → skip 강등" "$why"

  # ㉔ 출력 계약 — `signal: <name> @ <short8> [code]` + 정확히 1줄 (F5). `signal:` 만 찍는
  #   구현이 ①②⑧⑯ 을 전부 통과하는 구멍을 막는다. [head] 와 **[branch] 양쪽**을 잰다 (H3 —
  #   전건 [head] 를 내는 구현 차단). 추출본(코드 size·sha 없음)은 red.
  sig "$TMP/repo" "commit: $A_C4" "본문"
  run_sig "$TMP/repo" --run t-run g9.ok
  why=""
  [ "$RC" -eq 0 ] || why="rc=$RC (기대 0)"
  [ -z "$why" ] && [ "$(printf '%s\n' "$OUT" | grep -c .)" -ne 1 ] && why="stdout 이 정확히 1줄이 아니다"
  [ -z "$why" ] && ! has "signal: g9.ok @ ${A_C4:0:8} [head]" && why="형식 위반 — '@ <short8> [head]' 가 없다: $OUT"
  if [ -z "$why" ]; then
    sig "$TMP/repo" "commit: $A_C3" "본문"
    run_sig "$TMP/repo" --run t-run g9.ok
    has "signal: g9.ok @ ${A_C3:0:8} [branch]" || why="형식 위반 — '@ <short8> [branch]' 가 없다: $OUT"
  fi
  report "㉔" "출력 계약: @ short8 [head]·[branch] · 1줄" "$why"

  # ㉕ ★F1 [치명적]의 유일한 증인 — origin/main 존재 + merge-base 실패(무관 이력).
  #   종전 스펙은 이 형상에서 sha==HEAD 면 signal[head] **초록**이었다. 판정 불가 = rc 3.
  sig "$TMP/repo-unrel" "commit: $U_C4" "본문"
  run_sig "$TMP/repo-unrel" --run t-run g9.ok
  why=""
  [ "$RC" -eq 3 ] || why="rc=$RC (기대 3) — merge-base 실패가 초록/낡음으로 위장됐다"
  [ -z "$why" ] && ! has "[git-error]" && why="[git-error] 코드가 없다"
  report "㉕" "origin/main 존재+merge-base 실패 → rc3 [git-error]" "$why"
}

# ── 변이 엔진 (사본 전용 — 앵커 소실 시 rc=9 로 크게 죽는다) ────────
make_mutant() { # make_mutant <M-id> <src> <dst>
  python3 - "$1" "$2" "$3" <<'PY'
import sys

mid, src, dst = sys.argv[1:4]
MUT = {
    "M1": ('  if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then', "  if false; then"),
    "M2": ('  if [ "$inmain" -eq 0 ]; then', "  if false; then"),
    "M3": ('  if [ "$anc" -ne 0 ]; then', "  if false; then"),
    "M4": ('  if [ -z "$MERGE_BASE" ]; then', "  if false; then"),
    "M5": ('head -n 1 "$SIGNAL_FILE"', 'cat "$SIGNAL_FILE"'),
    "M6": ('''  if ! printf '%s' "$SHA_RAW" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then''', "  if false; then"),
    "M7": (
        'case "$RUN" in eod) echo "✗ --run eod 는 금지다 — 앞 회차 신호를 물려받는다 ([BL-706]). '
        '회차 슬러그를 써라: --run <회차이름>" >&2; exit 1 ;; esac',
        ":",
    ),
    "M8": (" | tr -d '\\r'", ""),
    "M9": ('  finish 3 "abort" ""', '  finish 1 "abort" ""'),
    "M10": ('  if [ "$mb_rc" -ne 0 ] || [ -z "$MERGE_BASE" ]; then', "  if false; then"),
    "N1": ("# signal-check — 스킬 게이트 신호의 **신선도** 판정. ([BL-706])", "#"),
    "N2": ('WHY="HEAD 와 동일"', 'WHY="현재 커밋과 같다"'),
    "N3": ('  if [ "$sha" = "$HEAD_SHA" ]; then', '  if [ "$HEAD_SHA" = "$sha" ]; then'),
}
old, new = MUT[mid]
s = open(src, encoding="utf-8").read()
if old not in s:
    sys.stderr.write("✗ 변이 앵커를 못 찾았다 [%s]: %r\n" % (mid, old))
    sys.exit(9)
if s.count(old) != 1:
    sys.stderr.write("✗ 변이 앵커가 유일하지 않다 [%s] x%d\n" % (mid, s.count(old)))
    sys.exit(9)
open(dst, "w", encoding="utf-8").write(s.replace(old, new))
PY
}

run_mutants() {
  # 합격 = 각 M 의 red 집합이 기대와 **정확히** 일치(1건) · 각 N 은 red 0건.
  # red 0건인 M = 하네스가 눈이 멀었다(또는 등가 변이). 전건 red 인 M = 판별력 증거가 아니다.
  # ★M9 기대 = ⑨㉕ **둘** — A14 가 동결 골격대로 abort() 를 호출하므로 abort 의 rc 를 무는
  #   변이는 abort 경로의 두 증인(⑨ 비저장소 · ㉕ merge-base 실패)을 함께 죽인다. 동결 초판의
  #   「⑨ 만」은 A14 골격과 자기모순이었다(생성자가 finish 3 분리로 회피했던 자리 — G6 기록).
  local spec="M1=⑫ M2=③ M3=⑲ M4=⑭ M5=⑮ M6=⑪ M7=⑩ M8=⑯ M9=⑨㉕ M10=㉕ N1= N2= N3="
  local entry mid expect mrc verdict
  local mfail=0
  echo ""
  echo "── 변이 M1~M10 · 음성 대조 N1~N3 (사본 주입 · 케이스 25건 전량 재실행) ──"
  QUIET=1
  for entry in $spec; do
    mid="${entry%%=*}"; expect="${entry#*=}"
    CHECK_BIN="$CHECK"; ARGPARSE_SRC=""
    if [ "$mid" = "M7" ]; then
      make_mutant M7 "$GATES" "$TMP/mutant-gates.sh"; mrc=$?
      ARGPARSE_SRC="$TMP/mutant-gates.sh"
    else
      make_mutant "$mid" "$CHECK" "$TMP/mutant.sh"; mrc=$?
      CHECK_BIN="$TMP/mutant.sh"
    fi
    if [ "$mrc" -ne 0 ]; then
      printf '  ✗ %-3s 앵커 소실 — 하네스가 낡았다 (rc=9)\n' "$mid"
      mfail=$((mfail + 1))
      continue
    fi
    run_suite
    verdict=""
    [ "$RED_IDS" = "$expect" ] || verdict="red=[$RED_IDS] 기대=[$expect]"
    if [ -n "$verdict" ]; then
      printf '  ✗ %-3s %s\n' "$mid" "$verdict"
      mfail=$((mfail + 1))
    else
      if [ -n "$expect" ]; then printf '  ✓ %-3s → 정확히 %s 만 red\n' "$mid" "$expect"
      else printf '  ✓ %-3s → red 0건 (등가 확인)\n' "$mid"; fi
    fi
  done
  QUIET=0; CHECK_BIN="$CHECK"; ARGPARSE_SRC=""
  return "$mfail"
}

# ── 실행 ──────────────────────────────────────────────────────────
echo "══ signal-check 하네스 ══"
echo "  fixture: git 저장소 4벌 + 비저장소 1벌 (tmp 트리)"
echo ""

run_suite
echo ""
echo "  케이스: ${PASS}/25 통과, ${FAIL} 실패"
if [ "$FAIL" -gt 0 ]; then
  echo "  red = [$RED_IDS]"
  exit 1
fi

if [ "$MODE" = "--mutants" ]; then
  if run_mutants; then
    echo ""
    echo "✓ 변이 13종 전건 판별 (M 각 기대 집합과 정확 일치 · N 각 0건)"
  else
    echo ""
    echo "✗ 변이 판별 실패 — 위 표를 봐라"
    exit 1
  fi
fi

echo "✓ 전건 통과"
