# Dev-log Index

> 회고 기록을 **찾기 위한** 색인. 요약은 최근 12회차만 한 줄씩 두고 나머지는 날짜·제목만 둔다.
> 이 파일은 매 세션 읽히므로 **줄당 300자 상한**을 `scripts/docs-audit.sh` 가 강제한다 (초과 시 exit 1).
> ★**회고 원문은 2026-08-06 문서 대개편에서 삭제됐다** — 원문 조회는
> `git show 0f0f0b06:docs/dev-log/<파일명>` (파일명 = `YYYY-MM-DD-슬러그.md`, 압축 전 색인 원문 = `git show 0f0f0b06:docs/archive/dev-log/index-full-2026-08-02.md`).
> ★**단 `docs/lessons.md` 승격 대기 중인 회차의 버퍼는 파일로 남는다** (ADR-026 §3 — dev-log 는 이력이 아니라
> 입력 버퍼다). 링크가 걸린 항목 = 버퍼 존재, `— dev-log` 로 끝나는 항목 = 승격 완료 후 비워진 것.

---

## 최근 12회차

> 13번째가 생기면 **가장 오래된 항목을 아래 「전체 이력」으로 내린다** — 이 섹션은 12개를 넘지 않는다.
> PR 번호는 머지 커밋(`git log`)으로 검증했다 — dev-log 본문은 머지 **전**에 쓰이므로 PR 번호를 담지 않는다.

- **2026-08-06 docs-overhaul(fix-doc)** — ★**[ADR-026] SSOT 7축 Accepted** · docs **39M→4.1M(−90%)** · `.ai/` 해체 → `.claude/rules/`. ★자동 로드 **v2.0.64+ 확인** — 08-02 「로더 없음」 실측은 버전 종속. RESOLVED 94·링크 240 강등, archive/dev-log 삭제(tombstone). ★내 회귀: 개행 넘는 링크 정규식이 BL-451/452 삼킴 → 복구·LESSON-073
- **2026-08-06 entry-set-divergence** — ★[BL-604] 동인 분리 → **프레임 반전**: 워밍업 기여 0건(B≡R(fill) multiset 동일)·세션 공백 0쌍·「예측 못 한 46건」은 키 규약 관측(체결 지연 57%가 ±3봉 밖). 장전봉 정렬 81/90=90%, 진짜 미예측 **2/90**. `replay`/`entrysets` 신설. FE 정직성 3종+BL-609 Resolved — [dev-log](2026-08-06-entry-set-divergence.md)
- **2026-08-06 backtest-reality-gap** — ★백테스트↔라이브 원장 **첫 대조**. 병목은 비용·체결가가 아니라 **진입 집합** — 매칭 34/84, 예측 못 한 46건 = 손실 62%([BL-604]). 비용은 taker 0.055% 단일(가정의 1/2.7, [BL-603]). 스팟/perp 144쌍 전건 양수·중앙 +29.95(**BL-535 종결**). ★귀속 off-by-one 이 가격축 부호를 바꿨다 — dev-log
- **2026-08-06 ci-diet** — CI **23~25분 → 14.8분**(PR #548/#549/#550 · 47 패키지 제거). ★★**12분 미달은 구조적** — 코퍼스 첫-접촉 비용이 샤드마다 중복(+519s 전부, [BL-598]). ★샤드 추정 **2.2배 오차** — `--durations` 는 「누가 먼저 돌았나」의 함수. ★★**§5 전제는 죽은 게 아니라 휴면**(3h22m 뒤 steps=0 재발). **public 전환** — dev-log
- **2026-08-06 night-watch** — ★**[ADR-025] Accepted**(12h 전향 예측 4/4 — phantom 0 · 발주 84 · 카운터 차분 +223) · **BL-594/596 Resolved · BL-591 P2 강등**. ★계획 재기동 1회로 B2 실증, 누적 12.75h 연속. ★★e2e red 는 flake 가 아니라 **소크 열린 포지션↔로케이터 결합**(BL-597) — dev-log
- **2026-08-05 conditional-stop-ownership** — ★**라이브 조건부 진입 체결 권한을 주문 원장으로** ([ADR-025], **BL-595 Resolved**). 사망 **5건 재현**(비트 일치) → 수리 전 5/5 발산, 후 5/5 일치. ★★**형 B 는 거짓 사망** — 엔진이 2봉 뒤졌을 뿐. ★★codex: **오래 산 세션에서 보호가 먼저 꺼진다**(78h) — dev-log
- **2026-08-05 live-replay-visibility** — 판별식 = **직접 회복 검사**(원장 안 봄) · **FAIL 유지 · 실격 9→10**. ★★★**전제 반증** — `run_live` 는 이미 **89테스트가 ~90회** 호출. 변이 **12/12 KILLED ⇒ 신규 0**. ★[BL-595] 형 A 를 **Trust Layer 골든이 잡았다**. ★★codex: **진부분집합은 관측이다** → **래칫** — dev-log
- **2026-08-05 divergence-rejudgement** — ★★★**「두 현상」이 반증됐다** — 사망 4건 부검: 엔진이 앞선 3건 · **거래소가 앞선 1건**. 뿌리는 방향이 아니라 **엔진과 거래소가 서로 다른 stop 주문**을 든다는 것(신규 [BL-595]). ★판별식 교체(19건 전량 표: phantom **11→7**, 사망상관 4/4 보존, **FAIL 유지**). ★사전등록 미충족이라 **src 0줄** — dev-log
- **2026-08-05 soak-clock-restoration** — 소크를 **커밋에 고정**해 편집과 분리(음성 대조: 배너 1→2 vs 1→1) + 「1주 안정」을 기계 판정으로([ADR-024]). ★★★**게이트가 첫 5시간에 phantom 7건·사망 2건을 냈다** — BL-003 의 차단자는 달력 시간이 아니라 `phantom` 이다. ★★codex 가 **거짓 PASS 5경로** 적발 — dev-log
- **2026-08-04 handler-visibility-nightly-broker** — ★최대 `try` 본문 **845→8줄**, 새 `.py` 0개. ★★★**codex 가 「행위 변경 0」 반증** — lazy import 이동으로 **실패가 커밋 뒤로**(다중집합은 문장 순서를 못 본다). ★내 도구 42주입 중 **16 거짓 음성**. ★nightly 는 **10/10 alembic 사망**(이슈 89건 무효) — dev-log
- **2026-08-04 direction-channel-decomposition** — ★★★**`direction` 은 두 현상** — 무해 `replay_lag` **7** : 치명 `phantom` **4**(경과 24.7초 vs 909초, 겹침 0, 사망 2/2). ★소크 중단·발산 축 **동결** → [BL-580] 12곳(census **96→84**). ★★「전부 같은 형태」를 **기존 테스트가 반증** — dev-log
- **2026-08-04 engine-state-ssot** — 설계 회차(코드 0줄 · 소크 무중단). ★★★**기각 3건이 순환**이었다 — 「엔진에 쓸 자리가 없다」는 경계가 아니라 **고칠 결함**이다. ④=0 에 이어 **veto 절반까지** 꺼짐(사망 2건 모두 **이미 판정불가 뒤** 죽었다). ★**Trust Layer 23테스트가 `run_live` 0회 호출** ⇒ 갈라져도 CI green. **ADR-023 Proposed** — dev-log
## 전체 이력

- **2026-08-04 engine-position-ssot** — 슬라이스 1(계측) PR #539 OPEN, **슬라이스 2 미착수 확정**. ④ = 0(사망 2건 상류에 `exchange_only` 0건, 최악 ≤1/21). ★★★**net 은 맞고 legs 는 틀리다** — 외부 오라클 11건 오답 **0** 인데 적중 4 중 **3건이 `legs=2`**(거래소는 단일). 판정은 net, 주입은 legs. ⑤ 판정불가 **27.6%** — dev-log
- **2026-08-03 breach-rejection-recovery** — 소크를 105분에 끊은 거절. ★가드는 **발주 시각에 옳았다** — 거래소가 2.1초 뒤 자기 시각으로 `110093` 거절, 그 뒤 **복구가 없어** 엔진 시뮬만 전진했다. 거절을 「돌파 확정 증거」로 읽고 시장가 전환 집행. ★거울 코드 `110092` 포함. 변이 **8/8** · 유도로 프로덕션 발화 확인. **BL-590 Resolved** — dev-log
- **2026-08-03 soak-divergence-root** — 소크를 65분에 끊은 발산. ★엔진은 취소를 못 본 게 아니라 **주문을 아예 모른다**(포지션 = `run_live` 시뮬). 뿌리는 계획기가 「대기 주문이 있다」만으로 시장가 전환을 껐다는 것 — 그 주문은 **발화 불가**였다. ★★한 번에 둘을 고치면 서로의 증거를 가린다. **BL-589/587/585/588 Resolved · 소크 재가동** — dev-log
- **2026-08-03 backtest-metric-oracle** — 회귀망이 위험조정지표에 **감지력 0** 이었다(5벌 전부 sharpe=0·sortino/calmar=null). 컨벤션 대조 + 비축퇴 2벌로 채널 신설. **BL-461 Resolved** — 하루치 1h 봉이 **Sharpe 16.56** 을 보고했다. ★표적 2건 빗나감. ★★**소크가 65분에 죽었다 → BL-589(P1)** — dev-log
- **2026-08-03 metric-guard-residual-sweep** — 발주 outbox 12곳 수리 8·보류 4, 신규 H8 — dev-log
- **2026-08-03 metric-guard-residual-close** — BL-580 잔여 **25곳** 주입 판정 ⇒ **수리함 23 · 판정 보류 2**(census 129→104). ★산문 2줄이 25곳을 잘못 뺐다(「blast radius 0」은 10/10 이 OSError 탈출). ★**내 하네스가 계약을 깨 도달 불가 분기를 「유해」로 만들 뻔했다**(codex G6) — dev-log
- **2026-08-03 gate-trustworthiness** — 「전부 통과」가 증거가 되게 만든다. ★**순서는 랜덤이 아니었다**(`pytest-randomly` 미설치 ⇒ `-p no:randomly` no-op) — **수집 집합** 운이었다. 뿌리 = 정의 모듈 패치 창의 첫 적재가 가짜를 **모듈 전역으로 영구 복사**. 오염원 4곳·전역 8개, 상시 가드 신설. **BL-583 Resolved** PR #528 — dev-log
- **2026-08-03 metric-guard-residual** — 「감쌀 필요 없다」의 근거를 고장 주입으로 재판정. 명시 4곳 **전건 반증** ⇒ 12곳 수리(census 141→129). **BL-582 「7종 도달 불가」→5종**(엔진 구동이 2종 반증). ★부수: **스위트가 실행 순서로 red/green 이 갈린다**(기존 테스트로 재현) ⇒ BL-583 PR #528 — dev-log
- **2026-08-02 metric-guard-parity** — 계측 실패가 성공한 발주를 실패로 기록하고 **주문을 하나 더 냈다**(`assert 2 == 1`). 머니-패스 가드 **18곳**, census 159→141. ★백로그가 지목한 두 파일에 최강 P1 이 **없었다**. **BL-579 Resolved**, 신규 BL-580~582 — dev-log
- **2026-08-02 context-budget-repair** — 문서를 읽는 비용. `INDEX.md` **−92.3%**(151,256→11,610 tok) · 자동 로드 고정비 **−42.2%** · 줄길이 상한 게이트 신설. ★**착수 전제 3건 반증** — `CONTEXT.md`·`.ai/rules` 는 자동 로드가 **아니다** dev-log
- **2026-08-02 canonical-measurement-surface** — 손 SQL 을 쓸 이유를 없앤 정본 술어 측정 표면 3종. **BL-576 프로덕션 발화 검증 통과**, **BL-577 전제 반증**(가드는 실재했다 — 내용 grep 은 파일명에만 있는 문자열을 못 잡는다), 신규 BL-579. PR #520 — dev-log
- **2026-08-02 divergence-label-split** — 로그 이벤트 하나가 덮던 발화 8곳을 사건별 6 이름으로 갈라 **BL-576 Resolved**. 판정식 정본을 §G1.1 로 이관 — 살아남은 유일한 완전 판정 표가 OR 버전이었다(삭제에 의한 역선택). PR #519 — dev-log
- **2026-08-01 entry-completeness-rejudgement** — **4개 채널 중 3개가 유실 채널이 아니었다** ⇒ 「축소」. 층위1 확정 거절률 16.67% → 2.44%. **BL-536 Resolved · BL-522 P1→P2**, 신규 BL-578. PR #518 — dev-log
- **2026-08-01 silent-surface-honesty** — 조용히 실패하는 표면 4건(BL-570/542/571/572). 뿌리는 **RHF 가 defaultValue 를 그대로 setValueAs 에 넘겨 `Number(null) === 0`** — 이 전략은 설정을 저장할 방법이 없었다. 신규 BL-577. PR #517 — dev-log

> 요약 문장을 두지 않는다 — 상세는 링크 대상에 있다. 자기 dev-log 가 없는 회차는 원문 아카이브로 보낸다.

- 2026-08-01 · conditional-fill-visibility — dev-log
- 2026-07-31 · reversal-ledger-sync — dev-log
- 2026-07-30 · close-mismatch-soak — dev-log
- **2026-07-30 close-mismatch-visibility** — **재던 곳에 없었다** — C2 는 유실 채널이 아니라 청산 tick 수. `110017` 두 갈래(same side 9 / position is zero 30)가 한 라벨에 묻혀 화면이 9건 전부를 초록으로 냈다. soak 미실시. PR #511 — dev-log
- 2026-07-30 · live-entry-completeness — dev-log
- 2026-07-30 · conditional-entry-alignment — dev-log
- **2026-07-30 engine-exchange-alignment** — **BL-543**(position epoch) 착지 + BL-535 부분. **실주행 soak 이 단위테스트를 반증** — 재생 아티팩트는 사라졌으나 공백 뒤 세션이 정반대 방향으로 사망 ⇒ **BL-544** 신설. PR #503 — dev-log
- 2026-07-29 · live-orphan-close — dev-log
- 2026-08-01 · entry-completeness-rejudgement 사전등록 감사 — log
- 2026-07-28 · live-close-completeness — log
- 2026-07-28 · live-outcome-parity — log
- 2026-07-28 · live-entry-parity — log
- 2026-07-28 · live-ops-hygiene — log
- 2026-07-28 · live-observability — archive · 판정표
- 2026-07-27 · live-conditional-hardening — log
- 2026-07-27 · live-conditional-entry — log
- 2026-07-26 · live-engine-parity — log
- 2026-07-26 · live-entry-wiring — log
- 2026-07-26 · BL-474 webhook ingress 패리티 — log
- 2026-07-26 · dogfood-restore — log
- 2026-07-26 · money-path-finish — log
- 2026-07-26 · backtest-trust — log
- 2026-07-25 · exit-money-path — archive
- 2026-07-25 · exit-attribution — archive
- 2026-07-25 · money-path-accuracy — archive
- 2026-07-25 · close-completeness — archive
- 2026-07-24 · trading-surface-pack — archive
- 2026-07-24 · position-cockpit — archive
- 2026-07-24 · perf-surface — archive
- 2026-07-24 · opspack-ws2 — archive
- 2026-07-24 · tier-c — archive
- 2026-07-23 · functional-parity — archive
- 2026-06-30 · stress_test 1차 deepen — log
- 2026-06-30 · backtest 1차 deepen (ADR-021) — log
- 2026-06-26 · trading 2차 deepen — log
- 2026-06-26 · 트레일링 라이브 등재 — log
- 2026-05-16 · Sprint 60 plan — log
- 2026-05-15 · CLAUDE.md align audit — log
- 2026-05-15 · Track B trading deepen (audit-only) — log
- 2026-05-14 · Sprint 60 close-out — log
- 2026-05-13 · Sprint 59 close-out — log
- 2026-05-12 · Sprint 54 회고 — log
- 2026-05-12 · Sprint 54 Bayesian/Genetic 문법 ADR — log
- 2026-05-12 · Sprint 58 post — alertcondition() 신호 탐지 — archive
- 2026-05-12 · Sprint 58 post — Pine 호환성 실험 — archive
- 2026-05-11 · Sprint 58 close-out — log
- 2026-05-11 · Sprint 57 close-out — log
- 2026-05-11 · Sprint 56 close-out — log
- 2026-05-11 · Sprint 56 chore prereq CI/CD — log
- 2026-05-11 · Sprint 55 close-out — log
- 2026-05-11 · Sprint 55 master — log
- 2026-05-11 · Sprint 53 회고 — log
- 2026-05-11 · Sprint 52 회고 — log
- 2026-05-11 · Sprint 51 회고 — log
- 2026-05-10 · Sprint 50 회고 — log
- 2026-05-10 · Sprint 49 회고 — log
- 2026-05-09 · Sprint 48 close-out — log
- 2026-05-09 · Sprint 48 BL-201 audit — log
- 2026-05-09 · Sprint 47 close-out — log
- 2026-05-09 · Sprint 46 close-out — log
- 2026-05-09 · Sprint 45 회고 — log
- 2026-05-09 · deepen pilot — pine_v2 — log
- 2026-05-09 · deepen pilot — trading — log
- 2026-05-09 · deepen pilot — frontend — log
- 2026-05-08 · Sprint 44 close-out — log
- 2026-05-08 · Sprint 42 master — log
- 2026-05-08 · Sprint 42 Day 7 midcheck — log
- 2026-05-07 · Sprint 41 회고 — log
- 2026-05-07 · Sprint 39 회고 — log
- 2026-05-07 · Sprint 38 회고 — log
- 2026-05-06 · Sprint 37 회고 — log
- 2026-05-06 · dogfood Day 7 (Sprint 36) — log
- 2026-05-05 · Sprint 35 회고 — log
- 2026-05-05 · office-hours Sprint 35 분기 결정 — log
- 2026-05-05 · Sprint 34 회고 — log
- 2026-05-05 · dogfood Day 6.5 — log
- 2026-05-05 · dogfood Day 6 — log
- 2026-05-05 · BL-178 root cause spike — log
- 2026-05-05 · Sprint 33 회고 — log
- 2026-05-05 · Sprint 32 회고 — log
- 2026-05-05 · Sprint 31 Day 4 dogfood handoff — log
- 2026-05-05 · Sprint 31 Pine v6 호환 ADR — log
- 2026-05-05 · Sprint 30 회고 — log
- 2026-05-05 · ADR-019 Surface Trust Pillar — log
- 2026-05-05 · Sprint 30 chart lib 결정 ADR — log
- 2026-05-04 · Sprint 29 회고 — log
- 2026-05-04 · Sprint 29 baseline snapshot — log
- 2026-05-04 · Sprint 29 v1→v2 pivot — log
- 2026-05-04 · Sprint 28 회고 — log
- 2026-05-04 · Sprint 28 kickoff plan — log
- 2026-05-04 · Sprint 27 Beta prereq hotfix — log
- 2026-05-04 · Sprint 26 Pine Signal Auto-Trading — log
- 2026-05-04 · dogfood Day 1 — Sprint 27 launch — log
- 2026-05-03 · Sprint 25 Hybrid — log
- 2026-05-03 · Sprint 24b Backend E2E 자동 dogfood — log
- 2026-05-03 · Sprint 24a WebSocket 안정화 — log
- 2026-05-03 · Sprint 23 C-3 묶음 — log
- 2026-05-03 · Sprint 22 BL-091 architectural — log
- 2026-05-03 · Sprint 21 dogfood Day 1 — log
- 2026-05-02 · Sprint 21 BL-096 coverage expansion — log
- 2026-05-02 · Sprint 20 dogfood Day 0 준비 — log
- 2026-05-02 · Sprint 19 technical debt — log
- 2026-05-02 · Sprint 18 BL-080 architectural — log
- 2026-05-02 · Sprint 17 prefork fix — log
- 2026-05-01 · Sprint 16 live 검증 + backfill — log
- 2026-05-01 · Sprint 15 stuck order watchdog — log
- 2026-04-27 · dogfood Day 3 (Sprint 14) — log
- 2026-04-26 · dogfood Day 2 (Sprint 13) — log
- 2026-04-25 · dogfood Day 1 (Sprint 12) — log
- 2026-04-24~ · dogfood Week 1 — Path β — log
- ~2026-04-23 · Sprint 1-14 회고 위치 매트릭스 — archive

---

## ADR + 사후 회고 (번호순, 신뢰도 높은 결정 기록)

- 021 — backtest 제출 멱등성 Redis + PG advisory dual-lock 유지 (단일 unit 통합 거부, 2026-06-30 backtest-deepen C3 KILL) — [`021-backtest-idempotency-dual-lock.md`](../decisions/021-backtest-idempotency-dual-lock.md)
- 020 — Trust Layer CI — 3-Layer Parity (P-1/2/3) 설계 (구 ADR-013, 2026-05-29 renumber — Optimizer ADR-013 과 ID 충돌 해소) — [`020-trust-layer-ci-design.md`](../decisions/020-trust-layer-ci-design.md)
- 018 — Sprint 12 WebSocket Supervisor + Sprint 15-A/B Architecture Cleanup — [`018-sprint12-ws-supervisor-and-exchange-stub-removal.md`](../decisions/018-sprint12-ws-supervisor-and-exchange-stub-removal.md)
- 017 — FE Polish Bundle 1/2 묶음 회고 (FE-01~04 + FE-A~F) — [`017-fe-polish-bundle-1-2-retro.md`](../decisions/017-fe-polish-bundle-1-2-retro.md)
- 016 — Sprint Y1 Pre-flight Pine Coverage Analyzer (Trust Layer 사용자 축) — [`016-sprint-y1-coverage-analyzer.md`](../decisions/016-sprint-y1-coverage-analyzer.md)
- 015 — Sprint 7d 회고 (OKX Adapter + Trading Sessions + Passphrase 암호화) — [`015-sprint-7d-okx-sessions.md`](../decisions/015-sprint-7d-okx-sessions.md)
- 014 — Sprint 8b + 8c 합본 회고 (pine_v2 Tier-1 래퍼 + 3-Track Dispatcher) — [`014-sprint-8b-8c-pine-v2-expansion.md`](../decisions/014-sprint-8b-8c-pine-v2-expansion.md)
- ~~013~~ — Trust Layer CI → **ADR-020 으로 renumber** (2026-05-29, Optimizer ADR-013 과 충돌 해소). 위 020 항목 참조
- 012 — Sprint 8a Tier-0 Final Report (Week 1-3 완주, v3.0) — [`012-sprint-8a-tier0-final-report.md`](../decisions/012-sprint-8a-tier0-final-report.md)
- 011 — Pine Script 실행 전략 v4 (Alert Hook Parser + 3-Track Architecture) — [`011-pine-execution-strategy-v4.md`](../decisions/011-pine-execution-strategy-v4.md)
- 010b — Product Roadmap 프레임 & 입력 결정 (재작성본, canonical) — [`010b-product-roadmap.md`](../decisions/010b-product-roadmap.md)
- 010a — Dev CPU Budget Policy + Next.js Anti-Pattern 15건 — [`010a-dev-cpu-budget.md`](../decisions/010a-dev-cpu-budget.md)
- ~~010~~ — Product Roadmap 1차 초안 (DEPRECATED, 2026-05-15 cleanup git rm — git history 보존, 010b 가 canonical)
- 009 — shadcn/ui v4 Nova Preset 규칙 예외 (form.tsx radix-ui + ui/ 직접 수정) — [`009-shadcn-v4-form-radix-exception.md`](../decisions/009-shadcn-v4-form-radix-exception.md)
- 008 — Sprint 7c FE 따라잡기 — 스코프 결정 기록 — [`008-sprint7c-scope-decision.md`](../decisions/008-sprint7c-scope-decision.md)
- 007 — Sprint 7a Bybit Futures + Cross Margin — 사전 결정 기록 — [`007-sprint7a-futures-decisions.md`](../decisions/007-sprint7a-futures-decisions.md)
- 006 — Sprint 6 Trading 데모 설계 리뷰 결과 + 3 핵심 의사결정 — [`006-sprint6-design-review-summary.md`](../decisions/006-sprint6-design-review-summary.md)
- 005 — DateTime tz-aware + AwareDateTime TypeDecorator 도입 — [`005-datetime-tz-aware.md`](../decisions/005-datetime-tz-aware.md)
- 004 — Pine 파서 접근법 선택 근거 — [`004-pine-parser-approach-selection.md`](../decisions/004-pine-parser-approach-selection.md)
- 003 — Pine 런타임 안전성 + 파서 범위 결정 — [`003-pine-runtime-safety-and-parser-scope.md`](../decisions/003-pine-runtime-safety-and-parser-scope.md)
- 002 — 병렬 스캐폴딩 전략 — [`002-parallel-scaffold-strategy.md`](../decisions/002-parallel-scaffold-strategy.md)
- 001 — 기술 스택 결정 — [`001-tech-stack.md`](../decisions/001-tech-stack.md)

---

## 운영 규칙

- 신규 dev-log 작성 시 본 INDEX 에도 한 줄 추가 (시간 역순 또는 번호순 위치 유지)
- ★**요약 줄 상한 300자.** 초과하면 `scripts/docs-audit.sh` 가 exit 1 로 막는다 — grep 한 줄이 곧 대량 읽기다
- ★**요약은 「최근 12회차」에만 둔다.** 13번째가 생기면 가장 오래된 항목을 「전체 이력」(날짜·이름·링크만)으로 내린다
- AGENTS.md 의 "현재 작업" 섹션은 **활성 sprint 1개 + 직전 완료 sprint 1개 + 다음 분기** 만 inline. 그 외 모든 회고는 본 INDEX 에서 발견
- BL ID 가 부여된 follow-up 은 [`docs/backlog.md`](../backlog.md) 에서 추적
- Sprint 1-14 의 별도 dev-log 가 없는 항목은 원문 아카이브의 "Sprint 1-14 매트릭스" 에서 ADR/spec/plan/dogfood 위치 cross-link

---

★압축 전 요약 원문 = `index-full-2026-08-02.md`
