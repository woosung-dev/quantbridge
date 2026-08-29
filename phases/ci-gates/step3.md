# Step 3: `openapi-check` 와 `mypy` 를 CI backend 잡에 **차단 게이트**로 편입

## 읽어야 할 파일

- `.github/workflows/ci.yml` (특히 `jobs.backend` — `defaults.run.working-directory: apps/api`)
- `tools/scripts/ci-changed-scopes.sh` (어떤 변경이 backend 잡을 켜는지)
- `docs/backlog.md` 의 `### BL-827`

## 배경

`mise run openapi-check` 가 `ci.yml` 어디에서도 호출되지 않는다(`grep openapi ci.yml` = **0건**).
그래서 엔드포인트 4종이 계약 밖으로 나간 것을 아무도 못 봤다. mypy 도 [ADR-037] 제로베이스 때
철거된 뒤 돌아오지 않았다.

★**착수 전 실측으로 함정 하나가 사라졌다** — `mise run openapi-check` 는 `.env.local` 을 통째로
소싱하는데 **CI 엔 그 파일이 없다.** 2026-08-30 에 CI backend 잡이 **이미 갖고 있는 env 8종만으로**
`uv run python scripts/export_openapi.py --check` 가 rc=1(= drift 검출, 설정 크래시 아님)을 내는 것을
확인했다. `TRADING_ENCRYPTION_KEYS` 가 그 잡에 이미 있다. ⇒ 정말로 **스텝 2개**다.

## 작업

`.github/workflows/ci.yml` 의 `jobs.backend.steps` 에 스텝 2개를 추가한다.
자리는 **`uv run ruff check .` 다음, `uv run pytest` 앞**(싼 게이트를 먼저 태운다).

1. **계약 drift** — `uv run python scripts/export_openapi.py --check`.
   `env:` 블록은 같은 잡의 `uv run pytest` 스텝이 이미 갖고 있는 **8종을 그대로** 복사해 붙인다
   (`DATABASE_URL`·`TEST_DATABASE_URL`·`REDIS_URL`·`CELERY_BROKER_URL`·`CELERY_RESULT_BACKEND`·
   `REDIS_LOCK_URL`·`TRADING_ENCRYPTION_KEYS`). 새 secret 을 만들지 마라 — 필요 없다.
2. **타입** — `uv run mypy src`. 별도 env 가 필요 없다(`uv sync --all-extras --dev` 가 이미 돈다).

두 스텝 모두 **`continue-on-error` 를 붙이지 마라** — 2026-08-30 결정: 차단 게이트다.
왜 그 자리에 무엇이 왜 있는지 주석 1~2줄을 남겨라(이 파일의 기존 주석 밀도를 따라라).

★[ADR-037] 재입힘 규칙 — 「문서화된 사고 1건 = 슬림 복귀 1건」. 이번 복귀는 **최소판**이다:
잡을 새로 만들지 말고 기존 `backend` 잡에 스텝만 얹어라.

## Acceptance Criteria

`phases/ci-gates/index.json` 의 step 3 `ac` 와 동일하다. 요지:
`ci.yml` 을 **YAML 로 파싱**해 backend 잡 안에 두 스텝이 실재하고 `continue-on-error` 가 없음을
단언 · 양성 대조로 frontend 잡의 기존 스텝이 그대로 보임 · 두 게이트를 로컬에서 실제로 돌려 rc=0.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. YAML 들여쓰기가 기존 스텝과 같은 층인지 확인한다(잡을 잘못 물면 `working-directory` 가 달라져
   조용히 다른 곳에서 돈다).
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `on.paths` 를 쓰지 마라. 이유: 워크플로가 아예 안 돌아 required check 가 **영구 대기**한다
  (2026-08-26 에 이 레포가 밟은 함정 — `ci.yml` 헤더 주석이 기록한다). 경로 스코프는
  `changes` 잡 + `if:` 로 이미 돌아간다.
- `tools/scripts/ci-changed-scopes.sh` 와 그 테스트를 건드리지 마라. 이유: 이 lane 밖이고,
  `contracts/**` 는 지금 「분류 안 됨 → fail-safe 전량 실행」이라 게이트는 이미 발화한다.
- 새 잡(`backend_static` 같은 것)을 만들지 마라. 이유: 최소판 복귀 원칙 + 그 이름은 문서가
  존재한다고 거짓말했던 유령이다(step 0 이 그 문장을 지웠다).
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
