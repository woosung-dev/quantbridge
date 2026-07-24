<!-- perf-surface 스프린트(성과 표면 A1~A4)의 멀티에이전트 운영 계약 — opspack-ws2 계약 대비 델타만 기록 -->

# perf-surface 운영 계약 (델타)

> 기본 계약은 [`../opspack-ws2/operating-contract.md`](../opspack-ws2/operating-contract.md) 전부 상속 (→ tier-c → functional-parity → c-language-port 체인). 아래는 이번 스프린트에서 달라진 것만.
> 플랜 정본: `~/.claude/plans/quantbridge-perf-surface-handoff.md` + 세션 실행 지도 `~/.claude/plans/perf-surface-snug-prism.md`

## 1. 범위 (사용자 확정 2026-07-24)

- **Phase A 전체(A1~A4) + 여유 시 A5 문서 위생.** Phase B(position-cockpit)는 본 PR 머지 후 별도 세션(짝 문서).
- **A1** 백테스트 목록 성과 열(11열 + 서버 정렬) · **A2** 전략 목록 성과 3칸 · **A3** 대시보드 §03 최적화 병합 + §04 per-strategy 미터 · **A4** 트레이드 상세 구간 미니차트.
- **마이그레이션 0** — 전부 read-time 파생. alembic 왕복은 무변경 확인 1회.
- **수익률 표기 = total_return + 미청산 부기**(total_open_trades>0 행 부기/툴팁 + 리포트 각주 1줄). 확정 재질문 금지.
- **PR #467 = 사용자 별도 머지** — 이번 스프린트에서 #467 관련 작업 금지. 문서 위생 몫 = dev-log INDEX 7월 3건 + Quick Summary + TODO.md 갱신만.

## 2. 워커 편성 델타 (4분할, 권역별 worktree)

| 워커                 | 권역                                                                                              | 비고                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `ps/w1-be-perf`      | C1~C5 BE: serializers/schemas/service/repository/router + strategy latest + optimizer denormalize | backtest/{schemas,service,router}.py 소유 — W1 선행   |
| `ps/w2-be-ohlcv`     | C6 BE: get_trade_by_index + trade_ohlcv + OHLCVRepository cross-inject                            | W1 과 backtest 3파일 공유 → 순차 통합(리베이스)       |
| `ps/w3-fe-surface`   | C1~C5 FE: backtest-list 11열/서버정렬 + strategy-list 3칸 + dashboard §03/§04 + 리포트 각주       | features/backtest/\* 소유 — W3 선행                   |
| `ps/w4-fe-minichart` | C6 FE: getTradeOhlcv/useTradeOhlcv + trade-range-chart + trade-detail-table 배선                  | W3 과 features/backtest/\* 공유 → 순차 통합(리베이스) |

- cherry-pick 순서 = **W1 → W2 → W3 → W4** (메인 트리에서만). W1 defer(equity_curve) 커밋 독립 유지. 워커당 1커밋(+W1 defer 별도).
- Generator = codex exec 병렬(-s workspace-write, 권역별 worktree, git 조작 금지). Evaluator = Claude 적대 서브에이전트(4축 + 게이트 직접 실행 겸임).

## 3. 게이트 기준 (이번 스프린트 baseline — W0 재측정 실측)

- opspack-ws2 머지 후 문서치: BE 2533+46skip / FE 1044(182) / canon 32 / authed 63(404 비허용).
- **W0 재측정 실측**: FE **1044(182)** ✅ (= 문서치) / BE 재측정값은 checklist.md §게이트 표. 그 실측값이 공식 baseline.
- Phase A 순증 목표: BE +5신규~ / FE +4신규~. authed 신규 spec 0 예상(기존 `authed-canon-remaining.spec.ts` 확장) — 발생 시 playwright.config.ts 열거식 testMatch 등재 의무.
- **게이트 세트 2종(별개)**: e2e:design-canon **32 불변** + vitest `design-canon-source.test.ts` diffRatchet(radius/hex/em-dash allowlist **증감 양방향 실패**).

## 4. 오라클 델타 (§7.3 — 앱으로 앱 검증 금지)

- 성과 열 3표본: 목록 값 ↔ 리포트 상세 값 ↔ psql `metrics` 손계산 3점 대조. **모순 표본 4a3bb5d3/8f6ba11a 필수 포함**(미청산 부기 실증, total_open_trades=1).
- 전략 최신 성과: psql DISTINCT ON 수동 쿼리 ↔ 응답.
- 미니차트: psql ohlcv 수동 range ↔ bars 수·첫/끝 봉.
- Opus MCP playwright 실브라우저 dogfood(storageState 쿠키 주입). 정체성 프로브(BE openapi title + FE `<title>`) 없이 오라클 선언 금지.
