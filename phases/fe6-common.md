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

각 step 의 AC 는 다음 셋으로 구성된다. 형태는 `index.json` 의 `ac` 배열이 정본이다.

1. **vitest 실행** — 새 테스트 파일만 돌리고 `--coverage.include` 로 **대상 소스만** 잰다.
   산출물 2개(`coverage-summary.json` · `results.json`)를 `apps/web/coverage/<lane>/` 에 남긴다
   (그 경로는 `apps/web/.gitignore` 가 이미 무시한다)
2. **판정** — `python3 tools/harness/assert_fe.py` 가 케이스 수와 커버리지를 rc 로 답한다.
   ★**이 스크립트는 아무것도 실행하지 않는다** — ⑴ 이 만든 JSON 을 읽을 뿐이다
3. **소스 무변경** — `git diff --quiet -- <대상 소스>`. cov lane 에만 붙는다

★**케이스 수 하한을 채우려고 의미 없는 케이스를 늘리지 마라.** 그것은 AC 를 게임하는 것이고,
사람이 diff 를 읽을 때 걸린다. 하한은 「이만큼은 덮어야 대상을 실제로 실행한 것」의 최소치다.

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
