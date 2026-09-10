# ADR-043 — 소크 의식 층을 종료한다. 이미지가 pin 을 대체하고, 배포는 스크립트 하나다

- **상태:** Accepted (2026-09-10, 사용자 결정 3건)
- **범위:** `.github/workflows/release.yml`(PR #886) · `tools/scripts/deploy.sh` · `tools/scripts/host-bootstrap.sh` · `infra/compose/docker-compose.server.yml` · 삭제 = `tools/scripts/soak-*.sh` 6종 · `docker-compose.soak.yml` · `apps/api/scripts/soak_gate_predicate.py` 와 그 테스트
- **관련:** [ADR-024](./024-soak-stability-gate.md)(**Superseded** — 이 ADR 이 대체) · [ADR-037](./037-harness-zero-base.md) §② 1(소크 존치 근거 — 정정) · [ADR-029](./029-monorepo-realign.md)(COMPOSE 배열 정본 — 정정) · [ADR-034](./034-auth-self-host-better-auth.md) D2(DDL 승인 경로 — 정정) · [ADR-028](./028-backlog-deferred-verdict.md)(판정 축 3→2)

## 결정

1. **소크 의식 층을 종료한다.** `.soak/src` 커밋 고정(pin) · `down→pin→up` 순서 · 24h 창 계산 게이트 · 30분 감시 타이머 ·
   compose 3층(base+isolated+soak)을 전부 지운다. **앱 안의 안전장치는 남긴다** — `position_divergence` 감지 →
   세션 `auto_death` · kill switch · 고아 주문 스캐너 · reconcile · 텔레그램 경보(`src/trading/`·`src/tasks/`). 게이트가 잡던
   실격 15건은 전부 **앱이 스스로 만든 이벤트**를 게이트가 세어 준 것이다.
2. **이미지가 pin 을 대체한다.** `release.yml` 이 main 머지마다 `ghcr.io/woosung-dev/quantbridge-{backend,frontend}:sha-<7>` 을
   올린다. 「서버 워커가 어느 코드를 도는가」의 답은 `.soak/pin-history.jsonl` 이 아니라 **이미지 태그**다. 서버는 빌드하지 않는다.
3. **배포는 `tools/scripts/deploy.sh <sha>` 하나다.** 순서 = `git pull --ff-only`(compose·스크립트) → **24h 무실격 검사**(아래) →
   이미지 `alembic heads` vs DB `alembic_version` 대조 → `docker compose pull` → 워커 롤링(beat→optimizer-heavy→worker→ws-stream) →
   FE `up -d` → 호스트 API(`uv sync` → import probe → `systemctl --user restart`) → `/health` → `docker-reclaim.sh --confirm` → 텔레그램 요약.
   롤백 = `deploy.sh <이전 sha>`.
4. **BE·FE 모두 main 머지마다 자동 반영한다. 단 DDL 이 있으면 멈춘다.** head 가 DB 와 다르면 `deploy.sh` 는 rc 2 로 멈추고
   텔레그램으로 「DDL 필요」를 알린다. 사람이 `deploy.sh --migrate <sha>` 를 친다(`db-backup.sh run` 선행 → 이미지 안
   `run_alembic_with_lock` → 재확인). **「서버 DB DDL = 매번 명시 승인」 규칙은 그대로다** — 집행기만 바뀌었다.
5. **창 개념 대신 한 줄.** 배포 전 `trading.live_signal_sessions` 에서 지난 24h 의 `deactivated_reason ∈ AUTOMATIC_DEATH_REASONS`(8종,
   정본 = `src/trading/models.py:SessionDeactivationReason`) 건수를 센다. 1건이라도 있으면 rc 2 로 멈춘다. 이것이 ADR-024 C3 의
   auto_death 축을 **그대로 물려받은 유일한 판정**이다.
6. **호스트 전용 설정은 레포가 만든다.** `host-bootstrap.sh --install` 이 `/etc/docker/daemon.json`(json-file 10m×3) 과
   `/etc/systemd/journald.conf.d/quantbridge.conf`(`SystemMaxUse=500M`) 를 쓰고 `--status` 가 드리프트를 잰다.

## 이유

### 소크는 졸업했다 (2026-09-10 14:29 UTC 서버 실측)

| 항목 | 값 |
| --- | --- |
| 판정 | **PASS** — C1~C5 전부 ✓ |
| 24h 창 | **5회** / 필요 3회 (누적 644.7h) |
| 최장 연속 | **291.4h**(8/16~8/28, 한 커밋) |
| 실격 | **0건**(8/14 이후 27일) — 그 전 3주는 15건(코드 7 · 운영 7 · 미판정 1) |
| 9/3 호스트 재부팅 | 컨테이너가 `restart: unless-stopped` 로 스스로 올라왔고 **창이 이어졌다** |
| 어둠 비율 | 99.7% — 매매가 실제로 일어난 시간은 0.3% |
| 서버 코드 | 8/30 자, main 대비 **11일 / 9커밋** 낡음 |

게이트의 원래 소비자는 「실자금 진입 판단」이었고 그것은 **2026-08-23 사용자 결정(실자금 안 간다)** 으로 사라졌다.
남은 역할은 「새 코드가 매매 정합성을 깨면 잡는 경보기」인데, 그 감지는 앱이 하고 게이트는 세기만 했다.
그리고 어둠 99.7% 는 소크가 「안 죽는다」를 증명했지 「잘 산다」를 증명하지 못했다는 뜻이다 — 후자는 백테스트·스트레스 축과
PRD §5 의 일이다.

### 배포와 소크가 배타적이었던 이유는 시스템이 아니라 정의였다

ADR-024 창 조건 ②「고정 커밋 불변」이라 코드가 바뀌면 새 창이 열린다. main 은 30일간 233번 움직였는데 서버는 ~10일에 한 번
배포됐다 — 매 머지를 반영하면 24h 창이 영원히 안 생기기 때문이다. 재부팅 실측이 보여 주듯 **매매 자체는 재시작을 견딘다**
(`acks_late`·`reject_on_worker_lost`·ws lease 60s·reconcile 5분). 창은 시스템 속성이 아니라 측정 정의였고, 그 정의의 목적이 사라졌다.

### 외부 관행 (2026-09-10 조사, 코드 대조 후 채택)

- 12-factor build/release/run · Docker CI 가이드 · GitHub GHCR 표준 워크플로 · Kamal: **CI 가 빌드해 레지스트리에 올리고 서버는 pull** 이
  규모와 무관한 기본값이다. Coolify 조차 「빌드 서버 분리」를 문서화한다(빌드가 운영 앱 CPU 를 먹는다).
- 태그 = 불변 sha, `latest` 는 별칭. 롤백 = 이전 태그로 up.
- Google SRE: 런북 복붙 배포 자체는 toil 50% 미만이면 허용이다. 이 레포의 문제는 toil 이 아니라 **결과를 아무도 안 본다**였다
  (8/30 에 넣은 회수 한 줄이 깨진 채 열흘 — 서버 4벌 잔존).
- 레포가 공개라 `ubuntu-24.04-arm` 러너와 GHCR 이 무료다(실측 `isPrivate=false`).

### 사용자 결정 3건 (2026-09-10)

⑴ 소크 의식 층 종료(앱 경보 유지) ⑵ BE 는 main 머지마다 자동 반영, DDL 있으면 멈춤 ⑶ FE 도 머지마다 자동.

## 트레이드오프

**잃는 것**
- **phantom·tick_stall 축이 사라진다.** ADR-024 C3 의 세 갈래 중 auto_death 만 남는다. phantom 분류기(`classify_direction_divergence.py`)와
  표본 기반 tick 정체 판정(`gate-samples.jsonl`)은 소크 산출물 없이는 잴 수 없다. 대신 앱 경보(kill switch·orphan scanner·
  `alert.py`)가 같은 사건을 텔레그램으로 낸다 — 그것은 창을 리셋하지 않고 **사람에게 알린다**.
- **「같은 코드 24h」 증명이 없어진다.** 대신 배포 간격이 곧 검증 간격이고, 실격 시 원인 후보는 「직전 배포 한 벌」로 좁다.
- 워크트리 규칙 2개는 **그대로다** — 근거가 소크 mount 가 아니라 공유 컨테이너·isolated 층의 src mount 였다.

**얻는 것**
- 배포가 3층 compose·pin·창 단절 걱정 없이 스크립트 하나다. 서버 CPU 를 빌드에 쓰지 않는다(2 OCPU 공유).
- 롤백이 태그다. 의존성이 바뀐 커밋도 되돌아간다(종전 런북 §3.4⑵ 「해결책을 레포가 모른다」 해소).
- 3,110줄 셸 + 973줄 판정기 + 3,761줄 테스트가 사라진다. 그 자리에 스크립트 2개와 테스트 1개.

## 고르지 않은 대안

| 대안 | 기각 이유 |
| --- | --- |
| pull-based(watchtower) | 원본 아카이브(2025-12) · 기본 폴링 24h · 실패가 서버 로그에만 남는다 |
| Coolify / Dokploy | 서버에 UI·DB 가 상주한다 — 2 OCPU 공유 호스트에 부담, 플랫폼 자체가 SPOF |
| Ansible | 파일 2개(daemon.json·journald) 위해 도구를 하나 더 붙인다 — `--install` 관용구가 이미 6종 |
| 게이트를 이미지 태그 기준으로 개조 | 861줄 유지 비용 > 한 줄 쿼리. 소비자([BL-003])가 이미 없다 |

## 집행

- 서버 전환(★배포 = 승인 축): `soak-watch.sh --uninstall` → `soak-stack.sh down` → `git pull` → `host-bootstrap.sh --install` →
  `deploy.sh <sha>`(첫 실행은 사람이 본다) → 배포 전용 ssh 키(forced command) → `docker-reclaim.sh --install`.
- 그 뒤 `release.yml` 에 deploy 잡(별도 PR). 호스트 API 컨테이너화는 [BL-865].
- 삭제 파일의 원문 = `git show <이 PR 직전 sha>:<경로>`.
