// KPI 통계 값 슬롯 — 소스 쿼리의 오류/미수신을 성공-0 과 분리해 정직하게 노출한다.
// (LESSON-039 Surface Trust: isError 를 성공-빈 과 섞으면 백엔드 오류가 '0·미등록·미해결
//  없음' 같은 거짓 정상으로 렌더된다.) 성공했을 때만 실제 값을 그린다.

import type { ReactNode } from "react";

export function StatValue({
  isError,
  isPending,
  children,
}: {
  isError?: boolean;
  isPending?: boolean;
  children: ReactNode;
}) {
  if (isError) return <span className="kpi-na">확인 불가</span>;
  if (isPending) return <span className="kpi-na">불러오는 중</span>;
  return <>{children}</>;
}
