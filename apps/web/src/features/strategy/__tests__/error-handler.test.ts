import { beforeEach, describe, expect, it, vi } from "vitest";

import { handleMutationError } from "@/features/strategy/error-handler";
import { ApiError } from "@/lib/api-client";

const toastError = vi.hoisted(() => vi.fn());
vi.mock("sonner", () => ({ toast: { error: toastError } }));

describe("handleMutationError", () => {
  beforeEach(() => {
    toastError.mockClear();
  });

  it("4xx ApiError — `API 422 …` 대신 서버 사유를 보인다", () => {
    handleMutationError(
      new ApiError(422, "validation_error", "API 422 /api/v1/strategies", {
        detail: "전략 이름이 중복됩니다",
      }),
    );
    expect(toastError).toHaveBeenCalledWith("실패: 전략 이름이 중복됩니다");
  });

  it("서버 사유가 없는 4xx 는 ApiError.message 로 폴백한다", () => {
    handleMutationError(new ApiError(400, "bad_request", "API 400 /x"));
    expect(toastError).toHaveBeenCalledWith("실패: API 400 /x");
  });

  it("ApiError 가 아닌 4xx 모양 값은 기본 문구를 쓴다", () => {
    handleMutationError({ status: 400 });
    expect(toastError).toHaveBeenCalledWith("실패: 알 수 없는 오류");
  });

  it("5xx 는 일반 서버 오류 안내를 유지한다", () => {
    handleMutationError(new ApiError(503, "unavailable", "API 503 /x"));
    expect(toastError).toHaveBeenCalledWith("서버 오류. 잠시 후 다시 시도해 주세요.");
  });
});
