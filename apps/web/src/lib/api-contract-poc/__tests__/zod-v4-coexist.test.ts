// BL-717 PoC AC ⑵ — 생성 스키마(orval, `import * as zod from "zod"`)와 수기 스키마
// (`import { z } from "zod/v4"`)가 같은 zod@4 런타임에서 공존하며 같은 표본을 판정하는지 실증.
// zod@4 패키지에서 "zod" 루트와 "zod/v4" 서브패스는 같은 v4 구현을 가리킨다 — 이 테스트가 그 가정을 고정한다.
import { describe, expect, it } from "vitest";

import { StrategyListResponseSchema } from "@/features/strategy/schemas";

import { listStrategiesApiV1StrategiesGetResponse } from "../generated/orval/schemas.zod";

// 두 스키마의 필수 필드 교집합을 모두 채운 표본. datetime 은 Z 표기 —
// 생성 스키마는 zod.iso.datetime({}) 라 offset(+09:00) 을 거부한다 (수기는 offset:true 로 허용).
const sample = {
  items: [
    {
      id: "3f9c6f1e-7a25-4b6e-9f5d-2b8f0a4c9d11",
      name: "poc-strategy",
      pine_version: "v5",
      parse_status: "ok",
      parse_errors: null,
      timeframe: null,
      symbol: null,
      is_archived: false,
      created_at: "2026-08-13T00:00:00Z",
      updated_at: "2026-08-13T00:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  limit: 20,
  total_pages: 1,
};

describe("BL-717 PoC — zod v4 공존 (수기 zod/v4 ↔ 생성 zod)", () => {
  it("같은 표본을 수기·생성 스키마가 모두 통과시킨다", () => {
    const handwritten = StrategyListResponseSchema.parse(sample);
    const generated = listStrategiesApiV1StrategiesGetResponse.parse(sample);

    expect(handwritten.items[0]?.id).toBe(sample.items[0]?.id);
    expect(generated.items[0]?.id).toBe(sample.items[0]?.id);
    expect(handwritten.total_pages).toBe(generated.total_pages);
  });

  it("깨진 uuid 를 양쪽 모두 거부한다 (생성물이 실제로 검증함을 판별)", () => {
    const broken = {
      ...sample,
      items: [{ ...sample.items[0], id: "not-a-uuid" }],
    };
    expect(() => StrategyListResponseSchema.parse(broken)).toThrow();
    expect(() => listStrategiesApiV1StrategiesGetResponse.parse(broken)).toThrow();
  });

  it("offset datetime 은 생성 스키마만 거부한다 — 계약이 수기보다 엄격한 지점의 고정", () => {
    const offsetTs = {
      ...sample,
      items: [
        {
          ...sample.items[0],
          created_at: "2026-08-13T09:00:00+09:00",
          updated_at: "2026-08-13T09:00:00+09:00",
        },
      ],
    };
    expect(() => StrategyListResponseSchema.parse(offsetTs)).not.toThrow();
    expect(() => listStrategiesApiV1StrategiesGetResponse.parse(offsetTs)).toThrow();
  });
});
