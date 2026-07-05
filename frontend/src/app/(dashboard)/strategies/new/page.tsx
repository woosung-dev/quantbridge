// 전략 생성 페이지 (server) — 3-step wizard 클라이언트 로직은 NewStrategyWizard 로 위임.

import { NewStrategyWizard } from "./_components/new-strategy-wizard";

export default function NewStrategyPage() {
  return <NewStrategyWizard />;
}
