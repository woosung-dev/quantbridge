<!-- tier-c 스프린트의 멀티에이전트 운영 계약 — functional-parity 계약 대비 델타만 기록 -->

# tier-c 운영 계약 (델타)

> 기본 계약은 [`../functional-parity/operating-contract.md`](../functional-parity/operating-contract.md) 전부 상속 (그 문서가 다시 [`../c-language-port/operating-contract.md`](../c-language-port/operating-contract.md) 를 상속). 아래는 이번 스프린트에서 달라진 것만.
> 플랜 정본: `~/.claude/plans/tier-c-squishy-pebble.md`

## 1. 범위 (사용자 확정 2026-07-24)

- **A안: Tier C 4종 전부 + WS Tier 1** — 펀딩 노출완성+베이지안 prior 해제 / 포지션 대조 / 알림 규칙 / WS 최소안(주문·킬스위치·세션 push, 폴링=정합성 SSOT 불변).
- WS Tier 2(ticker/미실현 P&L/position 채널)는 후속 스프린트.
- **알림 실수신 검증 이연**: 로컬 env 에 SLACK*WEBHOOK_URL/TELEGRAM*\* 미설정(실측). 발송 계약은 유닛+mock 으로 잠그고 실수신은 후속 세션.

## 2. 워커 편성 델타 (웨이브)

| 웨이브 | 워커 브랜치       | 권역                                                                 | 비고                                       |
| ------ | ----------------- | -------------------------------------------------------------------- | ------------------------------------------ |
| W1     | `tc/funding-be`   | 축3 A+B: v2_adapter total_funding 4-site + backfill                  | celery_app.py beat 는 W1 에서 이 워커만    |
| W1     | `tc/optimizer-fe` | 축3 D: normal prior 해제 + E1 + BE docstring                         |                                            |
| W1     | `tc/position-be`  | 축2 S1: PositionService + `/positions`                               | trading router/schemas/dependencies append |
| W1     | `tc/realtime-be`  | 축1 S0+S1: `src/realtime/` 신설 + auth 추출 + main.py                | trading 파일 무접촉                        |
| W2     | `tc/alerts-be`    | 축2 S2: alert_rules 테이블+CRUD+beat+giveup 훅                       | `tasks/trading.py` 소유 — W2 선행          |
| W2     | `tc/publish-be`   | 축1 S2: realtime_publisher + 발행 5지점                              | `tasks/trading.py` 는 alerts-be 커밋 후    |
| W2     | `tc/funding-fe`   | 축3 C: 체크박스+총 펀딩 행                                           | 축3 A 커밋 후                              |
| W2     | `tc/realtime-fe`  | 축1 S3: ws-client + realtime feature                                 |                                            |
| W3     | `tc/cockpit-fe`   | 축2 S3 + 축1 S4 통합: 진단 카드 3장 + alert-rules 모듈 + authed spec | 단일 워커 (session-diagnostics 충돌 회피)  |

- cherry-pick 순서 = 표의 위→아래. 워커당 1커밋.

## 3. 게이트 기준 (이번 스프린트 baseline)

- baseline 재측정(§7.1) 결과는 checklist.md §게이트 표에 기록 — 그 실측값이 이번 스프린트의 공식 baseline (문서상 983/2433 은 참고치).
- authed-canon 스냅: §06 진단 카드 상태 변화로 기대값 동반 갱신 의무 (변경은 해당 FE 슬라이스가 소유).
- 신규 BE WS 테스트는 starlette `TestClient.websocket_connect` (기존 httpx ASGITransport 는 WS 미지원 — 실측).

## 4. 오라클 델타 (§7.3)

- 펀딩: `equity_off − equity_on == total_funding == psql 손계산` 3점 일치 (엔진 밖 SQL 산술).
- 포지션: Bybit demo 웹 콘솔 + raw curl `/v5/position/list` 2계통 (앱 API 로 앱 API 검증 금지).
- 알림: 발송 시도 로그 + dispatcher mock 호출 + Redis dedupe TTL 실측 (실수신 이연).
- WS: 체결 push 가 폴링 주기(5s)보다 빠른 갱신 타임스탬프 실측.
- cancel_order 실거래소 왕복(전 스프린트 잔여): DB `state='cancelled'` psql 실측 — dogfood 겸사.
