<!-- opspack-ws2 스프린트의 결정 기록 (append-only) — 왜 그렇게 했는지의 SSOT -->

# opspack-ws2 컨텍스트 노트 (append-only)

## 2026-07-24 계획 확정

1. **PR #469 머지 확인** — MERGED @6edc8e9 (2026-07-24T01:22Z). stage/opspack-ws2 는 이 커밋 베이스.
2. **사용자 4결정** (별점 표 + AskUserQuestion): ① BL-418/419 Phase 1 포함 ② BL-417 = 컬럼 제거 ③ ticker 팬아웃 = 전원 브로드캐스트 ④ 미실현 P&L = "총 세션" 카드 교체.
3. **★Telegram env 반전** — tier-c 문서는 "미설정"이었으나 backend/.env.local 에 TELEGRAM_BOT_TOKEN(46자)/TELEGRAM_CHAT_ID(10자) SET 실측(awk 길이 검사 — 값 미노출). 실발송 경로에 flag/stub 없음(`common/telegram_alert.py:109-112` 미설정 시만 silent skip) → **코드 변경 0 으로 실수신 검증 가능**. D4 편입. SLACK_WEBHOOK_URL 은 부재 → Slack mock 유지.
4. **BL-417 소비자 전수 실측** — 로직 소비 0건: BE 는 API 통과 노출(`router.py:471`)뿐, FE 는 zod 선언(`live-sessions/schemas.ts:53`)+픽스처뿐. 포지션 대조·Phase 2 미실현 모두 `last_strategy_state_report["open_trades"]` 사용 → 제거가 SSOT 단일화. **backend.md §7 "컬럼 삭제 2단계 배포" 1단계 압축 예외**: 로컬 단일 운영 + FE zod required 라 분리 배포 시 parse 실패 → FE/BE 동일 커밋 강제가 오히려 안전.
5. **beat /data 근본 원인** — Dockerfile 에 `/data` 미존재 → named volume 첫 생성 시 root 소유 초기화(Docker 는 이미지 마운트 포인트의 내용·소유권을 빈 볼륨에 복사). Sprint 4(2026-04-25 dev-log) 부터 만성 재발. 픽스 = 이미지에 appuser 소유 `/data` 선생성(A안). entrypoint gosu 안(CSO-2 후퇴)·경로 이전안(동일 문제 재발) 기각. 기존 볼륨은 재생성 필요 — D1 반증 절차에 포함.
6. **BL-421 근본 해소 = BE 200 전환** — FE 는 이미 404→null 흡수 중이나 **브라우저 네이티브 네트워크 404 로그는 JS 로 억제 불가**. authed `/\b40[0-9]\b/` 브로드 allowlist 가 현재 이를 삼키는 중 → allowlist 제거(404 미등재)가 검출력 게이트.
7. **P1-W2(beat 인프라) 오케스트레이터 직접 예외** — 코드 2줄 + 검증(볼륨 재생성 실측)이 본체라 codex 워커 비용 불균형. 계약 예외 3종(1줄급 통합 마찰) 준용, 본 노트로 기록.
8. **BL-418 무효 payload 시 skip 채택** — FE zod 가 어차피 silent drop 하므로 발행 무의미. raise 는 발행 지점 12곳의 no-raise 계약 위반. counter 분리(`qb_rt_publish_invalid_total` vs 기존 `qb_rt_publish_failed_total`=인프라 실패)로 조기 검출.
9. **codex G0 (REVISE → 반영 완료, thread 019f91e4-3a46)** — 유효 finding 반영: ① FE `updated_at z.string()` → nullable 완화 W1 편입 ② `tests/trading/test_realtime_publisher.py` probe payload 가 BL-418 검증 도입 후 무효 → W4 소유 편입(failed/invalid counter 기대값 분리) ③ drop 전 psql 오라클 실측 = **non-empty 0/3** (데이터 손실 0, 1단계 drop 안전 확정) ④ P2: `list_distinct_active_symbols()` repository 경유 + register 킥은 `live_session_service.py` commit 후 — WA 소유 파일에 repo/service 추가 ⑤ P2 ticker `ts` 는 epoch-ms — FE stale 계산 ms 고정 + 빈 문자열/비유한 mark 명시 거절 ⑥ manager send_to_all 은 등록(인증) 소켓만 순회 + 실패 소켓 제거 테스트 ⑦ ws_stream 용량: 로컬 1계정 전제 concurrency 3 유지 + "계정 N+1 ≤ concurrency" 규약, 멀티계정 starvation 은 후속 BL 등재 예정. FRAME 1건(beat 픽스 기반영)은 의도된 선행 — 무해.
10. **베이스라인 반전 — telegram 테스트 env 오염**: 사용자가 tier-c 후 TELEGRAM\_\* 를 .env.local 에 세팅 → `test_send_silent_skip_when_token_unset` FAIL (delenv 는 pydantic-settings 의 env_file 로딩을 못 막음). 오케스트레이터 직접 hermetic 픽스(init kwarg 오버라이드) @d50bb2d. 실효 baseline = **2489+1(env-fail→픽스 후 2490 상당) / FE 1019**.
11. **beat /data 검증 우회** — `docker volume rm` 이 권한 설정 차단 → 기존 볼륨(이전 세션 chown 1000 완료) 유지 + **익명 볼륨(자동 삭제) fresh-seed 검증**으로 대체: `docker run --rm -v /data <image>` → uid 1000 + WRITE_OK 실측. 픽스 주장(fresh volume=appuser) 동일 강도로 반증됨.
12. **P1 통합 발견 — 마이그레이션 IF EXISTS**: 테스트 DB 는 conftest `metadata.create_all`(신모델)로 재생성되는데 alembic_version(비모델 테이블)은 생존 → stale revision 에서 drop 마이그레이션 단독 실행 시 UndefinedColumn. `DROP COLUMN IF EXISTS`(20260626_0001 선례) @26bdf01. **교훈: 컬럼 제거 마이그레이션은 항상 IF EXISTS.**
13. **D4b 실발화 방법론** — 실손실 세션 부재 + `list_active_loss_rules_with_sessions` 가 세션 활성 요구(:64) → ① 귀속 주문 1건 pnl 일시 변조(−0.0138→−100, tier-c D5 위조 선례 준용) ② 세션 `is_active=true` + **`last_evaluated_bar_time=now()+2h`**(list_active_due 필터로 엔진 평가 원천 차단 — 데모 주문 0, evaluate_all due 0 실측) ③ beat 실발화 `{'evaluated':1,'fired':1}`(실 Bybit 잔고 조회 1.7s 포함) + 실 Telegram 수신 ④ 2주기 `alert_rule_throttled` 실측 ⑤ 전량 복구(pnl·is_active·bar_time·redis 키) psql 재검증. **미래 bar_time 트릭 = 활성-비평가 안전 창의 재사용 가능 레시피.**
14. **dogfood 부수 발견 (BL 등재 대기)**: ① 비활성 세션의 진단(규칙·포지션·상태)을 코크핏 UI 로 열 수 없음 — `/live-sessions` 가 active 전용(router list_active)이고 상세 진입은 리스트 클릭뿐 (Opus 는 RQ 캐시 주입으로 우회) ② 615f63e1 에 loss_limit 0.01%/watchdog telegram 활성 규칙 2건이 dogfood 산출물로 영속 — 실사용 관점 무해(비활성 세션)라 존치.
15. **S0 평가 델타** — 계약 슬라이스(10파일 소형)는 서브에이전트 대신 오케스트레이터 인라인 4축 검증으로 갈음: diff 전문 정독 + JS `split(":",1)` limit 시맨틱 vs Python maxsplit 쌍둥이 정합 반증 + sandbox 차단분(DB 테스트 62건) 직접 재현. WA/WB/WC 는 서브에이전트 적대 평가 유지.
16. **Bybit public WS URL 단일 상수** — demo 는 mainnet 공개 시세 공유(public 스트림에 demo variant 없음). `wss://stream.bybit.com/v5/public/linear` 공용. 구현 시 공식 docs 재확인 표기 의무(tickers delta 에 markPrice 부재 가능 → 스냅샷 병합).
