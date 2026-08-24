# Step 3: 웨이트리스트·제품 화면 정리 + **부재 가드**를 세운다

## 읽어야 할 파일

- **`phases/n7-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- **Step 0~2 의 `summary`** — 새 어휘·문구. 같은 문자열을 써라
- `apps/web/src/features/waitlist/components/waitlist-faq.tsx` · `waitlist-hero.tsx` — **대상 ①②**
- `apps/web/src/features/live-sessions/components/live-session-form.tsx` — **대상 ③**
- `apps/web/src/app/privacy/page.tsx` · `src/app/terms/page.tsx` — 잔존분 확인용

## 착수 전 실측 (2026-08-24 · CONTROL)

`메인넷` 을 말하는 **소스 파일(테스트 제외) = 7개**. Step 0~2 가 4개를 처리했고
**이 step 이 남은 3개**를 맡는다:

| # | 파일 | 무엇이 문제인가 |
| --- | --- | --- |
| ① | `waitlist-faq.tsx:22` | 「Bybit 데모와 **메인넷**입니다. 두 환경 모두 … **실제로 주문을 넣어 확인했습니다**」 |
| ② | `waitlist-hero.tsx` | 메인넷 배지/문구 |
| ③ | `live-session-form.tsx` | 「**메인넷 출시 전까지**」 · 「메인넷은 안정성 검증 후 **단계적으로 활성화할 예정입니다**」 ⇒ **미래 약속.** 결정 ⑴ 은 안 간다이다 |

★③ 은 마케팅이 아니라 **제품 UI** 다. 사용자가 라이브 세션을 만들 때 보는 문구라
**가장 직접적인 약속**이다.

## 작업

1. ①②③ 의 문구를 결정 ⑴ 기준으로 고친다.
   ★③ 의 「단계적으로 활성화할 예정」 같은 **미래 약속은 지워라** — 대체 문구는 현재형으로.
2. `privacy/page.tsx` · `terms/page.tsx` 에 남은 언급이 있으면 같은 기준으로 정리한다.
3. 해당 `__tests__` 기대를 맞춘다 (지우지 말고 고쳐라).
4. **부재 가드를 신설한다** — `apps/web/src/lib/__tests__/decision-surface-guard.test.ts`
   - **소스 파일 목록을 명시**하고(≥7개 경로), 그 파일들에 `메인넷` 이 **없다**를 단언
   - ★★**양성 대조를 반드시 함께 둬라**: 「목록의 파일이 전부 **실제로 존재하고 읽혔다**」와
     「읽은 총 바이트 > 0」. 파일 경로가 오타면 부재 단언은 **닿지도 않고 참**이 된다
   - ★★★**금지 토큰을 이 테스트 파일에 리터럴로 적으면 자기 자신이 걸린다.**
     AC 는 `__tests__` 를 제외하고 훑지만, **가드가 자기 파일을 훑지 않도록** 목록을
     소스 파일로 한정해라. 토큰은 조각으로 조립하거나 상수로 분리해라
   - 결정 ⑶ 축(`okx` 등)도 같은 방식으로 한 케이스 더

## Acceptance Criteria

1. `test -f apps/web/src/lib/__tests__/decision-surface-guard.test.ts`
2. `cd apps/web && pnpm exec vitest run src/lib/__tests__/decision-surface-guard.test.ts`
3. `test "$(grep -c 'src/' apps/web/src/lib/__tests__/decision-surface-guard.test.ts)" -ge 7`
4. `test "$(grep -rl '메인넷' apps/web/src --include='*.ts' --include='*.tsx' 2>/dev/null | grep -v '__tests__' | wc -l | tr -d ' ')" -eq 0`
5. `cd apps/web && pnpm exec biome check src`
6. `cd apps/web && pnpm exec tsc --noEmit`
7. `cd apps/web && pnpm test -- --run`

★**AC 3 이 가드의 양성 대조다** — 파일 목록이 비거나 한두 개뿐인 가드를 막는다.
★**AC 7 은 FE 전량 회귀다.** 이 lane 이 3화면을 건드렸으므로 마지막에 한 번 전부 돌린다.
★착수 전 실측: AC 4 는 **7개 파일**이라 **지금 red 다.**

## ★변이 자기검사 (AC 로는 못 재니 `summary` 로 증명해라)

1. 가드를 세운 뒤, 소스 파일 하나에 `메인넷` 을 **한 줄 다시 심어라.**
2. 가드가 **red** 가 되는지 확인해라. 안 되면 그 가드는 아무것도 안 재고 있다.
3. **복원해라** — ★`git checkout` 금지. 스냅샷 되쓰기 + `sha256` 왕복 대조.
4. **음성 대조**: `__tests__` 안에 같은 토큰이 있어도 red 가 **아니어야** 한다(스코프 확인).

## `summary` 에 반드시 담을 것

- 고친 좌표 3개 + privacy/terms 처리 결과
- ③ 의 미래 약속 문구를 **무엇으로 대체했는지** (전문)
- **변이 결과**: 어디에 심었고 어떤 메시지로 red 였는지 · 복원 sha256 대조 · 음성 대조 결과
- 가드가 **못 잡는 것** (예: 이미지·번역 리소스·서버 응답 문자열)

## 금지사항

- **미래 약속을 다른 표현으로 바꿔 남기지 마라** (「추후」·「검토 중」 포함). 결정 ⑴ 은 안 간다이다.
- **금지 토큰을 가드 테스트에 리터럴로 적어 자기 자신을 잡게 만들지 마라.**
- **가드 파일 목록을 글롭으로만 두지 마라** — 경로를 명시해야 AC 3 이 의미를 갖는다.
  글롭을 쓰고 싶으면 **명시 목록과 함께** 쓰고 둘이 일치하는지 단언해라.
- **변이를 심은 채로 끝내지 마라** (AC 4 가 잡는다).
- **`docs/**` · `apps/api` 를 만지지 마라.**
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
