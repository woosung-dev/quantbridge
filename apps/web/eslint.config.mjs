// ESLint v9 flat config — **React 안전 축 전용**으로 좁혔다 ([ADR-039], 2026-08-21).
// 포맷·스타일·a11y·Next 규칙은 `biome.jsonc` 가 가져갔다. 여기 남은 것은
// **Biome 이 못 하는 일**뿐이고, 항목마다 「왜 못 하나」를 실측째로 적어 둔다.
//
// ┌ 왜 ESLint 가 안 없어지나 (2026-08-21 실측) ──────────────────────────────────┐
// │ ⑴ set-state-in-effect / -in-render : Biome 523 규칙에 **대응 규칙 없음**      │
// │     프로브 3형태 → ESLint 3검출 / Biome 0검출 (양성 대조 2/2 로 검사기 생존 확인) │
// │ ⑵ react-compiler                   : Biome 의 `useReactCompiler` 가 **한글에서 panic** │
// │     13 파일 `is not a char boundary; it is inside '제'` — 우리 규약이 한국어다  │
// │ ⑶ @tanstack/query/exhaustive-deps  : Biome 에 대응 규칙 **0건**               │
// │ ⑷ no-restricted-syntax (템플릿 리터럴): Biome 의 noRestrictedImports 는        │
// │     정적 import 와 동적 `import("...")` 는 보지만 `import(`@/app/${x}`)` 은 못 본다 │
// └──────────────────────────────────────────────────────────────────────────────┘
//
// ★`eslint-config-next` 를 뺐으므로 파서를 **직접** 물린다. 없으면 espree 가 TS 를 못 읽고
//   `Parsing error: Unexpected token :` 로 죽는다(실측).
import tsParser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";
import reactCompiler from "eslint-plugin-react-compiler";
import queryPlugin from "@tanstack/eslint-plugin-query";

const config = [
  {
    // Biome 의 `files.includes` 와 **같은 제외 집합**을 쓴다. 한쪽만 제외하면 그 경로에
    // 주인이 둘이 되거나 없어진다. `test-results/` 는 Playwright 가 남의 minified 번들
    // 사본을 떨구는 자리라 반드시 빠져야 한다(2026-08-14 실측 — lint 를 e2e 뒤에 돌리면 red).
    ignores: [
      ".next*/**",
      "node_modules/**",
      "dist/**",
      "coverage/**",
      "src/**/generated/**",
      "src/components/ui/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaFeatures: { jsx: true }, sourceType: "module" },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-compiler": reactCompiler,
      "@tanstack/query": queryPlugin,
    },
    rules: {
      // ★ LESSON-004 핵심 방어선 (infinite-loop 방지) — disable 금지.
      //   ★★넷을 **한 벌로** 둔다. rules-of-hooks / exhaustive-deps 는 Biome 에도 있지만
      //     거기선 껐다 — 한 축의 판정자는 하나여야 하고, 공식 구현이 이쪽이다.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "react-hooks/set-state-in-effect": "error",
      "react-hooks/set-state-in-render": "error",

      // React 19 컴파일러 호환성. Biome 대체분(`nursery/useReactCompiler`)은 한글 파일에서
      // panic 하므로 이 축은 옮길 수 없다 — 위 헤더 ⑵.
      "react-compiler/react-compiler": "error",

      // queryKey 일관성 (AGENTS.md §H-2). Biome 에 대응 규칙이 없다.
      "@tanstack/query/exhaustive-deps": "error",
    },
  },
  {
    // ★★FSD Lite 레이어 경계 ([ADR-035]) — **정적/동적 import 는 Biome 이 가져갔다**
    //   (`style/noRestrictedImports`. 그 규칙은 `import()` 를 네이티브로 본다).
    //   여기 남은 것은 **템플릿 리터럴 우회 하나뿐**이다:
    //   `import(`@/app/${name}`)` — 라우트명을 변수로 받는 lazy import 가 이 위반의 가장
    //   현실적인 모양이고, 2026-08-16 적대 리뷰가 탐침으로 통과를 실측해 닫은 갈래다.
    //   Biome 은 이 모양을 못 보므로 AST 선택자를 계속 ESLint 가 든다.
    files: ["src/features/**", "src/components/**", "src/lib/**", "src/hooks/**", "src/store/**"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "ImportExpression > TemplateLiteral > TemplateElement:first-child[value.raw=/(^@\\u002Fapp\\u002F)|(^\\.{1,2}\\u002F.*\\bapp\\u002F)/]",
          message: "하위 층은 app/ 을 템플릿 리터럴로도 동적 import 하지 않는다 (ADR-035).",
        },
      ],
    },
  },
];

export default config;
