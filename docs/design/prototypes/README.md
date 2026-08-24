# QuantBridge 프로토타입 — 화면 캐논

> **정본은 [`shotgun-2026-07/`](./shotgun-2026-07/) 하나다.** 2026-04 의 1세대 12벌은 2026-08-07 에
> 삭제됐다 (아래 §1세대). 이 디렉터리 직하에 남은 것은 이 README 뿐이다.
> **규약 본문 = [`shotgun-2026-07/_KIT.md`](./shotgun-2026-07/_KIT.md)** — 새 화면을 만들거나 기존
> 화면을 고치기 전에 그 파일을 연다. 용어 SSOT 는 `shotgun-2026-07/terminology-ssot.md`,
> ★**회차 기록 5종은 2026-08-23 에 삭제됐다** — 아래 tombstone 참조.
>
> ★**이 하위 트리는 2026-07 캡처 시점의 원문이다.** 구 `frontend/`·`backend/` 경로 표기(→
> [ADR-029](../../adr/029-monorepo-standard-layout.md) 로 `apps/web/`·`apps/api/`)와 Clerk 표기(→
> [ADR-034](../../adr/034-auth-self-host-better-auth.md) 로 Better Auth)는 **일부러 고치지 않았다**.
> 현재 경로·인증을 알고 싶으면 그 두 ADR 을 봐라.

## 보고 검사하는 법

```bash
cd docs/design/prototypes/shotgun-2026-07
python3 serve.py                       # http://localhost:4173/viewer.html (no-store, 캐시 사고 방지)
python3 preflight.py --all             # 정적 검사. FAIL 0 이어야 한다
node runtime-check.mjs screen-NN-*.html  # 1440/1024/768/375 실측 (가로 스크롤·대비·포커스 링)
```

`python3 -m http.server` 를 쓰지 마라 — `Cache-Control` 을 안 보내서 고친 화면이 안 바뀐 것처럼 보인다.

## 2세대 캐논 20종

**17벌**

|  #  | 파일                        | 화면            |  #  | 파일                         | 화면            |
| :-: | --------------------------- | --------------- | :-: | ---------------------------- | --------------- |
| 01  | `screen-01-trading-cockpit` | 트레이딩 코크핏 | 10  | `screen-10-optimizer-detail` | 옵티마이저 상세 |
| 02  | `screen-02-dashboard`       | 대시보드        | 11  | `screen-11-orders`           | 주문            |
| 03  | `screen-03-backtests-list`  | 백테스트 목록   | 12  | `screen-12-onboarding`       | 온보딩          |
| 04  | `screen-04-trade-detail`    | 트레이드 상세   | 13  | `screen-13-error-pages`      | 에러 · 유지보수 |
| 05  | `screen-05-backtest-setup`  | 백테스트 설정   | 14  | `screen-14-landing`          | 랜딩            |
| 06  | `screen-06-strategies-list` | 전략 목록       | 15  | `screen-15-login`            | 로그인          |
| 07  | `screen-07-strategy-create` | 전략 생성       | 16  | `screen-16-pricing`          | 요금제          |
| 08  | `screen-08-strategy-editor` | 전략 편집       | 17  | `screen-17-waitlist`         | 웨이트리스트    |
| 09  | `screen-09-optimizer-list`  | 옵티마이저 목록 |     |                              |                 |

**보조 3벌**

| 파일                            | 역할                                                                                                                        |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `variant-c.html`                | **C 디자인 언어의 정본**(`_KIT.md:5`)이자 백테스트 리포트 화면. `screen-NN` 번호가 없는 이유는 셋 중 먼저 확정됐기 때문이다 |
| `light-01-report.html`          | 백테스트 리포트 라이트 테마                                                                                                 |
| `light-02-trading-cockpit.html` | 트레이딩 코크핏 라이트 테마                                                                                                 |

`_kit.html` 은 화면이 아니라 **공용 셸**이다. 새 화면은 이것을 복사해서 시작하고, `PAGE-SPECIFIC`
마커 위쪽 CSS 는 한 글자도 고치지 않는다 (`preflight.py` 가 바이트 비교로 잡는다).

## 라우트 ↔ 캐논 (FE `page.tsx` 25개, 2026-08-07 실측)

**캐논 보유 19**

| 라우트                  | 캐논        | 라우트                   | 캐논                         |
| ----------------------- | ----------- | ------------------------ | ---------------------------- |
| `/`                     | `screen-14` | `/backtests`             | `screen-03`                  |
| `/pricing`              | `screen-16` | `/backtests/new`         | `screen-05`                  |
| `/waitlist`             | `screen-17` | `/backtests/[id]`        | **`variant-c`** + `light-01` |
| `/sign-in`, `/sign-up`  | `screen-15` | `/backtests/[id]/trades` | `screen-04`                  |
| `/onboarding`           | `screen-12` | `/optimizer`             | `screen-09`                  |
| `/dashboard`            | `screen-02` | `/optimizer/[id]`        | `screen-10`                  |
| `/strategies`           | `screen-06` | `/orders`                | `screen-11`                  |
| `/strategies/new`       | `screen-07` | `/trading`               | `screen-01` + `light-02`     |
| `/strategies/[id]/edit` | `screen-08` | `/maintenance`           | `screen-13` §03(503)         |

`screen-13` 은 `not-found.tsx`(404)·`error.tsx`(500)도 함께 덮는다(`page.tsx` 가 아니라 위 25개 밖).

**캐논 미보유 6** — `/admin/waitlist`(어드민) · `/disclaimer` · `/privacy` · `/terms` ·
`/not-available`(지오블록 안내) · `/share/backtests/[token]`.
앞 다섯은 `legal-page-shell` 계열 보일러플레이트라 캐논이 필요 없다.

**캐논만 있고 라우트 없는 것은 0개** — 위 20종이 전부 소진된다.

## 미설계 잔여

- **공통 설정 4종** — 프로필 · 빌링 · 알림센터 · 도움말. 캐논도 라우트도 없다.
- **Phase 4 라이브 5종** — 라이브 전환 · 리스크 관리 · 알림 · 리포트. ★**지금 대상이 아니다** —
  실자금 라이브는 [BL-003](../../backlog.md#bl-003) 뒤이고, 현재 계정 모드는 Bybit demo 뿐이다.

## 1세대 (2026-04-14 ~ 2026-08-07, 삭제)

`00-landing.html` ~ `11-error-pages.html` 12벌 + `INTERACTION_SPEC.md`. 태그 **`prototypes-gen1`**
이 삭제 직전 커밋을 고정한다 — 태그를 지우지 마라. 지우면 squash·rebase 머지 후 fresh clone 에서
아래 명령이 `not a valid object name` 으로 깨진다.

```bash
git ls-tree --name-only prototypes-gen1 -- docs/reference/design/prototypes/
git show prototypes-gen1:docs/reference/design/prototypes/05-onboarding.html
```

**왜 지웠나.** 정본이 두 세대로 갈려 있으면 「어느 프로토타입이 맞나」가 모호해지고, 실제로
2026-08 첫째 주에 그 모호성이 잘못된 진단을 낳았다. 구 README 는 2세대를 **한 번도 언급하지 않은 채**
「Tier 1 완료 · Phase 2 0개」로 얼어 있었지만, 실제로는 Phase 2 「최적화」가 `screen-09`/`screen-10`
으로 캐논이 생겨 구현까지 끝났고(`/optimizer`), Monte Carlo·Walk-Forward 는 별도 페이지가 아니라
`/backtests/[id]` 안의 `stress-test-panel.tsx` 패널로 들어갔으며, Phase 3 「거래소 연동·세션·라이브
모니터링」은 `screen-01`/`screen-11` 에 흡수됐다.

**`INTERACTION_SPEC.md` 는 승계자 없이 폐기됐다.** 화면 종속이 아닌 공통 계약 7종을 2세대와 항목
단위로 대조한 결과, **승격 대상이 0건**이었다 — 셋은 2세대가 이미 상위집합이고, **넷은 실측이
반증**했다.

| 1세대 계약                | 판정 | 근거                                                                                                                                                                                                                                                                |
| ------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 액션 버튼 동작 원칙       | 폐기 | 시각·카피 축은 `_KIT.md` §3 색 규율 + §8 문체가 덮고, 행동 축은 코드가 이미 그 패턴이다(`sonner` 24파일)                                                                                                                                                            |
| 폼 검증                   | 폐기 | 스택은 `apps/web/AGENTS.md` §1·§8 이 정본. ★「서버 에러는 인풋 아래」가 **코드와 어긋난다** — 실제는 폼 레벨 `root.serverError` 이고 필드 아래는 클라이언트 검증 전용이다                                                                                           |
| 실시간 데이터             | 폐기 | ★**Socket.IO 는 이 레포에 없다**(FE·BE 의존성 0건). 실제는 네이티브 WS(`backend/src/realtime/router.py`) + React Query 무효화 힌트 + 폴링 병행                                                                                                                      |
| 로딩/에러/빈 상태         | 폐기 | `_KIT.md` §1 #10 + §6 이 **상위집합**(무데이터 셀까지 4종). FE 축은 `apps/web/AGENTS.md` §3·§6                                                                                                                                                                      |
| 접근성                    | 폐기 | `_KIT.md` §1 #2/#3/#4/#11 + §4.10 + §7 `runtime-check.mjs` 가 **실측 가능한 형태의 상위집합**                                                                                                                                                                       |
| 반응형                    | 폐기 | ★**4개 중 3개가 틀렸다** — `_kit.html` 실측은 1440 구간 없음(`max-width:1240px` 무조건) · 검색바 숨김 **1024**(1200 아님) · 사이드바 **64px**(60 아님). 768 햄버거만 일치                                                                                           |
| Kill Switch 특별 주의사항 | 폐기 | ★**아키텍처가 다르다** — Kill Switch 는 버튼이 아니라 자동 게이트(`ensure_not_gated`)이고 `POST …/kill` 은 없다. 타이핑 확인·30초 쿨다운·전량 청산 버튼 전부 **0건**. 실재하는 건 감사 로그(`KillSwitchEvent` row)뿐이고 정본은 `../../domain/state-machines.md` 다 |

---

> ★**2026-08-23 다이어트.** `shotgun-2026-07/` 의 회차 문서 **5개 · 118 KB** 를 삭제했다 —
> `checklist.md`(43KB) · `HANDOFF-react-port.md`(34.5KB) · `cross-audit-notes.md`(16KB) ·
> `context-notes.md`(15KB) · `evaluation-report.md`(10KB). 원문 = `git show 4c65bc0e:docs/design/prototypes/shotgun-2026-07/`.
>
> **남긴 둘과 근거:** `_KIT.md`(규약 본문 — 코드 주석 3곳이 `_KIT.md §4.5`·`§4.8` 로 절 번호를 인용한다) ·
> `terminology-ssot.md`(화면 용어 원장). **`screen-*.html` 도 남는다** —
> `apps/web/e2e/design-canon-calibration.spec.ts:116` 이 `readdirSync` 로 그 글롭을 읽는다(마크다운은 안 읽는다).
