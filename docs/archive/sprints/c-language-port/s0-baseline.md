<!-- S0 검사 장치의 캘리브레이션·baseline 실측 출력을 그대로 보존하는 산출물 -->

# S0 baseline — 실측 출력 기록 (2026-07-20)

> checklist S0 검증 게이트 "★캘리브레이션 … **출력 그대로 기록**" 의 이행.
> 이 수치가 후속 슬라이스 래칫의 기준선이다. 재현: 아래 명령을 그대로 실행한다.

---

## 1. 프로토타입 정본 — `node docs/prototypes/shotgun-2026-07/runtime-check.mjs`

착수 전 재현. **17/17 PASS, exit 0.**

```
PASS  screen-01-trading-cockpit.html  overflow=0 contrast=0 focus=0 motion=0 canon=41 console=0 tiny=0
PASS  screen-02-dashboard.html        overflow=0 contrast=0 focus=0 motion=0 canon=27 console=0 tiny=0
PASS  screen-03-backtests-list.html   overflow=0 contrast=0 focus=0 motion=0 canon=29 console=0 tiny=0
PASS  screen-04-trade-detail.html     overflow=0 contrast=0 focus=0 motion=0 canon=21 console=0 tiny=0
PASS  screen-05-backtest-setup.html   overflow=0 contrast=0 focus=0 motion=0 canon=7  console=0 tiny=0
PASS  screen-06-strategies-list.html  overflow=0 contrast=0 focus=0 motion=0 canon=25 console=0 tiny=0
PASS  screen-07-strategy-create.html  overflow=0 contrast=0 focus=0 motion=0 canon=7  console=0 tiny=0
PASS  screen-08-strategy-editor.html  overflow=0 contrast=0 focus=0 motion=0 canon=9  console=0 tiny=0
PASS  screen-09-optimizer-list.html   overflow=0 contrast=0 focus=0 motion=0 canon=25 console=0 tiny=0
PASS  screen-10-optimizer-detail.html overflow=0 contrast=0 focus=0 motion=0 canon=31 console=0 tiny=0
PASS  screen-11-orders.html           overflow=0 contrast=0 focus=0 motion=0 canon=33 console=0 tiny=0
PASS  screen-12-onboarding.html       overflow=0 contrast=0 focus=0 motion=0 canon=25 console=0 tiny=0
PASS  screen-13-error-pages.html      overflow=0 contrast=0 focus=0 motion=0 canon=7  console=0 tiny=0
PASS  screen-14-landing.html          overflow=0 contrast=0 focus=0 motion=0 canon=8  console=0 tiny=0
PASS  screen-15-login.html            overflow=0 contrast=0 focus=0 motion=0 canon=2  console=0 tiny=0
PASS  screen-16-pricing.html          overflow=0 contrast=0 focus=0 motion=0 canon=8  console=0 tiny=0
PASS  screen-17-waitlist.html         overflow=0 contrast=0 focus=0 motion=0 canon=8  console=0 tiny=0
총 17개 중 17개 통과.
```

## 2. 이식된 감사 코어 캘리브레이션 — `pnpm e2e:design-canon` (calibration)

`design-canon-audit.ts` 를 같은 17벌 + 라이트 2벌에 돌려 재현. **22 passed** (다크 17 + 라이트 2 + 위생 3). canon 카운트가 §1 과 전부 일치 — 이식된 코어가 원본과 같은 자다.

라이트 2벌 canon = 13 / 13 (`bgOf()` 의 배경 역전 처리를 태우는 유일한 대상).

## 3. 공개 라우트 — `design-canon-public.spec.ts` (CI)

| 라우트      | 하드 실패 | canon | 내역                                                                        |
| ----------- | --------- | ----- | --------------------------------------------------------------------------- |
| `/`         | **2**     | 169   | "Bybit Demo 연동 (Beta)" `#7a828c` 4.3:1 (AA 4.5 미달), 1440·375 두 폭. S1a |
| `/waitlist` | 0         | 6     | 깨끗                                                                        |

`/` 의 대비 결함은 토큰 감사가 잡은 `--text-muted` 와 같은 색이라 **S1a `--text-muted`→#8b939c 교정이 함께 해소**한다. `tiny=32` 는 게이트 아님(지표).

## 4. P1 4라우트 (authed, 로컬) — `authed-canon-p1.spec.ts`

백엔드 8000(DB 5436) 기동 + 데이터(백테스트 6·체결 최대 585·거래소 1) 상태 실측.

| 라우트                  | 하드 실패 | canon | 내역                                         | 해소 |
| ----------------------- | --------- | ----- | -------------------------------------------- | ---- |
| `/dashboard`            | 0         | 43    | 깨끗 (활성 세션 0 = 빈 코크핏)               | —    |
| `/backtests`            | 1         | 56    | 375px 가로 오버플로 (scrollWidth 436 > 375)  | S5   |
| `/backtests/:id/trades` | 3         | 214   | 검색·기간 시작·기간 종료 입력 포커스링 없음  | S6   |
| `/trading`              | 1         | 30    | outline-none 포커스가능 div ("Kill Switch…") | S8   |

`nextjs-portal`(next dev 오버레이)은 감사 코어에서 tag 제외 — 앱·프로토타입에 없는 dev 아티팩트다.

---

**주의.** `/dashboard` 는 라이브 세션 데이터가 없어 빈 코크핏이다. 채워지면 canon/하드 실패가 달라지므로 재측정해야 한다. P1 authed baseline 은 이 데이터 스냅샷 기준이다.
