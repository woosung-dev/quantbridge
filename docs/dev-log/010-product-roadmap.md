# ADR-010: Product Roadmap 프레임 & 입력 결정

> **DEPRECATED (2026-05-04 cleanup):** 본 문서는 1차 초안. **재작성본은 [`010b-product-roadmap.md`](./010b-product-roadmap.md)**. SSOT 는 [`docs/00_project/roadmap.md`](../00_project/roadmap.md). 본 파일은 ADR 1차 시도 기록 보존용으로만 유지 — 신규 참조 시 010b 또는 roadmap.md 우선.
>
> **작성일:** 2026-04-17
> **작성 세션:** Claude Code 플랜 모드 brainstorming 세션
> **상태:** ✅ 채택 (재작성본 010b 가 현재 활성)
> **관련 산출물:** [`docs/00_project/roadmap.md`](../00_project/roadmap.md)
> **연계 ADR:** [ADR-008](./008-sprint7c-scope-decision.md) (외부 demand red flag 해소 경로)

---

## 배경

`vision.md`는 Phase 1~4 기술 Horizon을, `TODO.md`는 Sprint 단위 추적을 제공한다. 그러나 **비즈니스·사용자·수익화·법무·Launch 축**은 문서에 없었다. 구체적으로:

- 수익 모델 (Freemium / Subscription / Fee share) 미기록
- GTM·사용자 획득 전략 미기록
- 비즈니스 KPI (MAU / LTV / CAC) 미기록
- Beta 프로그램 미기록
- 법무·규제 대응 미기록
- Phase 4 이후 비전 미기록

**ADR-008**(Sprint 7c scope 결정)에서 "외부 demand evidence 없음 — 메이커 본인 예측형 demand"를 red flag로 명시. 이를 해소하려면 **단계적 Beta → 외부 공개 경로**가 로드맵에 박혀있어야 한다.

본 ADR은 해당 공백을 메우기 위한 **제품 로드맵 프레임 선택**과 **11개 입력값 결정 근거**를 기록한다.

---

## 결정: Horizon 3 × Strategy Pillars 하이브리드

### 프레임 선택 근거

5가지 프레임을 비교했다:

| 옵션                     | 이유                                                         | 결과           |
| ------------------------ | ------------------------------------------------------------ | -------------- |
| A. Now–Next–Later        | 단순성은 좋으나 시간 축 불명확                               | ★★★            |
| B. Horizon 3 단독        | 시간 축 명확, 단 실행성 약함                                 | ★★★★           |
| **C. Horizon × Pillars** | 시간+주제 2차원, 비즈니스/기술 균형                          | **★★★★★ 채택** |
| D. OKR 분기별            | 측정 가능하나 외부 유저 0 상태에선 KR 거짓 precision 위험    | ★★             |
| E. JTBD (사용자 Job)     | 사용자 중심 우수, 단 demand evidence 없는 상태에선 가설 수준 | ★★             |

**채택 이유:**

- 기존 `vision.md` Phase 1~4가 이미 시간 축 로드맵 → Horizon에 자연스럽게 매핑
- Pillar 축(Trust/Scale/Monetize)이 비즈니스 공백을 **명시적으로 드러냄** (빈 칸 = 공백 신호)
- 외부 유저 0 + ADR-008 red flag 상태에서 OKR의 정량성은 거짓 확신 위험
- JTBD는 demand evidence 확보 후(H2 말) 보조 프레임으로 재검토 가능

---

## 11개 입력값 결정

| #   | 항목                | 결정                                                                                                     | 핵심 근거                                                                                                                                                                                             |
| --- | ------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 프레임              | Horizon × Pillars                                                                                        | 위 표 참조                                                                                                                                                                                            |
| 2   | 운영 모델           | **Indie SaaS, dogfood-first**                                                                            | 사용자 명시: "내가 돈 내고 쓰고 싶은 것이 quality bar. 외부 유료는 자연 결과". Solo(a)는 로드맵 필요성 낮고, VC/OSS/exit는 문서 근거 부족                                                             |
| 3   | 프라이머리 페르소나 | **a 주도 (파트타임 크립토 트레이더, Python 가능)**, b·c는 H2~H3 자연 흡수                                | 현 구현(Pine parser → vectorbt → Bybit Futures + Kill Switch)이 a의 Pain Point를 가장 직접 해결. Sprint 7c(Monaco + 3-step wizard)도 a에 맞춤. b(퀀트 입문자)는 dogfood 기준 "QB를 굳이 쓸 이유" 약함 |
| 4   | Dogfood 가치        | ⑤ 전부 (속도 + 통합 + Pine 생태계 + 리스크 관리)                                                         | 메이커 본인이 Python 가능함에도 QB를 쓰려는 이유 = 속도·통합·Pine 생태계·리스크 관리 복합                                                                                                             |
| 5   | 시간 범위           | **H1 0–1.5m / H2 1.5–4m / H3 4–9m**                                                                      | 현 Sprint 속도(1~7a를 2일) 유지 전제. 18m 로드맵은 indie solo엔 과도. ⚠ 번아웃 리스크 명시 필요                                                                                                       |
| 6   | 수익화              | **H1 금지** + `[free/paid 후보]` 태그만 / **H2 Freemium 가설** / **H3 가격 실험**                        | dogfood-first 철학: H1은 Trust 단일 집중. Monetize는 H2 가설, H3 실험. Performance fee는 규제 리스크로 제외. BYOK + self-host는 Indie SaaS 목표와 충돌                                                |
| 7   | 지리/규제           | **BYOK + no-fiat + "software tool" 프레이밍** + H2에 US·EU geo-block + Disclaimer/ToS                    | 이미 AES-256 MultiFernet + 사용자 소유 API Key 아키텍처 완성 → 프레이밍만 명시하면 법무 부담 최소. KR only는 시간 낭비(코드베이스가 해외 거래소 기반). US/EU는 규제 리스크로 H2 차단                  |
| 8   | Launch              | **Staged: H1 Stealth → H2 지인 Beta 5~10명 → H3 TV 커뮤니티 공개** + Build in public(주 1회) H1부터 병행 | ADR-008 red flag(외부 demand 없음) 단계적 해소. Primary 페르소나가 TV 유료 사용자이므로 H3 TV 커뮤니티 공개가 가장 효율적 채널                                                                        |
| 9   | Pillar 네이밍       | **Trust / Scale / Monetize** + 한국어 괄호 병기                                                          | 영어 우선 → Build in public 영어 채널, TV 커뮤니티 H3 공개와 자연 연결. 한국어 괄호로 국내 문서 일관성 유지                                                                                           |
| 10  | Sprint 8 분할       | **8a (DB CHECK) + 8b (capital_base)**                                                                    | 독립적 검증 대상. Sprint 1~7a의 SDD T1~T4 분해 패턴 유지. 메이커 단독 리뷰어 기준 PR 단위 작아야 속도 유지                                                                                            |
| 11  | AI 전략 생성        | **H3 유지 (실험 태그)**                                                                                  | LLM 생태계 성숙은 사실이나, Pine 보안(ADR-003)과의 충돌 검증 필요. Trust Pillar 우선 철학으로 H2 조기 도입 시 scope creep 큼. dogfood 기준 "본인이 AI 생성 전략에 실자본 맡길까?"도 불명확            |

---

## 핵심 철학: Dogfood-first Indie SaaS

### 원문

> "나도 만족 못 하면 다른 사람도 쓸 이유 없음. 내가 돈 내고 쓰고 싶은 걸 만들다 보면 외부 유료 또한 되는 게 아닐까."
> — 사용자 발언, 2026-04-17 로드맵 브레인스토밍

### 적용 원칙

1. **Quality bar = "메이커 본인이 돈 내고 쓸 수준"**
2. **Feature scope 판단 = "메이커 본인이 이번 달에 쓸까?"가 1차 필터**
3. **Beta/Launch 타이밍 = "본인이 1달 이상 실자본으로 써 본 뒤" 외부 오픈**
4. **Pricing = "메이커가 이 가격이면 낼까?"를 상한으로**
5. **반대 경보 = "외부 유저가 많이 원할 것 같다"는 근거만으로 feature 넣지 말 것** (ADR-008 red flag 재발 방지)

이 원칙은 사용자 메모리에도 저장됨: `feedback_dogfood_first_indie.md`.

---

## Pillar 우선순위: 🛡 Trust ≥ 🚀 Scale > 💰 Monetize

### 정의

- **Trust** — 실자본 맡길 수준의 품질 (백테스트 신뢰성, 실거래 안정성, 리스크 관리, 보안)
- **Scale** — 기능·거래소·사용자 확장
- **Monetize** — 수익화 모델 검증

### 강제 규칙

- Trust가 깨지면 Scale/Monetize **정지**. 예: mainnet 버그 → H2 Sprint 9 연기하고 fix 먼저.
- H1에 Monetize 작업 **금지**. 태깅(`[free/paid 후보]`)은 허용.
- Sprint 7c에서 잘라낸 항목(versioning / inline backtest / ExchangeAccount UI)은 H2 재평가 전까지 재도입 금지.

---

## ADR-008 red flag 해소 경로

ADR-008은 Sprint 7c의 demand가 "메이커 본인 예측형"이라는 한계를 명시했다. 본 로드맵은 다음 단계로 외부 demand evidence를 수집한다:

1. **H1 (Stealth)** — 메이커 본인이 실자본으로 dogfood. 내부 demand를 실제 사용 빈도로 검증.
2. **H2 (지인 Beta 5~10명)** — 외부 demand evidence 1차 수집. "Beta 5명 중 3명이 1주 연속 사용"이 H3 전환 조건.
3. **H3 (TV 커뮤니티 공개)** — 외부 demand evidence 2차 수집. 가격 실험으로 **지불 의사 evidence**까지 확보.

H2 말에 Beta 5명 확보 실패 시 Launch 전략 재검토 (Build in public 비중 증가, 타깃 페르소나 재정렬).

---

## 리스크

| 리스크                       | 발동 조건                     | 대응                                               |
| ---------------------------- | ----------------------------- | -------------------------------------------------- |
| 번아웃 (9m 공격적 페이스)    | Sprint 3개 연속 overrun       | Time-box 10% 확장 허용, 주 1일 휴식 규칙           |
| 외부 demand 없음 지속        | H2 말 Beta 5명 미확보         | Launch 전략 재검토                                 |
| 규제 변화 (한국 특금법 개정) | 2026년 내 발표                | BYOK/tool-framed 재검토, 최악의 경우 글로벌 타깃만 |
| Dogfood 불일치               | H1 종료 본인 사용 주 3회 미만 | NoCode UX 집중, 페르소나 가설 재검토               |

---

## 대안 (탈락)

### 대안 1: OKR 분기별 (옵션 D)

- **탈락 이유:** 외부 유저 0 상태에서 KR 정량 설정은 거짓 precision 위험. 예: "H1 MAU 100" 같은 KR을 쓰면 dogfood-first 철학과 충돌하고 번아웃 가속.
- **재검토 조건:** H3에서 첫 $1 유료 사용자 확보 후.

### 대안 2: JTBD (옵션 E)

- **탈락 이유:** demand evidence 없이 Job을 정의하면 가설 쌓기만 된다.
- **재검토 조건:** H2 말 Beta 5명 인터뷰 후 보조 프레임으로 도입.

### 대안 3: Sprint 확장 (기존 vision.md Phase 1~4 연장)

- **탈락 이유:** 비즈니스 공백(수익화·GTM·법무) 그대로 유지. 로드맵 요청 목적 미달성.
- **부분 채택:** 본 로드맵의 Trust Pillar H1~H2 작업이 기존 Phase 로드맵과 호환.

---

## 참조 자산

### 프로젝트 내부

- [docs/00_project/vision.md](../00_project/vision.md) — 페르소나·차별점·Phase 로드맵 (Horizon 매핑 기반)
- [docs/00_project/roadmap.md](../00_project/roadmap.md) — 본 ADR의 산출물
- [docs/dev-log/008-sprint7c-scope-decision.md](./008-sprint7c-scope-decision.md) — ADR-008, red flag 원출처
- [docs/TODO.md](../TODO.md) — 기술 부채 목록
- [docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md](../superpowers/plans/2026-04-17-sprint7c-strategy-ui.md) — H1 Sprint 7c 상세 plan

### User-local (참조용, 프로젝트 미커밋)

- Claude plan file: `~/.claude/plans/keen-herding-newell.md` — 본 ADR의 원본 계획
- 사용자 메모리: `~/.claude/projects/-Users-woosung-project-agy-project-quant-bridge/memory/feedback_dogfood_first_indie.md`
