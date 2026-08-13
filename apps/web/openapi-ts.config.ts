// BL-717 PoC 전용 @hey-api/openapi-ts 설정 — 타입 + zod 만 생성 (client SDK 없음).
// 실행: cd apps/web && pnpm dlx @hey-api/openapi-ts
export default {
  input: "../../contracts/openapi/poc/openapi.poc.json",
  output: "src/lib/api-contract-poc/generated/hey-api",
  plugins: [
    "@hey-api/typescript",
    {
      name: "zod",
      definitions: true,
      responses: { types: { infer: true } },
    },
  ],
};
