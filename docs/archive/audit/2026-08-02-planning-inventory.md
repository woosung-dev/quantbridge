# 계획 문서·진행률 인벤토리 (읽기 전용 조사)

> **조사일:** 2026-08-02  
> **기준 커밋:** `main@6ee0b2c7` (PR #521, status 동기화)  
> **범위:** `AGENTS.md` · `CONTEXT.md` · `docs/{status,roadmap,backlog}.md` · 현재 제품 요구/비전 · BL 감사 스크립트 · Git 이력  
> **방법:** 저장소 문서·스크립트·Git만 1차 근거로 읽었다. 코드, 기존 계획, BL 상태는 변경하지 않았다.

## 결론

현재 실행 계약은 **`metric-guard-parity`** 하나다. 다음 세션은 새 계획 문서나 legacy PRD가 아니라
[`docs/status.md`의 「다음 스프린트」](../../status.md#-다음-스프린트--metric-guard-parity-계측-실패가-머니-패스를-오기록하는-자리를-닫는다)에서 시작한다.

최우선 위험은 [BL-579](../../backlog.md#bl-579)다. Prometheus 계측 mutation 127곳 중 2곳은
거래소 쓰기 성공 직후라, 계측 예외가 성공한 발주를 실패로 기록할 수 있다. 현재 관측된 가드 실패는
0회이나, 가드 밖 지점은 자기 실패를 계수하지 못하므로 “위험 없음”의 근거가 아니다.

전체 작업량을 하나의 개발 진척률로 환산할 공인 산식은 없다. 대신 BL 상태의 정본 감사 결과는
**전체 236개 중 Active 149, Partial 7, Resolved 80, Unknown 0**이다. 따라서 완료율을 말할 때는
`Resolved 80/236 (33.9%)`와 `Partial 7/236 (3.0%)`를 분리해야 하며, Partial을 완료로 합산하면 안 된다.

## 1. 문서의 책임과 현재성

| 질문                                     | 정본                                                                                                                                                                                 | 이 조사에서의 해석                                                                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 지금 무엇을 실행하는가                   | [`status.md`](../../status.md)                                                                                                                                                       | 활성 Sprint는 없고 다음 실행 계약은 `metric-guard-parity`다. 이 파일의 다음 스프린트 블록만 다음 세션 진입점이다.                             |
| 미해결 위험의 상태·재개 조건은 무엇인가  | [`backlog.md`](../../backlog.md) + [`scripts/bl-audit.sh`](../../../scripts/bl-audit.sh)                                                                                             | BL 섹션의 `상태` 줄이 정본이며, 인덱스 표·로드맵 체크박스와 3면 대조한다.                                                                     |
| 그다음 후보·제품 방향은 무엇인가         | [`roadmap.md`](../../roadmap.md)                                                                                                                                                     | 후보와 그룹별 잔여 목록이다. 첫 실행 지시로 사용하면 안 되며 `status.md`와 충돌할 때 status가 우선한다.                                       |
| 현재 사용자에게 약속하는 범위는 무엇인가 | [`reference/product/requirements-overview.md`](../../reference/product/requirements-overview.md)                                                                                     | Pine Import → Verify → **Bybit Demo** Operate까지다. mainnet 공개·외부 Beta·프로덕션 배포는 현재 제품 약속 밖이다.                            |
| 제품의 장기 방향은 무엇인가              | [`reference/product/vision.md`](../../reference/product/vision.md)                                                                                                                   | Pine 전략을 백테스트·스트레스/최적화·데모 거래로 연결하는 비전과 비범위를 설명한다. 구체적 남은 일의 정본은 아니다.                           |
| 초기 PRD·과거 계획은 무엇인가            | [`archive/product/2026-04-14-original-prd.md`](../../archive/product/2026-04-14-original-prd.md), [`archive/superpowers/plans/README.md`](../../archive/superpowers/plans/README.md) | historical reference다. PRD 자체가 `pine_v2`/optimizer/스프린트 모델이 현행과 다르다고 명시하므로 진행률 산정·다음 작업 지시에는 쓰지 않는다. |

`AGENTS.md`도 위 질서를 고정한다. 새 세션의 기본 입력은 `CONTEXT.md` + `AGENTS.md` + `docs/status.md`이고,
`roadmap.md`·`backlog.md`는 필요할 때 읽는다. 특히 BL 숫자는 손으로 세지 말고 감사 스크립트를 쓰도록 규정한다.

## 2. 다음 스프린트: metric-guard-parity

### 확정된 범위

[`status.md`](../../status.md#첫-step)는 다음 세 작업을 이 순서로 적는다.

1. 현재 HEAD에서 baseline을 다시 측정한다.
2. **[BL-579]의 P1 2곳**부터 `tasks/trading.py`와 `services/order_service.py`에서 `_count_safely`를
   거래소 쓰기 이전 경계까지 끌어올린다.
3. [BL-576](../../backlog.md#bl-576)의 5 event 중 아직 관측되지 않은 3 event는 기다리지 말고
   발화 조건을 설계해 프로덕션에서 확인한다. 동시에 `/metrics`의 영구 누적 파일 수·용량을 재서 판단한다.

### 명시적 제외·보류

- 127개 mutation 지점을 일괄 수정하지 않는다. [BL-579](../../backlog.md#bl-579)는 P1 2곳의 결과를
  먼저 보라고 한다.
- [BL-574](../../backlog.md#bl-574)와 [BL-578](../../backlog.md#bl-578)은 **크기 측정 완료·수리 보류**다.
- C1 조건부 진입을 시장가로 전환하는 등 머니-패스 의미를 바꾸는 수리는 이 회차 범위가 아니다.
- 사전등록 판정식은 서술 파일에 다시 복제하지 않고
  [`generator-evaluator-pipeline.md` §G1.1](../../reference/operations/workflows/generator-evaluator-pipeline.md#g11--사전등록-판정식-정본화-2026-08-02-신설-여기가-판정식의-정본이다)을 쓴다.

### 착수 전 유의점

- 새 라벨 counter는 최초 발화 전 series가 없어 차분 검증이 불가능할 수 있으므로 `_touch_safely`로
  실체화해야 한다.
- soak 종료는 자동 flat이 아니다. 세션 종료와 별개로 주문 취소·포지션 청산, 그리고 착수 시점 flat 확인이 필요하다.
- `BL-576 Resolved`는 라벨 분리·일부 event 발화 검증의 완료를 뜻한다. status가 지정한 “잔여 3 event의
  프로덕션 확인”은 미확인 관측 증거를 보강하는 후속 작업이며, BL 상태를 다시 해석해 바꾸라는 뜻이 아니다.

## 3. BL 정량 스냅샷

### 재현 명령과 결과

```bash
scripts/bl-audit.sh
```

현재 HEAD에서 실제 실행한 결과:

| 상태     | 개수 |   비율 |
| -------- | ---: | -----: |
| Active   |  149 |  63.1% |
| Partial  |    7 |   3.0% |
| Resolved |   80 |  33.9% |
| Unknown  |    0 |   0.0% |
| 전체     |  236 | 100.0% |

우선순위별로는 P0 `Active 1`, P1 `Active 6 / Partial 3 / Resolved 20`,
P2 `Active 61 / Partial 2 / Resolved 34`, P3 `Active 81 / Partial 2 / Resolved 26`이다.
P0의 유일한 Active는 [BL-003](../../backlog.md#bl-003), 즉 Bybit mainnet runbook·smoke다.
그러나 그 Trigger는 Demo 안정 운영과 BL-004 완료 뒤의 H1 종료 직전이며, 현재 제품 범위는 Demo만이므로
이 수치가 다음 스프린트를 자동으로 바꾸지는 않는다.

감사는 `UNKNOWN 0`, 인덱스 표·섹션 상태·로드맵 체크박스의 불일치 0으로 종료했다. 이 정합성은
**상태가 없는 항목을 완료로 추정하지 않은 결과**이며, `Partial`을 Active나 Resolved로 흡수하지 않는다.
스크립트의 판정 규칙과 종료 조건은 [`scripts/bl-audit.sh`](../../../scripts/bl-audit.sh)에 있다.

### 열린 일의 카테고리

로드맵의 열린 체크리스트와 활성 BL의 실제 카테고리를 함께 보면, 남은 일은 다음처럼 구분된다.

| 카테고리                                   | 현황과 대표 항목                                                                                                                                         | 읽는 법                                                                                                                                                                          |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **현 스프린트: 관측 안전성**               | BL-579 (P2)                                                                                                                                              | 성공한 거래소 쓰기 뒤의 metric 예외가 money path 결과를 뒤집지 않게 하는 최상위 위험이다.                                                                                        |
| **테스트·인프라 P1 부채**                  | BL-015 OKX Private WS, BL-022 golden 재생성, BL-023 mutation 분류, BL-024 real-broker nightly E2E, BL-025 병렬 sprint 스킬, BL-026 mutation fixture 회귀 | status/roadmap은 실자금 머니-패스 P1 슬롯은 비었고, 열린 P1 여섯 건은 이 부류라고 명시한다. Trigger가 도래하지 않은 항목도 있어 순위 숫자만으로 즉시 착수 대상으로 보면 안 된다. |
| **거래소·머니-패스 잔여**                  | BL-438은 Partial (네이티브 TP/SL·trailing 청산 손익 귀속), BL-535는 Partial (백테스트 spot/perp 결과 차 대조), BL-446 cumulative-loss 시간축             | 이미 많은 live 정합성 패키지를 닫았지만, 부분 완료는 완료가 아니다. 각 BL의 Trigger·측정 근거를 다시 확인하고 시작한다.                                                          |
| **pine_v2·백테스트·optimizer 정확도**      | 레버리지/파산 관련 BL-460·466, Track A·Pine parity, warmup replay BL-441, optimizer/stress DTO·지표 항목                                                 | 현재 제품의 Verify 단계 품질을 높이는 중기 P2/P3 큐다. 정본 엔진은 `pine_v2`; vectorbt를 실행 엔진으로 되돌리는 계획은 없다.                                                     |
| **UI·프로토타입 이식·리포트 polish**       | 주문 상세, stress history, 전략 목록 필드/정렬, 차트·폼·보고서 UI 항목                                                                                   | [`roadmap.md`의 그룹 1](../../roadmap.md#1-프로토타입-이식-잔여-스키마api-확장-선행)과 P3 섹션에 모여 있다. 대부분은 API·스키마 확장 또는 저우선 UX 개선이다.                    |
| **Beta·배포·사용자 결정을 필요로 하는 일** | G1 DB hosting 재결정, BL-070~075, BL-005 실자본 dogfood, BL-145 cross-margin                                                                             | 코드만으로 닫을 수 없다. Beta 번들은 G1 결정 뒤의 사용자/manual·deploy-time 작업이며, 현재 스프린트와 병합하지 않는다.                                                           |

### 로드맵 체크박스의 한계

`roadmap.md`에는 열린 체크박스 105개와 완료 체크박스 22개가 보인다. 하지만 이것은 BL 전체의
직접적인 분모가 아니다. 일부 BL은 반복 참조되거나 상태표에만 있고, 일부 체크박스는 G1 같은 사용자
결정이다. 따라서 이 숫자로 프로젝트 완료율을 계산하지 않는다. 감사 스크립트가 매칭되는 BL에 한해
3면 정합성을 보증하므로, 전체 진행률의 수치는 위 BL 상태표를 사용한다.

## 4. PRD·스펙·디자인 문서에서 확인한 범위

### 현재 제품 계약

현재 요구 문서는 사용 흐름을 **Import → Verify → Operate**로 한정한다.

- Import: Pine Script 등록, 지원 범위와 degraded 여부를 먼저 판정한다.
- Verify: `pine_v2` bar-by-bar 백테스트와 Monte Carlo·Walk-Forward·파라미터 안정성·optimizer를 같은
  백테스트 계약으로 제공한다.
- Operate: Bybit **Demo** 계정에서 전략을 실행하고 주문·포지션·Kill Switch를 관찰한다.

이는 [`requirements-overview.md`](../../reference/product/requirements-overview.md)의 현재 계약과
[`CONTEXT.md`](../../../CONTEXT.md)의 `pine_v2` SSOT·Bybit Demo 제한에 일치한다. 초기 PRD가 말하는
“원클릭 라이브 전환”은 현재 약속이 아니다.

### 스펙의 수명 구분

- [`reference/product/`](../../reference/product/)와 [`reference/design/`](../../reference/design/)은
  오래 유지되는 계약이다. `DESIGN.md`는 Precision Instrument v3 디자인 시스템의 확정 사양이지
  실행 순서를 지시하는 스프린트 플랜은 아니다.
- 완료 스프린트의 수치·반증·판단은 [`dev-log/INDEX.md`](../../dev-log/INDEX.md)에 남는다. 예를 들어
  [canonical-measurement-surface 회고](../../dev-log/2026-08-02-canonical-measurement-surface.md)는
  BL-576 발화 검증, BL-577 전제 반증, BL-579 발견의 근거를 보존한다.
- `archive/product/`, `archive/superpowers/specs/`, `archive/superpowers/plans/`은 과거 설계와 계획이다.
  현재 실행 지시로 재활성화하지 않는다.

## 5. 최근 Git 흐름과 진행률을 읽는 방법

최근 main 이력은 기능 개수 확대보다 **라이브 거래 정합성의 발견 → 계측 → 재판정 → 실운영 검증** 루프에
집중돼 있다.

| 순서       | 커밋 / PR         | 1차 근거로 읽히는 변화                                                                    |
| ---------- | ----------------- | ----------------------------------------------------------------------------------------- |
| 2026-07-30 | `bc0046b6` / #513 | BL-560의 크기를 확정하고 조건부 진입 계측·BL 산식 정본을 보강했다.                        |
| 2026-08-01 | `b8d53141` / #518 | BL-536을 재판정해 “축소”로 바꾸었다.                                                      |
| 2026-08-02 | `df446d60` / #519 | BL-576 라벨을 분화하고 사전등록 판정식의 정본을 §G1.1로 옮겼다.                           |
| 2026-08-02 | `b476327e` / #520 | 손 SQL을 대체하는 정본 측정 표면, BL-576 프로덕션 발화 검증, BL-577 전제 반증을 머지했다. |
| 2026-08-02 | `6ee0b2c7` / #521 | #520 머지 뒤에도 남은 `status.md`의 “PR 준비 중” 표기를 동기화했다.                       |

현재 `HEAD`는 #521이고, `status.md`가 적는 “최근 머지”는 **최근 코드 스프린트 #520**을 가리킨다.
둘을 구별하면 모순이 없다: #521은 그 스프린트의 실행 상태를 즉시 정정한 문서 후속이다.

최근 PR은 전통적인 2-parent merge commit보다 제목의 `(#NNN)`로 식별되는 squash-style main commit이다.
그러므로 이 범위의 PR 진행을 검증할 때는 `git log --first-parent`의 제목·본문과 해당 SHA를 함께 인용한다.
`git log --merges`만으로 최근 PR 목록을 만들면 오래된 merge commit만 남아 실제 흐름을 놓친다.

## 6. 다음 보고에서 유지할 측정 규칙

1. **실행 우선순위:** `status.md`의 다음 스프린트 블록을 먼저 보고, roadmap은 후보, backlog는 항목별
   상태·재개 조건으로 사용한다.
2. **BL 정량:** `scripts/bl-audit.sh`의 ACTIVE/PARTIAL/RESOLVED/UNKNOWN을 그대로 제시한다.
   `Partial`을 완료율에 합산하지 않는다.
3. **완료 근거:** PR 번호만이 아니라 main SHA, 상태/회고의 검증 수치, BL 상태 줄을 함께 대조한다.
4. **측정 한계:** 문서에 적힌 BE/FE gate 수치는 그 스프린트의 기록이며, 다음 구현 세션에서는 반드시
   현재 HEAD에서 재측정한다. 이 조사에서 실제 실행한 검증은 `scripts/bl-audit.sh` 하나다.
5. **계획 변경 금지:** 이 파일은 상태 스냅샷이다. 다음 Sprint의 범위·BL 상태·제품 약속을 수정하거나
   두 번째 실행 원장을 만들지 않는다.

## 조사 메모의 위치 선택

이 문서는 실행 중인 스프린트의 dev-log가 아니라 완료된 읽기 조사 스냅샷이다. 그래서 최근의 비교·문서 구조
조사도 보관한 `docs/archive/audit/YYYY-MM-DD-<주제>.md` 관례를 따랐다. [`archive/audit/README.md`](./README.md)는
원래 보안 감사를 설명하지만, 실제 tree에는 2026-08-01의 비보안 조사 보고서들이 같은 위치에 있다.
자동 생성 dashboard/JSON만 두는 [`docs/reports/README.md`](../../reports/README.md)에는 두지 않았다.

## 1차 근거 목록

- [`AGENTS.md`](../../../AGENTS.md) — 세 문서 진입 규칙, BL 감사 사용 규칙, 도메인·Git 안전 경계
- [`CONTEXT.md`](../../../CONTEXT.md) — `pine_v2`·Demo-first 도메인 SSOT
- [`docs/README.md`](../../README.md) — 문서별 책임·수명 분리
- [`docs/status.md`](../../status.md) — 다음 스프린트, baseline, 명시적 제외
- [`docs/roadmap.md`](../../roadmap.md) — 그룹별 후보·Beta/Deferred·완료 이력
- [`docs/backlog.md`](../../backlog.md) — BL-003, BL-438, BL-535, BL-574, BL-576, BL-578, BL-579의 상태·근거
- [`scripts/bl-audit.sh`](../../../scripts/bl-audit.sh) — 상태 판정·3면 대조의 구현 정본
- [`docs/reference/product/requirements-overview.md`](../../reference/product/requirements-overview.md), [`vision.md`](../../reference/product/vision.md) — 현재 제품 계약과 장기 비전
- [`docs/reference/operations/workflows/generator-evaluator-pipeline.md`](../../reference/operations/workflows/generator-evaluator-pipeline.md) — 판정식·검증 단계 규율
- Git `main`의 `git log --first-parent`, `git show 6ee0b2c7`, `git show b476327e` — 최근 흐름과 병합 후 상태 동기화 근거
