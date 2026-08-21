# ADR-039 — FE 포매터·린터를 Biome 으로 옮기고, ESLint 는 React 안전 3축만 남긴다

- **상태:** Accepted (2026-08-21)
- **범위:** `apps/web` (+ 루트 lint-staged 배선)
- **관련:** [ADR-035](./035-fe-component-ownership.md)(레이어 경계) · [ADR-036](./036-tool-version-ssot-mise.md)(도구 버전 SSOT) · [ADR-037](./037-harness-zero-base.md)(게이트 제로베이스)

## 결정

1. **prettier 와 ESLint 를 레포에서 완전히 제거한다.** 설정 4개(`.prettierrc` ·
   `.prettierignore` ×2 · `eslint.config.mjs`)와 패키지 9개를 지운다.
2. **`apps/web` 의 포맷·린트는 Biome 2.5.9 단독**이다 (`apps/web/biome.jsonc` 하나).
3. **검사 4종을 잃는다.** 아래에 무엇을·왜·무슨 대안을 시도했는지 남긴다 — 이 절이 이 ADR 의
   본체다. 「없앴다」보다 「무엇이 이제 안 잡히는가」가 다음 사람에게 필요한 정보다.

> ★**초판(2026-08-21)은 「ESLint 는 못 없앤다」였다.** 사용자 판단으로 검사 4종을 포기하고
> 도구를 하나로 줄였다(2026-08-22). 아래 실측은 그대로 유효하다 — **못 하는 것의 목록**이지
> 남겨야 하는 이유가 아니다.

## 무엇을 잃었나 — 실측 4건

전부 2026-08-21 에 이 레포의 실제 트리로 잰 값이다.

### ⑴ `set-state-in-effect` / `set-state-in-render` — 대응 규칙이 없다

Biome 2.5.9 의 **523 규칙 전수**(스키마 파싱)에서 React 관련 56건을 뽑아 대조했다. 두 규칙에
해당하는 것이 **없다.** 무한루프 3형태를 심은 프로브로 확인:

| 프로브 | ESLint | Biome (`react:all` + `next:all` + recommended) |
| --- | --- | --- |
| `useEffect(() => setV(n+1), [n])` | ✅ error | **0건** |
| deps 없는 `useEffect(() => setC(c+1))` | ✅ error ×2 | **0건** |
| **양성 대조** (조건부 훅 · array index key) | — | ✅ 2/2 검출 — 검사기는 살아 있었다 |

이 축이 [LESSON-004](../lessons.md)(CPU 100% 무한루프 실사고)의 방어선이다.

**GritQL 플러그인으로 복원을 시도했고 실패했다.** v1 은 프로브 2/2 를 맞혔지만 실트리에서
**11/11 오탐**이었다 — `setTimeout(() => setX())` 같은 비동기 경계, `ref` 비교 가드
(AGENTS.md §H-1 이 권장하는 바로 그 탈출구)를 구문 매칭으로는 못 가른다. 직계 문장만 보게
좁힌 v2 는 프로브에서 **0 검출**로 무너졌다. 이 규칙은 의미 분석이지 패턴 매칭이 아니다.

### ⑵ `react-compiler` — Biome 대체분이 **한글에서 크래시한다**

`nursery/useReactCompiler` 는 진단 위치를 바이트 오프셋으로 자르는데 multi-byte UTF-8 경계를
보지 않는다. 이 레포는 규약상 주석·문자열이 한국어라 **13 파일**이 이렇게 죽는다:

```
processing panicked: start byte index 1799 is not a char boundary; it is inside '제'
```

음성 대조 — 이 규칙만 제외하면 panic **0**. 2.5.9 가 최신이라 올릴 버전도 없다.

### ⑶ `@tanstack/query/exhaustive-deps` — 대응 규칙 0건

queryKey 안정성(AGENTS.md §H-2). Biome 에 없고, 클로저 캡처 추적이라 GritQL 로도 안 된다.

### ⑷ 템플릿 리터럴 동적 import — `no-restricted-syntax` 한 갈래만 남았다

ADR-035 경계의 정적/동적 import 는 Biome 의 `noRestrictedImports` 가 **더 잘** 본다(동적
`import()` 네이티브 지원 — ESLint 는 AST 선택자를 따로 세워야 했다). 못 보는 것은
``import(`@/app/${x}`)`` 하나뿐이라 그 선택자만 ESLint 에 남겼다.

## 포기한 것

### tailwind 클래스 자동 정렬 — **`useSortedClasses` 가 코드를 깨뜨린다**

`prettier-plugin-tailwindcss` 의 대체품으로 켰다가 vitest 가 잡았다:

```diff
- className={"order-side " + o.side}   // "order-side buy"
+ className={"order-side" + o.side}    // "order-sidebuy"  ← 클래스가 사라진다
```

문서에 적힌 "Whitespace is collapsed" 가 **런타임에 연결되는 문자열의 유의미한 끝 공백**까지
지운다. 마침 그 클래스를 세는 테스트가 있어서 걸렸다 — 없었으면 조용히 통과했다.

품질 차이도 별도로 있다. prettier 가 정렬해 둔 트리에 이 규칙을 걸면 **337 파일 / 1,413줄**이
갈리고, Biome 은 접두사 단위로 뭉쳐 `font-bold font-display`(weight 가 family 앞)처럼 뒤집는다
(실측 열화 45줄). 단 **prettier 플러그인도 우리 테마를 안 읽고 있었다** — 레포에
`tailwind.config.*` 가 없고(v4 CSS-first) `.prettierrc` 에 `tailwindStylesheet` 도 없었다.

⇒ **정렬은 사람이 한다.** 되살리려면 위 공백 결함이 고쳐졌는지부터 재라.

### md · yml · yaml 포맷 (201 파일)

Biome 2.5.9 는 이 셋을 **파싱 중(⌛️)**이고 포맷을 못 한다. prettier 제거와 함께 이 파일들의
자동 정렬이 사라진다. **게이트였던 적이 없다** — CI 에 md/yaml 포맷 검사는 0건이었다.

## 경계 — 누가 무엇을 맡나

| 대상 | 주인 |
| --- | --- |
| `apps/web` 의 ts · tsx · mjs · css · json | **Biome** (포맷 + 린트) |
| `set-state-in-effect`·`-in-render` · react-compiler · tanstack queryKey · 템플릿 리터럴 import | **없음 — 사람이 지킨다** |
| md · yml · yaml · 레포 루트 json | **없음** (수동) |

★**hooks 축 2종은 Biome 으로 돌아왔다.** 초판에서 `useExhaustiveDependencies` /
`useHookAtTopLevel` 을 껐던 이유는 「ESLint 가 단독 판정자」였기 때문인데 그 도구가 없어졌다.
단 `reportUnnecessaryDependencies: false` 는 필수다 — 기본값이면 7건이 뜨는데 전부
「남는 dep」이고 그 대상이 `themeKey`·`data`, 즉 effect 가 읽지 않고 **트리거로만 쓰는** 값이라
따르면 테마를 바꿔도 차트가 안 다시 그려진다.

## 제외 경로 3종 (`biome.jsonc` `files.includes`)

| 경로 | 이유 |
| --- | --- |
| `src/components/ui` | AGENTS.md §9 가 shadcn 직접 수정을 금지. `useImportType` 이 7파일을 고쳤다 |
| `src/styles/globals.css` | KITPORT 구간이 `_kit.html` 과 **바이트 대조**. 맡겼더니 테스트 3건 red |
| `**/generated` | 코드젠 산출물 — 재생성마다 diff |

## 측정

| 항목 | 전 (eslint+prettier) | 후 (Biome 단독) |
| --- | --- | --- |
| **도구** | 2 | **1** |
| **설정 파일** | 4 | **1** |
| **설정 실효 줄**(주석 제외) | 109 | **98** |
| FE lint | eslint **16.0s** | biome **0.2s** |
| FE format | **게이트 없음** (트리의 379파일이 미정렬이었다) | biome 0.1s |
| **CI frontend 잡** | 233.6s (직전 5회 평균) | **186s** → ESLint 제거 후 재측정 필요 |
| `apps/web` 패키지(transitive) | 1,034 | **813** |
| 제거 패키지(직접) | — | prettier · prettier-plugin-tailwindcss · eslint · eslint-config-next · eslint-config-prettier · @typescript-eslint/parser · eslint-plugin-react-hooks · eslint-plugin-react-compiler · @tanstack/eslint-plugin-query (**9**) |
| 추가 패키지 | — | `@biomejs/biome` (**1**) |
| 디스크 | — | **+61MB** (네이티브 바이너리) |

★**설정이 도입 전보다 작아진 것은 최소화를 실측했기 때문이다.** 초판 설정은 실효 165줄이었고,
각 항목을 하나씩 빼서 `biome check` 의 rc·진단수를 대조해 **잉여 13건**을 걷어냈다 —
`indentWidth`·`quoteStyle`·`semicolons`·`trailingCommas` 등은 **Biome 기본값과 같은 값**이었다.
⚠️단 `assist.organizeImports: "off"` 는 **빼면 안 된다** — 지우면 import 정렬이 켜져 303파일이 어긋난다.

★★**「진단이 안 늘어난다」를 「잉여」로 읽으면 안 된다.** 그 스윕이 `noUnusedVariables` 와
`useImportType` 을 잉여로 분류했는데, 판별력 배터리가 **위반을 심자 green** 을 냈다 —
위반이 0이었을 뿐 recommended 가 안 켜 주는 규칙이었다. 설정을 줄일 때는 **위반을 심어
다시 잡히는지**까지 봐라. 이 두 줄은 되살렸다.

★**대량 리포맷 374 파일은 Biome 의 비용이 아니다.** ts/tsx 포맷 게이트가 **애초에 없었고**
(`lint-staged` 는 `*.{json,md,yml,yaml}` 에만 prettier 를 걸었다), prettier 로 게이트를 세워도
같은 379 파일이 바뀐다. 실제로 Biome 출력은 prettier 출력과 **바이트 동일**하다 — Biome 이
맡는 전 파일에서 불일치 0(단 `css.parser.tailwindDirectives` 필수, 끄면 globals.css 6건 갈림).

## 검증

### ⑴ 게이트 초록

`biome check` rc=0 · `eslint` rc=0 · `tsc --noEmit` rc=0 · `vitest` **1896/1896** · `next build` rc=0.
CI(PR #769) — backend · frontend · live-smoke **전부 SUCCESS**.

### ⑵ 판별력 — 위반을 심어 「누가 무엇을 잡나」를 전수 측정 (10/10)

초록은 게이트가 옳다는 증거가 아니다. 이 레포에서 검사기가 무증거를 낸 적이 여러 번이라
([LESSON-124]) 케이스마다 임시 파일 1개를 심고 rc 를 직접 읽었다(파이프·`tail` 없이 python).

**최종 배터리 (Biome 단독, 18케이스 · 18/18 일치, 2026-08-22)**

| 심은 위반 | 기대 | 실측 |
| --- | --- | --- |
| 포맷 위반 | RED | **RED** |
| `noUnusedVariables` · `useImportType` | RED | **RED** |
| ADR-035 정적 `import` · 동적 `import("@/app/x")` | RED | **RED** |
| rules-of-hooks(조건부 훅) · exhaustive-deps(빠진 dep) | RED | **RED** |
| `<img>` · 동기 script · iterable key 없음 · img alt 없음 · 포커서블 aria-hidden | RED | **RED** |
| **제외 경로** `src/components/ui` · `**/generated` | green | **green** |
| **[상실]** `set-state-in-effect` | green | **green** |
| **[상실]** `react-compiler`(props 변이) | green | **green** |
| **[상실]** tanstack queryKey | green | **green** |
| **[상실]** 템플릿 리터럴 import | green | **green** |

「상실」 4행은 **green 이 나오는 것이 정상**이다 — 그 축에 판정자가 없음을 배터리가 명시적으로
기록한다. 다음 사람이 「왜 안 잡히지?」를 다시 조사하지 않게 하려는 것이다.

기준선(무변경 트리) 및 배터리 종료 후 트리 모두 green · dirty 0 — 배터리가 트리를 오염시키지 않았다.

★**이 배터리가 내 오독 1건을 잡았다.** `react-compiler` 초판 프로브(`render 중 ref.current = v`)가
green 을 냈다. 배선이 죽은 줄 알았으나 `eslint --print-config` 로 규칙이 `[2]` 로 살아 있음을
확인했고, props 변이로 바꾸자 즉시 red 였다 — **틀린 것은 게이트가 아니라 내 프로브**였다.
그 과정에서 §H-3 드리프트(아래)가 드러났다.

### ⑶ 멱등성 · 재현성 · 상호 안정성

| 축 | 결과 |
| --- | --- |
| 멱등성 | `check --write` 2회 → 변경 **0 · 0** |
| **재현성** | 소스를 이전 커밋으로 되돌린 뒤 재포맷 → 트리 해시가 **기준과 바이트 동일**(`2e95352622ecaeb9`) |
| 상호 안정성 | `format --write` 뒤 `lint` rc=0 · `ci` rc=0 · dirty 0 (서로를 안 깨뜨린다) |
| 성능 | `biome ci` 0.33s · `format` 0.13s · `lint` 0.22s |

## 곁다리 발견 — `apps/web/AGENTS.md` §H-3 이 낡았다

§H-3 은 「render phase 에서 `ref.current = x` 대입을 `eslint-plugin-react-compiler` 가
"Cannot access refs during render" 로 error 차단한다」고 적는다. **현재 핀(19.1.0-rc.2)에서
그 모양은 발화하지 않는다**(최소 재현으로 실측 green). 규칙 자체는 살아 있다 — props 변이는
error 로 잡는다. §H-3 의 **권고는 유효**하되 「lint 가 막아 준다」는 부분이 보증되지 않는다.
