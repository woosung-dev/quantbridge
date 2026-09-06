// 백테스트 진행 폴링 간격 계약 — 「서버가 끝낸 시각」과 「화면이 아는 시각」의 격차를 고정한다.
//
// 왜 이 파일이 생겼나 (2026-09-06 d1 실사용 1차 루프 실측):
//   온보딩 위저드를 3회 완주시켜 재니 **제출 → 결과 표시 = 30.07 / 30.09 / 30.54초** 였는데
//   같은 백테스트의 **서버 시간은 0.82 / 0.89 / 1.19초** 였다(`backtests` 원장 직독,
//   queue + engine). 즉 사용자가 기다린 30초 중 **29초가 폴링 대기**다.
//   `progress` 요청은 주행당 정확히 2회만 나갔다(제출 직후, 그리고 30초 뒤).
//
// 무엇을 재는가 — **상수 값이 아니라 두 폴링의 관계다.**
//   값을 그대로 단언하면 상수를 두 곳에 적는 것과 같아 회귀를 못 잡는다(미러링 항진명제).
//   같은 파일의 스트레스 테스트 폴링이 이미 2초이고 그쪽이 옳은 자릿수다 — 백테스트 진행이
//   그보다 **느리면 안 된다**는 관계가 이 계약의 본체다.

import { describe, expect, it } from "vitest";

import { progressRefetchInterval, stressTestRefetchInterval } from "../hooks";

// React Query 의 Query 는 내부 필드가 많아 부분 객체를 그대로 못 넘긴다.
// refetchInterval 계약이 읽는 것은 `state.status` 와 `state.data` 둘뿐이다.
// biome-ignore lint/suspicious/noExplicitAny: 폴링 계약이 읽는 두 필드만 있는 최소 대역이다
function fakeQuery(state: { status: string; data?: unknown }): any {
  return { state };
}

// 실측 상한 — 서버가 1.19초에 끝낸 결과를 화면이 이보다 늦게 알면 대기가 계산을 압도한다.
const MAX_PENDING_POLL_MS = 5_000;

describe("백테스트 진행 폴링 간격", () => {
  it("실행 중에는 스트레스 테스트 폴링보다 느리지 않다", () => {
    const running = progressRefetchInterval(
      fakeQuery({ status: "success", data: { status: "running" } }),
    );
    const stress = stressTestRefetchInterval(
      fakeQuery({ status: "success", data: { status: "running" } }),
    );
    expect(typeof running).toBe("number");
    expect(typeof stress).toBe("number");
    expect(running as number).toBeLessThanOrEqual(stress as number);
  });

  it("실행 중 폴링 간격이 서버 실행 시간 규모를 넘지 않는다", () => {
    // 2026-09-06 실측: 서버 총 0.82~1.19초. 5초를 넘으면 사용자가 기다리는 시간의
    // 대부분이 계산이 아니라 대기가 된다.
    const running = progressRefetchInterval(
      fakeQuery({ status: "success", data: { status: "running" } }),
    );
    expect(running as number).toBeLessThanOrEqual(MAX_PENDING_POLL_MS);
  });

  it("terminal 상태에서는 폴링을 멈춘다 (기존 계약 무회귀)", () => {
    for (const status of ["completed", "failed", "cancelled"]) {
      expect(progressRefetchInterval(fakeQuery({ status: "success", data: { status } }))).toBe(
        false,
      );
    }
  });

  it("데이터 도착 전에도 폴링을 유지한다 (기존 계약 무회귀)", () => {
    const beforeFirstResponse = progressRefetchInterval(
      fakeQuery({ status: "pending", data: undefined }),
    );
    expect(typeof beforeFirstResponse).toBe("number");
  });
});
