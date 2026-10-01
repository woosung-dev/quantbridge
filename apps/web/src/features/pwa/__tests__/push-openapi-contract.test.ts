// 웹 푸시 엔드포인트 4종의 FE Zod 스키마를 OpenAPI 생성본(contracts/openapi/openapi.json)에 고정한다.
// 서버가 필드를 바꾸면 FE 파싱이 런타임에 처음 터지기 전에 여기서 먼저 빨개진다(pwa.md §2.7).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  CreatePushSubscriptionRequestSchema,
  PushConfigSchema,
  PushSubscriptionSchema,
  PushTestResultSchema,
} from "../schemas";

type JsonSchema = {
  properties?: Record<string, Record<string, unknown>>;
  required?: string[];
  $ref?: string;
};

type Operation = {
  requestBody?: { content?: Record<string, { schema?: unknown }> };
  responses?: Record<string, { content?: Record<string, { schema?: unknown }> }>;
};

type OpenApiDocument = {
  components?: { schemas?: Record<string, JsonSchema> };
  paths?: Record<string, Partial<Record<"get" | "post" | "delete", Operation>>>;
};

const WEB_ROOT = resolve(__dirname, "../../../..");
const OPENAPI_PATH = resolve(WEB_ROOT, "../../contracts/openapi/openapi.json");
const openApi = JSON.parse(readFileSync(OPENAPI_PATH, "utf-8")) as OpenApiDocument;

const schemas = openApi.components?.schemas ?? {};
const paths = openApi.paths ?? {};
const ref = (name: string) => ({ $ref: `#/components/schemas/${name}` });
const jsonSchemaOf = (part?: { content?: Record<string, { schema?: unknown }> }) =>
  part?.content?.["application/json"]?.schema;
const propKeys = (name: string) => Object.keys(schemas[name]?.properties ?? {}).sort();

const ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc";

describe("push OpenAPI consumer contract", () => {
  it("네 엔드포인트가 계약에 실재하고 각자의 스키마를 가리킨다", () => {
    expect(jsonSchemaOf(paths["/api/v1/push/config"]?.get?.responses?.["200"])).toEqual(
      ref("PushConfigResponse"),
    );
    const subscriptions = paths["/api/v1/push/subscriptions"];
    expect(jsonSchemaOf(subscriptions?.post?.requestBody)).toEqual(
      ref("CreatePushSubscriptionRequest"),
    );
    // 201 생성 · 200 기존(upsert) — FE 는 둘을 같은 스키마로 파싱한다.
    expect(jsonSchemaOf(subscriptions?.post?.responses?.["201"])).toEqual(
      ref("PushSubscriptionResponse"),
    );
    expect(jsonSchemaOf(subscriptions?.post?.responses?.["200"])).toEqual(
      ref("PushSubscriptionResponse"),
    );
    expect(jsonSchemaOf(subscriptions?.delete?.requestBody)).toEqual(
      ref("DeletePushSubscriptionRequest"),
    );
    expect(Object.keys(subscriptions?.delete?.responses ?? {})).toContain("204");
    expect(jsonSchemaOf(paths["/api/v1/push/test"]?.post?.responses?.["200"])).toEqual(
      ref("PushTestResponse"),
    );
  });

  it("응답 Zod 스키마의 필드 집합이 생성 계약과 같다", () => {
    expect(Object.keys(PushConfigSchema.shape).sort()).toEqual(propKeys("PushConfigResponse"));
    expect(Object.keys(PushSubscriptionSchema.shape).sort()).toEqual(
      propKeys("PushSubscriptionResponse"),
    );
    expect(Object.keys(PushTestResultSchema.shape).sort()).toEqual(propKeys("PushTestResponse"));
    expect(schemas.PushConfigResponse?.required?.sort()).toEqual(["enabled", "public_key"]);
  });

  it("구독 등록 본문은 endpoint·keys·user_agent 이고 endpoint 제약이 서버와 같다", () => {
    const request = schemas.CreatePushSubscriptionRequest;
    expect(Object.keys(CreatePushSubscriptionRequestSchema.shape).sort()).toEqual(
      propKeys("CreatePushSubscriptionRequest"),
    );
    expect(request?.required?.sort()).toEqual(["endpoint", "keys"]);
    expect(request?.properties?.endpoint).toMatchObject({
      pattern: "^https://",
      minLength: 9,
      maxLength: 2048,
    });
    expect(request?.properties?.keys).toEqual(ref("PushSubscriptionKeys"));
    expect(propKeys("PushSubscriptionKeys")).toEqual(["auth", "p256dh"]);
    // DELETE 본문은 endpoint 하나뿐이다(api.ts 가 `{endpoint}` 만 싣는다).
    expect(propKeys("DeletePushSubscriptionRequest")).toEqual(["endpoint"]);
  });

  it("FE 스키마가 서버의 non-https 422 를 입구에서 먼저 거른다 (양성 대조 포함)", () => {
    const valid = { endpoint: ENDPOINT, keys: { p256dh: "p", auth: "a" }, user_agent: null };
    expect(CreatePushSubscriptionRequestSchema.safeParse(valid).success).toBe(true);
    expect(
      CreatePushSubscriptionRequestSchema.safeParse({
        ...valid,
        endpoint: "http://fcm.googleapis.com/x",
      }).success,
    ).toBe(false);
    expect(
      CreatePushSubscriptionRequestSchema.safeParse({ ...valid, keys: { p256dh: "", auth: "a" } })
        .success,
    ).toBe(false);
  });
});
