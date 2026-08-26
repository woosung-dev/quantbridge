#!/usr/bin/env bash
# 변경 파일 목록 → 어떤 CI 잡을 돌려야 하는가(backend / frontend).
#
# ★재입힘 근거(ADR-037 「문서화된 사고 1건 = 슬림 복귀 1건」) — 추측이 아니라 실측이다.
#   2026-08-26 최근 머지 PR 30건 분류: **문서만 9건(30%)** · BE만 11건(37%) · FE만 3건(10%) ·
#   둘다/공유 7건(23%). BE 잡 ~13분 · FE 잡 ~4분 기준으로 **30 PR 당 약 236분**이
#   검증 대상이 없는 잡에 들어가고 있었다.
#
# ★★함정 — `on.pull_request.paths` 로 구현하면 안 된다. 그러면 워크플로 자체가 안 돌아
#   required check 가 **영구 대기**한다(ci.yml 의 merge_group 주석이 기록한 것과 같은 함정).
#   그래서 이 스크립트는 잡을 **안 돌리는** 것이 아니라 `if:` 조건을 만든다 — skip 된 잡은
#   GitHub 이 성공으로 친다. main 은 현재 브랜치 보호가 없지만(2026-08-26 실측 = 404),
#   켜는 날 이 구조가 그대로 성립해야 한다.
#
# ★★★fail-safe 가 이 스크립트의 유일한 설계 원칙이다 — **모르면 둘 다 돌린다.**
#   이 레포는 「CI 가 돌았다고 여겼는데 안 돌았다」를 두 번 겪었다(night4-ci-truth).
#   그래서 ⑴ diff 를 못 얻으면 둘 다 ⑵ 분류 안 되는 경로가 하나라도 있으면 둘 다
#   ⑶ 무엇을 왜 건너뛰는지 항상 출력한다.
#
# usage:
#   ci-changed-scopes.sh <base_sha> <head_sha>   # git diff 로 목록을 얻는다
#   ci-changed-scopes.sh --stdin                 # 파일 목록을 stdin 으로 받는다(테스트용)
#
# 출력: stdout 에 `backend=true|false` `frontend=true|false` 두 줄.
#       $GITHUB_OUTPUT 이 있으면 거기에도 같이 쓴다.
set -uo pipefail

emit() {
  local backend="$1" frontend="$2" reason="$3"
  echo "판정: backend=${backend} frontend=${frontend} — ${reason}" >&2
  echo "backend=${backend}"
  echo "frontend=${frontend}"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      echo "backend=${backend}"
      echo "frontend=${frontend}"
    } >>"${GITHUB_OUTPUT}"
  fi
}

# ── 파일 목록 취득 ────────────────────────────────────────────────────────
files=""
if [[ "${1:-}" == "--stdin" ]]; then
  files="$(cat)"
else
  base="${1:-}"
  head="${2:-}"
  if [[ -z "${base}" || -z "${head}" ]]; then
    emit true true "base/head sha 가 비었다 — fail-safe 전량 실행"
    exit 0
  fi
  if ! files="$(git diff --name-only "${base}" "${head}" 2>&1)"; then
    emit true true "git diff 실패(${base}..${head}) — fail-safe 전량 실행"
    exit 0
  fi
fi

# 빈 diff 는 「변경 없음」이 아니라 「못 읽었다」로 본다.
# 이 레포는 빈 입력이 초록으로 새는 함정을 5회 이상 밟았다.
if [[ -z "${files//[[:space:]]/}" ]]; then
  emit true true "변경 파일 0건 — 빈 입력을 통과로 읽지 않는다, fail-safe 전량 실행"
  exit 0
fi

echo "변경 파일 $(echo "${files}" | grep -c .)건:" >&2
echo "${files}" | sed 's/^/  /' >&2

# ── 분류 ─────────────────────────────────────────────────────────────────
backend=false
frontend=false
unknown=""

while IFS= read -r f; do
  [[ -z "${f}" ]] && continue
  case "${f}" in
    # 공유 — 둘 다 돌린다. 이 목록이 이 스크립트의 안전 마진이다.
    .github/*|tools/*|infra/*|mise.toml|package.json|pnpm-workspace.yaml|.husky/*|Makefile|Dockerfile*|docker-compose*)
      backend=true; frontend=true ;;
    apps/api/*) backend=true ;;
    apps/web/*) frontend=true ;;
    # 검증 대상이 없는 것 — 어느 잡도 켜지 않는다.
    docs/*|phases/*|*.md|LICENSE|.gitignore|.gitattributes|.editorconfig|.vscode/*|.claude/*|.codex/*)
      ;;
    *)
      unknown="${unknown}${f} " ;;
  esac
done <<<"${files}"

# ★모르는 경로가 하나라도 있으면 둘 다 — 새 최상위 파일이 조용히 미검증으로 새는 것을 막는다.
if [[ -n "${unknown}" ]]; then
  emit true true "분류되지 않은 경로가 있다(${unknown% }) — fail-safe 전량 실행"
  exit 0
fi

if [[ "${backend}" == "false" && "${frontend}" == "false" ]]; then
  emit false false "검증 대상 경로 변경 0건(문서·회차 정의만) — BE·FE 둘 다 건너뛴다"
  exit 0
fi

emit "${backend}" "${frontend}" "변경 경로 기준"
