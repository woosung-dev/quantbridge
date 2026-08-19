#!/bin/bash
# Codex PreToolUse[Bash] — 위험 명령 차단. (finsight 이식, QuantBridge 개조판)
# 입력: stdin JSON. Bash 도구의 명령은 .tool_input.command (문자열 또는 argv 배열).
# 위험 패턴이면 permissionDecision=deny 를 stdout JSON으로 반환해 호출을 막는다.

# 도구 핀 — mise shim 을 PATH 앞에 세운다(jq 등 파생 도구 버전 고정, ADR-036).
_QB_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$_QB_ROOT/tools/scripts/lib/mise-shim-path.sh" ]; then
  # shellcheck source=/dev/null
  . "$_QB_ROOT/tools/scripts/lib/mise-shim-path.sh"
  qb_pin_tool_path || true
fi

INPUT=$(cat)

CMD=$(printf '%s' "$INPUT" | jq -r '
  (.tool_input.command // .tool_input.cmd // "") as $c
  | if ($c | type) == "array" then ($c | join(" ")) else ($c | tostring) end')

# 패턴: rm -rf · git push --force/-f · git reset --hard · DROP TABLE ·
#       docker rm · docker volume rm (컨테이너·앱 DB 는 메인과 1벌 공유 — AGENTS.md)
if printf '%s' "$CMD" | grep -qE 'rm[[:space:]]+-rf|git[[:space:]]+push[[:space:]]+(--force(-with-lease)?|-f)([[:space:]=]|$)|git[[:space:]]+reset[[:space:]]+--hard|DROP[[:space:]]+TABLE|docker[[:space:]]+rm|docker[[:space:]]+volume[[:space:]]+rm'; then
  jq -cn '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "BLOCKED: 위험한 명령어가 감지되었습니다 (rm -rf / git push --force·-f / git reset --hard / DROP TABLE / docker rm / docker volume rm)."
    }
  }'
fi

exit 0
