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
      // React 19 컴파일러 호환성 — 기존 tech debt 때문에 일시적으로 warn,
      // 스프린트 진행에 따라 점진적 error 격상 예정 (현재 draft.ts 1건 등)
      "react-compiler/react-compiler": "warn",
      // queryKey 일관성 — 기존 hooks.ts / trading/hooks.ts 에 token 누락 7건.
      // 일시적으로 warn, Clerk JWT token 통합 refactor 시 error 격상 예정.
      "@tanstack/query/exhaustive-deps": "warn",
    },
  },
  prettier,
  {
    ignores: [".next/**", "node_modules/**", "dist/**", "coverage/**"],
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
