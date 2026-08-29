# Step 0: PoC 생성물 5좌표 삭제 + `openapi-check` 2단 → 1단

## 읽어야 할 파일

- `docs/backlog.md` 의 `### BL-827` 섹션 (파급 7좌표를 전수로 갖는다)
- `mise.toml` 의 `[tasks.openapi-check]`
- `docs/api/endpoints.md` 의 「계약 파일」 절
- `docs/adr/031-api-contract-axis-poc.md` (특히 「도입 범위」·「롤백」 절)

## 배경 (2026-08-30 사용자 결정)

[ADR-031] 의 orval PoC 생성물은 **비교 산출물로서 수명이 끝났다.** 참조가 0건이고
재생성 절차가 어디에도 없어 소스(`openapi.poc.json`)와 어긋난 채 굳었다.
⇒ **삭제한다.** ADR-031 자신이 「PoC 산출물은 전부 추가 파일이라 무손실 제거된다」고 적어 뒀다.

## 작업

1. 아래 5좌표를 삭제한다 (2026-08-30 전수 확인 — 이 밖에 코드 참조는 없다):
   - `apps/web/src/lib/api-contract-poc/` — 디렉터리 통째. 생성물 2종 +
     `__tests__/zod-v4-coexist.test.ts`(**PoC 전용**이라 생성 스키마가 사라지면 잴 대상이 없다)
   - `apps/web/orval.poc.config.ts`
   - `contracts/openapi/poc/` — 디렉터리 통째 (`openapi.poc.json`)
   - `tools/scripts/openapi-poc-filter.py`
   - `apps/api/tests/scripts/test_openapi_poc_filter.py`
2. `mise.toml` 의 `[tasks.openapi-check]` 를 **2단 → 1단**으로 줄인다 — `cd ..` 와
   `python3 tools/scripts/openapi-poc-filter.py --check` 두 줄을 지우고 `description` 도
   「전량 + orval 부분집합 2단」에서 전량 1단을 말하는 문구로 고친다.
3. 문서 3곳:
   - `docs/api/endpoints.md` — 「소비 경로는 **두 단이다**」 문단을 1단 서술로 고친다.
     ★같은 절의 「CI `backend_static` 잡이 같은 검사를 한다」는 **거짓이다**(그런 잡은 존재한
     적이 없다). 이 lane 의 step 3 이 CI backend 잡에 `export_openapi.py --check` 스텝을
     넣는다 — 그 사실로 바꿔 적어라.
   - `docs/adr/031-api-contract-axis-poc.md` — **본문 결정·근거는 고치지 마라**(ADR 은 그때의
     결정 기록이다). 파일 맨 끝에 「## 후속 (2026-08-30)」 블록 하나만 덧붙여 ⑴ PoC 생성물
     5좌표 삭제 ⑵ 전면 전환은 여전히 미결정 ⑶ 게이트는 전량 1단만 CI 에 편입을 적는다.
   - `docs/adr/035-fe-component-ownership.md` 의 「⑶ 1단만 막고 2단은 열어 뒀다」 문단 —
     **그 반증 서사는 그대로 둔다**(그때의 사실이다). 문단 끝에 1줄만 덧붙인다:
     2026-08-30 에 2단(PoC)이 삭제돼 게이트는 1단만 남는다.

## Acceptance Criteria

`phases/ci-gates/index.json` 의 step 0 `ac` 와 동일하다. 요지:
잔존 0 · 코드/설정에 PoC 참조 0 · `mise.toml` 은 여전히 `export_openapi` 를 부른다(양성 대조) ·
FE `tsc --noEmit` clean · FE `biome check .` clean.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. 프로젝트 규약(디렉터리 구조·허용 스택·규칙 파일 필수 항목)을 벗어나지 않았는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `contracts/openapi/openapi.json` 을 이 step 에서 재생성하지 마라. 이유: **다음 step 의 판정
  대상**이다. 여기서 같이 바꾸면 무엇이 drift 를 지웠는지 diff 가 말하지 못한다.
- `.github/workflows/ci.yml` 을 이 step 에서 건드리지 마라. 이유: step 3 의 소관이고, 지금
  넣으면 아직 red 인 게이트를 CI 에 얹는 것이 된다.
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: 3 lane 이 공유하는 파일이라
  머지 충돌이 나고, 원장을 닫는 것은 회차 종료 시 사람이 한다.
- `apps/web/biome.jsonc` 의 무시 목록이나 `zod/v4` 규약을 손대지 마라. 이유: 삭제 파급 밖이다.
- 커밋하지 마라(커밋은 러너 소관).
