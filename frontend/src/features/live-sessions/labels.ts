// 라이브 세션 도메인 화면 표기 SSOT — 시그널 이벤트 상태 라벨.
// 프로토타입 17벌에 라이브 세션 이벤트 로그 화면이 없어 원장 지정은 없다. enum 값 자체를
// 화면에 그대로 인쇄하지 않기 위한 한국어 라벨 매핑이며, no-raw-enum-labels 가드(S9 확장
// 스코프)가 features/live-sessions/components 의 원시 status 렌더를 잡는다.

import type { LiveSignalEventStatus } from "./schemas";

/**
 * 시그널 이벤트 상태 3종. schemas.ts 의 LiveSignalEventStatusSchema 와 1:1.
 * - pending    : 아직 거래소로 보내지 않은 시그널
 * - dispatched : 주문으로 전송된 시그널
 * - failed     : 전송에 실패한 시그널
 * 톤 색은 소비처(live-session-detail)가 자체 클래스로 입히므로 라벨만 둔다.
 */
export const LIVE_SIGNAL_EVENT_STATUS_LABEL: Record<LiveSignalEventStatus, string> = {
  pending: "대기",
  dispatched: "전송됨",
  failed: "실패",
};
