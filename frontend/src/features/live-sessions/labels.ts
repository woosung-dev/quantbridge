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

/**
 * 시그널 이벤트 방향. backend/src/trading/models.py:542 의 direction str = "long" | "short".
 * FE schema 는 z.string() 자유문자열이라 labelOf 로 미지값을 안전 폴백한다.
 * no-raw-enum-labels 가드(W1 확장, "direction" 필드)가 원시 방향 렌더를 잡는다.
 */
export const LIVE_SIGNAL_DIRECTION_LABEL: Record<"long" | "short", string> = {
  long: "롱",
  short: "숏",
};

/**
 * BL-484 — 세션 종료 사유. **화면의 유일한 코드→한국어 매핑 지점(SSOT)** 이다.
 *
 * 코드 집합의 정본은 BE `src/trading/models.py` 의 `SessionDeactivationReason` 다.
 * 그전까지 사유는 Slack/Telegram 으로만 나가고 DB·화면에 없었다 — 알림을 놓치면 화면
 * 어디에도 "왜 멈췄나" 가 없었다.
 *
 * ★소비처는 `labelOf` 를 거쳐 읽는다. 미등재 코드는 원문 코드가 그대로 나오고 dev 콘솔에
 * 경고가 뜬다 — BE 가 새 사유를 먼저 배포했을 때 화면에서 조용히 사라지는 것이 최악이다.
 * 사유 부재(null / 키 없음)는 이 표의 관심사가 아니라 소비처가 "안 그리기" 로 처리한다.
 */
export const LIVE_SESSION_DEACTIVATION_REASON_LABEL: Record<string, string> = {
  // preflight — 평가 진입 전에 막았다.
  coverage_unrunnable: "지원하지 않는 Pine 함수",
  degraded_unconsented: "결과가 어긋나는 Pine 기능",
  equity_baseline_missing: "자본 기준선 부재",
  equity_exhausted: "자본 소진",
  // runtime — Pine 재생 중 발산했다.
  run_live_error: "전략 실행 오류",
  runtime_divergence: "엔진 실행 발산",
  // 포지션 정합 실패.
  gap_resync_position_mismatch: "평가 공백 후 포지션 불일치",
  position_divergence: "엔진↔거래소 포지션 방향 불일치",
  // 사람이 Stop 을 눌렀다.
  user_stopped: "사용자 중단",
};
