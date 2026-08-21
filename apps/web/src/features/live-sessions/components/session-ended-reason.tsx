// BL-484 — 종료된 세션의 "왜 죽었는가" 칩. 목록 카드와 상세 배지가 **같은 컴포넌트**를 쓴다.
//
// ★두 화면에 각자 JSX 를 두면 어휘·조건·부재 처리가 갈린다(LESSON-063 cross-page primitive
// 우회). 한국어 매핑은 `../labels` 의 LIVE_SESSION_DEACTIVATION_REASON_LABEL 이 SSOT 이고,
// 렌더 규칙(부재면 안 그린다)은 여기 하나다.

import { labelOf } from "@/lib/labels";

import { LIVE_SESSION_DEACTIVATION_REASON_LABEL } from "../labels";

type Props = {
  reason: string | null | undefined;
  /** 목록은 세션마다 한 개씩 뜨므로 호출부가 고유 testid 를 준다. */
  testId: string;
};

export function SessionEndedReason({ reason, testId }: Props) {
  // 사유 부재(null = 마이그레이션 이전 종료 / undefined = 구 응답에 키 없음 / "")는
  // **아무것도 그리지 않는다.** "사유 없음" 같은 가짜 확정을 만들지 않기 위해서다.
  if (!reason) return null;
  return (
    <span
      className="rounded-sm bg-destructive/10 px-2 py-0.5 text-xs font-medium text-[color:var(--destructive)]"
      data-testid={testId}
      title="세션이 종료된 사유"
    >
      {labelOf(LIVE_SESSION_DEACTIVATION_REASON_LABEL, reason, "live-session deactivation reason")}
    </span>
  );
}
