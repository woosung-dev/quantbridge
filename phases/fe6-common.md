# fe6-\* 공통 규약 — 밤샘 루프 6차 FE lane 전부가 이 문서를 따른다

★**이 파일은 step 파일이 경로로 참조한다.** 내용을 step 파일에 복사하지 마라 — 낡은 사본이 된다.

## 이 회차의 두 갈래

| 갈래                   | lane                       | 무엇을 바꾸나                                                        |
| ---------------------- | -------------------------- | -------------------------------------------------------------------- |
| **커버리지 (cov)**     | `fe6-api-*` · `fe6-hooks-*` | **테스트 파일만 신설한다. 대상 소스는 0줄도 고치지 마라**            |
| **부채 (debt)**        | `fe6-debt-*`               | **소스를 고친다.** 담당 디렉터리 밖의 파일은 건드리지 마라           |

두 갈래는 **파일이 겹치지 않도록** 배분했다(착수 전 CONTROL 실측: cov lane 대상인
`*/api.ts`·`*/hooks.ts`·`unrealized.ts` 에 부채 위반 **0건**). 그 전제를 깨지 마라.

## 읽어야 할 파일 (갈래 공통)

- `apps/web/AGENTS.md` — FE 규칙 본문. **§7~§11 TS 컨벤션**과 **§9 shadcn 직접 수정 금지**
- `apps/web/biome.jsonc` — 린터·포매터 SSOT. **주석이 규칙마다 「왜 이 값인가」를 적어 뒀다**
- `apps/web/vitest.config.ts` — `resolve.alias` 로 `server-only`·`next/font/google` 을 스텁으로
  바꾼다. **그 둘은 vitest 에서 top-level throw 라 alias 없이는 모듈 전체가 죽는다**

## mock 관용구 — 베끼지 말고 열어서 모양을 따라라

| 무엇을 쓸 때                | 정본 파일                                                       |
| --------------------------- | --------------------------------------------------------------- |
| `api.ts` 래퍼 인자 단언     | `src/features/backtest/__tests__/hooks.all-trades.test.ts` — `vi.mock("../api", async (importOriginal) => ...)` 로 **일부만** 교체하는 모양 |
| React Query 훅 (`renderHook`) | `src/features/backtest/__tests__/hooks.stress-test.test.ts` — `renderHook` + `QueryClientProvider` 래퍼 |
| 스키마 파싱 단언            | `src/features/waitlist/__tests__/api.test.ts` — ★**이 파일은 이름과 달리 `api.ts` 를 한 줄도 실행하지 않는다**(스키마·query-keys 만 본다). 이름이 맞는 테스트는 증거가 아니다 |

★`apiFetch` 의 계약은 `src/lib/api-client.ts` 가 정본이다 — `params` 의 `undefined` 는 쿼리에서
**빠지고**, 204 는 `undefined` 를 반환하며, 실패는 `ApiError(status, code, ...)` 를 **throw** 한다.
`code` 는 `{"detail":{"code":…}}` 를 **한 겹 파고들어** 찾는다.

## AC 는 러너가 재실행한다 — 네가 통과시키는 것이 아니다

★**AC 는 그 프로젝트의 표준 러너만 쓴다.** 판정 전용 스크립트는 두지 않는다 — vitest·biome·
coverage 가 이미 필요한 것을 **rc 로** 답하기 때문이다(2026-08-22 실측으로 확인하고 판정기 3종을 지웠다).

| 갈래 | AC 구성 |
| --- | --- |
| cov lane | ⑴ `test -f` **새 테스트 파일이 실제로 있는가** ⑵ `vitest run <새 파일> --coverage --coverage.include=<대상> --coverage.thresholds.perFile --coverage.thresholds.lines=N` ⑶ `git diff --quiet -- <대상 소스>` |
| debt lane | ⑴ `biome lint --only=<규칙…> <담당 경로>` ⑵ 담당 범위 `vitest run` 회귀 |

★**⑴ 이 있는 이유** — **vitest 는 인자 중 없는 파일을 조용히 무시한다**(있는 것 1 + 없는 것 1 → rc=0,
실측). 그게 없으면 테스트 파일을 일부만 만들어도 나머지 AC 가 통과할 수 있다.
★**`perFile` 이 핵심이다** — 대상이 여럿인 lane 에서 **각 파일이** 하한을 넘어야 한다.
한 파일을 몰아서 덮고 나머지를 비워 두면 통과하지 못한다.
★**커버리지 하한을 채우려고 단언 없는 케이스를 늘리지 마라.** 커버리지는 실행만 해도 오른다 —
사람이 diff 를 읽을 때 걸린다.

## 금지사항 (갈래 공통)

- **커밋하지 마라.** 커밋은 러너 소관이다
- **`docs/**` 를 만지지 마라.** 이유: lane 12벌이 같은 원장 파일을 고치면 병합이 통째로 충돌한다
- **`biome.jsonc` 를 만지지 마라.** 이유: 12 lane 이 공유하는 유일한 설정 파일이다.
  ★**부채 lane 이 규칙을 켜고 싶어도 켜지 마라** — 위반이 남은 파일이 하나라도 있으면
  `lint-staged` 의 `biome check --write` 가 **그 파일을 건드리는 모든 커밋을 막는다**.
  규칙 활성화는 12 lane 이 전부 머지된 뒤 CONTROL 이 한 번에 한다
- **`src/components/ui/**` 를 고치지 마라.** 이유: shadcn 생성물이라 `shadcn add` 와 영구 드리프트가 난다(`apps/web/AGENTS.md` §9)
- **`src/styles/globals.css` 의 KITPORT 구간을 만지지 마라.** 이유: `_kit.html` 과 바이트 대조로
  묶여 있어(`src/__tests__/design-canon-kit-port.test.ts`) 포맷만 해도 즉시 red 다
- **`.skip`·`.only`·`xfail`·`@ts-expect-error` 로 통과시키지 마라.** 막히면 `blocked` 를 써라
- **다른 lane 의 디렉터리를 고치지 마라.** 배분표는 `phases/README.md` 의 6차 절에 있다

## 사람 개입이 필요하면

`index.json` 의 그 step 에 `"status": "blocked"` 와 `"blocked_reason"`(무엇이 왜 막혔는지 —
증거가 되는 명령과 출력 요약)을 쓰고 **즉시 중단**한다. ★**추측으로 소스를 고쳐 통과시키지 마라.**
5차에서 `blocked` 하나가 **진짜 제품 결함**([BL-819])을 잡았다 — 막히는 것은 정당한 출구다.

## `summary` 에 무엇을 적나

다음 step 이 문맥 없이 이어받는다. **다음 step 에 쓸모 있는 것만** 적어라:

- 이번 step 이 덮은 심볼과 **아직 안 덮은 심볼**
- 대상이 실제로 어떻게 동작했는지 중 **네 예상과 달랐던 것** (★이것이 가장 값이 크다)
- mock 을 어디에 걸었는지 (다음 step 이 같은 자리를 다시 찾지 않도록)
