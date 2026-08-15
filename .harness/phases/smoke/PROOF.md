# guardrail-proof

- backend 패키지 매니저: uv
- frontend 패키지 매니저: pnpm
- 워크트리에서 `make up` 을 돌려도 되나: 아니오 — 컨테이너와 앱 DB 한 벌을 공유해 함께 깨질 수 있다.
- Golden Rules (Immutable) 항목 수: 5
- 주입된 4축 문서의 제목 4개: QuantBridge — Context, QuantBridge — TradingView Pine Script 전략 → 백테스트·데모·라이브 트레이딩 퀀트 플랫폼, Backend Rules (FastAPI + SQLModel), Frontend Rules (Next.js 16)
