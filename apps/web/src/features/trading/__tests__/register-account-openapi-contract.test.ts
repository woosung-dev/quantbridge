// Bybit Demo 계정 등록의 생성 계약을 FE Zod schema와 OpenAPI 생성본에 함께 고정한다.
// 서버가 exchange/mode/passphrase를 다시 받기 시작하면 UI가 조용히 예전 정책으로 돌아가지 않게 한다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { RegisterAccountRequestSchema } from "../schemas";

type OpenApiRequestSchema = {
  additionalProperties?: boolean;
  properties?: Record<string, unknown>;
  required?: string[];
};

type OpenApiDocument = {
  components?: { schemas?: Record<string, OpenApiRequestSchema> };
  paths?: Record<
    string,
    { post?: { requestBody?: { content?: Record<string, { schema?: unknown }> } } }
  >;
};

const WEB_ROOT = resolve(__dirname, "../../../..");
const OPENAPI_PATH = resolve(WEB_ROOT, "../../contracts/openapi/openapi.json");
const openApi = JSON.parse(readFileSync(OPENAPI_PATH, "utf-8")) as OpenApiDocument;

describe("RegisterAccountRequest OpenAPI consumer contract", () => {
  it("Bybit Demo 등록 본문은 label/api_key/api_secret 세 필드만 가진다", () => {
    const schema = openApi.components?.schemas?.RegisterAccountRequest;
    expect(schema).toBeDefined();
    expect(schema?.additionalProperties).toBe(false);
    expect(Object.keys(schema?.properties ?? {}).sort()).toEqual([
      "api_key",
      "api_secret",
      "label",
    ]);
    expect(schema?.required).toEqual(["api_key", "api_secret"]);
    expect(schema?.properties?.api_key).toMatchObject({
      type: "string",
      minLength: 1,
      maxLength: 200,
      format: "password",
      writeOnly: true,
    });
    expect(schema?.properties?.api_secret).toMatchObject({
      type: "string",
      minLength: 1,
      maxLength: 200,
      format: "password",
      writeOnly: true,
    });
  });

  it("웹 Zod 입력 필드와 POST requestBody가 생성 계약을 그대로 소비한다", () => {
    const schema = openApi.components?.schemas?.RegisterAccountRequest;
    const requestBody =
      openApi.paths?.["/api/v1/exchange-accounts"]?.post?.requestBody?.content?.["application/json"]
        ?.schema;

    expect(Object.keys(RegisterAccountRequestSchema.shape).sort()).toEqual(
      Object.keys(schema?.properties ?? {}).sort(),
    );
    expect(requestBody).toEqual({ $ref: "#/components/schemas/RegisterAccountRequest" });
    expect(
      RegisterAccountRequestSchema.safeParse({
        label: null,
        api_key: "demo-api-key",
        api_secret: "demo-api-secret",
      }).success,
    ).toBe(true);
    expect(
      RegisterAccountRequestSchema.safeParse({
        label: null,
        api_key: "demo-api-key",
        api_secret: "demo-api-secret",
        exchange: "bybit",
      }).success,
    ).toBe(false);
  });
});
