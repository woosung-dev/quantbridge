# QuantBridge — PRD (제품 정의 · 범위 · 현재 위치)

> **이 문서가 답하는 것** — 무엇을 만드나 / 누구를 위해 / 무엇을 **안** 하나 / 지금 어디까지 왔나 / 다음은 뭔가.
> 「왜 그렇게 정했나」는 [`adr/`](./adr/), 「지금 실행할 일」은 [`status.md`](./status.md),
> 「열린 결함」은 [`backlog.md`](./backlog.md), 「무엇이 반증됐나」는 [`lessons.md`](./lessons.md) 다.
>
> ★**2026-08-23 통합.** `domain/vision.md`(144줄) · `roadmap.md`(550줄) · `domain/requirements-overview.md`(46줄)
> 셋이 같은 질문(「제품이 뭔가」)을 나눠 답하고 있어 **이 한 파일로 합쳤다.** 원문 = `git show 4c65bc0e:docs/`.
> 합친 이유는 실측이다 — roadmap 의 미완 체크박스 **87개 중 79개가 원장에 없는 죽은 BL** 을 가리키고 있었고,
> 머리 20줄이 「그 앞:」 회차 이력이었다. living 체크리스트가 changelog 가 된 것이다.

---

## 0. 지금 유효한 제품 결정 (2026-08-23 사용자 결정)

이 셋이 아래 모든 범위 문장을 지배한다.

| # | 결정 | 따라 나오는 것 |
| --- | --- | --- |
| ⑴ | **실자금(mainnet) 안 간다** | 계정 모드는 **Bybit Demo 만**. money-path 「실자금 정밀도」 축은 닫혀 있다 |
| ⑵ | **Beta 외부 공개 당분간 안 연다** | **실사용자 0명**이 전제다. waitlist 파이프라인은 키만 넣으면 열리지만 열지 않는다 |
| ⑶ | **멀티 거래소 안 한다** | **Bybit 하나**. ★OKX 는 BE 에 어댑터가 **남아 있다**(`trading/providers.py:1878` `OkxDemoProvider` + `registry.py:41` 등록) — **더 안 키운다**. FE 는 이미 `schemas.ts:114` 에서 `z.enum(["bybit"])` 로 하나만 받는다. **Binance 는 주석뿐이라 진짜 0건** |

★**하나가 뒤집히면 `git show 21e40d5c:docs/backlog.md` 에서 해당 축을 되살려라 — 다시 쓰지 마라**
(`backlog-deferred.md`·`backlog-resolved.md` 동일 SHA). ★**glob 을 쓰지 마라** — `git show <sha>:docs/backlog*.md` 는
확장이 안 돼 **rc=0 인데 0바이트**다(2026-08-23 실측). 이 레포가 반복해 밟은 「빈 입력이 초록으로」 패턴이다.

---

## 1. 제품

TradingView Pine Script 전략을 가져와 **같은 코드로** 백테스트 → 스트레스 테스트 → 데모 트레이딩까지 연결하는 웹 퀀트 플랫폼.

**메우는 단절 셋:**

1. **TV 백테스터의 한계** — 슬리피지·수수료·자본 제약 모델이 단순하고 Monte Carlo / Walk-Forward 가 없어 over-fit 판단이 어렵다.
2. **거래소 자동화 단절** — 자동 실행하려면 Pine 을 Python/JS 로 다시 쓰거나 3rd-party 봇에 종속된다.
3. **검증→실거래의 신뢰 공백** — 백테스트가 좋아도 실제 슬리피지를 확인할 단계가 없다.

**한 줄 포지셔닝:** TradingView UX × vectorbt 백테스트 정밀도 × 거래소 직결 = **"TradingView 의 Trust Layer"**.

**핵심은 기능 수가 아니라 결과와 가정이 얼마나 정직하게 보이는가다.**

## 2. 사용자 흐름

1. **Import** — Pine Script 등록. 지원 범위·degrade 여부를 **먼저** 확인한다.
2. **Verify** — `pine_v2` 인터프리터로 백테스트. 필요하면 스트레스 테스트·최적화.
3. **Operate** — 검증한 전략을 **Bybit Demo** 계정에서 자동 실행. 주문·포지션·Kill Switch 관찰.

## 3. 현재 범위 — 지금 약속하는 것

| 영역 | 계약 | 상세 정본 |
| --- | --- | --- |
| 전략 | Pine 등록·파싱·지원 범위 판정. **미지원 항목이 하나라도 있으면 부분 실행하지 않는다** | [`domain/domain-overview.md`](./domain/domain-overview.md) · [`domain/supported-indicators.md`](./domain/supported-indicators.md) |
| 전략 브리핑 | 백테스트 **제출 전에** 「이 전략이 무엇을 하는가」를 보여준다 — 판정어는 결정론 층(AST·coverage)이 내고 LLM 산문은 **판정하지 않는 보조 설명**이다. Python 은 **읽기 전용 뷰** | [`adr/040`](./adr/040-strategy-brief-outside-trust-layer.md) · [`adr/042`](./adr/042-pine-to-python-readonly-renderer.md) |
| 전략 생성 | 자연어 → LLM 이 Pine+Python 산출, **Pine 이 정본**. all-or-nothing 통과 실패 시 저장 거부 | [`adr/041`](./adr/041-ai-strategy-generation.md) |
| 백테스트 | `pine_v2` bar-by-bar 실행 결과와 리포트 | [`architecture/pine-execution-architecture.md`](./architecture/pine-execution-architecture.md) |
| 검증 확장 | Monte Carlo · Walk-Forward · 파라미터 안정성 · 최적화 — 같은 백테스트 계약 재사용 | [`architecture/system-architecture.md`](./architecture/system-architecture.md) |
| 시장 데이터 | OHLCV 수집 + TimescaleDB hypertable 보관 | [`architecture/data-flow.md`](./architecture/data-flow.md) |
| 트레이딩 | **Bybit Demo 만**. 주문 전 리스크 평가 + Kill Switch | [`domain/state-machines.md`](./domain/state-machines.md) · [`api/endpoints.md`](./api/endpoints.md) |
| 신뢰·안전 | 실행·지원 범위·비용·리스크를 숨기지 않는다. Pine 회귀는 Trust Layer CI 로 방어 | [`architecture/trust-layer-architecture.md`](./architecture/trust-layer-architecture.md) |

## 4. 비범위 — 의식적으로 안 하는 것

**결정 3건이 닫은 것** (§0): 실자금/mainnet · 외부 Beta 공개 · 멀티 거래소(OKX·Binance).

**설계 단계에서 제외한 것:**

- **Web3 / 온체인 자동매매** — 중앙화 거래소(Spot + Perpetual) 한정
- ~~**AI 전략 자동 생성** — Pine 은 사용자가 작성/임포트한다. LLM 이 전략을 만들어주지 않는다~~
  → ★**2026-08-27 [ADR-041] 로 범위 안으로 들어왔다.** 자연어로 전략을 생성한다 — LLM 이 Pine 과
  Python 을 둘 다 내고 **Pine 이 정본**이며, `analyze_coverage` all-or-nothing 이 저장 여부를 판정한다.
  ★**여전히 안 하는 것 둘** — ⑴ 기존 Pine 을 LLM 이 **Python 으로 번역**해 실행([ADR-011] §7, 실측
  「수렴도 0」) ⑵ 사용자·LLM 이 쓴 **Python 을 서버에서 실행**([ADR-004] 「영구 불채택」·[ADR-042] §실측).
- **사용자 Python 전략 실행** — Python 은 **읽기 전용 뷰**로만 존재한다([ADR-042]). 실행기는 만들지 않는다
- **모바일 네이티브 앱** — 반응형 웹만
- **멀티 사용자 협업** — 실시간 공동 편집 없음
- **옵션 등 파생상품** — Spot + Perpetual Futures 한정
- **알고리즘 마켓플레이스 · 회계/세무 리포트** — 외부 도구 연동 권장

변경은 **ADR 로 기록**한다. 산문으로 슬쩍 넓히지 마라.

## 5. 성공 지표

> ★★★**2026-08-30 사용자 결정 — 이 표를 닫았다.** 원문 = `git show ec26e28d:docs/PRD.md`.
> **근거는 원장 트리아주와 같다** — 2026-08-24 실측에서 **6줄 중 한 줄도 잰 적이 없었고**(`lessons.md` 대조 0건),
> 그중 둘은 **측정 자체가 불가능**했다(1Y 단일 목표는 정의 불성립 · vectorbt 대조군은 2026-08-06 에 의존성째 제거).
> 나머지 넷 중 셋(`임포트 → 첫 결과 < 5분` · `3클릭 이내` · `파싱 성공률 80%+`)은 **잴 대상이 없다** —
> 결정 ⑵ 로 외부 공개를 안 열어 실사용자가 0명이고, 「주요 패턴」의 모집단도 정의된 적이 없다.
> ⇒ **목표를 적어 두고 한 번도 재지 않으면 그 표는 제품 문서가 아니라 희망 목록이다.** 지웠다.

**살아 있는 수 하나 — 이것만 실측이다.**

| 지표 | 실측 |
| --- | --- |
| 백테스트 처리량 (6M/1H corpus, `run_backtest_v2`) | **277.18~3,689.36 bar/s** (`s2_utbot`~`s5_ema_trend`) · 측정 = `apps/api/tests/strategy/pine_v2/test_execution_speed.py` |

★**이 수를 그대로 1Y 로 환산하지 마라.** 분모 `run_backtest_v2` 가 **파스를 포함**하는데 파스는 bar 수와
무관한 고정비다(`s3_rsid` 21.752초 = parse 16.432 + execute 5.185 + 후처리 0.132). bar 를 2배로 늘리면
커지는 것은 execute 뿐이라 선형 환산 43.6초가 아니라 **약 27.1초**가 맞다 ⇒ **`bar/s` 는 데이터가
길수록 저절로 좋아지는 수다.** 고정비를 분모에서 빼거나 cold/warm 을 나눠 **두 수**로 내는 것이 남은 일이다
(측정 구조 자체의 결함은 [BL-830] 이 갖는다).

**지표를 다시 세울 때의 선행 조건** — 셋 다 지금은 성립하지 않는다:

1. **잴 대상이 있을 것** — UX 지표(첫 결과까지 시간 · 클릭 수)는 **사용자가 있어야** 잰다. 결정 ⑵ 가 열려야 한다.
2. **모집단이 정의돼 있을 것** — 「파싱 성공률」은 분모(어떤 Pine 코퍼스인가)를 먼저 고정해야 수가 된다.
3. **대조군이 있을 것** — 「정확도」는 무엇과 비교하는지가 지표의 절반이다. vectorbt 를 지운 뒤 그 자리가 비어 있다.

★**새 지표를 세우면 같은 회차에 한 번 재고 `lessons.md` 에 남겨라.** 그러지 않으면 이 표는 다시 희망 목록이 된다.

## 6. 지금 어디까지 왔나 (2026-08-23)

**작동하는 것** — Pine v2 AST 인터프리터 · 백테스트 · 스트레스 테스트 · 옵티마이저 · Bybit Demo 라이브 트레이딩(Auto-Loop 포함) · TimescaleDB 시장 데이터 · self-host Better Auth([ADR-034]) · 프로덕션 배포(`qb.woosung.dev` / `qb-api.woosung.dev`, Cloudflare Access 뒤).

**안 여는 것** — waitlist 초대 파이프라인은 **코드·테스트·화면 완비**이고 서버에 키 3종만 넣으면 열린다. 결정 ⑵ 로 **열지 않는다**. 절차 = [`operations/waitlist-activation.md`](./operations/waitlist-activation.md).

**열린 결함** — [`backlog.md`](./backlog.md) 의 **미완 10건**(2026-08-25 — n11 의 [BL-520] 종결로 12→11,
같은 날 [BL-650] 종결(캐시 자동 소각 정책, 사용자 결정)로 11→10).
**7건이 데모 라이브 축**이다(청산 원장 2배 적재 [BL-477]·[BL-529] · StrEnum 크래시 [BL-453] 등).
나머지 3건은 데모 라이브 밖이다 — 소크 C1 게이트 해석([BL-641]) ·
TradingView webhook 실측 미착수([BL-774]) · ws-stream 스트레스([BL-371]). 실자금 정밀도 항목은 결정 ⑴ 로 닫혔다.
★**착수 가능한 후보는 [`status.md`](./status.md) 의 ⓪ 표**(= ACTIVE ∪ (PARTIAL ∧ 트리거 도래))가 정한다 — 12 가 아니다.
★★**2026-08-24 n9 실측 — 남은 12건 중 「노력만으로 닫히는 것」은 절반뿐이다.** 4건은 **사용자 결정**이 막고
([BL-477]·[BL-529] 원장 행 정리 · [BL-650] 캐시 정책 · [BL-661] 거래소 쓰기), 1건은 **외부 접근**([BL-774]),
2건은 **유효한 처방이 없다**([BL-489] 2-pass 는 고정점에 도달하지 못해 반증됐다 · [BL-619] 뿌리 미상).
**시간을 더 써도 그 7건은 안 닫힌다** — 여는 열쇠는 결정이지 회차가 아니다.
★**2026-08-25 — 그 열쇠가 하나 돌았다.** [BL-650] 은 사용자 결정(기동 시 자동 소각)으로 닫혔다 —
사용자 결정 대기는 3건, 「결정·외부 접근·처방 부재로 안 닫히는 것」은 6건이 됐다.

**다음에 할 일** — [`status.md`](./status.md) 의 살아 있는 `다음 행동 =` **하나**가 유일한 진입점이다. 그 뒤 개발 항목은 ⓪ 표에서 고른다.

## 7. 핵심 비즈니스 규칙 (요약)

전문은 [`AGENTS.md`](../AGENTS.md) · [`apps/api/AGENTS.md`](../apps/api/AGENTS.md).

- 금융 숫자는 `Decimal` — `float` 금지
- Pine → 실행 시 `exec()`/`eval()` 절대 금지 ([ADR-003])
- Pine 미지원 함수 1개라도 포함 시 전체 "Unsupported" ([ADR-003])
- OHLCV 는 TimescaleDB hypertable
- 거래소 API Key 는 AES-256(Fernet) 암호화 저장 — 평문 컬럼 금지

## 8. 변경 규칙

제품 범위가 바뀌면 **이 문서를 짧게 고치고** 같은 세션에 다음 중 **정확히 한 곳**을 갱신한다.

| 무엇이 바뀌었나 | 어디 |
| --- | --- |
| 지금 실행할 일 | `status.md` |
| 열린 위험·결함 | `backlog.md` |
| 왜 그렇게 정했나 | `adr/` — **결정 / 이유 / 트레이드오프 3줄**. 회차 발견을 여기 쌓지 마라 |
| 무엇이 반증됐나 | `lessons.md` |
| 오래 유지할 구현 계약 | `architecture/`·`domain/`·`api/`·`development/`·`operations/` |

★**끝난 회차 기록은 어느 문서에도 쌓지 않는다** — 커밋 메시지와 git log 가 정본이다.
이 규칙이 없어서 `roadmap.md` 가 550줄, `status.md` 가 124KB, ADR 하나가 72KB 가 됐다(2026-08-23 실측).
