#!/usr/bin/env bash
#
# "여기는 메인 체크아웃인가" 를 판정하고, 아니면 0 이 아닌 코드로 죽는다.
# 공유 자원(컨테이너 1벌 · 앱 DB `quantbridge` · Redis)을 건드리는 Makefile 타깃이
# **자기 레시피 안에서** 이걸 먼저 호출한다.
#
#   make 안에 표현된 가드는 make 가 끌 수 있다. 실측으로 전부 페이로드에 도달했다:
#     make -i <타깃>            → 가드 실패를 무시하고 **다음 레시피 줄**로 넘어간다
#     MAKEFLAGS=-i make <타깃>  → 위와 같다
#     make 'qb-guard=@:' <타깃> → 가드가 make 변수였으므로 빈 명령으로 덮인다
#
#   그래서 두 가지를 바꿨다:
#     1. 판정을 **make 밖(이 스크립트)** 으로 뺀다 → 덮어쓸 변수가 없다
#     2. 호출을 페이로드와 **같은 셸 명령**에 `|| exit 1` 로 묶는다 → `-i` 가 make 의
#        종료 코드는 무시해도 셸은 이미 죽었으므로 페이로드가 실행되지 않는다
#
# 판정 근거는 git 이다 — 워크트리에서만 git-dir 과 git-common-dir 이 갈린다.
# 슬롯 번호(`QB_SLOT`)로 판정하지 않는다. 그건 `make QB_SLOT=0` 한 줄로 꺼진다.
#
# 사용법:  scripts/assert-main-checkout.sh [타깃이름]
# 종료:    0 = 메인 체크아웃(진행해도 된다) / 1 = 워크트리(거부)

set -uo pipefail

_target="${1:-이 타깃}"

_gd="$(git rev-parse --absolute-git-dir 2>/dev/null || true)"
_gc_raw="$(git rev-parse --git-common-dir 2>/dev/null || true)"
_gc=""
[ -n "$_gc_raw" ] && _gc="$(cd "$_gc_raw" 2>/dev/null && pwd || true)"

# git 이 없거나 레포가 아니면 판정 불가다. **통과시킨다** — 이 스크립트의 역할은
# "워크트리에서만 막는 것" 이고, git 이 없는 환경은 워크트리가 아니다.
# (판정 불가를 차단으로 바꾸면 CI·컨테이너에서 정상 타깃이 전부 죽는다.)
if [ -z "$_gd" ] || [ -z "$_gc" ]; then
  exit 0
fi

[ "$_gd" = "$_gc" ] && exit 0

cat >&2 <<EOF
✗ '${_target}' 은 메인 체크아웃 전용이다 (여기는 워크트리).
  컨테이너와 앱 DB 는 슬롯과 무관하게 1벌 공유다 — 여기서 실행하면 다른 워크트리와 메인이 깨진다.
  → 메인에서 실행해라: cd $(dirname "$_gc") && make ${_target}
  (근거: docs/reference/worktree-parallel.md §2.1)
EOF
exit 1
