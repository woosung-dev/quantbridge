import { describe, expect, it } from "vitest";
import { z } from "zod/v4";

import { zodV4Resolver } from "../zod-v4-resolver";

type FlatErrors = Record<string, { type: string; message: string }>;

describe("zodV4Resolver", () => {
  it("returns parsed values with transforms and defaults on success", async () => {
    const schema = z.object({
      amount: z.string().transform((value) => Number(value)),
      label: z.string().default("default label"),
    });

    const result = await zodV4Resolver(schema)({ amount: "42" } as never, undefined, {} as never);

    expect(result.values).toEqual({ amount: 42, label: "default label" });
    expect(result.errors).toEqual({});
  });

  it("maps a flat key issue and clears values on failure", async () => {
    const schema = z.object({ email: z.email() });
    const parsed = schema.safeParse({ email: "nope" });
    expect(parsed.success).toBe(false);
    if (parsed.success) {
      return;
    }

    const result = await zodV4Resolver(schema)({ email: "nope" }, undefined, {} as never);
    const errors = result.errors as unknown as FlatErrors;

    expect(result.values).toEqual({});
    expect(errors.email).toEqual({
      type: parsed.error.issues[0]?.code,
      message: parsed.error.issues[0]?.message,
    });
  });

  it("joins nested issue paths with dots", async () => {
    const schema = z.object({ a: z.object({ b: z.string() }) });

    const result = await zodV4Resolver(schema)({ a: { b: 1 } } as never, undefined, {} as never);
    const errors = result.errors as unknown as FlatErrors;

    expect(errors["a.b"]).toMatchObject({
      type: "invalid_type",
      message: expect.any(String),
    });
  });

  it("keeps the first issue when one path has multiple issues", async () => {
    const schema = z.object({
      code: z.string().min(5, "minimum five characters").regex(/^\d+$/, "digits only"),
    });
    const parsed = schema.safeParse({ code: "ab" });
    expect(parsed.success).toBe(false);
    if (parsed.success) {
      return;
    }
    expect(parsed.error.issues).toHaveLength(2);

    const result = await zodV4Resolver(schema)({ code: "ab" }, undefined, {} as never);
    const errors = result.errors as unknown as FlatErrors;

    expect(errors.code).toEqual({
      type: parsed.error.issues[0]?.code,
      message: parsed.error.issues[0]?.message,
    });
  });

  it("maps a superRefine custom issue to its target field", async () => {
    const schema = z
      .object({ password: z.string(), confirm: z.string() })
      .superRefine((values, ctx) => {
        if (values.password !== values.confirm) {
          ctx.addIssue({
            code: "custom",
            path: ["confirm"],
            message: "비밀번호 확인이 일치하지 않습니다",
          });
        }
      });

    const result = await zodV4Resolver(schema)(
      { password: "secret", confirm: "different" },
      undefined,
      {} as never,
    );
    const errors = result.errors as unknown as FlatErrors;

    expect(errors.confirm).toEqual({
      type: "custom",
      message: "비밀번호 확인이 일치하지 않습니다",
    });
  });

  it("supports asynchronous refinements", async () => {
    const schema = z.object({
      email: z.string().refine(async () => false, "이미 사용 중인 이메일입니다"),
    });

    const result = await zodV4Resolver(schema)(
      { email: "user@quantbridge.app" },
      undefined,
      {} as never,
    );
    const errors = result.errors as unknown as FlatErrors;

    expect(result.values).toEqual({});
    expect(errors.email).toEqual({
      type: "custom",
      message: "이미 사용 중인 이메일입니다",
    });
  });
});
