# Step 1: `contracts/openapi/openapi.json` 재생성 — 계약 밖으로 나간 엔드포인트 4종을 되돌린다

## 읽어야 할 파일

- `apps/api/scripts/export_openapi.py` (헤더 주석이 실행법과 `--check` 계약을 갖는다)
- `docs/api/endpoints.md` 의 「계약 파일」 절

## 배경 (2026-08-30 실측)

게이트가 CI 밖이라 **회차 4개에 걸쳐** 엔드포인트가 계약 밖으로 나갔다. 지금 drift 는 845줄이고
빠진 것은 스키마가 아니라 **엔드포인트 4종 전량**이다:

- `/api/v1/llm/models`
- `/api/v1/strategies/generate`
- `/api/v1/strategies/{strategy_id}/brief`
- `/api/v1/strategies/{strategy_id}/brief/narrative`

## 작업

`contracts/openapi/openapi.json` 을 코드에서 재생성한다:

```
cd apps/api && set -a; . ./.env.local; set +a; uv run python scripts/export_openapi.py
```

★**계약을 코드에 맞춘다 — 코드를 계약에 맞추지 마라.** 위 4종은 [ADR-040]·[ADR-041]·[ADR-042]
와 PR #843 이 정당하게 추가한 실재 엔드포인트다. 계약 파일이 뒤처진 것이지 코드가 틀린 게 아니다.

★`.env.local` 통째 소싱은 의무다(AGENTS.md §5) — `DATABASE_URL` 만 단독 주입하지 마라.

## Acceptance Criteria

`phases/ci-gates/index.json` 의 step 1 `ac` 와 동일하다. 요지:
`mise run openapi-check` rc=0 · 위 4종 path 가 계약 파일에 **실재**(양성 대조: `paths` ≥ 20개).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. 두 번 돌려 byte-identical 인지 확인한다(export 는 결정적이어야 한다).
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/api/src/**` 를 수정하지 마라. 이유: 이 step 은 **산출물 갱신**이다. 코드가 같이 바뀌면
  diff 가 「무엇이 계약을 바꿨나」를 말하지 못한다.
- `export_openapi.py` 의 `APP_ENV`/`APP_NAME` 고정을 풀지 마라. 이유: 환경 파생값이 산출물에
  새면 drift 판정이 비결정이 된다(스크립트 헤더가 그 사고를 기록한다).
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
