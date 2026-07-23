<!-- tier-c 스프린트 중 내려진 결정과 근거의 누적 기록 (append-only) -->

# tier-c 컨텍스트 노트

## 2026-07-24 W0 — 스프린트 성립 결정

1. **범위 확정 (사용자)**: A안 = Tier C 4종 전부 + WS Tier 1. WS Tier 2 후속. 알림 실수신 검증은 채널 미세팅으로 mock 까지만 — 후속 이연.
2. **실측 반전 2건 (§7.1 baseline preflight 재확인 사례)**:
   - 펀딩 "검증 부담 최대" 전제 반증 — PR #351 이 백테스트 엔진에 accrual 을 이미 end-to-end 배선(손계산 oracle 9건 포함). 이번 작업 = 노출 완성(total_funding 4-site) + backfill + FE 활성화. 메모리의 "PR #351 = 트레이딩 쪽" 라벨은 착오였다.
   - WS "최저비용" 전제 반증 — ws_stream 은 아웃바운드 전용. 인바운드 서버·팬아웃·WS 인증·FE 계층 전부 신설 = 4종 중 최대 규모.
3. **WS 아키텍처 3결정**: (a) uvicorn API in-process (`src/realtime/` 신설, lifespan 소유) (b) Redis pub/sub `qb:rt:user:{user_id}`, WS 이벤트 = invalidate 힌트 전용(폴링=정합성 SSOT, setQueryData 금지), 발행 5지점 commit 직후, publisher 는 절대 raise 안 함 (c) 첫 메시지 auth + Origin 명시 검증.
4. **포지션 대조 상대 = `LiveSignalState.last_open_trades_snapshot`** — Order 합산은 거래소측 TP/SL 체결이 Order 행으로 안 남아 원리적 드리프트라 기각. 강제 정합 금지, verdict 6종 정직 표기. 비영속(마이그레이션 0). money-path `fetch_position` 불변 — 대조용 `fetch_open_positions` 신설(hedge = raise 아닌 2건 반환).
5. **alert_rules 는 PG enum 미사용** — String(32)+StrEnum (LiveSignalInterval 선례). functional-parity 의 enum 혼합 케이싱 P1 재발을 원천 차단.
6. **알림 threshold = 절대 손실 %** — "킬스위치 한도의 x%" 저장 기각(config 변경 시 규칙 의미가 몰래 바뀌는 커플링).
7. **손실한도 접근 알림 = beat 신설 의무** — 킬스위치 평가는 주문 시도 시에만 실행됨을 실측. 기존 발화 지점 삽입만으로는 "80% 접근" 관측 불가.
8. **Telegram 팬아웃 = 신규 `trading/alerting.py` 디스패치** — `send_critical_alert` 시그니처 확장 기각(호출처 6+ Slack 시맨틱 보존). telegram_alert.py 의 최초 배선 지점.
9. **펀딩 체크박스 활성화 = 의도적 캐논 이탈** — 프로토타입(screen-05:1504)도 disabled 로 그려져 있으나 funding 배선 이후 산물이 아니므로 활성화. 코드 주석에 근거 1줄 의무.
10. **DB 5436 프로브 실측**: orders=12 / strategies=6 / **funding_rates=4행** — forward-only 인제스션 갭이 실데이터로 확인(backfill 필요성 실증). quantbridge_test 존재.

## 2026-07-24 W0 — baseline preflight 발견 (§7.1 적중)

1. **BE pytest 인캔테이션에 `DATABASE_URL` 오버라이드 추가 의무 (3-env)**: 2-env(TEST\_\*)만으로는 `test_market_data_backfill.py` 2건이 FAIL — `_async_backfill` 이 worker 엔진을 `DATABASE_URL`(backend/.env.local 의 5433 = 남의 DB)로 생성해 InvalidPasswordError. `DATABASE_URL=...5436/quantbridge_test` 추가 시 2/2 그린. **실효 baseline = 2433 passed · 46 skipped** (문서 기준과 합계 일치). 전 워커 게이트 인캔테이션에 반영 완료.
2. FE baseline = 983 passed(171 파일) 정확 재현. ruff/mypy/tsc/lint 전부 0.
3. host psql 부재 — DB 오라클은 `docker exec quantbridge-db psql` 로 수행.
