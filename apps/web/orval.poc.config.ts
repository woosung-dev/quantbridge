// BL-717 PoC 전용 orval 설정 — zod 스키마만 생성한다 (HTTP client 없음).
// orval 은 dlx 로만 실행하므로 defineConfig import 없이 플레인 객체를 export 한다.
// 실행: cd apps/web && pnpm dlx orval@7 --config orval.poc.config.ts
export default {
  quantbridgePocZod: {
    input: {
      target: "../../contracts/openapi/poc/openapi.poc.json",
    },
    output: {
      mode: "single",
      client: "zod",
      target: "src/lib/api-contract-poc/generated/orval/schemas.zod.ts",
    },
  },
};
