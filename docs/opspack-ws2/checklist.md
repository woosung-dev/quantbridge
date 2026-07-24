<!-- opspack-ws2 스프린트(정비 팩 + WS Tier 2)의 작업 항목·게이트 추적 체크리스트 (SSOT) -->

# opspack-ws2 체크리스트

> 스프린트 정본: `~/.claude/plans/transient-crafting-yeti.md` · 운영 계약: [`operating-contract.md`](operating-contract.md) · 결정 기록: [`context-notes.md`](context-notes.md)
> 기준 커밋: main @ `6edc8e9` → `stage/opspack-ws2`

## 0. 범위 (사용자 확정 2026-07-24)

- Phase 1 정비 팩 6종(beat 권한·BL-417 제거·BL-421 pending·BL-422·BL-418·BL-419) → ★단계 게이트 → Phase 2 WS Tier 2(public ticker + 미실현 P&L, position 채널 제외).
- Telegram 실수신 dogfood 편입(env SET 실측). Slack mock 유지.

## 1. Phase 1 — 정비 팩

- [x] **W0** — stage 브랜치 + 문서 3종 + 베이스라인 재측정(§7.1: FE 1019/177 · BE 2489+1 env-fail→hermetic 픽스 @d50bb2d 로 2490 상당) + codex G0 (REVISE→반영, context-notes #9)
- [x] **beat /data 권한 (오케스트레이터)** — Dockerfile /data seed @a7c47d5 + 반증: 익명 볼륨 fresh-seed uid 1000·WRITE_OK + 재시작 후 PermissionError 0·즉시 발화·schedule 파일 1000:1000 (D1 선행 완료, context-notes #11)
- [x] **op/contract-core** — 적대평가 ACCEPT(반증 8종·dev DB 왕복 2회 원상복귀) @66cf316 + 평가 노트 2건 반영(stale 주석·rows==0 대칭 spy)
- [x] **op/alert-ui** — 적대평가 ACCEPT(반증 16입력 실행·fail-on-base 증명) @fe5f343, docs 헝크 제외
- [x] **op/rt-contract** — 적대평가 ACCEPT(반증 7종·12지점 독립 재대조 일치) @8317564
- [x] **P1 통합** — cherry-pick 3건 클린 + prettier 정규화 @a68f839 + ★통합 발견 1건: 마이그레이션 테스트 5 FAIL(테스트 DB metadata-스키마 + stale alembic_version) → DROP IF EXISTS 방어(20260626 선례 미러) @26bdf01
- [x] **P1 dogfood** — D1 beat(선행) / D2 /state 200+`evaluated:false` 17회+·콘솔 404 0(Opus 실브라우저) / D3 ok 어포던스·"0.01%" 트리밍·201×2+409×1 / D4a 실 Telegram 수신(`{'telegram': True}`) + **D4b 풀 파이프라인 실발화**(beat→규칙평가→실잔고→발화 `fired:1`→2주기 throttled + redis TTL — 합성 손실 주입·전량 복구, context-notes #13)

## 2. Phase 2 — WS Tier 2 (★Phase 1 게이트 표 전부 ✅ 후에만 착수)

- [x] **op/ws2-s0** — ticker 계약 @ffb0a70. 소형 계약 슬라이스라 오케스트레이터 인라인 적대 검증(diff 전문 + split-limit 쌍둥이 반증 + DB 게이트 재현 62+13 그린)으로 갈음 — context-notes #16
- [x] **op/ws2-stream** — 적대평가 ACCEPT(반증 8종 — private 20 무수정 green·순환 import 실증·monotonic 스로틀·DB 포함 312 재현) @9d78371
- [x] **op/ws2-fanout** — 적대평가 ACCEPT(반증 6종 격추 실패 — mutation-safe 이중 사본·재연결 재구독 직접 재현) @fb4be92
- [x] **op/ws2-fe** — 적대평가 REVISE 2건(em-dash 래칫·authed 단정 환경 의존) → 오케스트레이터 직접 반영 후 1044 그린 @ee82513
- [x] **P2 통합** — cherry-pick 3건 클린 + prettier 정규화 @1eaf8a3 + 게이트 풀런 그린
- [ ] **dogfood D5~D8** — ticker 2계통 오라클 / 미실현 손계산 / 재연결·lease / Opus 실브라우저 콘솔 0

## 3. 마무리

- [ ] codex read-only 최종 누적 diff 리뷰 1회 (finding §7.3 코드 대조)
- [ ] `/vercel-react-best-practices` FE 변경분 검토 → eslint+tsc → (수정 시) 스코프 재게이트
- [ ] 문서 3종 갱신 + TODO.md + BL 등재/해소 → push(`QB_PRE_PUSH_BYPASS=1`) → stage→main PR 1개 (squash 는 사용자)

## 4. 게이트 추적

| 게이트                   | baseline (W0 재측정)                      | Phase 1 목표/실측                                                                                    | Phase 2 목표/실측                        |
| ------------------------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| FE vitest                | 1019 (177 파일) ✅ 재측정                 | ≈+7 그린 / ✅ **1026**                                                                               | +15~25 그린 / ✅ **1044** (+18)          |
| FE tsc / lint / prettier | 0                                         | 0 / ✅ 0·0·0(터치 파일)                                                                              | 0 / ✅ 0·0·0                             |
| BE pytest (3-env)        | 2489+1 env-fail(→hermetic 픽스) ✅ 재측정 | ≈+7 그린 / ✅ **2502 passed·46 skip**                                                                | +25~35 그린 / ✅ **2531** (+29)          |
| BE ruff / mypy           | 0 / 0                                     | 0 / ✅ 0·0 (197 파일)                                                                                | 0 / ✅ 0·0 (198 파일)                    |
| e2e:design-canon         | 32                                        | 32 불변 / ✅ **32/32**                                                                               | 32 불변 / ✅ **32/32**                   |
| e2e:authed               | 63                                        | 63 (allowlist 강화) / ✅ **63/63** (404 비허용 하 실주행)                                            | 63± / ✅ **63/63** (KPI 단정 환경독립화) |
| alembic up→down→up       | —                                         | 그린 / ✅ dev DB 왕복 2회(평가자·psql DDL 검증) + 테스트 DB 5종 + upgrade 적용(20260724_0002·컬럼 0) | 해당 없음                                |
| beat 볼륨 재생성 실측    | —                                         | uid 1000·발화 지속 / ✅ 익명볼륨 seed + 재시작 발화                                                  | —                                        |
| DB/외부 오라클           | —                                         | Telegram 실수신 / ✅ D4a 직발송 True + D4b beat 실발화 `fired:1`·throttled·TTL 3597                  | ticker 2계통·미실현 손계산 / —           |
| Opus MCP dogfood         | —                                         | D1~D4 / ✅ **전 항목 PASS** (증거 스크린샷 5종·네트워크·콘솔 덤프)                                   | D5~D8 / —                                |

## 5. 환경 (재발 방지 실측치 — tier-c 승계)

- DB 5436 오버레이 + redis 6380 (스택 가동 중 확인). psql 은 `docker exec quantbridge-db psql -U quantbridge -d quantbridge`.
- BE pytest **3-env**: `DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5436/quantbridge_test` + `TEST_DATABASE_URL=`(동일) + `TEST_REDIS_LOCK_URL=redis://localhost:6380/3`.
- FE 3100 + BE `FRONTEND_URL` + `PLAYWRIGHT_BASE_URL=http://localhost:3100`. 정체성 프로브(openapi title/<title>) 없이 오라클 선언 금지.
- codex sandbox: FE worktree 사전 `pnpm install`, BE 는 메인 `.venv/bin/*` 직접, DB 게이트는 평가자/오케스트레이터.
- 게이트 풀런 중 stage 커밋 동결. worktree 커밋 lint-staged 미가동 → 통합 시 prettier --check.
