# Step 2: 랜딩 화면 — FAQ·기능 소개를 SSOT 에 맞춘다

## 읽어야 할 파일

- **`phases/n7-common.md`**
- **Step 0·1 의 `summary`** — 새 어휘와 disclaimer 문구. **같은 문자열을 써라**
- `apps/web/src/features/marketing/components/landing-faq.tsx` — **대상 ①**
- `apps/web/src/features/marketing/components/landing-features.tsx` — **대상 ②**
- 같은 디렉터리의 `__tests__`

## 착수 전 실측 (2026-08-24 · CONTROL)

`landing-faq.tsx:15` 원문:

> 「지금 연결되는 거래소는 Bybit 하나뿐입니다. **데모와 메인넷 두 환경을 지원합니다.**
> OKX 와 Binance, Bitget 은 **로드맵에 있을 뿐** 아직 연동 코드가 없습니다.」

★**앞 문장은 참이고 뒤 두 문장이 결정 ⑴⑶ 과 어긋난다.** 「Bybit 하나뿐」은 그대로 옳다.
`landing-features.tsx` 에도 메인넷 언급이 있다.

★★**이 카피는 「거짓말」이 아니라 「낡은 사실」이다** — 메인넷 주문은 [BL-024] 에서 실제로
넣어 확인한 적이 있다. 지금 문제는 **제품이 그것을 더 이상 제공하지 않는다**는 것이다.
그러니 「한 적 없다」로 바꾸지 말고 **「지금 무엇을 제공하는가」**로 바꿔라.

## 작업

1. FAQ 답변을 **현재 제공 범위**로 다시 쓴다 — Bybit **데모**.
2. 미지원 거래소 문장을 Step 0 의 새 어휘로 바꾼다(「로드맵에 있을 뿐」 금지).
3. `landing-features.tsx` 의 메인넷 언급을 같은 기준으로 정리한다.
4. 해당 `__tests__` 의 기대를 맞춘다 — **지우지 말고 고쳐라.**

## Acceptance Criteria

1. `cd apps/web && pnpm exec vitest run src/features/marketing src/lib/__tests__/marketing-canon.test.ts`
2. `test "$(grep -l '메인넷' apps/web/src/features/marketing/components/landing-faq.tsx apps/web/src/features/marketing/components/landing-features.tsx 2>/dev/null | wc -l | tr -d ' ')" -eq 0`
3. `test "$(grep -rli 'okx' apps/web/src/features/marketing 2>/dev/null | wc -l | tr -d ' ')" -eq 0`
4. `test "$(grep -c 'Bybit' apps/web/src/features/marketing/components/landing-faq.tsx)" -ge 1`
5. `cd apps/web && pnpm exec biome check src/features/marketing`
6. `cd apps/web && pnpm exec tsc --noEmit`

★**AC 3 은 `__tests__` 도 포함해 훑는다** — 테스트에 거래소 이름을 하드코딩해 두면 red 다.
SSOT 에서 렌더/import 해라.
★**AC 4 가 양성 대조**다. 착수 전 AC 2·3 은 **red** 다.

## `summary` 에 반드시 담을 것

- 새 FAQ 답변 **전문** (Step 3 이 부재 가드를 세울 때 대조군으로 쓴다)
- 「낡은 사실」을 어떻게 다뤘는지 — 과거 이력을 부정하지 않고 현재 범위를 말했는지
- 뒤집은 단언 before/after

## 금지사항

- **「한 적도 없다」로 쓰지 마라.** 이유: 메인넷 주문은 실제로 확인한 이력이 있다([BL-024]).
  거짓을 거짓으로 덮는 것이다. **현재 제공 범위**를 말해라.
- **미래 약속을 새로 만들지 마라** (「곧 지원 예정」 등). 결정 ⑶ 은 **안 한다**이다.
- **테스트에 거래소 이름을 하드코딩하지 마라** (AC 3 이 집행한다).
- **`docs/**` · `apps/api` 를 만지지 마라.**
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
