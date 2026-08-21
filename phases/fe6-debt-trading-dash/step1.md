# Step 1: 문자열 템플릿 + complexity 4종 — trading · live-sessions · dashboard · waitlist · components · lib 린트 부채 42건

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/biome.jsonc` — **이 회차가 갚는 부채가 이 파일 주석에 적혀 있다.**
  a11y 7종은 「미도래지 기각이 아니다 · 규칙 하나 = 수리 회차 하나」, `noArrayIndexKey` 는
  「되살릴 때는 고칠 회차와 함께」라고 적혀 있다. **그 회차가 이것이다**
- `apps/web/AGENTS.md` §9 — shadcn 직접 수정 금지

## 담당 범위 (★이 밖은 건드리지 마라)

- `apps/web/src/features/trading`
- `apps/web/src/features/live-sessions`
- `apps/web/src/features/dashboard`
- `apps/web/src/features/waitlist`
- `apps/web/src/features/alert-rules`
- `apps/web/src/features/realtime`
- `apps/web/src/components`
- `apps/web/src/lib`
- `apps/web/src/hooks`
- `apps/web/src/store`

## 착수 전 실측 (2026-08-22 · CONTROL)

검사 229파일 · 위반 **42건**

| 규칙 | 건수 |
| --- | --- |
| `suspicious/noArrayIndexKey` | 20 |
| `a11y/useAriaPropsSupportedByRole` | 6 |
| `style/useTemplate` | 5 |
| `a11y/useSemanticElements` | 4 |
| `a11y/noSvgWithoutTitle` | 4 |
| `a11y/noNoninteractiveTabindex` | 1 |
| `a11y/noRedundantRoles` | 1 |
| `a11y/useButtonType` | 1 |

## 이 lane 만의 사실

★★**`src/components/ui/**` 는 절대 고치지 마라**(shadcn 생성물 · `apps/web/AGENTS.md` §9).
  `biome.jsonc` 가 그 디렉터리를 `files.includes` 에서 이미 제외하므로 위반으로도 안 잡힌다 —
  잡히는 것은 `src/components/` 의 **나머지**다. 실수로 `ui/` 를 열지 마라.
★`noArrayIndexKey` 20건으로 이 lane 이 최대다. 주문·포지션 표가 많은데 그 행에는
  대개 `order_id`·`trade_id` 같은 안정 키가 **이미 있다** — 먼저 데이터를 봐라.
★`src/lib`·`src/hooks`·`src/store` 는 다른 lane 이 안 건드린다. 여기가 담당이다.

## 작업

`style/useTemplate` 와 `complexity` 4종을 0 으로 만든다.

- `useTemplate` — 문자열 결합(`"a" + b`)을 템플릿 리터럴로. ★★**공백을 잃지 마라.**
  2026-08-22 에 `useSortedClasses` 가 `"order-side " + side` 의 **끝 공백을 지워** 클래스명을
  뭉갠 전례가 있다. 결합 문자열의 앞뒤 공백을 눈으로 확인해라
- `noUselessFragments` — 자식이 하나뿐인 `<>…</>` 제거
- `noUselessSwitchCase` — `default` 와 같은 일을 하는 case 제거. ★**동작이 정말 같은지**
  확인하고 지워라
- `useOptionalChain` — `a && a.b` → `a?.b`. ★`a` 가 **`0`·`""` 일 때 의미가 달라지는 자리**가
  아닌지 봐라(falsy 와 nullish 는 다르다)
- `useLiteralKeys` — `obj["key"]` → `obj.key`

## Acceptance Criteria

1. `cd apps/web && pnpm exec biome lint --only=style/useTemplate --only=complexity/noUselessSwitchCase --only=complexity/noUselessFragments --only=complexity/useOptionalChain --only=complexity/useLiteralKeys src/features/trading src/features/live-sessions src/features/dashboard src/features/waitlist src/features/alert-rules src/features/realtime src/components src/lib src/hooks src/store`
2. `cd apps/web && pnpm exec vitest run src/features/trading src/features/live-sessions src/features/dashboard src/features/waitlist src/components src/lib src/hooks`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `phases/fe6-common.md` 의 금지사항을 어기지 않았는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`apps/web/biome.jsonc` 를 고치지 마라.** 이유: 12 lane 이 공유하는 유일한 설정 파일이라
  고치면 병합이 통째로 충돌한다. **규칙 활성화는 전 lane 머지 후 CONTROL 이 한 번에 한다.**
- **담당 범위 밖의 파일을 고치지 마라.** 이유: 다른 lane 이 그 자리를 맡고 있다.
- **`src/components/ui/**` 와 `src/styles/globals.css` 의 KITPORT 구간을 고치지 마라.**
- **테스트를 낮춰서 통과시키지 마라.** 회귀가 red 면 마크업 쪽을 다시 봐라.
- 커밋하지 마라(커밋은 러너 소관).
