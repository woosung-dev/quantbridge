import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import queryPlugin from "@tanstack/eslint-plugin-query";
import reactCompiler from "eslint-plugin-react-compiler";

// ESLint v9 flat config — Next.js 16부터 next lint 제거, eslint 직접 호출
// Sprint FE-01 LESSON-004 (CPU 100% 무한 루프 사고) 대응:
// - react-hooks/* 규칙 모두 error 격상 (set-state-in-effect 는 infinite-loop 방어선)
// - @tanstack/eslint-plugin-query: queryKey 안정성 / 캐시 정책 검증
// - eslint-plugin-react-compiler: React 19 컴파일러 호환성 검증
// Sprint FE-02: 잔여 warn 8건을 0건으로 떨어뜨리고 warn → error 일괄 격상
// (react-compiler 1건, @tanstack/query/exhaustive-deps 7건 모두 해소)
const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  ...queryPlugin.configs["flat/recommended"],
  {
    plugins: {
      "react-hooks": reactHooks,
      "react-compiler": reactCompiler,
    },
    rules: {
      // ★ LESSON-004 핵심 방어선 (infinite-loop 방지) — disable 금지
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "react-hooks/set-state-in-effect": "error",
      "react-hooks/set-state-in-render": "error",
      // React 19 컴파일러 호환성 — Sprint FE-02 에서 draft.ts useRef 패턴으로
      // 잔여 warn 0건 달성 → error 격상 (이후 신규 위반 CI 에서 차단)
      "react-compiler/react-compiler": "error",
      // queryKey 일관성 — Sprint FE-02 에서 Clerk userId identity 를 factory 에
      // 통합하고 queryFn 을 모듈-level factory 로 분리하여 잔여 warn 0건 → error 격상
      "@tanstack/query/exhaustive-deps": "error",
    },
  },
  prettier,
  {
    // src/**/generated/** — 코드젠 산출물(BL-717 PoC). header-audit 의 /generated/ 면제와 같은 축.
    // ★`test-results/` · `playwright-report/` 는 **실행 산출물**이다(둘 다 `.gitignore` 에 있다).
    //   Playwright 는 실패 시 `test-results/.playwright-artifacts-*/traces/resources/*.js` 로
    //   페이지의 **minified 번들 사본**을 떨군다. 그것까지 lint 하면 남의 코드가 우리 규칙에
    //   걸려 `no-unused-vars` **error** 가 나고, 그 결과 「e2e 를 돌린 뒤 lint 를 돌리면 red」가
    //   된다(2026-08-14 실측 — `final-gates` 가 FE lint FAIL 1건을 냈고 원인이 이것이었다).
    //   게이트 순서상 lint 가 e2e 보다 앞이라 평소엔 안 걸리고 **연속 실행에서만** 걸린다.
    ignores: [
      ".next*/**",
      "node_modules/**",
      "dist/**",
      "coverage/**",
      "src/**/generated/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  {
    rules: {
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports" },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];

export default config;
