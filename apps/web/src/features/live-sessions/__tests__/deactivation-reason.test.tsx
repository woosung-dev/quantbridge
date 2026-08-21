// BL-484 — 종료 사유 칩과 코드→한국어 매핑 SSOT 회귀.
//
// 재는 것 셋:
//  1. 사유가 있으면 한국어로 보인다 / 없으면 아무것도 안 그린다 (부재를 위장하지 않는다).
//  2. 목록 카드와 상세 배지가 **같은 문구**를 낸다 (두 화면이 다른 말을 하지 않는다).
//  3. ★BE `SessionDeactivationReason` 의 사유 전건에 FE 라벨이 있다 (cross-language drift).
//     BE 가 새 사유를 먼저 배포하면 화면에는 영문 코드가 그대로 뜬다 — 그걸 여기서 막는다.

import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LIVE_SESSION_DEACTIVATION_REASON_LABEL } from "../labels";
import { SessionEndedReason } from "../components/session-ended-reason";

const BACKEND_MODELS = path.resolve(__dirname, "../../../../../../apps/api/src/trading/models.py");

/** BE enum 블록에서 사유 문자열을 뽑는다. 블록을 못 찾으면 실패 — 조용히 통과하면 가드가 죽는다. */
function backendReasonCodes(): string[] {
  const source = readFileSync(BACKEND_MODELS, "utf8");
  const start = source.indexOf("class SessionDeactivationReason(StrEnum):");
  expect(
    start,
    "BE 의 SessionDeactivationReason 을 못 찾았다 — 이 테스트가 stale 이다",
  ).toBeGreaterThan(-1);
  // 다음 top-level 정의까지가 그 클래스 본문이다.
  const rest = source.slice(start + 1);
  const end = rest.search(/\nclass |\ndef /);
  const body = end === -1 ? rest : rest.slice(0, end);
  const codes = [...body.matchAll(/^ {4}(\w+) = "([^"]+)"$/gm)].map((m) => m[2]!);
  expect(codes.length, "BE enum 멤버를 하나도 못 뽑았다").toBeGreaterThan(0);
  return codes;
}

describe("세션 종료 사유 (BL-484)", () => {
  it("사유가 있으면 한국어 문구를 배지 옆에 그린다", () => {
    render(<SessionEndedReason reason="runtime_divergence" testId="reason-chip" />);

    expect(screen.getByTestId("reason-chip")).toHaveTextContent("엔진 실행 발산");
  });

  it.each([null, undefined, ""])(
    "사유가 %s 면 아무것도 그리지 않는다 (과거 행에서 깨지지 않고 가짜 확정도 안 만든다)",
    (reason) => {
      const { container } = render(<SessionEndedReason reason={reason} testId="reason-chip" />);

      expect(screen.queryByTestId("reason-chip")).not.toBeInTheDocument();
      expect(container).toBeEmptyDOMElement();
    },
  );

  it("미등재 코드는 원문을 그대로 노출한다 — 조용히 사라지지 않는다", () => {
    render(<SessionEndedReason reason="brand_new_reason" testId="reason-chip" />);

    expect(screen.getByTestId("reason-chip")).toHaveTextContent("brand_new_reason");
  });

  it("BE SessionDeactivationReason 전건에 FE 라벨이 있다", () => {
    const missing = backendReasonCodes().filter(
      (code) => LIVE_SESSION_DEACTIVATION_REASON_LABEL[code] === undefined,
    );

    expect(missing, `FE 라벨 누락 사유: ${missing.join(", ")}`).toEqual([]);
  });

  it("FE 라벨에 BE 가 모르는 코드가 없다 (죽은 라벨 축적 방어)", () => {
    const codes = new Set(backendReasonCodes());
    const orphans = Object.keys(LIVE_SESSION_DEACTIVATION_REASON_LABEL).filter(
      (code) => !codes.has(code),
    );

    expect(orphans, `BE 에 없는 FE 라벨: ${orphans.join(", ")}`).toEqual([]);
  });
});
