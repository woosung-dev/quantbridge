#!/bin/bash
# Codex Stop — 변경 영역 경량 lint 게이트. (finsight 이식, QuantBridge 개조판)
# 통과하면 정상 stop, 실패하면 decision:block 으로 codex를 이어 자가교정시킨다
# (codex의 Stop block은 턴을 거부하지 않고 reason을 새 프롬프트로 이어붙임).
# 입력: stdin JSON. .stop_hook_active 로 무한 루프를 막는다(자가교정 1회 제한).
#
# ★경량·오프라인만 — pytest·build·네트워크·DB 금지. codex 샌드박스가 네트워크·DB 를
#   막으므로 그런 검사를 넣으면 상시 red 가 된다. git diff 로 변경 영역을 판정해
#   apps/api → ruff check, apps/web → eslint 만 돌린다.

# 도구 핀 — mise shim 을 PATH 앞에 세운다(uv·pnpm·jq 버전 고정, ADR-036).
_QB_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$_QB_ROOT/tools/scripts/lib/mise-shim-path.sh" ]; then
  # shellcheck source=/dev/null
  . "$_QB_ROOT/tools/scripts/lib/mise-shim-path.sh"
  qb_pin_tool_path || true
fi

INPUT=$(cat)
ROOT="$_QB_ROOT"
ALLOW='{"continue": true}'

# 이미 Stop 훅으로 한 번 이어졌으면 더 반복하지 않는다(한 번만 자가교정).
ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false')
[ "$ACTIVE" = "true" ] && { printf '%s\n' "$ALLOW"; exit 0; }

cd "$ROOT" || { printf '%s\n' "$ALLOW"; exit 0; }

# 변경 영역 판정 — 미커밋 변경(HEAD 대비) + 미추적 파일. 커밋 여부와 무관하게
# 이 턴의 작업 트리를 본다. git 이 없거나 실패하면 게이트를 건너뛴다(fail-open).
CHANGED=$({ git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | sort -u) || CHANGED=""

FAIL=0
OUT=""

# ★환경 부재 = 코드 결함이 아니다 — codex 샌드박스는 네트워크가 막혀 install 로 자가교정할 수
#   없으므로, 의존성이 없는 트리에서는 경고만 남기고 건너뛴다(그 레인만 fail-open).
if printf '%s\n' "$CHANGED" | grep -q '^apps/api/' && [ -d apps/api/.venv ]; then
  if ! API_OUT=$(cd apps/api && uv run ruff check . 2>&1); then
    FAIL=1
    OUT="$OUT
[apps/api ruff]
$API_OUT"
  fi
fi

if printf '%s\n' "$CHANGED" | grep -q '^apps/web/' && [ -d apps/web/node_modules ]; then
  if ! WEB_OUT=$(pnpm -C apps/web lint 2>&1); then
    FAIL=1
    OUT="$OUT
[apps/web eslint]
$WEB_OUT"
  fi
fi

if [ "$FAIL" -eq 0 ]; then
  printf '%s\n' "$ALLOW"
else
  jq -cn --arg r "변경 영역 lint가 실패했습니다. green이 될 때까지 고치세요.

$(printf '%s' "$OUT" | tail -n 40)" '{decision: "block", reason: $r}'
fi

exit 0
