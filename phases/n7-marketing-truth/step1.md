# Step 1: 요금제 화면 — 표와 카피를 SSOT 에 맞춘다

## 읽어야 할 파일

- **`phases/n7-common.md`**
- **Step 0 의 `summary`** — 새 `status` 어휘와 disclaimer 문구 전문이 거기 있다. **그대로 써라**
- `apps/web/src/app/pricing/page.tsx` — **대상**
- `apps/web/src/app/pricing/__tests__/page.test.tsx`
- `apps/web/src/lib/marketing-canon.ts` — Step 0 이 고친 SSOT (**읽기만**)

## 착수 전 실측 (2026-08-24 · CONTROL)

`pricing/page.tsx` 안:

- 파일 머리 주석 `:3` — 「OKX/Binance/Bitget 은 로드맵으로만 표기(§4.8). 공개 판매 전 · 사용자 1명」
- `:83` 기능 표 행 — `{ label: "OKX · Binance · Bitget 연동", cells: [road, road, road] }`
- `:300` — `OKX · Binance · Bitget 연동 <span className="chip">로드맵</span>`
- 본문에 **메인넷 1건 · OKX 4건**

★줄 번호는 움직인다. **먼저 재라.**

## 작업

1. 메인넷 주장을 제거한다 — 지원 범위는 **Bybit 데모**다.
2. OKX·Binance·Bitget 표기를 Step 0 의 새 어휘로 바꾼다. **「로드맵」 칩을 그대로 두지 마라.**
   ★`road` 셀 헬퍼의 **이름과 라벨**도 함께 봐라 — 이름이 `road` 인 채로 두면 다음 사람이
   또 「로드맵」으로 읽는다.
3. 파일 머리 주석(`:3` 부근)도 고쳐라. ★**주석이 코드보다 앞서 나가면 그게 다음 회차의 함정이다** —
   이 레포가 반복해 겪었다.
4. `page.test.tsx` 의 기대를 새 계약으로 맞춘다.
   ★**단언을 지워서 통과시키지 마라** — 「OKX 가 로드맵으로 보인다」를 재던 단언이 있으면
   그것을 **「지원하지 않음으로 보인다」**로 **바꿔라.**

## Acceptance Criteria

1. `cd apps/web && pnpm exec vitest run src/app/pricing src/lib/__tests__/marketing-canon.test.ts`
2. `test "$(grep -c '메인넷' apps/web/src/app/pricing/page.tsx)" -eq 0`
3. `test "$(grep -ci 'okx' apps/web/src/app/pricing/page.tsx)" -eq 0`
4. `test "$(grep -c 'Bybit' apps/web/src/app/pricing/page.tsx)" -ge 1`
5. `cd apps/web && pnpm exec biome check src/app/pricing`
6. `cd apps/web && pnpm exec tsc --noEmit`

★**AC 3 은 「OKX 를 이 화면에서 아예 안 쓴다」**를 뜻한다. 미지원 목록을 화면에 남기고 싶으면
**SSOT(`EXCHANGE_SUPPORT`)에서 렌더**해라 — 화면에 거래소 이름을 **다시 적지 마라.**
그게 이 SSOT 가 존재하는 이유다(파일 머리 주석: 「화면마다 지어내는 것을 막는다」).
★**AC 4 가 양성 대조다** — 화면에서 거래소 이야기를 통째로 지우는 우회로를 막는다.
★착수 전 실측: AC 2 는 1건, AC 3 은 4건이라 **지금 둘 다 red 다.**

## `summary` 에 반드시 담을 것

- 고친 좌표 (재측정값)
- `road` 류 헬퍼/변수 이름을 무엇으로 바꿨는지
- OKX 이름을 SSOT 렌더로 돌렸는지, 아니면 화면에서 제거했는지와 그 이유
- 뒤집은 테스트 단언 before/after

## 금지사항

- **화면에 거래소 이름을 새로 하드코딩하지 마라** — SSOT 에서 렌더해라 (AC 3 이 집행한다).
- **단언을 지워서 통과하지 마라. 고쳐라.**
- **가격 숫자를 채워 넣지 마라.** 이유: 파일 `:2` 가 「가격은 미정이라 비워 둔다」고 적었고
  그건 이 lane 의 주제가 아니다.
- **`docs/**` · `apps/api` 를 만지지 마라.**
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
