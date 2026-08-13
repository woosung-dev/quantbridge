# ADR-029: 모노레포 표준 배치 — apps/ · tools/ · infra/ 전면 재배치

- **날짜:** 2026-08-13
- **상태:** Accepted
- **관련:** [ADR-026](026-documentation-ssot.md)(문서 SSOT) · [ADR-027](027-nested-agents-md.md)(중첩 AGENTS.md — 경로만 이동, 메커니즘 불변)

## Context

회사 표준으로 Polyglot Monorepo 구조(`apps/` 독립 배포 단위 · `packages/` 는 검증된 공유만 ·
`contracts/` OpenAPI 계약 SSOT · native toolchain · 루트 명령 인터페이스 · per-app CI)를 확정했다.
QuantBridge 는 표준 7축 중 3축(배포 단위 분리 · 루트 명령 = Makefile · per-app CI = paths-filter)을
이미 충족했지만 디렉터리 이름이 표준과 달랐다. 사용자 결정: **전면 물리 재배치 + 표준 풀 정렬**
(2026-08-13, 실측 표면 — `backend|frontend/` 리터럴 976줄/214파일 · 루트 `scripts/` ~367줄 · compose
호출 ~20줄 — 을 제시한 뒤의 결정이다).

## Decision

### 경로 등가표 (과거 문서·git 히스토리를 읽을 때의 사전)

| 구 경로                          | 신 경로                             |
| -------------------------------- | ----------------------------------- |
| `backend/`                       | `apps/api/`                         |
| `frontend/`                      | `apps/web/`                         |
| `scripts/` (루트)                | `tools/scripts/`                    |
| `docker-compose*.yml` (루트 4벌) | `infra/compose/docker-compose*.yml` |
| `docker/db/`                     | `infra/db/`                         |

앱 내부 상대 경로는 불변이다 — 예: `apps/api/scripts/`(구 `backend/scripts/`)는 앱 소유의
스크립트 디렉터리이고 루트 `tools/scripts/` 와 다르다.

### compose 프로젝트명은 계속 **체크아웃 루트에서 파생**한다

compose 4벌 모두 `name:` 키가 없고 프로젝트명(=볼륨 소유)은 프로젝트 디렉터리에서 파생된다.
파일을 `infra/compose/` 로 옮기며 그냥 `-f` 하면 프로젝트 디렉터리가 `infra/compose` 가 되어
프로젝트명이 바뀌고 **기존 TimescaleDB·beat-data 볼륨이 고아**가 된다. 그래서:

- 모든 호출은 `--project-directory <체크아웃 루트>` 를 동반한다 — Makefile 은 `COMPOSE_FLAGS` 변수,
  `tools/scripts/soak-stack.sh` 는 COMPOSE 배열이 정본.
- `name:` 고정은 **기각** — 메인/소크 서버/워크트리가 서로 다른 디렉터리명 파생을 쓰므로 한 이름으로
  고정하면 다른 체크아웃의 볼륨이 고아가 된다.
- 수용 기준(통과함): 이동 전후 `docker compose config` 렌더 diff = 경로 치환분만(base 9쌍 ·
  isolated/soak 비경로 diff 0) · 프로젝트명 3층 전부 불변.

### 역사 문서는 원문 보존

`docs/dev-log/`·`docs/lessons.md` 인용부·ADR-001~028 본문·`phases/`·`docs/reports/`·`docs/archive/`·
`git show <sha>:` 좌표·`apps/api/tests/fixtures/bl595/*.json`(`_comment` 가 「손으로 고치지 마라」인
캡처 원본)·backlog.md 의 ✅ Resolved 섹션은 **구 경로 그대로 둔다**. 과거 기록의 경로는 위 등가표로
읽는다. 살아있는 지시(reference/ · 루트 문서 · status/roadmap 활성부 · backlog 미종결 섹션)는 갱신했다.

### 비목표 (이번 결정에 포함되지 않음)

- compose 서비스명/컨테이너명/이미지명(`backend-worker` 등) 변경 — CI 잡 이름(`backend`,
  `frontend`)도 동일하게 유지 (식별자이지 경로가 아니다)
- pnpm/uv workspace 도입 — 앱이 각 1벌이라 실수요 없음 (루트 package.json 은 husky 도구 전용 유지)
- `packages/`·`apps/admin`·`apps/mobile` 생성 — 제2앱 계획 없음 (「빈 폴더 관성 금지」)
- FE API 레이어의 생성 client 전면 전환 — [BL-717] PoC 가 먼저다

## Consequences

- **이행 함정 4종을 게이트로 봉인했다** — ① ci.yml paths-filter 글롭(미수정 시 CI 전량 skip+초록)
  ② `final-gates.sh` 의 diff 접두 영역 판정 ③ compose 프로젝트명 파생(위) ④ 이동 스크립트의
  `SCRIPT_DIR/..`·`parents[N]`·`__dirname` 류 **깊이 파생**(리터럴 grep 에 안 걸린다 — 26개 셸 +
  py/ts 11곳을 전수 재계산했고, 전량 pytest·vitest·게이트 하네스 9종이 재발을 문다).
- **롤아웃 lockstep 필요** — 소크 서버의 systemd 유닛과 맥 LaunchAgent 가 구 `scripts/` 절대경로를
  굽고 있어 pull 전 uninstall → pull → 재설치 순서가 필수다([BL-719]). 워크트리는 전부 재생성.
- 롤백 = squash 머지 1커밋 revert (역-리네임 자동 생성). 볼륨은 프로젝트명 유지로 무손실.
  untracked 로컬 상태(.env.local·.venv·node_modules·.metrics)는 git 이 옮기지 않으므로 이행/롤백
  체크리스트가 별도로 다룬다([BL-719] 본문).
