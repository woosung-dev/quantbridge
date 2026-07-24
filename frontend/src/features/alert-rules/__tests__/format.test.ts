// 알림 규칙 퍼센트 문자열의 표시용 정리를 검증한다.
import { describe, expect, test } from "vitest";

import { formatThresholdPercent } from "../format";

describe("formatThresholdPercent", () => {
  test("끝의 0만 제거해 정수로 표시한다", () => {
    expect(formatThresholdPercent("5.00000000")).toBe("5");
  });

  test("의미 있는 소수 자릿수는 보존한다", () => {
    expect(formatThresholdPercent("2.50000000")).toBe("2.5");
  });

  test("이미 정리된 입력은 그대로 반환한다", () => {
    expect(formatThresholdPercent("0.01")).toBe("0.01");
  });
});
