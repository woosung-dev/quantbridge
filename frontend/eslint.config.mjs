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
