#!/usr/bin/env bash
# BL-181 Sprint 38 — backend src marker 변경 → worker watchfiles reload 흔적 검증 sentinel.
#
# 전제: `make up-isolated-watch` 실행 후 backend-worker container UP.
# 동작: backend src 안에 marker 파일 생성 → 5s 대기 → docker logs 에서 변화 감지 키워드 grep.
# 종료 코드: 0 = reload 흔적 발견, 1 = 흔적 없음.

set -eu

# resolve repo root from script location (worktree-safe — no hardcoded path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MARKER_FILE="${REPO_ROOT}/backend/src/__sentinel_bl181__.py"
CONTAINER="quantbridge-worker"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "✗ BL-181 sentinel SKIP — container '${CONTAINER}' 미실행. make up-isolated-watch 후 재시도." >&2
  exit 1
fi

# capture log baseline timestamp (이전 reload 흔적과 구분)
BASELINE_TS="$(date -u +%Y-%m-%dT%H:%M:%S)"

# 1. marker 생성 (변경 감지 trigger)
echo "# BL-181 sentinel marker $(date +%s)" > "${MARKER_FILE}"

# 2. watchfiles 가 변경 감지 후 reload 시작하기까지 대기
sleep 5

# 3. baseline 이후 logs 에서 변화 감지 흔적 grep (watchfiles 출력 패턴)
if docker logs --since "${BASELINE_TS}" "${CONTAINER}" 2>&1 | grep -qE "(WatchedFileChange|file change|change detected|Restarting|Stopping|Reloading)"; then
  echo "✓ BL-181 sentinel PASS — worker auto-reload 감지"
  rm -f "${MARKER_FILE}"
  exit 0
else
  echo "✗ BL-181 sentinel FAIL — worker reload 흔적 없음"
  echo "  -- recent logs (${CONTAINER}) --" >&2
  docker logs --since "${BASELINE_TS}" "${CONTAINER}" 2>&1 | tail -20 >&2
  rm -f "${MARKER_FILE}"
  exit 1
fi
