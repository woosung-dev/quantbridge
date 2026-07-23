<!-- 디자인 문서 중 어느 것이 정본인지 판정하는 지도 — 문서를 읽기 전에 여기서 층과 세대를 먼저 확인한다 -->

# 디자인 문서 지도 — 어느 문서가 정본인가

> **이 파일의 목적.** 이 레포의 디자인 문서는 여러 개가 동시에 "확정" 도장을 달고 있다.
> 그런데 서로 **경쟁하는 게 아니라 다루는 층이 다르다.** 라벨이 없으면 그 사실이 안 보여서
> "어느 쪽을 따라야 하나" 로 읽히고, 실제로 그 혼동이 폐기된 규칙을 코드로 만든 적이 있다(§6).
> 디자인 문서를 읽기 전에 **여기서 층과 세대를 먼저 확인하라.**

작성 2026-07-23 · C 디자인 언어 이식 완료 직후

---

## 1. 한 줄 판정

**화면을 만들거나 고칠 때 = `screen-01~17-*.html` + `_KIT.md` §4.
토큰·컴포넌트 값을 볼 때 = `DESIGN.md`.**
두 문서는 어긋나 있지 않다. 층이 다르다.

C 디자인 언어 이식은 **2026-07-22 자로 17벌 전체 완료**됐다(`PR #463` · `#464` · `#466`).
"이식 중이라 화면이 섞여 보인다" 는 이제 유효한 설명이 아니다.

---

## 2. 두 층 — 이게 핵심이다

| 층                         | 정본                                                                         | 다루는 것                                                                                |
| -------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **토큰 · 컴포넌트 시스템** | [`DESIGN.md`](../DESIGN.md)                                                  | 색 토큰 값, 타이포, 간격, radius, 그림자, shadcn 컴포넌트 패턴, App Shell, Tailwind 매핑 |
| **화면 · 용어 캐논**       | `screen-01~17-*.html` + [`_KIT.md`](./prototypes/shotgun-2026-07/_KIT.md) §4 | 어떤 화면이 무엇을 말하는가 — 라벨 문구, 표 열, 수치, 인쇄 금지 목록, 문체               |

**`DESIGN.md` 는 폐기 대상이 아니다.** 실측 근거 둘.

1. **값이 이미 같다.** `DESIGN.md` §2.1 의 다크 팔레트(`--bg #0b0d0f` · `--bg-alt #101214` · `--card #141619` · `--card-raised #1a1d21` · `--text-primary #e8eaed` · `--primary #f08c2e`)는 C 캐논 `variant-c.html` 값과 **일치**한다. C 프로토타입이 앱 팔레트를 이어받았기 때문이다.
2. **살아있는 인용이 압도적이다.** `frontend/` 안에서 `DESIGN.md` 를 §번호까지 인용하는 곳이 30곳 이상이고, `globals.css` · `brand-palette.ts` · `components/ui/*` 가 전부 그 계보다.

그래서 S1a 이식이 **토큰 리네임 0** 으로 끝났다. 캐논 이름(`--copper` · `--ink` · `--r-*`)은 앱 토큰을 가리키는 **별칭 브리지**로 얹었고, `@theme` 키(Tailwind 유틸 이름)는 그대로다.

---

## 3. 문서별 판정

| 문서                                                                       | 세대 · 층                    | 상태                          | 쓰임                                                                  |
| -------------------------------------------------------------------------- | ---------------------------- | ----------------------------- | --------------------------------------------------------------------- |
| [`DESIGN.md`](../DESIGN.md)                                                | 토큰 층                      | **현행**                      | 색·타이포·간격·컴포넌트 값의 정본                                     |
| `prototypes/shotgun-2026-07/screen-01~17-*.html`                           | 화면 층                      | **현행 캐논 (최상위)**        | 시각·카피의 지상 진실                                                 |
| [`_KIT.md`](./prototypes/shotgun-2026-07/_KIT.md)                          | 화면 층                      | **현행 캐논**                 | 하드제약 15 + §4 워크스페이스 캐논                                    |
| [`terminology-ssot.md`](./prototypes/shotgun-2026-07/terminology-ssot.md)  | 화면 층                      | 현행 캐논 (하위)              | enum↔한국어 대조표 + `labels.ts` 이식 모듈                            |
| [`c-language-port/HANDOFF.md`](./c-language-port/HANDOFF.md)               | 이식 기록                    | **정본 (6판)**                | 이식 결과·잔여 부채                                                   |
| `c-language-port/` 나머지 5종                                              | 이식 기록                    | 정본                          | 체크리스트·결정 근거·기준선·운영 계약                                 |
| `prototypes/00~11-*.html` · `INTERACTION_SPEC.md` · `prototypes/README.md` | 구세대 (Stage 2, 2026-04-14) | **superseded** — 단 삭제 금지 | §5 참조                                                               |
| `prototypes/shotgun-2026-07/HANDOFF-react-port.md`                         | 이식 기록                    | **superseded**                | 착수 _전_ 판. 위 6판이 이어받음                                       |
| `prototypes/shotgun-2026-07/variant-a.html` · `variant-b.html`             | 화면 층 후보                 | **탈락**                      | shotgun 에서 진 안. 일부 아이디어만 C 로 흡수(`evaluation-report.md`) |

---

## 4. 화면 층 안에서 어긋나면

**위쪽이 이긴다.**

1. **`screen-01~17-*.html`** — 화면이 지상 진실이다
2. **`_KIT.md` §4** — 워크스페이스 캐논
3. **`terminology-ssot.md`** — 용어

근거는 `_KIT.md:126` 의 "**어긋나면 화면이 옳고 이 문서가 고칠 쪽이다.**" 이고,
`terminology-ssot.md:5` 도 스스로 `_KIT.md` §4 를 상위로 선언한다.

---

## 5. 구세대를 지우지 않는 이유

`prototypes/00~11-*.html` 은 superseded 지만 **살아있는 코드가 행 번호까지 인용**한다. 옮기거나 지우면 끊긴다.

| 인용하는 코드                                                                     | 인용 대상                                   |
| --------------------------------------------------------------------------------- | ------------------------------------------- |
| `frontend/src/app/(dashboard)/onboarding/_components/illustration-frame.tsx:2,85` | `05-onboarding.html:654-757`                |
| `frontend/src/styles/globals.css:589`                                             | `08-backtest-setup.html` `.range-slider`    |
| `frontend/src/styles/globals.css:690`                                             | `04-login.html:536-545` + `00-landing.html` |
| `frontend/README.md:70`                                                           | `00-landing.html`                           |

`INTERACTION_SPEC.md` 는 **코드 인용 0건**이다 — C 이식이 인용하던 컴포넌트(`kill-switch-modal.tsx` 등)를 재작성했다. 이력 보존 목적으로만 남는다.

---

## 6. 문서 대신 검사가 강제하는 것

이 지도가 못 막는 표류는 테스트가 막는다. 문서를 고칠 때 아래도 같이 봐야 한다.

| 검사                                          | 동결하는 것                                                             |
| --------------------------------------------- | ----------------------------------------------------------------------- |
| `src/__tests__/design-canon-tokens.test.ts`   | 캐논 토큰 22종 ↔ `globals.css` 값 일치 (`KNOWN_MISMATCHES = []`)        |
| `src/__tests__/design-canon-kit-port.test.ts` | 이식된 공용 CSS ↔ `_kit.html` 정규화 동일 (의도적 편차 2건만 allowlist) |
| `src/__tests__/design-canon-source.test.ts`   | 소스 텍스트 래칫 — radius 리터럴 · 하드코딩 hex · 노출 em-dash          |
| `src/__tests__/no-raw-enum-labels.test.ts`    | 원시 enum 이 라벨 매핑 없이 JSX 로 인쇄되는 회귀                        |
| `e2e/design-canon-*.spec.ts`                  | 실제 라우트 런타임 캐논 감사 (public · authed P1 · 캘리브레이션 22)     |

**실제로 터진 사례.** `terminology-ssot.md` 의 B5/B7 헤더가 `abbr="샤프"` · `abbr="수익률"` 을 지시했는데 `_KIT.md:532/534` 는 전자를 "17벌 0건, 폐기" · 후자를 "수익률은 축약하지 않는다" 로 금지했다. 같은 파일의 이식용 TS 모듈이 그 폐기된 규칙을 담고 있었고, 그대로 `frontend/src/features/optimizer/labels.ts` 의 `OBJECTIVE_METRIC_ABBR` 이 됐다(소비처 0인 죽은 export). 2026-07-23 에 회수했다.

---

## 7. 알려진 잔여 불일치

고치지 않고 기록만 한 것. 제품 결정이 필요하거나 층이 다르다.

- **거래소 표기.** `docs/README.md:14` 기술 스택은 `CCXT (Bybit, Binance, OKX)` 인데, 화면 캐논(`_KIT.md` §4.8)은 **앱 화면에서 Bybit 단일**이고 OKX 는 로드맵이다. 실측하면 셋 다 사실이다 — 백엔드에 OKX 배선이 51곳 있고(`backend/src`), FE 폼 enum 은 이미 `z.enum(["bybit"])` 로 좁혀졌으며(`frontend/src/features/trading/schemas.ts:71`), 실제 연결·주문 실증은 Bybit 하나뿐이다. **"지원 거래소" 를 말할 때 어느 층인지 밝히지 않으면 과장이 된다.**
- `docs/prototypes/` 아래 구세대와 신세대가 한 디렉토리에 섞여 있다. §5 때문에 이동은 못 하고, 배너로 대체했다.
