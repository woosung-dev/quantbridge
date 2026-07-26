<!-- opspack-ws2 스프린트(정비 팩 + WS Tier 2)의 멀티에이전트 운영 계약 — tier-c 계약 대비 델타만 기록 -->

# opspack-ws2 운영 계약 (델타)

> 기본 계약은 [`../tier-c/operating-contract.md`](../tier-c/operating-contract.md) 전부 상속 (→ functional-parity → c-language-port 체인). 아래는 이번 스프린트에서 달라진 것만.
> 플랜 정본: `~/.claude/plans/transient-crafting-yeti.md`

## 1. 범위 (사용자 확정 2026-07-24)

- **순차 2단계 + ★단계 게이트**: Phase 1 정비 팩(beat /data 권한 + BL-417·421·422 + BL-418·419 포함 확정) → 체크리스트·게이트 전부 그린 후에만 → Phase 2 WS Tier 2(public ticker + 미실현 P&L, position 채널 제외).
- 사용자 4결정: ① BL-418/419 포함 ② BL-417 = **컬럼 제거**(소비자 0 실측) ③ ticker 팬아웃 = **전원 브로드캐스트**(router 무변경) ④ 미실현 P&L = trading 코크핏 **"총 세션" 카드 교체** + dashboard foot 부기.
- **알림 실수신 반전**: backend/.env.local 에 TELEGRAM_BOT_TOKEN/CHAT_ID **SET 실측**(tier-c 문서와 반대) → D4 Telegram 실수신 dogfood 편입(코드 변경 0). Slack 미설정 → mock 유지.

## 2. 워커 편성 델타

### Phase 1

| 워커                  | 권역                                                                                           | 비고                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `op/contract-core`    | BL-417+421+419 (BE live_signal·trading 4파일·alembic·repo + FE live-sessions·authed allowlist) | 충돌 컴포넌트 {417,419,421} 단일 워커                                           |
| (오케스트레이터 직접) | beat /data 권한 — Dockerfile 2줄+compose 주석                                                  | **예외 적용**: 2줄급 인프라 + 검증(볼륨 재생성 실측)이 본체. context-notes 기록 |
| `op/alert-ui`         | BL-422 (session-diagnostics ok 어포던스 + format.ts)                                           |                                                                                 |
| `op/rt-contract`      | BL-418 (PAYLOAD_MODELS 배선 + invalid counter)                                                 |                                                                                 |

cherry-pick 순서: beat 인프라 → contract-core → rt-contract → alert-ui.

### Phase 2

| 워커            | 권역                                                                                                                   | 비고                                               |
| --------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `op/ws2-s0`     | ticker 계약(BE/FE 스키마 쌍둥이 + to_bybit_raw_symbol 미러)                                                            | 직렬 선행 — PAYLOAD_MODELS 에 TickerPayload 등재   |
| `op/ws2-stream` | BybitPrivateStream 3-seam 파라미터화 + bybit_public_stream.py + websocket_task + celery_app + publish_ticker + compose | 기존 private 테스트 **무수정 green** = 회귀 게이트 |
| `op/ws2-fanout` | realtime/manager.py 브로드캐스트                                                                                       | router.py 무변경                                   |
| `op/ws2-fe`     | store ticker slice + unrealized + 두 cockpit + authed spec                                                             | 코크핏 단일 워커(tier-c 선례)                      |

cherry-pick 순서: s0 → stream → fanout → fe.

## 3. 게이트 기준 (이번 스프린트 baseline)

- tier-c 머지 후 문서치: BE 2490+46skip / FE 1019(177) / canon 32 / authed 63. **W0 재측정 실측값이 공식 baseline** (checklist.md §게이트 표).
- Phase 1 순증 목표: BE +7 / FE +7 + alembic 왕복(drop column) + beat 볼륨 재생성 실측.
- Phase 2 순증 목표: BE +25~35 / FE +15~25 + 신규 celery 태스크 큐 라우팅 단정 테스트.
- authed 신규 spec 0 예상(기존 spec 수정만) — 발생 시 playwright.config.ts 열거식 testMatch 등재.

## 4. 오라클 델타 (§7.3)

- beat 권한: 볼륨 재생성 → `ls -ln /data` uid 1000 + 5분 내 worker 로그 evaluate 수신 + restart 후 지속.
- /state pending: DevTools Network 200+`evaluated:false` + 콘솔 404 도배 0 — **authed allowlist 의 `/\b40[0-9]\b/` 브로드 패턴 제거가 게이트** (404 는 어떤 형태로도 미등재).
- Telegram: 실 챗 수신 + worker fired 로그 + redis dedupe 키 (재시험 시 DEL — 1h throttle).
- ticker: 공개 REST `v5/market/tickers` markPrice + Bybit 웹 콘솔 **2계통** (±수 tick). 앱으로 앱 검증 금지.
- 미실현: `(mark−entry)×qty×sign` 수기 손계산 + `/positions` 거래소 unrealized 부호·규모 정합(차이 허용오차 기록).
