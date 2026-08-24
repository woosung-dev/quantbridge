# Step 0: 마케팅 공동 원장(SSOT)을 **결정 ⑴⑶ 에 맞춘다**

## 읽어야 할 파일

- **`phases/n7-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- **`docs/PRD.md` §0 · §3 · §4** — 사용자 결정 3건과 범위/비범위. **이 lane 의 판정 근거다**
- `apps/web/src/lib/marketing-canon.ts` — **이번 lane 의 SSOT** (3화면이 이걸 렌더한다)
- `apps/web/src/lib/__tests__/marketing-canon.test.ts` — 그 불변식
- `apps/web/src/components/exchange-support-table.tsx` + `src/components/__tests__/exchange-support-table.test.tsx`

## 배경 — 무엇이 어긋났나

**2026-08-23 사용자 결정 3건**(`docs/PRD.md` §0):
⑴ **실자금(mainnet) 안 간다** — 계정 모드는 **Bybit Demo 만**
⑵ Beta 외부 공개 안 연다 ⑶ **멀티 거래소 안 한다 — Bybit 하나**

그런데 `marketing-canon.ts` 는 이렇게 적고 있다:

```ts
{ exchange: "Bybit", environment: "메인넷", status: "supported", scope: "주문 · 포지션 · TP/SL" },
{ exchange: "OKX",   environment: null, status: "roadmap", scope: null },
{ exchange: "Binance", ... "roadmap" ... },
{ exchange: "Bitget",  ... "roadmap" ... },
```

- **메인넷을 `supported` 라 선언한다** ⇒ 결정 ⑴ 과 정면 충돌.
  PRD §3 의 트레이딩 계약은 **「Bybit Demo 만」**이다.
- **OKX·Binance·Bitget 을 `roadmap` 이라 부른다** ⇒ 결정 ⑶ 은 **「안 한다」**다.
  「로드맵」은 **순서를 정해 뒀다**는 뜻이라 사실이 아니다. PRD §4 는 이 셋을 **비범위**로 적었다.

★**FE 는 이미 좁아져 있다** — `src/features/trading/schemas.ts:114` 가 `z.enum(["bybit"])` 다.
**마케팅 카피만 옛 범위를 말하고 있다.** PRD §4 는 「산문으로 슬쩍 넓히지 마라」고 적었는데
**산문이 이미 넓혀 놓은 상태**다.

★★**BE 의 OKX 어댑터는 이 lane 의 범위가 아니다** — PRD §0 ⑶ 이 **「더 안 키운다」**라고
명시했다(제거가 아니다). `apps/api` 를 건드리지 마라.

## 설계 결정 (CONTROL 이 정했다 — 임의로 바꾸지 마라)

**⑴ `EXCHANGE_SUPPORT` 는 Bybit **데모** 한 행만 남긴다.** 메인넷 행 삭제.

**⑵ 「로드맵」이라는 말을 버린다.** OKX·Binance·Bitget 은 **「지원하지 않음 · 추가 계획 없음」**이다.
`status` 유니언의 `"roadmap"` 을 그 뜻을 담은 이름으로 **바꾸고**(예: `"unsupported"`),
`ROADMAP_DISCLAIMER` 문구도 **미래를 약속하지 않는 현재형**으로 다시 쓴다.
★행 자체를 지울지 남길지는 네 재량이다 — **남기는 편이 「무엇이 안 되는지」를 보여줘 더 정직하다.**
다만 남긴다면 라벨이 「로드맵」이면 안 된다.

**⑶ 관련 상수·caption 도 함께 정합한다** — `EXCHANGE_NO_ENV_TITLE`·`EXCHANGE_NO_SCOPE_TITLE`·
`EXCHANGE_TABLE_CAPTION` 이 「연결 작업을 시작하지 않아」/「로드맵 행은」이라고 말한다.

## ★★이 step 의 함정 — 공허해지는 불변식

`marketing-canon.test.ts` 에는 이런 케이스가 있다:

```ts
it("keeps roadmap rows as environment and scope no-data pairs", ...)   // 0행이면 공허하게 참
it("contains both roadmap and supported rows", ...)                    // 0행이면 red
it("keeps OKX on the roadmap and limits supported exchanges to Bybit", ...)
```

⇒ **첫 케이스는 행이 0이 되면 아무것도 안 재고 통과한다.** 둘째는 red 가 난다.
**둘 다 「고쳐야 할」 것이지 「지워야 할」 것이 아니다.**
새 계약(지원 1행 + 미지원 N행)을 **같은 강도로** 다시 못박아라 — 특히
**「supported 행은 정확히 1행이고 그 environment 는 데모다」**를 단언해라.

## 작업

1. **PRD §0·§3·§4 를 먼저 읽어라.** 이 lane 의 모든 판정 근거가 거기 있다.
2. `marketing-canon.ts` 를 위 설계 결정대로 고친다.
3. `exchange-support-table.tsx` 가 새 `status` 값을 렌더하도록 맞춘다.
4. **두 테스트 파일의 불변식을 새 계약으로 다시 쓴다** (지우지 말고 고쳐라).
   ★**공허성 방어를 반드시 남겨라** — 「supported 정확히 1행」 · 「미지원 행 ≥ 1」.

## Acceptance Criteria

1. `cd apps/web && pnpm exec vitest run src/lib/__tests__/marketing-canon.test.ts src/components/__tests__/exchange-support-table.test.tsx`
2. `test "$(grep -c '메인넷' apps/web/src/lib/marketing-canon.ts)" -eq 0`
3. `test "$(grep -c '로드맵' apps/web/src/lib/marketing-canon.ts)" -eq 0`
4. `test "$(grep -c 'exchange:' apps/web/src/lib/marketing-canon.ts)" -ge 1`
5. `test "$(grep -c 'Bybit' apps/web/src/lib/marketing-canon.ts)" -ge 1`
6. `cd apps/web && pnpm exec biome check src/lib src/components/exchange-support-table.tsx`
7. `cd apps/web && pnpm exec tsc --noEmit`

★**AC 4·5 가 양성 대조다** — 표를 통째로 비워서 부재 단언을 통과하는 우회로를 막는다.
★착수 전 실측(2026-08-24): AC 2 는 **2건**, AC 3 은 **10건**이라 **지금 둘 다 red 다.** 정상이다.

## `summary` 에 반드시 담을 것

- `status` 유니언을 **무엇으로 바꿨는지**와 그 이유 (다음 step 들이 같은 어휘를 쓴다)
- `EXCHANGE_SUPPORT` 최종 행 구성
- 새 disclaimer 문구 **전문** (다음 step 이 화면에서 같은 문자열을 써야 한다)
- 고친 불변식 목록과 **각각이 무엇을 막는지**

## 금지사항

- **불변식 테스트를 지워서 통과하지 마라.** 이유: 그것이 이 SSOT 의 유일한 방어선이다. 고쳐라.
- **`apps/api` 를 건드리지 마라.** 이유: BE 의 OKX 어댑터는 PRD §0 ⑶ 이 **존치**로 정했다.
- **`docs/**` 를 만지지 마라** (PRD 갱신은 CONTROL 이 통합 PR 에서 한다).
- **성능 3값(`PERF_FIGURES`)을 건드리지 마라.** 이유: 이 lane 의 주제가 아니고 파생 불변식이 걸려 있다.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
