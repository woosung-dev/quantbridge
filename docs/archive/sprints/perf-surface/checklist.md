<!-- perf-surface 스프린트(성과 표면 A1~A4)의 작업 항목·게이트 추적 체크리스트 (SSOT) -->

# perf-surface 체크리스트

> 스프린트 정본: `~/.claude/plans/quantbridge-perf-surface-handoff.md` · 세션 지도: `~/.claude/plans/perf-surface-snug-prism.md` · 운영 계약: [`operating-contract.md`](operating-contract.md) · 결정 기록: [`context-notes.md`](context-notes.md)
> 기준 커밋: main @ `b023ce5` (PR #470 opspack-ws2) → `stage/perf-surface`

## 0. 범위 (사용자 확정 2026-07-24)

- Phase A 전체(A1~A4) + 여유 시 A5 문서 위생. 수익률 = total_return + 미청산 부기. PR #467 작업 금지.

## 1. §0 전제 게이트

- [x] main = b023ce5 + 트리 클린 + `stage/perf-surface` 신설(main 베이스)
- [x] 스택 기동 확인: db 5436·redis 6380·worker·beat·ws-stream·optimizer-heavy Up
- [x] baseline 재현: FE **1044(182)** ✅ (문서치 일치) / BE 재측정(§게이트 표)
- [ ] codex G0 read-only 1회 → finding 코드 대조 후 반영

## 2. 계약 + 워커

- [ ] 계약 C1~C6 동결 + 워커 프롬프트 4종 배포
- [ ] **ps/w1-be-perf** — C1~C5 BE 생성 → 적대평가 → 게이트
- [ ] **ps/w2-be-ohlcv** — C6 BE 생성 → 적대평가 → 게이트
- [ ] **ps/w3-fe-surface** — C1~C5 FE 생성 → 적대평가 → 게이트
- [ ] **ps/w4-fe-minichart** — C6 FE 생성 → 적대평가 → 게이트

## 3. 통합 + 검증

- [ ] cherry-pick W1(+defer)→W2→W3→W4 (메인 트리) + 단계별 게이트 + prettier --check
- [ ] 오라클 3점 대조(모순 표본 4a3bb5d3/8f6ba11a 필수)
- [ ] Opus MCP dogfood(성과 열·전략 최신·미니차트, storageState)

## 4. 마무리

- [ ] codex read-only 최종 누적 diff 리뷰 → §7.3 판정
- [ ] `/vercel-react-best-practices` FE 변경분 검토
- [ ] 게이트 전수(eslint+tsc / pnpm e2e+canon+authed / pnpm build fe-isolated 재기동)
- [ ] 문서 3종 + TODO.md + BL → push(QB_PRE_PUSH_BYPASS=1) → stage→main PR 1개(squash 사용자)
- [ ] A5(여유 시): dev-log INDEX 7월 3건 + Quick Summary + TODO [확인 필요] 총수익률 항목 닫기

## 5. 게이트 추적

| 게이트                                 | baseline (W0 재측정)          | Phase A 목표/실측                 |
| -------------------------------------- | ----------------------------- | --------------------------------- |
| FE vitest                              | **1044 (182 파일)** ✅ 재측정 | +4신규~ 그린 / —                  |
| FE tsc / lint / prettier               | 0                             | 0 / —                             |
| BE pytest (3-env)                      | — (재측정 중)                 | +5신규~ 그린 / —                  |
| BE ruff / mypy                         | 0 / 0                         | 0 / —                             |
| e2e:design-canon                       | 32                            | 32 불변 / —                       |
| e2e:authed                             | 63                            | 63 (404 비허용) / —               |
| vitest design-canon-source diffRatchet | 불변                          | 증감 0 / —                        |
| alembic up→down→up                     | —                             | 무변경 확인 1회 / —               |
| DB/외부 오라클                         | —                             | 성과 3표본·전략 최신·미니차트 / — |
| Opus MCP dogfood                       | —                             | 성과 열·부기·미니차트 / —         |

## 6. 환경 (재발 방지 실측치 — opspack-ws2 승계)

- DB **5436** 오버레이 + redis **6380**. psql = `docker exec quantbridge-db psql -U quantbridge -d quantbridge`.
- BE pytest **3-env**: `DATABASE_URL`=`TEST_DATABASE_URL`=`postgresql+asyncpg://quantbridge:password@localhost:5436/quantbridge_test` + `TEST_REDIS_LOCK_URL=redis://localhost:6380/3`.
- FE **3100** + BE 8100 (3000=nexus-core 점유). `PLAYWRIGHT_BASE_URL=http://localhost:3100`. 정체성 프로브 없이 오라클 선언 금지.
- codex sandbox: FE worktree 사전 `pnpm install`, BE 는 메인 `.venv/bin/*` 직접, DB 게이트는 평가자/오케스트레이터.
- 게이트 풀런 중 stage 커밋 동결. worktree 커밋 lint-staged 미가동 → 통합 시 prettier --check.
