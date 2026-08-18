// Waitlist 관리자 화면 용어 SSOT — 상태 라벨·칩 톤 + 액션 열 무데이터 사유.
// backtest/trading labels.ts 패턴 차용: 라벨 문자열은 여기서만 오고,
// 컴포넌트는 statusLabelOf / CHIP_TONE_CLASS 로만 그린다.

import type { StatusLabel } from "@/lib/labels";

import type { WaitlistStatus } from "@/features/waitlist/schemas";

/** 신청 상태 라벨 + 칩 톤. 필터 칩과 표 배지가 같은 문자열을 쓴다. */
export const WAITLIST_STATUS_LABEL: Record<WaitlistStatus, StatusLabel> = {
  pending: { label: "대기중", tone: "neutral" },
  invited: { label: "초대됨", tone: "accent" },
  joined: { label: "가입완료", tone: "done" },
  rejected: { label: "거절", tone: "warn" },
};

/**
 * 액션 열 무데이터(EMPTY_CELL) 사유 — pending 이 아닌 행은 승인 액션이 없다.
 * orders-blotter 의 `title={...EmptyReason(state)}` 관례를 따른다.
 */
export const WAITLIST_ACTION_EMPTY_REASON: Record<WaitlistStatus, string> = {
  pending: "승인 대기 중입니다.",
  invited: "이미 초대를 발송한 신청입니다.",
  joined: "이미 가입을 완료한 신청입니다.",
  rejected: "거절된 신청입니다.",
};
