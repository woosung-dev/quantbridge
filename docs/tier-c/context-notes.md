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

## 2026-07-24 G0 — codex read-only 플랜 검증 (273k tokens, 프레임 2 + MAJOR 5 + MINOR 2)

1. **★프레임 1 (코드 대조 확정)**: `last_open_trades_snapshot` 은 실경로에서 항상 `{}` — `to_report()` 가 open_trades 를 **리스트**로 내는데(strategy_state.py:813) live_signal.py 업서트 가드(L636-638)는 dict 만 저장. **대조 소스를 `last_strategy_state_report["open_trades"]` 로 변경** (report 는 dict 라 정상 저장 중 — 마이그레이션 불요 유지). 잠복 결함은 신규 BL 등재 예정 (이번 스프린트에서 저장 계약 수술은 범위 외 — 수술 시 소비자 전수 확인 필요).
2. **★프레임 2**: 발행 지점 5→7 확장 — cancel_order celery leg 전이(source="cancel") + live_signal 세션 자동 비활성 2곳(L429/L496) 추가. 거절 등 잔여 전이는 fetch_order_status terminal 발행 + 폴링 폴백이 커버(과잉 확장 금지).
3. **MAJOR 반영**: (a) WS 순서 계약 — Origin 불일치는 accept 전 close(=HTTP 403 핸드셰이크 거부, WS close code 미전달을 테스트로 실측 잠금), auth 실패만 accept 후 4401. (b) 세션 손실 provenance = `LiveSignalEvent.order_id` 귀속 조인 (Order 에 live_session_id 없음 — strategy_id 합산은 수동/타 세션 오염. 킬스위치와 스코프 다름을 발송 메시지에 정직 표기). (c) alert_rules 에 타입별 CheckConstraint (loss_limit↔threshold NOT NULL). (d) BL-388 tripwire 는 BE 3-site 만 강제 — FE zod 는 funding-fe 의 F4 vitest 가 담당(플랜 문구 과장 교정). (e) realtime lifespan 실패 정책 — listener 는 background task, Redis 불능이어도 앱 시작 차단 금지(degraded startup 계약 유지), shutdown cancel→await→close.
4. **MINOR 반영**: RealtimeBridge mount = Query Provider(Clerk 내부) 하위 (clerk-theme-bridge.tsx:16). 알림 검증 기준 통일 = mock 까지 (플랜 내 "실수신" 잔존 문구 정리).
5. G0 가 옳다고 확인한 항목: funding 호이스팅 전략 / WS in-process / Requestish 어댑터 + Origin 별도 검증 / String+StrEnum + partial unique / giveup 2지점 좌표 / fetch_open_positions 분리.

## 2026-07-24 수용 루프 실적 — 적대 평가(모델 교차)가 잡은 실버그 (워커 자기 게이트는 전부 그린이었다)

1. **tc-optimizer-fe F**: E1 필드 에러가 실 UI 에서 절대 미렌더 — zodV4Resolver 는 평탄 키("parameters.0.log_scale")로 errors 를 내는데 워커는 중첩 경로만 읽음. F6 테스트(워커 자신이 작성)가 정확히 반증. 픽스 = param-rows-fieldset 의 이중 흡수 패턴 미러.
2. **tc-realtime-fe P1**: 접속 URL 에 `/api/v1/realtime/ws` 경로 미부착 — 커밋된 모든 설정값(origin만)으로 실환경 접속 원천 불가 + 테스트가 env stub 에 경로를 구워 넣어 은폐(§7.3 전형). 픽스 = `realtimeWsUrl()` 코드 유도 + 최종 URL 값 단언.
3. **tc-alerts-be P1**: beat 태스크 task_routes `{"queue": "default"}` — 프로젝트 디폴트 큐 이름은 `celery` 고 `default` 소비 워커 부재 → **손실한도 알림 영구 미실행 silent failure** (LESSON-038 부류, 평가자가 celery 라우터 실해석으로 실증). 픽스 = 라우트 삭제(관례 = 전용 큐만 등재) + route 큐 이름 단정 테스트.
4. **tc-alerts-be P2 실증 2건**: (a) G0 핵심 결정인 귀속 조인 SQL 이 전 테스트에서 스텁 우회 — repo 레벨 DB oracle 테스트 신설 지시. (b) no-op 테스트의 AssertionError 가 훅의 except 에 삼켜져 반증 불가 — 평가자가 오동작 재현 테스트로 실증 후 카운터 스텁 교체 지시.
5. **환경 함정 (worktree)**: codex sandbox 가 uv 캐시·DB 소켓(5436)·DNS 를 차단 → 워커 자기 게이트는 부분 불능. 대응 = FE worktree 사전 pnpm install(스토어 하드링크 ~7s) + BE 는 메인 레포 `.venv/bin/*` 바이너리 직접 사용 + DB 게이트는 평가자/오케스트레이터가 재현. worktree 커밋은 lint-staged 미가동(루트 node_modules 부재) — W4 에서 prettier 정규화 확인 의무.
6. cherry-pick 은 반드시 메인 트리에서 (워크트리 안에서 자기 HEAD cherry-pick 은 no-op — 1회 실측).

## 2026-07-24 최종 누적 diff 리뷰 (codex 238k) + 통합 마찰 3건

1. **MAJOR 2건 해소**: (a) threshold_percent 상한 부재 — FE/BE 통과·NUMERIC(18,8) overflow 500. BE `le=100` + FE zod max 100 미러 + 422/필드 에러 테스트. (b) 워치독 세션 귀속 휴리스틱(전략·계좌·심볼) — 동일 조합 수동 주문 오발화. `LiveSignalEvent.order_id` 정확 귀속으로 교체(휴리스틱 finder 제거) + 수동 주문 no-op oracle.
2. **MINOR 2건 처리**: session_state 발행 시 FE 가 목록 키도 invalidate(활성 세션 수 정합 — 코드 반영). payload 계약 미강제 + live_signal errors 경로 발행 누락 → BL 등재로 이연.
3. **통합 마찰 3건 (오케스트레이터 직접, 계약 예외)**: test_migrations 기대 테이블 8→9 / 테스트 DB 고아 alert_rules drop 후 alembic head 정렬(create_all 선점 생성 vs alembic 이력 충돌 — 신규 마이그레이션 랜딩 시 테스트 DB 정렬 절차 확인) / dashboard-shell 테스트에 RealtimeBridge null mock(셸 mount 가 QueryClient 요구).
4. **★게이트 러닝 중 cherry-pick 금지 재확인**: 통합 풀런 도중 stage 에 커밋을 얹어 uvicorn --reload 재시작 → authed 4 did not run 위양성. 안정 상태 단독 재실행으로 63/63. "게이트 재현은 직렬"은 커밋 동결까지 포함한다.
5. **publish-be 평가 F2건**: 발행용 조회가 money-path 임계 구간 침범(전이 앞 SELECT 이동·save↔commit 사이 SELECT). 픽스 = 원위치 복원 + commit 후 suppress best-effort. 순수 append diff 재확인.
6. **최종 확정 게이트**: BE 2490+46skip / FE 1019(177) / ruff·mypy·tsc·lint·prettier 0 / canon 32 / authed 63. backfill 3심볼×2804행(2024-01-01~), 8h 갭 0. 워커 컨테이너 sentinel(§7.2) 통과.
