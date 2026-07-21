// Sprint 26 — Live Sessions pure helpers (테스트 가능 단위).
// Sprint 27 BL-140 — buildActivityTimeline (recent events cumulative).
// C 이식(W3-F) — formatDateTime 추가. 세션 시각을 결정적 UTC 로 인쇄한다.

import { EMPTY_CELL } from "@/lib/labels";

import type { LiveSignalEvent } from "./schemas";

/**
 * ISO datetime 을 `YYYY-MM-DD HH:mm` (UTC) 로 표기한다. 값이 없거나 파싱 불가면
 * 무데이터 셀 표기(EMPTY_CELL "—")를 돌려준다. 세션 상세·목록의 시각 열에 쓴다.
 *
 * backtest/utils.formatDateTime · strategy/utils.formatDateTime 과 같은 규약이다.
 * toLocaleString 류는 실행 환경 타임존에 따라 결과가 갈려 캐논(모든 화면이 같은 사실을
 * 말한다)과 컴포넌트 테스트를 깨뜨리므로 쓰지 않는다(도메인 경계 유지 위해 로컬 보유).
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY_CELL;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return EMPTY_CELL;
  const yyyy = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${yyyy}-${mo}-${dd} ${hh}:${mm}`;
}

// ── Refetch interval — active session 일 때만 빠르게 폴링 ────────────────
//
// LESSON-004 H-1: useEffect dep 에 RQ data 사용 금지 — refetchInterval callback
// 안에서 q.state.data 사용은 RQ 가 제공하는 stable closure 이므로 OK.
// 본 helper 는 hooks.ts 에서 callback 안에서 호출.

export const LIVE_SESSION_STATE_REFETCH_ACTIVE_MS = 5_000;
export const LIVE_SESSION_STATE_REFETCH_IDLE_MS = 30_000;
export const LIVE_SESSION_LIST_REFETCH_MS = 30_000;
export const MAX_LIVE_SESSIONS_PER_USER = 5;

/**
 * Sprint 26 — pure helper for unit testing.
 * is_active=true → 5s refetch, false → 30s.
 */
export function computeLiveSessionStateRefetchInterval(isActive: boolean): number {
  return isActive
    ? LIVE_SESSION_STATE_REFETCH_ACTIVE_MS
    : LIVE_SESSION_STATE_REFETCH_IDLE_MS;
}


// ── 실현손익 표시 포맷 (Wave0 cockpit — 부호·tone SSOT) ──────────────────
// BE Decimal-as-string 입력. precision 보존 위해 원본 string 유지(재포맷 X),
// 부호 판정만 Number 로. detail 패널 + list 배지가 공유.

export type PnlTone = "profit" | "loss" | "flat";

export interface RealizedPnlDisplay {
  text: string;
  tone: PnlTone;
}

export function formatRealizedPnl(raw: string): RealizedPnlDisplay {
  const n = Number(raw);
  if (!Number.isFinite(n) || n === 0) {
    return { text: raw, tone: "flat" };
  }
  if (n > 0) {
    return { text: `+${raw}`, tone: "profit" };
  }
  return { text: raw, tone: "loss" };
}


// ── Activity Timeline — events windowed cumulative entry/close (Sprint 27 BL-140) ─

export type ActivityTimelinePoint = {
  label: string;
  entries_in_window: number;
  closes_in_window: number;
};

// 내부 helper — bar_time asc → 같은 bar 면 sequence_no asc 정렬.
// comparator 의 Date.parse 반복 호출을 epoch ms 키 사전 계산으로 제거.
// buildActivityTimeline / buildActivityTimelineWithEquity 가 공유 (정렬 1회 통합).
type SortedEvent = { ev: LiveSignalEvent; ts: number };

function sortEventsChronologically(
  events: ReadonlyArray<LiveSignalEvent>,
): SortedEvent[] {
  return events
    .map((ev) => ({ ev, ts: Date.parse(ev.bar_time) }))
    .sort((a, b) =>
      a.ts !== b.ts ? a.ts - b.ts : a.ev.sequence_no - b.ev.sequence_no,
    );
}

// 정렬된 events → cumulative entry/close datapoint 변환.
function toTimelinePoints(
  sorted: ReadonlyArray<SortedEvent>,
): ActivityTimelinePoint[] {
  let entries = 0;
  let closes = 0;
  return sorted.map(({ ev }) => {
    if (ev.action === "entry") entries += 1;
    else if (ev.action === "close") closes += 1;
    return {
      // codex G.2 P2 #3 — toLocaleString() (장시간 세션 X축 중복 방어).
      label: new Date(ev.bar_time).toLocaleString(),
      entries_in_window: entries,
      closes_in_window: closes,
    };
  });
}

/**
 * Sprint 27 BL-140 — events 윈도우 내 cumulative entry/close 카운트.
 *
 * codex G.2 P1 #4 — BE repository 가 created_at.desc() 응답이라 bar_time desc
 *   보장 X. client-side 명시 정렬 (bar_time asc → 같은 bar 면 sequence_no asc) 의무.
 * codex G.2 P1 #5 — 진정한 cumulative 아니라 "최근 N events 누적" (window=100,
 *   events.items 응답 limit). label 명시 의무 (UI에서 처리).
 *
 * @param events  events.items (limit=100, BE created_at desc 응답).
 * @returns chronological 순서로 정렬된 cumulative datapoint.
 */
export function buildActivityTimeline(
  events: ReadonlyArray<LiveSignalEvent>,
): ActivityTimelinePoint[] {
  return toTimelinePoints(sortEventsChronologically(events));
}

// Sprint 28 Slice 3 (BL-140b) — entry/close + real cumulative equity 통합.
import type { EquityCurvePoint } from "./schemas";

export type ActivityTimelineWithEquityPoint = ActivityTimelinePoint & {
  cumulative_pnl: number; // BE 의 string Decimal → FE number (chart 렌더용, precision 충분)
};

/**
 * Sprint 28 BL-140b — buildActivityTimeline + equity_curve 병합.
 *
 * BE 의 equity_curve (LiveSignalState.equity_curve) 를 entry/close timeline 과 정렬 병합.
 * 같은 timestamp 의 event 가 있으면 equity 도 함께 표시. equity 만 있는 datapoint 는
 * entry/close 직전 값 carry-forward (line chart 연속성).
 *
 * @param events  events.items (limit=100, BE created_at desc 응답).
 * @param equityCurve  state.equity_curve (BE 누적 PnL timeseries, ASC sorted).
 * @returns dual-axis chart 용 datapoint.
 */
export function buildActivityTimelineWithEquity(
  events: ReadonlyArray<LiveSignalEvent>,
  equityCurve: ReadonlyArray<EquityCurvePoint>,
): ActivityTimelineWithEquityPoint[] {
  // 정렬 1회 통합 — timeline 변환과 equity 매칭이 같은 정렬 결과를 공유.
  const sortedEvents = sortEventsChronologically(events);
  const baseTimeline = toTimelinePoints(sortedEvents);

  // equity_curve 의 timestamp_ms → cumulative_pnl 매핑
  const sortedEquity = equityCurve
    .slice()
    .sort((a, b) => a.timestamp_ms - b.timestamp_ms);

  // two-pointer — 양쪽 모두 asc 정렬이므로 equity 인덱스는 뒤로만 전진 O(E+N).
  // (기존: 이벤트마다 sortedEquity 전체 선형 재스캔 O(E×N).)
  let eqIdx = 0;
  let cumulativePnl = 0; // 첫 equity point 이전 이벤트는 0 (기존 시맨틱스 유지)
  return baseTimeline.map((point, idx) => {
    const entry = sortedEvents[idx];
    if (!entry) {
      return { ...point, cumulative_pnl: 0 };
    }

    // bar_time 이전(≤)의 마지막 equity 값 carry-forward.
    while (
      eqIdx < sortedEquity.length &&
      sortedEquity[eqIdx]!.timestamp_ms <= entry.ts
    ) {
      cumulativePnl = parseFloat(sortedEquity[eqIdx]!.cumulative_pnl);
      eqIdx += 1;
    }

    return {
      ...point,
      cumulative_pnl: cumulativePnl,
    };
  });
}
