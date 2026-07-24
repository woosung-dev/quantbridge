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
9. **Bybit public WS URL 단일 상수** — demo 는 mainnet 공개 시세 공유(public 스트림에 demo variant 없음). `wss://stream.bybit.com/v5/public/linear` 공용. 구현 시 공식 docs 재확인 표기 의무(tickers delta 에 markPrice 부재 가능 → 스냅샷 병합).
