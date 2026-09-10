#!/usr/bin/env bash
#
# quantbridge **소유분만** 회수하는 도커 디스크 회수기 ([BL-849] 분리 · 2026-09-10)
#
# 왜 있나
#   회수가 `frontend-deploy.md` §3.3 의 한 줄에 얹혀 있어 **FE 를 배포할 때만** 돌았다. BE 배포는
#   그 줄을 안 타고 BE 이미지는 태그가 없어 재빌드가 드물다 — FE 무배포 기간이 길어지면 build cache
#   만 자란다([BL-849]). 그 한 줄 자체도 깨져 있었다: `{{.ID}}` 로 지우면 같은 ID 에 태그가 둘일 때
#   실패하고 `2>/dev/null` 이 그것을 숨겼다(2026-09-10 서버 실측: 정책은 3세대인데 4벌이 남아 있었다).
#
# 무엇을 안 하나 (★가장 중요)
#   · **남의 이미지는 절대 안 건드린다.** 이 호스트(`/dev/sda1` 97G)는 kairos·truewords·nexus 와 한
#     디스크를 쓰고 그쪽 태그는 **그쪽 롤백 경로**다. 대상은 저장소 이름이 `${QB_RECLAIM_PREFIX}-` 로
#     시작하는 것뿐이고, 그 밖의 ref 는 코드 경로상 `rmi` 인자로 갈 수 없다(`_assert_ours`).
#   · **`docker image prune` / `system prune` 을 부르지 않는다.** 무차별이라 위 규칙을 못 지킨다.
#   · **경보를 겸하지 않는다.** 경보는 `disk-guard.sh` 다 — 회수 실패로 경보가 죽으면 둘 다 잃는다.
#
# 무엇을 하나
#   ⑴ 저장소마다 **최신 KEEP 세대**(기본 3 = 롤백 창)를 남기고 나머지 태그를 `rmi` 한다.
#      ★**컨테이너가 쓰는 태그는 세대와 무관하게 보호**한다(실행 중이든 정지든 — `docker ps -a`).
#   ⑵ `docker builder prune --filter until=${QB_RECLAIM_BUILDER_AGE}` (기본 168h).
#   ★기본은 **dry-run** 이다. 지우려면 `--confirm`. 실패는 숨기지 않는다 — `rmi` 가 하나라도 실패하면 rc=1.
#
# 사용:
#   tools/scripts/docker-reclaim.sh              # dry-run — 무엇을 지울지 인쇄만
#   tools/scripts/docker-reclaim.sh --confirm    # 실제 회수
#   tools/scripts/docker-reclaim.sh --status     # 저장소별 세대 수 · 후보 · build cache · 설치본 신선도
#   tools/scripts/docker-reclaim.sh --install    # systemd user timer (매주 일요일 04:30 · 백업 03:00 뒤)
#   tools/scripts/docker-reclaim.sh --uninstall
#
# 종료 코드: 0 = 정상(지울 것이 없어도 0) / 1 = rmi·prune 실패 또는 전제 미충족
#
# env (전부 `.env.example` 에 있다):
#   QB_RECLAIM_PREFIX       저장소 접두사. 기본 `quantbridge`. 이 밖은 **보지도 않는다**.
#   QB_RECLAIM_KEEP         저장소당 남길 세대. 기본 3.
#   QB_RECLAIM_BUILDER_AGE  builder prune 의 `until`. 기본 168h.
#
# 테스트 seam: `docker` 는 PATH 로 찾는다 — `apps/api/tests/scripts/test_docker_reclaim.py` 가 가짜
#   `docker` 를 PATH 앞에 놓고 ⑴ 세대 보호 ⑵ 사용 중 보호 ⑶ 타 프로젝트 무접촉 ⑷ 실패 비은폐를 잰다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

PREFIX="${QB_RECLAIM_PREFIX:-quantbridge}"
KEEP="${QB_RECLAIM_KEEP:-3}"
BUILDER_AGE="${QB_RECLAIM_BUILDER_AGE:-168h}"

UNIT_NAME="dev.quantbridge.docker-reclaim"
UNIT_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"

MODE="dry-run"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --confirm) MODE="confirm" ;;
    --status) MODE="status" ;;
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    -h | --help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    *)
      echo "알 수 없는 인자: $1  (--help)" >&2
      exit 1
      ;;
  esac
  shift
done

case "${KEEP}" in
  '' | *[!0-9]*)
    echo "✗ QB_RECLAIM_KEEP 는 양의 정수여야 한다: '${KEEP}'" >&2
    exit 1
    ;;
esac
[ "${KEEP}" -ge 1 ] || {
  echo "✗ QB_RECLAIM_KEEP 는 1 이상이어야 한다 — 0 이면 실행 중 태그까지 후보가 된다" >&2
  exit 1
}

command -v docker > /dev/null 2>&1 || {
  echo "✗ docker 가 PATH 에 없다" >&2
  exit 1
}

# ── 판독 ────────────────────────────────────────────────────────────────────────
# `docker images` 는 생성 시각 내림차순이다 — 저장소별로 잘라도 그 순서가 유지된다.
# 저장소 필터는 **접두사 + 하이픈** 이다. `quantbridge` 만 주면 `quantbridge2-*` 같은 이웃도 잡는다.
_list_ours() { # stdout: "<repo>\t<tag>" (dangling 은 repo 가 <none> 이라 여기 안 들어온다)
  docker images --format '{{.Repository}}\t{{.Tag}}' "${PREFIX}-*" | awk -F'\t' '$2 != "<none>"'
}

_in_use_refs() { # stdout: 컨테이너가 참조하는 image 문자열 (실행 중 + 정지 전부)
  docker ps -a --format '{{.Image}}'
}

# ★단 하나의 안전판 — rmi 인자로 가는 모든 ref 는 여기를 지난다. 접두사 밖이면 죽는다.
_assert_ours() {
  case "$1" in
    "${PREFIX}-"*) return 0 ;;
    *)
      echo "✗ 내부 오류: 접두사 밖 ref 가 회수 후보에 들어왔다 — ${1} (아무것도 지우지 않았다)" >&2
      exit 1
      ;;
  esac
}

# stdout: 지울 ref 목록 (한 줄 하나). 저장소별 KEEP 초과분 − 사용 중.
_candidates() {
  local in_use
  in_use="$(_in_use_refs | sort -u)"
  _list_ours | awk -F'\t' -v keep="${KEEP}" '
    {
      n[$1]++
      if (n[$1] > keep) print $1 ":" $2
    }' | while IFS= read -r ref; do
    if printf '%s\n' "${in_use}" | grep -qxF -- "${ref}"; then
      echo "  ↷ 보호(컨테이너 사용 중): ${ref}" >&2
      continue
    fi
    printf '%s\n' "${ref}"
  done
}

_summary() {
  echo "■ 대상 접두사 ${PREFIX}-* · 저장소당 ${KEEP}세대 유지 · builder prune until=${BUILDER_AGE}"
  _list_ours | awk -F'\t' '{ n[$1]++ } END { for (r in n) printf "  %-40s %d 태그\n", r, n[r] }' | sort
}

# ── 회수 ────────────────────────────────────────────────────────────────────────
_reclaim() { # $1 = dry-run | confirm
  local do_it="$1" rc=0 ref n=0
  _summary
  while IFS= read -r ref; do
    [ -n "${ref}" ] || continue
    _assert_ours "${ref}"
    n=$((n + 1))
    if [ "${do_it}" = confirm ]; then
      if docker rmi "${ref}"; then
        echo "  ✓ rmi ${ref}"
      else
        echo "  ✗ rmi 실패: ${ref}" >&2
        rc=1
      fi
    else
      echo "  · (dry-run) rmi ${ref}"
    fi
  done < <(_candidates)
  echo "  후보 ${n}건"

  if [ "${do_it}" = confirm ]; then
    if docker builder prune -f --filter "until=${BUILDER_AGE}"; then
      echo "  ✓ builder prune until=${BUILDER_AGE}"
    else
      echo "  ✗ builder prune 실패" >&2
      rc=1
    fi
  else
    echo "  · (dry-run) docker builder prune -f --filter until=${BUILDER_AGE}"
    echo "■ dry-run 이다 — 지우려면 --confirm"
  fi
  return "${rc}"
}

# ── systemd ─────────────────────────────────────────────────────────────────────
_install() {
  command -v systemctl > /dev/null 2>&1 || {
    echo "✗ systemctl 이 없다 — 이 설치 경로는 리눅스 전용이다." >&2
    exit 1
  }
  mkdir -p "${UNIT_DIR}" || exit 1
  cat > "${UNIT_DIR}/${UNIT_NAME}.service" << EOF2
[Unit]
Description=QuantBridge 도커 디스크 회수 (${PREFIX}-* 저장소당 ${KEEP}세대 · builder prune ${BUILDER_AGE})

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=/usr/local/bin:${HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin
Environment=QB_RECLAIM_PREFIX=${PREFIX}
Environment=QB_RECLAIM_KEEP=${KEEP}
Environment=QB_RECLAIM_BUILDER_AGE=${BUILDER_AGE}
ExecStart=/bin/bash ${SCRIPT_DIR}/docker-reclaim.sh --confirm
EOF2

  # ★벽시계 고정(`OnCalendar`) — 형제 유닛과 같은 이유([BL-737]). 일요일 04:30 = 백업(03:00) 뒤,
  #   disk-guard(매시 15분)·soak-watch(00/30) 와 안 겹친다. 실패는 journal 에 남고 텔레그램은 안 쏜다 —
  #   회수 실패는 디스크가 **아직** 안 찼다는 뜻이고 그 축은 disk-guard 가 본다.
  cat > "${UNIT_DIR}/${UNIT_NAME}.timer" << 'EOF2'
[Unit]
Description=QuantBridge 도커 디스크 회수 — 매주 일요일 04:30 (벽시계 고정)

[Timer]
OnCalendar=Sun *-*-* 04:30
AccuracySec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF2

  systemctl --user daemon-reload || exit 1
  systemctl --user enable --now "${UNIT_NAME}.timer" || exit 1
  echo "✓ 설치 완료 — 매주 일요일 04:30 에 ${PREFIX}-* 만 회수한다"
  echo "  로그: journalctl --user -u ${UNIT_NAME}.service"
}

_uninstall() {
  command -v systemctl > /dev/null 2>&1 || {
    echo "✗ systemctl 이 없다." >&2
    exit 1
  }
  systemctl --user disable --now "${UNIT_NAME}.timer" > /dev/null 2>&1 || true
  rm -f "${UNIT_DIR}/${UNIT_NAME}.timer" "${UNIT_DIR}/${UNIT_NAME}.service"
  systemctl --user daemon-reload > /dev/null 2>&1 || true
  echo "✓ 해제 완료"
}

_status() {
  _summary
  echo "  회수 후보:"
  _candidates | sed 's/^/    /'
  echo "  build cache: $(docker system df --format '{{.Type}} {{.Size}} reclaimable={{.Reclaimable}}' 2> /dev/null | awk '/Build Cache/' || echo '판독 실패')"
  local unit="${UNIT_DIR}/${UNIT_NAME}.service"
  if [ -f "${unit}" ]; then
    if grep -qF "ExecStart=/bin/bash ${SCRIPT_DIR}/docker-reclaim.sh" "${unit}"; then
      echo "  설치본: ✓ 최신 (${unit})"
    else
      echo "  설치본: ★낡았다 — ExecStart 가 이 체크아웃을 가리키지 않는다. --install 을 다시 해라"
    fi
  else
    echo "  설치본: 없음 (--install)"
  fi
}

case "${MODE}" in
  dry-run) _reclaim dry-run ;;
  confirm) _reclaim confirm ;;
  status) _status ;;
  install) _install ;;
  uninstall) _uninstall ;;
esac
