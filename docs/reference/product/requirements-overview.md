# QuantBridge — 현재 제품 범위

> **역할:** 지금 사용자에게 약속하는 제품 경계의 짧은 정본. 구현 상태는 코드와 [`status.md`](../../status.md), 우선순위·배포/베타 진입 조건은 [`roadmap.md`](../../roadmap.md), 열린 위험과 재개 조건은 [`backlog.md`](../../backlog.md)가 맡는다.
>
> **관련:** 제품 방향은 [`vision.md`](./vision.md), 도메인·상태의 상세 계약은 [`../domain/`](../domain/), API 경계는 [`../interfaces/endpoints.md`](../interfaces/endpoints.md)다. 초기 REQ 카탈로그와 Sprint 설계·측정 기록은 `archive/product/`에 보존한다.

---

## 제품 약속

TradingView Pine Script 전략을 가져와 같은 플랫폼에서 검증하고, 현실적인 비용·리스크 조건을 드러낸 뒤 **Bybit Demo Trading**까지 연결한다. 핵심은 기능 수가 아니라 결과와 가정이 얼마나 정직하게 보이는가다.

사용자 흐름은 세 단계다.

1. **Import** — Pine Script를 등록하고 지원 범위·degrade 여부를 먼저 확인한다.
2. **Verify** — `pine_v2` 실행 엔진으로 백테스트하고, 필요하면 스트레스 테스트·최적화를 수행한다.
3. **Operate** — 검증한 전략을 Bybit Demo 계정에서 자동 실행하며 주문·포지션·Kill Switch 상태를 관찰한다.

## 현재 범위

| 영역 | 현재 계약 | 상세 정본 |
| --- | --- | --- |
| 전략 | Pine Script 등록·파싱·지원 범위 판정. 미지원 항목이 하나라도 있으면 부분 실행하지 않는다. | [`domain-overview.md`](../domain/domain-overview.md), [`supported-indicators.md`](../domain/supported-indicators.md) |
| 백테스트 | `pine_v2`의 bar-by-bar 실행 결과와 리포트를 제공한다. | [`pine-execution-architecture.md`](../architecture/pine-execution-architecture.md) |
| 검증 확장 | Monte Carlo, Walk-Forward, 파라미터 안정성 및 최적화는 같은 백테스트 계약을 재사용한다. | [`system-architecture.md`](../architecture/system-architecture.md) |
| 시장 데이터 | OHLCV를 수집하고 TimescaleDB에 보관한다. | [`data-flow.md`](../architecture/data-flow.md) |
| 트레이딩 | 사용자 계정 모드는 **Bybit Demo만** 허용하며, 주문 전 리스크 평가와 Kill Switch를 적용한다. | [`state-machines.md`](../domain/state-machines.md), [`endpoints.md`](../interfaces/endpoints.md) |
| 신뢰·안전 | 실행·지원 범위·비용·리스크를 숨기지 않고, Pine 회귀는 Trust Layer CI로 방어한다. | [`trust-layer-architecture.md`](../architecture/trust-layer-architecture.md) |

> **경계:** 현재 계정 모드와 안전 규칙은 [`AGENTS.md`](../../../AGENTS.md)의 QuantBridge 고유 규칙이 정본이다. live/mainnet 공개·외부 Beta·프로덕션 배포는 구현 여부와 별개로 아직 제품 약속에 포함하지 않으며, 시작 조건은 roadmap의 Beta·Deferred 게이트를 따른다.

## 비범위와 의사결정 위치

- 현재 scope 밖의 배포 토폴로지, 도메인·DNS, 외부 Beta, mainnet runbook은 [`roadmap.md`](../../roadmap.md)에서 trigger가 도래할 때 결정한다.
- 특정 Sprint의 KPI, 구현률, dogfood 수치, 경쟁 비교는 현재 제품 계약이 아니다. 재사용 가치가 있는 근거만 `archive/`(`docs/archive/`)에서 찾는다.
- 상세 함수·DB 엔티티·API payload를 이 문서에 다시 쓰지 않는다. 코드와 도메인/API reference가 바뀌면 그 계약을 먼저 갱신한다.

## 변경 규칙

제품 범위가 바뀌면 이 문서를 짧게 고치고 같은 세션에 다음 중 정확히 한 곳을 갱신한다.

- 지금 실행할 일 → `status.md`
- 열린 위험·결함 → `backlog.md`
- 다음 제품/배포 선택 → `roadmap.md`
- 오래 유지할 구현 계약 → 해당 `reference/` 문서
- 종료된 판단·측정 → `dev-log/` 또는 `archive/`
