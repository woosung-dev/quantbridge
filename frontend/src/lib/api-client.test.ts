// 서버가 보낸 거부 사유를 화면 문구로 옮기는지 검증한다 (dogfood-restore D3)
import { describe, expect, it } from "vitest";

import { ApiError, describeApiError } from "./api-client";

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
      detail: [
        { msg: "Value error, first" },
        { msg: "Value error, second" },
      ],
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
