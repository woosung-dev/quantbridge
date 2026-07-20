# 디자인 문서 지도 — 어느 문서가 정본인가

> **이 파일의 목적.** 이 레포의 디자인 문서는 **2세대가 공존**한다. 현재 앱이 실제로 따르는 1세대와, 이식 목표인 2세대다.
> 둘 다 "확정" 도장이 찍혀 있어서 라벨 없이는 어느 쪽을 따라야 할지 알 수 없다. 이 표가 그 판정을 대신한다.
> 문서를 읽기 전에 **여기서 세대를 먼저 확인하라.**

작성 2026-07-20 · C 디자인 언어 이식 진행 중

---

## 1. 한 줄 요약

**현재 앱 = 1세대(Precision Instrument). 목표 = 2세대(C 디자인 언어). 이식은 진행 중이고 아직 끝나지 않았다.**
그래서 지금 앱을 열면 **1세대와 2세대가 섞여 보이는 게 정상**이다. 결함이 아니라 전환 상태다.

---

## 2. 문서별 세대·상태·역할

| 문서                                                                                                          | 세대                            | 상태                               | 역할                                        |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------------- | ------------------------------------------- |
| [`DESIGN.md`](../DESIGN.md)                                                                                   | **1세대** Precision Instrument  | **현행** — 앱 대부분이 이걸 따른다 | 현재 디자인 시스템 (색·타이포·컴포넌트)     |
| [`docs/prototypes/README.md`](./prototypes/README.md) · `INTERACTION_SPEC.md` · `00~11-*.html`                | **구세대** Stage 2 (2026-04-14) | **superseded** — 단 삭제 금지      | 아래 §4 참조. 살아있는 코드가 아직 인용한다 |
| [`docs/prototypes/shotgun-2026-07/_KIT.md`](./prototypes/shotgun-2026-07/_KIT.md)                             | **2세대** C 디자인 언어         | **목표 캐논**                      | 하드제약 15 + §4 워크스페이스 캐논          |
| `docs/prototypes/shotgun-2026-07/screen-01~17-*.html`                                                         | **2세대**                       | **목표 캐논 (최상위)**             | 확정 화면 17벌. 시각적 정본                 |
| [`docs/prototypes/shotgun-2026-07/terminology-ssot.md`](./prototypes/shotgun-2026-07/terminology-ssot.md)     | **2세대**                       | 목표 캐논 (하위)                   | enum↔한국어 대조표 + `labels.ts` 이식 모듈  |
| `docs/prototypes/shotgun-2026-07/variant-a.html` · `variant-b.html`                                           | 2세대 후보                      | **탈락**                           | shotgun 에서 진 안. 이력 보존용             |
| `docs/prototypes/shotgun-2026-07/HANDOFF-react-port.md`                                                       | 이식                            | **superseded**                     | 이식 착수 *전*에 쓰인 판. 아래 정본을 볼 것 |
| [`docs/c-language-port/HANDOFF.md`](./c-language-port/HANDOFF.md)                                             | 이식                            | **진행 정본**                      | 현재 슬라이스 상태·다음 할 일               |
| [`docs/c-language-port/checklist.md`](./c-language-port/checklist.md) · `context-notes.md` · `s0-baseline.md` | 이식                            | 진행 정본                          | 슬라이스 S0~S9 · 결정 근거 · 측정 기준선    |

---

## 3. 2세대 안에서의 우선순위

세 문서가 어긋나면 **위쪽이 이긴다.**

1. **`screen-01~17-*.html`** — 화면이 지상 진실이다
2. **`_KIT.md` §4** — 워크스페이스 캐논
3. **`terminology-ssot.md`** — 용어

근거는 `_KIT.md:126` 이다. "**어긋나면 화면이 옳고 이 문서가 고칠 쪽이다.**"
`terminology-ssot.md:5` 도 스스로 `_KIT.md` §4 를 상위로 선언한다.

---

## 4. 구세대를 지우지 않은 이유

`docs/prototypes/00~11-*.html` 은 superseded 지만 **아직 살아있는 코드가 행 번호까지 인용**한다. 옮기거나 지우면 그 인용이 전부 깨진다.

| 인용하는 코드                                                                 | 인용 대상                                     |
| ----------------------------------------------------------------------------- | --------------------------------------------- |
| `frontend/src/app/(dashboard)/onboarding/_components/option-card-radio.tsx:2` | `05-onboarding.html` `.option` (304-385)      |
| `.../onboarding/_components/progress-stepper.tsx:2`                           | `05-onboarding.html` `.progress` (167-236)    |
| `.../onboarding/_components/illustration-frame.tsx:2,85`                      | `05-onboarding.html` (654-757)                |
| `.../onboarding/_components/onboarding-view.tsx:31`                           | `05-onboarding` 4단계 라벨                    |
| `frontend/src/app/(auth)/_components/split-screen-shell.tsx:2`                | `04-login.html`                               |
| `frontend/src/app/(dashboard)/trading/_components/kill-switch-modal.tsx:3`    | `INTERACTION_SPEC.md` §03 (**살아있는 의무**) |
| `frontend/README.md:70`                                                       | `00-landing.html`                             |

이 인용들은 이식이 해당 화면에 도달하면(온보딩 = `screen-12`, 로그인 = `screen-15`) 자연히 2세대로 갈아탄다. **그 전까지는 구세대 파일이 제자리에 있어야 한다.**

---

## 5. 알려진 잔여 불일치

이식이 끝나면 사라지지만, 지금은 남아 있어 헷갈릴 수 있는 것들이다.

- **두 스타일 시스템 공존.** 이식된 화면은 시맨틱 CSS(`globals.css @layer components`), 나머지는 Tailwind 유틸리티다. 의도된 전환 상태다.
- **거래소 표기.** 2세대 캐논은 **Bybit 단일**(`_KIT.md:89`)이고 OKX 는 로드맵으로 내렸다. 그러나 `docs/README.md` 기술 스택 행과 백엔드 `schemas.ts` 에는 아직 OKX 가 남아 있다. 캐논이 이긴다.
- **라이트 테마.** 2세대 캐논은 **다크 기준**으로만 적용됐다. 라이트는 "동작만 보장, 외관은 미소유" 상태다.
- **구세대 슬롭 문구.** `00-landing.html` 의 `100+ 거래소` · `벡터화` 등은 2세대 하드제약 위반이다(ADR-011). 구세대라 그대로 두지만 **인용해서는 안 된다.**

---

## 6. 새 세션이 할 일

1. 이 지도를 읽는다
2. [`docs/c-language-port/HANDOFF.md`](./c-language-port/HANDOFF.md) §0 에서 현재 슬라이스를 확인한다
3. 화면을 만들 땐 **`screen-NN-*.html` 을 열어서 보고** 베낀다. 재해석하지 않는다
