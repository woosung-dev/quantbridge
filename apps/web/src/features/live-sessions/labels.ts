// 라이브 세션 도메인 화면 표기 SSOT — 시그널 이벤트 상태 라벨.
// 프로토타입 17벌에 라이브 세션 이벤트 로그 화면이 없어 원장 지정은 없다. enum 값 자체를
// 화면에 그대로 인쇄하지 않기 위한 한국어 라벨 매핑이며, no-raw-enum-labels 가드(S9 확장
// 스코프)가 features/live-sessions/components 의 원시 status 렌더를 잡는다.

import type { StatusLabel } from "@/lib/labels";

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
 * 시그널 이벤트 방향. apps/api/src/trading/models.py:542 의 direction str = "long" | "short".
 * FE schema 는 z.string() 자유문자열이라 labelOf 로 미지값을 안전 폴백한다.
 * no-raw-enum-labels 가드(W1 확장, "direction" 필드)가 원시 방향 렌더를 잡는다.
 */
export const LIVE_SIGNAL_DIRECTION_LABEL: Record<"long" | "short", string> = {
  long: "롱",
  short: "숏",
};

/**
 * BL-572 — 세션 상태 칩. **표 · 목록 카드 · 상세 배지가 같은 이름을 쓰게 하는 SSOT** 다.
 *
 * 그전까지 표는 `is_active ? "ACTIVE" : "PAUSED"` 영문 리터럴을 박아 뒀고, 같은 화면의 목록
 * 카드는 동일 세션을 "종료된 세션" 으로 불렀다 — 한 화면에서 한 세션이 두 이름이었다.
 * 게다가 PAUSED 는 의미도 틀렸다. 이 세션들은 사유(`position_divergence` 등)와 함께 **끝난**
 * 것이지 재개를 기다리는 게 아니다. 종료 계열 어휘는 카드 쪽이 이미 맞았으므로 그쪽으로 모은다.
 *
 * 상태는 BE enum 이 아니라 `LiveSession.is_active` 불리언에서 파생하므로 `labelOf` 폴백이
 * 필요 없다 — 미지 코드가 올 자리가 없다. 톤까지 여기 두는 이유는 칩 색도 라벨과 같이
 * 갈라지기 때문이다(표가 accent/기본을 자체 삼항으로 정하고 있었다).
 */
export type LiveSessionStatus = "active" | "ended";

export const LIVE_SESSION_STATUS_LABEL: Record<LiveSessionStatus, StatusLabel> = {
  active: { label: "실행 중", tone: "accent" },
  ended: { label: "종료된 세션", tone: "neutral" },
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
