# ADR-039 — FE 포매터·린터를 Biome 으로 옮기고, ESLint 는 React 안전 3축만 남긴다

- **상태:** Accepted (2026-08-21)
- **범위:** `apps/web` (+ 루트 lint-staged 배선)
- **관련:** [ADR-035](./035-fe-component-ownership.md)(레이어 경계) · [ADR-036](./036-tool-version-ssot-mise.md)(도구 버전 SSOT) · [ADR-037](./037-harness-zero-base.md)(게이트 제로베이스)

## 결정

1. **prettier 를 레포에서 완전히 제거한다.** 설정 3개(`.prettierrc` · `.prettierignore` ×2)와
   패키지 2개(`prettier` · `prettier-plugin-tailwindcss`)를 지운다.
2. **`apps/web` 의 포맷·린트 주력은 Biome 2.5.9** 다 (`apps/web/biome.jsonc`).
3. **ESLint 는 없애지 않는다.** Biome 이 **구조적으로 못 하는 3축**만 남기고 126줄 → 78줄로 줄인다.

## 왜 ESLint 를 못 없앴나 — 실측 4건

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
| React Hooks 4종 · react-compiler · tanstack query · 템플릿 리터럴 import | **ESLint** |
| md · yml · yaml · 레포 루트 json | **없음** (수동) |

★**한 축에 주인은 하나다.** Biome 의 `useExhaustiveDependencies` / `useHookAtTopLevel` 은
**껐다** — 남는 도구가 그 축의 단독 판정자여야 하고, hooks 의 공식 구현은 ESLint 쪽이다.
실제로 Biome 판은 7건이 어긋났는데 전부 「남는 dep」이었고 그 대상이 `themeKey`·`data`,
즉 effect 가 읽지 않고 **트리거로만 쓰는** 값이었다 — 지우면 테마를 바꿔도 차트가 안 다시 그려진다.

## 제외 경로 3종 (`biome.jsonc` `files.includes`)

| 경로 | 이유 |
| --- | --- |
| `src/components/ui` | AGENTS.md §9 가 shadcn 직접 수정을 금지. `useImportType` 이 7파일을 고쳤다 |
| `src/styles/globals.css` | KITPORT 구간이 `_kit.html` 과 **바이트 대조**. 맡겼더니 테스트 3건 red |
| `**/generated` | 코드젠 산출물 — 재생성마다 diff |

## 측정

| 항목 | 전 | 후 |
| --- | --- | --- |
| FE lint | eslint 16.0s | biome 0.2s + eslint 12.4s |
| FE format | **게이트 없음** (트리의 379파일이 미정렬이었다) | biome 0.1s |
| `eslint.config.mjs` | 126줄 | 78줄 |
| 제거 패키지 | — | `prettier` · `prettier-plugin-tailwindcss` · `eslint-config-next` · `eslint-config-prettier` |
| 추가 패키지 | — | `@biomejs/biome` · `@typescript-eslint/parser`(파서 직접 물림) |
| 디스크 | — | **+10MB** (@biomejs 네이티브 바이너리 61MB) |

★**대량 리포맷 374 파일은 Biome 의 비용이 아니다.** ts/tsx 포맷 게이트가 **애초에 없었고**
(`lint-staged` 는 `*.{json,md,yml,yaml}` 에만 prettier 를 걸었다), prettier 로 게이트를 세워도
같은 379 파일이 바뀐다. 실제로 Biome 출력은 prettier 출력과 **바이트 동일**하다 — Biome 이
맡는 전 파일에서 불일치 0(단 `css.parser.tailwindDirectives` 필수, 끄면 globals.css 6건 갈림).

## 검증

`biome check` rc=0 · `eslint` rc=0 · `tsc --noEmit` rc=0 · `vitest` **1896/1896** · `next build` rc=0.
