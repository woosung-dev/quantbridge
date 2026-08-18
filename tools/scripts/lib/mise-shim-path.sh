# 도구 버전 핀 — mise shim 디렉터리를 PATH **앞에** 세운다. [BL-785] · [ADR-036]
#
# 왜 있나
#   [ADR-036] 이 도구 버전의 SSOT 를 루트 `mise.toml` 하나로 모았지만 **게이트가 안 따라왔다.**
#   tools/scripts/ 의 스크립트는 사용자 셸에서 상속한 PATH 로 돌고, 거기에 mise 가 걸려
#   있는지는 셸 초기화에 달려 있어 **실제로 갈린다**(2026-08-16 실측: 레포 루트에서 corepack
#   폴백 `pnpm 8.15.9`). `apps/web/pnpm-lock.yaml` 은 `lockfileVersion: "9.0"` 이라 pnpm 8 로는
#   읽히지 않으므로 그 셸에서는 `CI frozen-lockfile` 이 red 가 된다 — 그리고 그 증상은
#   「내 PR 이 lockfile 을 깼다」로 **오인된다**. lockfile diff 가 0 인 브랜치에서도 red 다.
#
# 왜 별 파일인가
#   같은 두 줄이 `.husky/pre-commit`·`.husky/pre-push` 에 이미 복제돼 있고, 게이트 계열
#   스크립트 5종이 여기에 더 붙는다. `lib/notify-telegram.sh` 헤더가 적은 이유가 그대로다 —
#   복제하면 한쪽만 고쳐지는 순간 **조용히 새는 쪽**이 생긴다. 시험 가능한 한 벌로 뺀다.
#   (훅 2종은 POSIX `sh -e` 로 도는 별 실행 경로라 인라인을 그대로 둔다. 규칙 본문은 여기다.)
#
# 계약
#   - source 전용이다. 직접 실행하지 마라(진입점이 없다).
#   - 부작용은 `PATH` **하나뿐**이다. stdout 에 아무것도 안 쓴다 — 진단은 stderr 로만 나간다.
#   - 호출자는 `set -uo pipefail` 아래에 있다고 가정한다. `set -e` 아래에서는 rc 를 직접 받아라.
#   - ★**mise 를 실행하지 않는다.** shim 은 자기완결 바이너리라 PATH 에 `mise` 가 없어도 돈다
#     (2026-08-17 실측: PATH 를 `/usr/bin:/bin` 으로 줄이고도 shim `pnpm` 이 9.12.0 을 냈다).
#     그래서 `mise exec --` 를 호출 지점마다 붙이는 것보다 싸고, 파생 도구(`alembic`·`prettier`·
#     `playwright` 를 부르는 `node`)까지 한 번에 덮는다.
#
# env
#   MISE_DATA_DIR   mise 데이터 디렉터리. 기본 `$HOME/.local/share/mise`.
#                   (mise 가 이 변수로 위치를 옮길 수 있으므로 경로를 굳히지 않는다.)

# qb_pin_tool_path → 0 = 핀 성공 / 1 = shim 디렉터리 부재(PATH 그대로, 경고만)
qb_pin_tool_path() {
  local shims="${MISE_DATA_DIR:-$HOME/.local/share/mise}/shims"
  if [ ! -d "$shims" ]; then
    # ★조용히 넘어가지 않는다. 여기서 침묵하면 게이트가 「어느 버전으로 돌았는지 모르는 채」
    #   초록/빨강을 내고, 그것이 [BL-785] 가 만든 오인 경로 그 자체다.
    echo "⚠ mise shim 디렉터리가 없다: $shims" >&2
    echo "  도구 버전이 핀(mise.toml)이 아니라 이 셸의 PATH 로 결정된다 — 결과를 CI 와 비교하지 마라." >&2
    return 1
  fi
  # ★조건 없이 **앞에** 붙인다. 「이미 PATH 에 있으면 건너뛴다」로 짜면, 낡은 도구가 shim 보다
  #   앞에 서 있는 바로 그 상황에서 아무것도 안 하게 된다 — 고치려는 병이 정확히 그것이다.
  #   중복 항목은 무해하다.
  PATH="$shims:$PATH"
  export PATH
  return 0
}
