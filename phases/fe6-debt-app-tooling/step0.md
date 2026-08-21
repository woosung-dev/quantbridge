# Step 0: 실사 + 안전 규칙군(svg title·button type·redundant role) — app 라우트 · e2e · scripts 린트 부채 41건

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/biome.jsonc` — **이 회차가 갚는 부채가 이 파일 주석에 적혀 있다.**
  a11y 7종은 「미도래지 기각이 아니다 · 규칙 하나 = 수리 회차 하나」, `noArrayIndexKey` 는
  「되살릴 때는 고칠 회차와 함께」라고 적혀 있다. **그 회차가 이것이다**
- `apps/web/AGENTS.md` §9 — shadcn 직접 수정 금지

## 담당 범위 (★이 밖은 건드리지 마라)

- `apps/web/src/app`
- `apps/web/src/__tests__`
- `apps/web/src/styles`
- `apps/web/e2e`
- `apps/web/scripts`

## 착수 전 실측 (2026-08-22 · CONTROL)

`src/app`+`__tests__`+`styles` 84파일 · **23건** / `e2e`+`scripts` 51파일 · **18건**

| 범위 | 규칙 | 건수 |
| --- | --- | --- |
| app 계열 | `suspicious/noArrayIndexKey` | 13 |
| app 계열 | `a11y/noSvgWithoutTitle` | 4 |
| app 계열 | `a11y/useSemanticElements` | 2 |
| app 계열 | `style/useTemplate` | 2 |
| app 계열 | `complexity/useOptionalChain` | 1 |
| app 계열 | `a11y/useButtonType` | 1 |
| e2e·scripts | `style/useTemplate` | 18 |

## 이 lane 만의 사실

★★★**`e2e/**`·`scripts/**` 의 `suspicious/noConsole` 15건은 이 lane 의 범위가 아니다.**
  그 자리의 `console.log` 는 **의도**다(테스트 러너·유틸 스크립트의 출력). 고치지 마라.
  그 15건은 CONTROL 이 규칙을 켤 때 `biome.jsonc` 의 `overrides` 로 면제한다.
  ⇒ 이 lane 의 AC 는 **범위를 둘로 나눠** 잰다: app 계열은 14규칙 전량, e2e·scripts 는
  `noConsole` 을 뺀 13규칙. AC 를 고치지 마라 — 그 비대칭이 의도다.
★`src/app/**` 은 [ADR-035] 의 라우트 조립층이다. `biome.jsonc` 의 `overrides` 가 이미
  이 범위에서 `noRestrictedImports` 를 끈다 — 라우트끼리의 참조는 금지 대상이 아니다.
★`e2e/**` 를 고치면 **playwright 스펙이 깨질 수 있다.** 이 lane 의 회귀 AC 에는
  playwright 실행이 없다(서버가 필요해서 AC 가 될 수 없다) — 그러니 `useTemplate` 수정은
  **문자열 결합을 템플릿 리터럴로 바꾸는 기계적 치환에서 벗어나지 마라.**

## 작업

1. **담당 범위의 위반을 전수 세라.** 아래 AC 의 첫 명령을 **`--min-files` 만 1 로 바꿔**
   먼저 돌려 보면 규칙별 건수가 나온다. 위 표와 다르면 **그 사실을 `summary` 맨 앞에 적어라.**
2. **이 step 의 규칙군만 0 으로 만든다** — `a11y/noSvgWithoutTitle` · `a11y/useButtonType` ·
   `a11y/noRedundantRoles`. 나머지 규칙은 **건드리지 마라**(step1~3 의 몫이고, 지금 손대면
   그 step 의 AC 가 착수 전에 이미 초록이라 판별력을 잃는다).
3. **수정 원칙**:
   - `noSvgWithoutTitle` — **의미 있는 아이콘**이면 `<title>` 을 넣는다. **장식이면**
     `aria-hidden="true"` 를 넣는다. 어느 쪽인지는 그 SVG 가 **정보를 나르는가**로 갈린다
   - `useButtonType` — `<button type="button">`. form 안의 제출 버튼만 `submit`
   - `noRedundantRoles` — 태그가 이미 그 role 이면 `role` 속성을 지운다

## Acceptance Criteria

1. `cd apps/web && python3 ../../tools/harness/assert_biome.py --rules a11y/noSvgWithoutTitle,a11y/useButtonType,a11y/noRedundantRoles --min-files 70 src/app src/__tests__ src/styles`
2. `cd apps/web && python3 ../../tools/harness/assert_biome.py --rules a11y/noSvgWithoutTitle,a11y/useButtonType,a11y/noRedundantRoles --min-files 40 e2e scripts`
3. `cd apps/web && pnpm exec vitest run src/app`

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
