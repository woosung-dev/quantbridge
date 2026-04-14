import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier";

// ESLint v9 flat config — Next.js 16부터 next lint 제거, eslint 직접 호출
const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
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
