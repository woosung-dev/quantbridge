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
  {
    // ★★FSD Lite 레이어 경계 ([ADR-035], 2026-08-16). `app/` 은 **최상위 조립층**이다 —
    //   아래 층(features · components · lib · hooks · store)이 그것을 거슬러 참조하면
    //   라우트 구조가 도메인 코드의 의존성이 되어 라우트를 못 옮긴다.
    //
    // ★왜 규칙으로 박는가: 2026-08-16 에 `app/**/_components/` 234파일을
    //   `features/*/components/` 로 옮겼는데, 그 배치를 **강제하는 장치가 하나도 없었다.**
    //   규칙이 없으면 다음 회차가 같은 자리로 되돌린다. 이동 시점 위반 = 0건이다.
    //
    // ★`app/` 자신은 제외다 — 라우트끼리의 참조는 이 규칙의 대상이 아니다.
    files: ["src/features/**", "src/components/**", "src/lib/**", "src/hooks/**", "src/store/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/app/*", "@/app/**"],
              message:
                "하위 층은 app/ 을 import 하지 않는다 (ADR-035). 공유가 필요하면 그 컴포넌트를 features/<domain>/components/ 또는 components/ 로 올려라.",
            },
          ],
        },
      ],
    },
  },
];

export default config;
