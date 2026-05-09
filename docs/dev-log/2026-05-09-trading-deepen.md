# /deepen-modules audit 2/3 — backend Trading 도메인 — 2026-05-09

> **Outcome:** Trading 도메인 (CCXT 어댑터 + KillSwitch + OrderService + Webhook) 1회 audit 완료. BL-202~205 4건 신규 등재. Sprint 47 = pine_v2 BL-200/201 + trading BL-202~205 = 6 BL 묶음 deepening sprint 로 확장 권고. **§7.5 검증 누적 1/3 → 2/3**.

## Context

Sprint 46 같은 세션 안 두 번째 audit. 첫 audit (pine_v2 SSOT) 는 사전 Explore 데이터로 Phase 3-4 만 수행했으나 스킬을 실제 invoke 한 게 아니었음. 본 trading audit 는 `/deepen-modules` Skill 도구로 실제 호출 → Phase 1 부터 자동 진행 검증 + 2/3 검증 누적.

**Beta 직전 도메인 audit 가치:** BL-003 (Bybit mainnet runbook) + BL-005 (1-2주 dogfood) 진입 전 trading 도메인 architectural debt 사전 차단. dogfood 중 발견 시 hot-fix 압박이 커지므로 사전 정리가 ROI 높음.

## Phase 1 결과 — Module Inventory & Depth Mapping

**Scope:** `backend/src/trading/**` (19 files / 5142 LOC, sweet spot 범위 내)

| 모듈                                  | LOC | Public Surface                                         | 분류                  | 비고                                                   |
| ------------------------------------- | --- | ------------------------------------------------------ | --------------------- | ------------------------------------------------------ |
| **providers.py**                      | 772 | `ExchangeProvider` Protocol + 5 concrete + 4 dataclass | 🟡 Mixed              | 5 provider class 한 파일, Protocol 정합                |
| **repository.py**                     | 714 | 3 Repository class                                     | 🔴 **God file**       | OrderRepository 단독은 deep, 3 repo 한 파일 = SRP 위반 |
| **service.py**                        | 562 | 5 Service + 2 Protocol                                 | 🔴 **God file**       | 5 서로 다른 책임 service 한 파일                       |
| **models.py**                         | 528 | SQLModel ORM 합본                                      | 🟡 (관행)             | ORM 한 파일 합본은 보편적                              |
| **router.py**                         | 405 | FastAPI router                                         | 🟢 Deep               | endpoint thin layer                                    |
| **websocket/bybit_private_stream.py** | 319 | WS connection + reconnect                              | 🟢 Deep               | 단일 책임                                              |
| **kill_switch.py**                    | 262 | `KillSwitchEvaluator` Protocol + 2 evaluator + Service | ✅ **Reference Deep** | Strategy pattern 정합 — pine_v2 Track 분기 정반대      |
| **websocket/reconciliation.py**       | 225 | reconcile loop                                         | 🟢 Deep               |                                                        |
| **exceptions.py**                     | 224 | 다수 Exception 클래스                                  | 🟡 (관행)             | exception 모음                                         |
| **websocket/state_handler.py**        | 221 | WS state transition                                    | 🟢 Deep               |                                                        |
| **schemas.py**                        | 200 | Pydantic 요청/응답 다수                                | 🟡 (관행)             | API 스키마 모음                                        |
| **dependencies.py**                   | 181 | FastAPI Depends factory                                | 🟡                    | DI factory 다수                                        |
| **funding.py**                        | 127 | funding rate 계산                                      | 🟢 Deep               |                                                        |
| **websocket/reconcile_fetcher.py**    | 116 | exchange order fetcher                                 | 🟢 Deep               |                                                        |
| **webhook.py**                        | 81  | `WebhookService` + parse function                      | 🟡 Shallow 의심       | 작아서 별 문제 X                                       |
| **equity_calculator.py**              | 80  | equity 계산                                            | 🟢 Deep               |                                                        |
| **fees.py**                           | 55  | fee 계산                                               | 🟢 Deep               |                                                        |
| **encryption.py**                     | 46  | AES-256 encrypt/decrypt                                | 🟢 Deep               |                                                        |

**Deep:Shallow 비율 = ~13:2 (양호).** 단 shallow 후보가 핵심 책임 (service / repository) 에 집중. Reference Deep = `kill_switch.py` (영상 칭찬할 패턴).

## Phase 2 결과 — Locality & Coupling Analysis

| 패턴                                  | 심각도 | Touch 파일                                          | Risk                                                             |
| ------------------------------------- | ------ | --------------------------------------------------- | ---------------------------------------------------------------- |
| **A. Provider Registry/Factory 부재** | 🔴 높  | providers.py + dependencies.py + service.py:146/515 | (exchange, mode) tuple 분기가 service 안 흩어짐 + silent failure |
| **B. service.py God File**            | 🟡 중  | service.py 1 파일 / 5 class                         | co-change 13회/3개월 = 1위. SRP 위반                             |
| **C. repository.py God File**         | 🟡 중  | repository.py 1 파일 / 3 class                      | co-change 9회. OrderRepository 단독 14+ method                   |
| **D. OrderStatus Literal triple**     | 🟡 중  | providers.py 3곳 + models.py                        | providers.py:73 cancelled 누락 confirmed = silent failure 1건    |

**Co-change top 5 (3개월):** service(13) / providers(11) / repository(9) / models(9) / kill_switch(7) / exceptions(7).

**Test coverage = 매우 강함** (48 test files / 19 source files = 2.5x).

- providers: 5 test 파일 (각 provider 별 분리 ✅)
- service: 10 test 파일 (이미 책임별 분리 — source 만 god file, **test 가 좋은 design 제시**)
- repository: 4 test 파일 (각 repo 별 분리 ✅)

→ STOP condition (coverage <70%) 안 트리거.

## Phase 3 결정 로그 — Grilling Session

| 후보                              | 별점  | ROI                  | 결정    | 사유                                         |
| --------------------------------- | ----- | -------------------- | ------- | -------------------------------------------- |
| **A. Provider Registry/Factory**  | ★★★★★ | 3.26 (절대 가치 1위) | ✅ 승인 | silent failure + BL-003 mainnet 진입 전 권장 |
| **B. service.py 분할**            | ★★★★☆ | 5.7                  | ✅ 승인 | co-change 13회 + test 가 design 제시         |
| **C. repository.py 분할**         | ★★★☆☆ | 6.75                 | ✅ 승인 | 가장 단순, B 와 묶기 자연스러움              |
| **D. OrderStatus Literal triple** | ★★★☆☆ | 6.75                 | ✅ 승인 | cancelled 누락 1건 confirmed                 |

**Sprint 권고:** Sprint 47 = pine_v2 BL-200/201 + trading BL-202/203/204/205 = **6 BL 묶음 deepening sprint** (~30-40h). 큰 편이지만 mainnet 진입 직전 architectural foundation 통합 정리.

## Phase 4 등재

### `docs/REFACTORING-BACKLOG.md` 신규 BL 4건 (P2 섹션)

- **BL-202** trading Provider Registry/Factory (★★★★★, M 6-9h)
  - **현 상태:** providers.py 5 class + dependencies.py:51 singleton 1개 + service.py:146/515 ad-hoc 분기
  - **목표:**

    ```python
    # backend/src/trading/providers/registry.py
    PROVIDER_REGISTRY: dict[tuple[ExchangeName, ExchangeMode], ExchangeProvider] = {
        (ExchangeName.bybit, ExchangeMode.demo): BybitDemoProvider(),
        (ExchangeName.bybit, ExchangeMode.live): BybitLiveProvider(),
        (ExchangeName.okx, ExchangeMode.demo): OkxDemoProvider(),
        # ...
    }

    def get_provider(account: ExchangeAccount) -> ExchangeProvider:
        key = (account.exchange, account.mode)
        provider = PROVIDER_REGISTRY.get(key)
        if not provider:
            raise UnsupportedExchangeMode(key)
        return provider
    ```

  - **영향 파일:** providers.py / dependencies.py / service.py 3 재배치 + tests 일부 update
  - **Risk:** 🔴 높 (CCXT 호출 전수 검증)

- **BL-203** trading service.py 분할 (★★★★☆, S-M 4-5h)
  - **목표 파일 구조:**
    ```
    backend/src/trading/service/
      ├── __init__.py        # public re-export
      ├── orders.py          # OrderService (236 LOC)
      ├── accounts.py        # ExchangeAccountService (~90 LOC)
      ├── webhook_secrets.py # WebhookSecretService (~50 LOC)
      ├── live_sessions.py   # LiveSignalSessionService (~100 LOC)
      └── protocols.py       # OrderDispatcher + StrategySessionsPort
    ```
  - **Risk:** 🟡 중 (단순 분할 + import mass migration)

- **BL-204** trading repository.py 분할 (★★★☆☆, S 2-3h)
  - **목표:** `repository/orders.py` / `repository/exchange_accounts.py` / `repository/kill_switch_events.py` / `repository/webhook_secrets.py`
  - **Risk:** 🟢 낮 (가장 단순, import 만 변경)

- **BL-205** OrderStatus Literal triple SSOT (★★★☆☆, XS-S 1-2h)
  - **현 silent failure:** providers.py:73 = `Literal["filled", "submitted", "rejected"]` (cancelled 누락)
  - **목표:** `models.OrderStatus` enum 만 사용, Literal hardcode 전수 제거
  - **Risk:** 🟢 낮

### LESSON 후보 2건 (lessons.md, 미작성 — Sprint 47 close-out 시 평가)

```
LESSON-063 후보 (deepen-modules trading audit, 2026-05-09): Trading 도메인 에서
"5 provider class + ad-hoc service if-branch dispatch" 패턴 = silent failure source.
새 exchange/mode 추가 시 service.py 분기 add 의무 → Registry/Factory 패턴이 디폴트
의무.

LESSON-064 후보 (deepen-modules trading audit, 2026-05-09): "test 가 이미
책임별 분리됐는데 source 만 god file" = test 가 좋은 design 을 보여주는 강력
신호. 분할 ROI 높음. 신규 도메인 작성 시 test 분리 패턴 = source 분리 패턴
mirror 의무.
```

## Sprint 47 권고 갱신

**Sprint 46 stage→main 사용자 머지 후, Sprint 47 = Architectural Deepening (확장):**

- Slice 1: BL-200 STDLIB triple SSOT (4-6h)
- Slice 2: BL-205 OrderStatus Literal triple (1-2h, BL-200 패턴 직접 응용)
- Slice 3: BL-204 repository.py 분할 (2-3h, 가장 단순)
- Slice 4: BL-203 service.py 분할 (4-5h, repository 분할 후 자연스러움)
- Slice 5: BL-202 Provider Registry/Factory (6-9h, 가장 큰 architectural)
- Slice 6: BL-201 Track S/A/M Strategy pattern (9-12h, SSOT 핵심)
- **Total: 26-37h** (4-6 worker 자율 병렬 시 wall-clock 8-12h 추정)

**Sprint kickoff §7.1 baseline preflight:**

- 252+ pine_v2 test + 48 trading test baseline 재측정
- co-change cluster 확인 (3개월 데이터 drift 없는지)
- §7.4 codex G.0 master plan validation + rapid prereq spike

## §7.5 검증 누적 갱신

> Sprint 46 검증 누적: pine_v2 SSOT pilot (1/3) → **+ trading audit (2/3)**

3/3 = 다음 도메인 (frontend dashboard-shell 또는 backtest+optimizer) audit 후 LESSON-XXX 정식 승격.

## 다음 audit 권고

| 후보 도메인                                                | scope    | 예상 발견                                  | 권고 timing           |
| ---------------------------------------------------------- | -------- | ------------------------------------------ | --------------------- |
| **frontend dashboard-shell + 16 페이지**                   | ~80 file | cross-page component 분리 후 locality 검증 | Sprint 48+ (3/3 검증) |
| **backend Backtest + Optimizer + StressTest**              | ~40 file | Celery task + vectorbt 강등 후 정합성      | Sprint 49+            |
| **backend Strategy + Webhook + Pine SSOT 외부 인터페이스** | ~30 file | trust layer 정합                           | dogfood Phase 2 후    |

## Verification (스킬 작동 검증)

✅ **`/deepen-modules` Skill 도구 invoke 성공** — frontmatter trigger 매칭 + Iron Law / 4-Phase / STOP conditions 모두 로드 + Phase 1 자동 진행
✅ Phase 1.1 Scope Lock = 사용자 명시했으므로 skip (스킬 instruction 정합)
✅ Phase 1.2 Bash + find/wc 으로 module tree 자동 생성
✅ Phase 1.3 Deep/Shallow 분류 표 18 모듈 작성
✅ Phase 2.1-2.3 git log co-change + grep dispatcher + grep triple SSOT 자동 진행
✅ Phase 3 ROI 계산 + AskUserQuestion 으로 사용자 결정 받음 (CLAUDE.md 별점 추천도 의무 준수)
✅ Phase 4 BL 등재 4건 + 본 dev-log 작성

**스킬 자체 보증:** 다음 도메인 audit 시 same flow 재현 가능.

## End-to-End 검증 (Sprint 47+ 시점)

- [ ] Sprint 47 kickoff 시 §7.1 baseline preflight 통과
- [ ] BL-200~205 6 BL 묶음 stage 머지 후 252+ pine_v2 + 48 trading test 회귀 0 보증
- [ ] Sprint 48+ 에서 다른 도메인 (frontend 또는 backtest) audit → 3/3 검증 누적
