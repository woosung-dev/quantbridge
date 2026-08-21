// 서버가 보낸 거부 사유를 화면 문구로 옮기는지 검증한다 (dogfood-restore D3)
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, describeApiError } from "./api-client";

describe("describeApiError", () => {
  it("FastAPI 검증 422 의 msg 를 꺼내고 'Value error, ' 접두사를 지운다", () => {
    // ★실측한 응답 본문 그대로(2026-07-26). 세션 폼에 `BTCUSDT.P` 를 넣었을 때
    //   화면에는 `API 422 /api/v1/live-sessions` 만 떴고 이 사유는 버려졌다.
    const err = new ApiError(422, "unknown_error", "API 422 /api/v1/live-sessions", {
      detail: [
        {
          type: "value_error",
          loc: ["body", "symbol"],
          msg: "Value error, Cannot normalize symbol: BTCUSDT.P",
          input: "BTCUSDT.P",
        },
      ],
    });

    expect(describeApiError(err)).toBe("Cannot normalize symbol: BTCUSDT.P");
  });

  it("여러 필드가 틀리면 모두 보여준다", () => {
    const err = new ApiError(422, "unknown_error", "API 422 /x", {
      detail: [{ msg: "Value error, first" }, { msg: "Value error, second" }],
    });

    expect(describeApiError(err)).toBe("first · second");
  });

  it("도메인 예외의 중첩 detail 문자열을 꺼낸다", () => {
    const err = new ApiError(409, "session_conflict", "API 409 /x", {
      detail: { code: "session_conflict", detail: "이미 활성 세션이 있습니다" },
    });

    expect(describeApiError(err)).toBe("이미 활성 세션이 있습니다");
  });

  it("해석할 수 없으면 원래 message 로 물러난다", () => {
    const err = new ApiError(500, "unknown_error", "API 500 /x", { detail: {} });

    expect(describeApiError(err)).toBe("API 500 /x");
  });

  it("ApiError 가 아니면 Error.message, 그것도 없으면 폴백", () => {
    expect(describeApiError(new Error("네트워크 끊김"))).toBe("네트워크 끊김");
    expect(describeApiError(null, "등록 실패")).toBe("등록 실패");
  });
});

// ★`ApiError.code` 해석은 **`apiFetch` 를 통해** 잰다. 코드 해석 함수만 직접 부르면
//   그 함수를 호출부에서 떼어내는 변이가 초록으로 빠져나간다(`apps/api/AGENTS.md` §10-2 와
//   같은 규약). 여기서는 `fetch` 만 갈아 끼운다.
describe("apiFetch — ApiError.code", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubResponse(status: number, body: unknown) {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(body), { status })),
    );
  }

  it("FastAPI 가 감싼 중첩 detail.code 를 편다", async () => {
    // ★이것이 [BL-671] 이 지목한 줄이다. 종전에는 최상위만 봐서 **언제나**
    //   `"unknown_error"` 였다 — 도메인 코드로 분기하는 UI 가 원리상 동작할 수 없었다.
    stubResponse(409, {
      detail: { code: "resting_conditional_entries", count: 1, detail: "…", orders: [] },
    });

    const err = await apiFetch("/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe("resting_conditional_entries");
    expect((err as ApiError).status).toBe(409);
  });

  it("최상위 code 가 있으면 그쪽이 이긴다", async () => {
    stubResponse(400, { code: "top_level", detail: { code: "nested" } });

    const err = await apiFetch("/x").catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("top_level");
  });

  it("음성 대조 — 어느 쪽에도 code 가 없으면 unknown_error 다", async () => {
    stubResponse(422, { detail: [{ msg: "Value error, nope" }] });

    const err = await apiFetch("/x").catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("unknown_error");
  });
});
