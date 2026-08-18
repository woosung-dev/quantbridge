// 백테스트 리포트 상세 라우트 레벨 Suspense fallback — App Router 규약.
// 클라이언트 DetailSkeleton(.page + C 어휘)을 그대로 재사용해 라우트 전환과
// 클라 로딩이 같은 골격 한 벌로 그려지게 한다 (두 언어·두 폭 이중 렌더 방지).

import { DetailSkeleton } from "@/features/backtest/components/backtest-detail-view";

export default function BacktestDetailLoading() {
  return <DetailSkeleton />;
}
