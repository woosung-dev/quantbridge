<!-- C 언어 React 이식 작업의 결정과 근거 기록 (2026-07-20 착수) -->

# C 언어 React 이식 — Context Notes

> 세션이 바뀌어도 이 문서만 읽으면 결정과 근거를 재도출 없이 이어갈 수 있게 유지한다. 계속 append.
> 진행 상태는 [`checklist.md`](./checklist.md) · 계획 원본은 `~/.claude/plans/quantbridge-c-kind-cray.md`.

---

## 배경

`docs/prototypes/shotgun-2026-07/` 의 확정 프로토타입 17벌을 Next.js 앱으로 옮긴다. 프로토타입은 사용자가 뷰어에서 직접 확정했고 2안 5쌍 픽도 끝난 **시각적 정본**이다. 재설계 대상이 아니다.

평가자 패널이 권고했지만 **사용자가 명시적으로 기각한 것**이 둘 있다. 다시 제안하지 않는다.

- A안(터미널 밀도)의 밀도 장치 이식 — 24셀 격자, 파라미터 테이프, 크로스헤어, 키보드 칩. 병합안 D 를 실제로 만들었고 기각당했다. **C 의 여백은 약점이 아니라 의도다.**
- 미터 바(`.meter`)와 번호 아이브로(`.eyebrow .num`) 제거 — 평가자 4명이 제거를 권고했으나 사용자가 "C 그대로"를 선택했다.

---

## 실측이 뒤집은 전제 (2026-07-20)

핸드오프 §3 이 이미 한 번 프레임을 고쳤다. "색 교체가 아니라 이름 정합 + 반경 통합 + 아이콘 레일 신설"이다. **이번 세션 실측으로 그 프레임을 다시 고쳤다.**

### 1. 색 불일치는 1건이 아니라 5건

핸드오프는 "`--text-muted` 하나뿐, 2줄이면 끝난다"고 적었다. 프로토타입 토큰 22종을 앱 `.dark` 와 1:1 대조하니 **일치 17 / 불일치 5** 였다.

| 프로토타입      | 앱 `frontend/src/styles/globals.css` | 프로토 값               | 앱 값                  |
| --------------- | ------------------------------------ | ----------------------- | ---------------------- |
| `--ink-3`       | `--text-muted` `:360`                | `#8b939c`               | `#7a828c`              |
| `--copper-soft` | `--primary-light` `:363`             | `rgba(240,140,46,0.12)` | `0.1`                  |
| `--copper-line` | `--primary-100` `:364`               | `rgba(240,140,46,0.3)`  | `0.2`                  |
| `--bull-soft`   | `--success-subtle` `:371`            | `rgba(45,212,167,.12)`  | `rgba(52,211,153,.12)` |
| `--warn-soft`   | `--warning-subtle` `:380`            | `rgba(229,169,61,0.1)`  | `0.12`                 |

핸드오프가 불투명 hex 14종만 세고 **rgba 틴트 4종을 빠뜨렸다.** `--bull-soft` 는 앱 내부 모순이기도 하다. `--success-subtle` 이 자기 `--bullish #2dd4a7` 이 아니라 `--success #34d399` 에서 파생돼 있다.

`brand-palette.ts:45` 의 `textMuted` 도 함께 고쳐야 한다(나머지 4개는 그 파일에 없다). 총 6줄이다.

**교훈.** 핸드오프가 "실측했다"고 적어도 무엇을 모집단으로 셌는지는 별개다. 22종 대조를 다시 돌린 것이 옳았다.

### 2. `--text-muted` 는 미관이 아니라 접근성 결함

카드 `#141619` 위 실측 대비다.

- 현행 다크 `#7a828c` = **4.66:1** — 캐논 하한 5.83 미달
- 수정 후 `#8b939c` = **5.83:1** — 통과
- 라이트 `#656e78` on `#ffffff` = **5.18:1** — 역시 미달인데 프로토타입에 라이트 대응값이 없다

라이트가 캐논을 못 넘는다는 사실이 라이트 테마 결정(아래)의 근거가 됐다.

### 3. 경로와 규모

- **`frontend/src/app/globals.css` 는 존재하지 않는다.** 실제는 `frontend/src/styles/globals.css`(895줄). 핸드오프의 모든 `globals.css:NNN` 좌표를 이 파일 기준으로 읽는다.
- **`/trading` 은 2,494줄이 아니라 4,269줄.** 핸드오프가 `features/live-sessions`(1,543줄)를 빠뜨렸고 그것은 `TradingTabs` 로 완전히 도달 가능하다.
- `trading/_components/kill-switch-modal.tsx` 177줄은 프로덕션 소비자 0건(테스트만).

### 4. 반경 작업 범위가 줄어든다

`rounded-*` 429회 실측 중 `--radius-sm`(4px)·`--radius-md`(6px)는 **Tailwind v4 기본값과 바이트 동일**이다. 즉 208개 사이즈 지정 중 142개는 토큰 층이 있으나 없으나 같게 렌더된다. 실제 오버라이드는 `lg`(10px)·`xl`(14px) 둘뿐이다.

그리고 스타일 아키텍처를 시맨틱 CSS 이식으로 정했으므로 **P1 화면의 반경은 `.card` 등이 `var(--r)` 를 쓰면서 자연 소멸한다.** 191파일 전역 퍼지는 P1 에 불필요하고 S9 로 내렸다.

---

## 확정 결정

### 사용자 인터뷰 (2026-07-20, 본 세션)

**1. 스타일 아키텍처 = 시맨틱 CSS 이식.**
`_kit.html` 공용 CSS 972줄(고유 클래스 116개)을 `globals.css` `@layer components` 로 옮기고 JSX 는 `className="card"` 를 쓴다.
근거. 프로토타입이 **바이트 단위로 정본으로 남아** `preflight.py` C16 "공용 CSS 무결성" 검사를 그대로 이식할 수 있다. Tailwind 유틸리티로 재표현하면 972줄 × 손으로 옮기는 재해석이 되고, 그것이 정확히 사용자가 금지한 "프로토타입 재해석"이다.
대가. P1 4화면은 시맨틱 클래스, 나머지 화면은 기존 Tailwind 유틸로 두 체계가 당분간 공존한다. 의도된 과도기다.

**2. 라이트 테마 = 유지하되 C 캐논 검사는 다크만.**
근거. 프로토타입은 하드제약 15 로 다크 전용이고 라이트 대응 토큰을 설계한 적이 없다. 라이트도 캐논을 통과시키려면 토큰 5건을 새로 설계해야 하는데 그건 정의상 프로토타입 밖의 창작이다. 라이트 제거는 이미 동작하는 기능과 그 테스트를 지우는 선택이라 과하다.
기록해 둘 것. **라이트 화면의 외관을 아무도 책임지지 않는 상태가 명시적으로 남는다.** 이것을 숨기지 않고 문서에 적는다.

**3. nav-count 배지 = 넣는다.**
근거. 새 API 가 필요 없다. 세 목록 스키마가 모두 `total` 을 이미 갖고 있고(`strategy/schemas.ts:107` · `backtest/schemas.ts:363` · `trading/schemas.ts:33`) `dashboard-cockpit.tsx:82` 가 이미 그 값을 읽는다. 셸에서 `limit=1` 로 3회 페치하면 된다.
주의. 주문은 캐논상 **미체결 수**(대기 4 + 전송 3 = 7)라 전체 원장 14건과 다른 수다. 화면이 그 차이를 반드시 설명해야 한다.

**4. disabled nav 2개 = 제거.**
`dashboard-nav-list.tsx:33` `/templates` · `:38` `/exchanges`. 둘 다 `disabled: true` 라 라우트가 없고 "곧 출시" 툴팁만 뜬다. 제거하면 프로토타입 nav 6개와 정확히 일치하고, 없는 기능을 있는 것처럼 보이는 정직성 문제도 함께 닫힌다.

### 이전 세션 확정 (재론 금지)

P1 4화면 1차 슬라이스 · `globals.css` 전면 교체 방식 · Track A 슬롭 9종 이식과 동시 · 거래소 Bybit 단일 캐논.

### 미해결 6건 중 계획이 판단한 4건

**평가 상한 = 100.**
`backend/src/optimizer/engine/bayesian.py:68` 과 `genetic.py:73` 이 둘 다 `= 100` 이다. `genetic.py:19` docstring 의 "50" 은 stale 이고 같은 파일 `:71-72` 가 "Sprint 57 BL-237 — optimizer_heavy queue 도입으로 50 → 100 relax" 를 기록해 둔다. 프론트 카피 `≤ 50회 평가`(`optimizer-page-view.tsx:88-90`)를 `최대 100회 평가` 로 고치고 백엔드 docstring 1줄도 함께 고친다.

**전략 수명주기 enum = 프로토타입에서 제거.**
`frontend/src/features/strategy/schemas.ts` 에 `draft`/`validated`/`deployed` 가 **0건**이고 백엔드에도 없다. 캐논 §4.9 "데이터 모델에 없는 값은 그리는 순간 가짜 데이터" 에 따라 `/dashboard` 전략 카드에서 상태 칩을 렌더하지 않는다. 서버 필드 신설은 별개 사안으로 남긴다.

**`.chip.warn` 대 `.chip.failed` = `warn`.**
사용 빈도는 `failed` 가 4 대 1 우세하지만 5개 선언 전부 `--warn` 토큰만 참조하고, 사용처 하나(`screen-08` 의 `저장되지 않은 변경`)는 실패가 아니다. `failed` 라는 이름이 5개 중 4개를 잘못 설명한다. React 는 새 코드라 소급 비용이 0이다.

**`strategy.backtest_count` 정의 = 이연.**
원장이 `screen-06`(전략 목록)이라 P1 밖이다. 해당 화면 이식 시 결정한다.

---

## 검사 장치 설계의 핵심 판단

### `runtime-check.mjs` 는 다시 쓸 필요가 없다

가장 중요한 발견이다. 이 검사기는 **이미 Playwright 기반**이고 핵심 로직(`AUDIT` `:18-92`, `MOTION_AUDIT` `:94-104`)이 전부 `page.evaluate` 안에서 도는 **URL 무관한 순수 함수**다. HTML 전용인 부분은 셋뿐이다 — 파일 탐색(`:13-15`), `pathToFileURL`(`:110`), 인증 부재.

따라서 "새로 만든다"가 아니라 **"다시 겨눈다"** 가 맞다. 대비(배경 합성 후 실제 렌더값), 포커스 링(실제 Tab 30회), reduced-motion 누수, 4폭 가로 스크롤, 콘솔 에러가 전부 그대로 넘어온다.

### 정적 검사는 vitest 가드, ESLint 커스텀 룰 아님

레포에 작동하는 가드 테스트 선례가 **2건** 있다(`no-internal-ids.test.ts` 187줄 · `no-fake-marketing.test.ts` 107줄). 반면 **ESLint 커스텀 룰 선례는 0건**이고 `no-restricted-syntax` 사용도 0건이다. 이 비대칭이 판단 근거다. `src/__tests__/` 에 두면 `ci.yml:68` 이 워크플로 수정 없이 자동으로 게이트한다.

### 차트 축 선형성만 진짜 대체가 필요하다

프로토타입은 인라인 SVG 라 라벨↔y좌표 공선성을 1.6px 이내로 쟀다. React 는 다르다. **P1 에서 차트가 있는 곳은 `/dashboard` 와 `/trading` 둘뿐이고 둘 다 lightweight-charts = 캔버스**라 DOM 으로 축을 못 읽는다(`/backtests` 와 `/trades` 는 차트 0건, 실측 확인).

→ 축 자체 대신 **축 설정을 단위 테스트로 고정**한다. `priceScale.mode` 가 로그·퍼센트가 아님, 포매터가 배율을 곱하지 않음. **BL-407 이 정확히 이 부류의 버그였다**(lwc v4 `PercentageFormatter` ×100 부재 + precision 양자화). 회귀 가치가 이미 실증됐다.

recharts(SVG)는 공선성 검사가 가능하지만 P1 범위에 recharts 차트가 0개라 이번엔 만들지 않는다.

### allowlist ratchet 을 쓰는 이유

가드를 도입하는 순간 기존 위반이 CI 를 빨갛게 만든다. 두 선택지 중 ratchet 을 골랐다.

- (기각) 가드 + 위반 전량 교정을 한 PR 로 — PR 이 리뷰 불가능하게 커진다
- (채택) 알려진 위반을 allowlist 로 고정하고 슬라이스마다 줄인다 — 백엔드가 이미 쓰는 패턴이다(`ci.yml:125-137` `--cov-fail-under=90`). allowlist 길이가 곧 진척 지표가 되고 새 위반은 즉시 빨개진다

### 위생 메타테스트는 생략 불가

파일 인벤토리가 조용히 비면 가드는 영원히 그린이다. `no-internal-ids.test.ts` 가 강한 형태를 갖고 있으니 그대로 쓴다(파일 수 범위 + 핵심 라우트 명시 열거). 반대 선례도 레포에 있다 — `ci.yml:55-65` 의 훅 grep 게이트는 위생 검사가 없어 `src/` 이름만 바뀌어도 조용히 통과한다.

---

## 슬라이스 순서의 근거

**S0 검사 장치가 먼저.** 안전망 없이 191파일 토큰 리네임에 들어가면 `chart-tokens.ts` 가 fallback 으로 떨어져 런타임 에러 없이 색만 틀린다. 가장 탐지하기 어려운 회귀다. 방법론 §7.1 baseline preflight 의 이행이기도 하다.

**캘리브레이션을 React 보다 먼저.** 새 spec 을 프로토타입 17벌(known PASS)에 먼저 돌려 같은 PASS 를 재현한다. 함정 #4 의 정확한 이행이며, 지난 세션에 이 절차로 검사기 자체 버그 4개를 잡았다.

**화면은 작은 것부터.** `/backtests`(528) → `/trades`(1,107) → `/dashboard`(409, 4 slice 횡단 + 차트) → `/trading`(4,269). 첫 화면에서 시맨틱 CSS 사용 패턴을 확립하고 나머지가 따르게 한다. `/backtests` 를 첫 화면으로 고른 결정적 이유는 **유일하게 서버 prefetch + HydrationBoundary 를 쓰기 때문**이다(레포 전체에서 이 패턴은 `backtests/page.tsx` 와 `strategies/page.tsx:79` 둘뿐). 그 패턴을 깨지 않는 이식 방법을 여기서 확정한다.

---

## 셸에 대한 재해석

핸드오프는 "`sidebarOpen` 이 뷰포트를 안 보고 데스크톱 토글 UI 도 없다"를 고칠 문제로 적었다. 실측하니 **고칠 게 아니라 지울 것**이었다.

- **프로토타입의 1024px 레일은 순수 CSS 다.** `:root { --sidebar-w: 64px }` + 라벨 `display:none`. JS 뷰포트 로직이 필요 없다.
- `sidebarOpen` 은 **런타임 상수 `true`** 다. `setSidebarOpen` 호출자 0건, `toggleSidebar` 는 `dashboard-header.tsx:28-29` 에서 `void` 로 버려진다. 접힌 상태 CSS 분기는 전부 도달 불가 코드다.

따라서 `ui-store.ts` 의 3개 API 와 헤더의 죽은 prop 2개를 삭제하고 CSS 미디어쿼리로 대체한다. 브레이크포인트 픽셀값(md 768 / lg 1024)은 이미 프로토타입과 일치한다.

---

## 알아 둘 함정

지난 세션에서 실제로 데인 것들과 이번에 새로 확인한 것이다.

1. **grep 만으로 판정하지 않는다.** em-dash 원시 grep 은 1,461건인데 대부분 주석이고 `"—"` 플레이스홀더 113건은 정당하다. 주석을 공백 치환한 뒤 노출 마크업만 검사해야 한다.
2. **에이전트 자기보고를 믿지 않는다.** 판정은 명령 출력에 건다. 이번에도 핸드오프의 "13/14 일치" 를 직접 대조해 5건 불일치를 찾았다.
3. **검사기는 known-good 산출물에 먼저 돌린다.**
4. **파일 단위 검증 통과 ≠ 전체 정합.** 프로토타입 17벌이 개별 통과 후 교차 감사에서 49건(BLOCKER 3)이 나왔다. React 에서는 **컴포넌트 경계**에서 같은 일이 일어난다. S9 가 그 대응이다.
5. **CI 가 셸·네비 회귀를 못 잡는다.** E2E 58케이스 중 CI 는 **4케이스만** 돈다(`smoke.spec.ts` 3 + `live-smoke` 1). authed 54케이스는 로컬 전용이라 슬라이스마다 로컬 실행 출력을 PR 에 붙여야 한다.
6. **프론트엔드 커버리지 임계가 없다.** 리디자인 중 테스트를 지워도 CI 가 침묵한다. 삭제한 테스트는 PR 본문에 명시한다.
7. **React Compiler 는 활성화돼 있지 않다.** `next.config.ts` 에 플래그가 없고 `eslint-plugin-react-compiler` 는 lint 룰로만 있다. "컴파일러가 자동 메모이즈한다"는 전제로 판단하면 안 된다(BL-407 세션에서 이미 거짓 전제로 확인된 사항).
8. **공유 프리미티브 blast radius.** `button`(16 디렉터리) · `skeleton`(17) · `input`(7) 은 P1 밖 라우트와 랜딩까지 닿고, `tick-ruler` 와 `pnl-tape` 는 **공개 마케팅 페이지**까지 닿는다. 프리미티브는 토큰 층에서만 건드리고 마크업 재작성은 P1 라우트 안에서 한다.

---

## 라이트 팔레트를 B2 로 정한 이유

근거 전문은 [`light-palette-trilemma.md`](./light-palette-trilemma.md). 여기에는 판단만 남긴다.

**핸드오프의 트릴레마 표가 두 군데 틀렸다.** 프로토타입 안의 감사표가 `--copper` 를 6.26(실측 7.53) ·
`--bull` 을 6.33(실측 9.99)으로 적고 있었다. 색상별로 일정한 배율의 계산기 오차이고 색값 자체는 맞다.
**이 오차가 "라이트 초록이 9.99 로 지나치게 어둡다"는 쟁점을 기록에서 지우고 있었다.**

**A 안은 ② 를 만족하지 않았다.** 핸드오프 표는 A 가 bull/bear 상호 1.57 을 만족한다고 적었지만
그건 텍스트 토큰 얘기고, 채움 3색은 L\* 56.2~56.3 으로 **완전 등광도(상호 1.00)** 였다. 각 채움을
그래픽 하한 3.0 에 독립 최적화한 결과다. 차트 범례의 자산곡선 키와 낙폭 키가 서로 구분되지 않는다.
즉 A 는 B1 이 기각당한 결함을 텍스트에서 그래픽으로 옮겨 놓은 것이었다.

**결정적이었던 것은 픽셀 실측이다.** 4안 중 어떤 두 개를 비교해도 최대 **0.61%**, 코크핏에서
A 와 A′ 는 **픽셀 0개** 차이였다. 사용자가 "다 비슷해 보인다"고 한 것이 정확한 관찰이었다.
**이걸 안을 만들기 전에 쟀어야 했다.** 트릴레마의 무게를 과대평가한 채로 4벌을 만들고 사용자에게
비교를 시켰다. 다음에 비슷한 판단이 오면 **차이의 크기를 먼저 실측한다.**

**B2 를 고른 근거.** `design-taste-frontend` 의 §4.2 COLOR CONSISTENCY LOCK 이 `mandatory` 이고
A/A′ 가 이를 위반한다. B1 은 모든 색을 캐논 하한에 정렬한 탓에 팔레트 전체가 등광도가 되어
위계가 사라지고(스프레드 1.01) 중첩 표면 canon 위반이 37 로 다크(33)보다 나빠졌다.
포기한 것은 ④ 생동감이며, **스킬에는 ④ 에 해당하는 조항이 없다** — 채점 85점이 판정이 아니라
참고치인 이유다. 실체는 차트선 하나 색이고 화면의 0.29% 다.

**채움 토큰은 값만 맞추지 않고 제거했다.** `--copper-fill` / `--bull-fill` / `--bear-fill` 를 같은 값으로
남겨 두면 나중에 한쪽만 바뀌어 LOCK 이 조용히 깨진다. 소비처 8곳(copper 4 · bull 1 · bear 3)을
텍스트 토큰으로 환원했다. 이 8이라는 수는 처음에 7로 잘못 셌고 생성기의 단언이 잡아냈다.

**`td.num` 명시도 결함은 이 시점에 고쳤다.** `td.num`(0,2,3)이 `.pos`/`.neg`(0,1,0)를 이겨 표의
손익 색이 두 테마 모두 죽어 있었다. 팔레트를 눈으로 고르는데 P&L 이 가장 조밀한 표면이 무채색으로
렌더되면 틀린 것을 보고 고르게 된다. **단 지금은 라이트 2벌에만 들어가 있고 `_kit.html` 과 다크
17벌에는 없다. S2 가 반영해야 한다.**

**preflight 실패는 건드리지 않았다.** `C19-dark` 와 `C16-kitdrift` 를 내 수정이 만든 것으로 오인해
`_kit.html` 을 고칠 뻔했다. `git show HEAD:` 로 원본을 꺼내 대조하니 **둘 다 수정 이전부터 나던
항목**이었다. 라이트는 토큰 블록이 공용 CSS 영역 안에 있어 `_kit.html` 과 필연적으로 어긋난다.
`_kit.html` 을 고쳤다면 다크 17벌이 전부 kitdrift 로 깨졌을 것이다.

---

## ★S1a 를 물 함정 — Turbopack CSS 캐시가 서버 재기동을 넘어 산다

S0 slice 2 반증 중에 실제로 데였다. **거짓 결함을 사용자에게 보고할 뻔했다.**

경위. dev 서버가 뜬 상태에서 `globals.css` 의 `--chart-dd-line` 을 리네임해 반증한 뒤
`cp` 로 원본을 되돌렸다. 디스크는 `git diff` 0 으로 깨끗했는데, 브라우저가 받는
컴파일 CSS 에는 **리네임된 이름이 그대로 남아** 런타임 가드가 계속 빨갰다.

시도한 것과 결과.

| 시도                                   | 결과                                  |
| -------------------------------------- | ------------------------------------- |
| `touch globals.css` (mtime 만 변경)    | 무효                                  |
| dev 서버 완전 재기동                   | **무효** — `.next` 캐시가 살아남는다  |
| `rm -rf .next`                         | 권한 차단                             |
| **파일 내용 변경(주석 1줄 추가/삭제)** | **유효** — 해시가 바뀌어야 무효화된다 |

원인은 복구 방식이었다. `cp` 로 되돌리면 내용이 원본과 **동일**해져 Turbopack 이
"바뀐 것 없음"으로 판단하고 stale 청크를 계속 낸다.

**S1a 수칙.**

1. `globals.css` 를 고친 뒤 런타임 검사가 이상하면 **앱을 의심하기 전에 컴파일 CSS 를 먼저 확인한다.**
   `page.on('response')` 로 `.css` 응답을 받아 실제 내려온 토큰을 읽는 것이 가장 빠르다.
2. 되돌릴 때 `cp`/`git checkout` 만으로 끝내지 말고 **내용 변경(주석 추가 후 삭제)으로 재컴파일을 강제**한다.
3. 검사기가 빨갛다고 곧바로 결함으로 보고하지 않는다. 이번에도 "정적 통과 · 런타임 실패" 라는
   모순이 신호였는데, 하마터면 앱 버그로 적을 뻔했다.

핸드오프 함정 #8("캐시. 열린 탭은 no-store 로도 안 막힌다")의 React 판이다. 그쪽은 브라우저
캐시였고 이쪽은 **빌드 캐시**라 더 질기다.

---

## S0 종료 — 검사 장치 이식 결과 (2026-07-20)

계획대로 `runtime-check.mjs` 를 "다시 겨눴다". 착수 전 `node runtime-check.mjs` = **17/17 PASS** 를 직접 재현하고 시작했다.

### 감사 코어를 공유 모듈로 뽑았다

`e2e/design-canon-audit.ts` = `AUDIT`(:18-110) · `MOTION_AUDIT` · 포커스링 프로브 · 4폭 이식. **캘리브레이션 spec 과 앱 spec 이 같은 모듈을 import 한다** — 사본을 두 벌 두면 "프로토타입 17/17 재현"이 앱에 대해 아무것도 증명하지 못하기 때문이다. 핸드오프가 적은 `design-canon.spec.ts` 대신 3분할(모듈 + `design-canon-calibration` + `authed-canon-p1`)로 갔다. 이유는 **`playwright.config.ts:63` 의 testMatch 가 `/design-canon-.*\.spec\.ts$/` 라 하이픈이 필수** — `design-canon.spec.ts` 는 매치되지 않아 0케이스로 조용히 통과할 자리였다.

### 캘리브레이션이 먼저다 (함정 #4 이행)

`design-canon-calibration.spec.ts` 로 프로토타입 17벌 + 라이트 2벌을 `file://` 로 감사 → **22 passed**, canon 카운트가 기준선과 전부 정확 일치. 반증 3종(임계 5.82→6.5 / width:3000px 주입 / 인벤토리 글롭 어긋냄)으로 가드가 실제로 잡는 것을 확인하고 되돌렸다.

### 정적 검사는 주석 인지 스캐너가 핵심

`design-canon-source.test.ts` — 반경 21 · hex 6 · 노출 산문 em-dash 100 을 per-file 정확일치 래칫으로 동결. **calibration 이 grep 함정을 실증했다.** raw hex 58 → 주석 제거 44 → `brand-palette.ts`(정의 계층) 제외 6. `PR #171`(3자리 hex 오검)·주석 안 hex/em-dash 가 전부 걸러졌다. ★em-dash 100 은 **회귀 동결이지 슬롭 판정이 아니다** — `unsupported-builtin-hints.ts` 29(hint 데이터)·`privacy` 6(정의 목록)·`kill-switch-modal` 3(S8 삭제예정) 등 정당/사멸 케이스가 섞여 있다. 감축은 S1b ④ 의 사람 판단.

### React baseline — 백엔드를 직접 띄워야 했다

★함정 2건 실측.

1. **포트 8000 을 cookmark(냉파) 프로젝트가 점유** 중이었다. `openapi.json` title `냉파 backend`·경로 2개로 판별. 리로드 수퍼바이저 PID 20022 를 정리해 비웠다.
2. **backend `.env.local` 의 DATABASE_URL 이 5433(ffwpu-postgres, 남의 DB)을 가리킨다.** QuantBridge DB 는 **5436**(`quantbridge-db`). `make be` 를 그냥 쓰면 남의 DB 에 붙는다 (메모리 `project_full_inspection_20260601` 기록 함정 재확인). `DATABASE_URL/TIMESCALE_URL=5436 · REDIS=6380 · FRONTEND_URL=3000` 오버라이드로 기동.

채워진 baseline(백테스트 6·체결 최대 585·거래소 1) 에서 P1 4라우트를 감사해 allowlist 확정. **nextjs-portal(next dev 오버레이)이 포커스 감사에서 거짓 결함**을 내 audit 코어에서 tag 제외하고 캘리브레이션 22 재확인. 실제 앱 결함 = backtests 375px overflow · trades 입력 3개 포커스링 · trading 포커스가능 div. **canon 은 게이트 아님**(지표).

### 고아 spec — 실행하니 stale

`sprint55-optimizer-bayesian` 을 배선해 돌리니 폼 UX 가 통째로 바뀌어(텍스트 `backtest_id` → `useBacktests` 드롭다운 피커, P1-8/S7-B) 첫 상호작용에서 타임아웃. `/optimizer` 는 P1 밖. 사용자 결정 = **test.skip + TODO**, 배선 되돌림. optimizer 이식 때 현행 UX 로 재작성.

### CI 배선

`pnpm e2e:design-canon` 을 `ci.yml` e2e 잡에 추가(병행안). 캘리브레이션(file://) + 공개 라우트 런타임 = CI, authed P1 = 로컬. `vercel-react-best-practices` 는 S0 이 React 런타임 코드 0 이라 보류 → S1a.

---

## 변경 이력

- **2026-07-20** — 계획 수립. 베이스라인 실측 3종 + 핸드오프 전제 독립 검증(색 5건 불일치 발견) + 사용자 인터뷰 4Q + 미해결 6건 처리 + 슬라이스 S0~S9 + 검사 장치 설계. 코드 수정 없음.
- **2026-07-20** — 라이트 팔레트 **B2 확정**. 핸드오프 전제 2건 반증(감사표 수치 오류 · A 안의 채움 등광도) + A′ 도출 + 4안 프로토타입 + 픽셀 실측(최대 0.61%) + 스킬 채점 → B2. 채움 토큰 제거 · `td.num` 교정 · 감사 블록 재계산 · 기각안 6벌 삭제. 라이트 2/2 · 다크 17/17 PASS.
- **2026-07-20** — **S0 종료.** 감사 코어 공유 모듈 이식(`design-canon-audit.ts`) + 캘리브레이션 22 재현 + 정적 검사 3종 래칫 + React P1 4라우트 baseline + CI 배선 + 고아 spec skip. 반증 7종 통과. 5 커밋(`97941e6`~`e8fc657`). 다음 = S1a.
- **2026-07-20 (실행 세션)** — **S2/S5 되돌림 사유 = 순서 위반 (사용자 확인).** 구현 내용은 유효, 정순 재진행, `f0715dc`·`57c3ec9` 참조 허용. baseline 3종 재재현(856/27/5 일치). codex 플랜 검증 5건 반영 — ① 리네임 시 직접 `var()` 소비처 전수 sweep 의무(`pnl-tape.tsx:68` 등) + `--card-3→--accent` [가정] 검증, ② S1a 게이트에 Tailwind 유틸 4종 computed-style 브라우저 검사 신설(`@theme inline` 파손 감지), ③ **S8 을 병렬조에서 제외**(S6∥S7 → S8 직렬 — `dashboard-cockpit.tsx:23-36` 크로스라우트 import 가 S8 소유 파일과 겹침), ④ authed 게이트 확인 시 `skipped=0` 동시 확인(`authed-canon-p1.spec.ts:101` skip 경로), ⑤ 본 문서 동기화.
- **2026-07-21** — **S9 종료 (마지막 슬라이스).** 6 커밋(`e0e1ee0`~`2601805`). 게이트 전종 그린(905 tests · tsc · lint · build · design-canon 29 · authed-canon-p1 5).
  - **교차 감사 결과 = 사실 모순 0건.** 파생 `/dashboard` §03 은 원장 `/backtests` 와 같은 `GET /api/v1/backtests` `.total`(limit 무관)을 읽고, 상태 라벨·칩 톤은 4화면 모두 S4 SSOT + `CHIP_TONE_CLASS` 를 경유한다(확장한 raw-enum 가드가 강제). nav-count 주문·세션 수도 동일 소스. **원장이 이길 상황(파생이 어긋남)이 발생하지 않았다** — S1a~S8 이 공유 SSOT + 공유 API 층으로 정합을 유지했기 때문. 유일한 형식 불일치 = live-session-detail/list 의 `toLocaleString`(vs C 이식 `formatDateTime`) → §05 미이식 층(3e) 이연.
  - **★공유 프리미티브 규칙이 반경 정리를 거의 무효화했다.** P1 4라우트+셸은 시맨틱 CSS(`.card`/`.btn` → `var(--r)`)만 소비해 마크업 반경 리터럴이 **0건**이다. 기록된 "rounded 6/16/5" 는 전량 P1 밖(waitlist·share·error·maintenance·onboarding·strategies) + 공용 UI 프리미티브(badge 1건만 정리). 즉 잔여 반경은 "P1 이식 대상"이 아니라 "P1 밖 라우트 이식 때 각자 정리할 몫"이다.
  - **StateBox 추출 판단.** `.state-box`(에러/빈) 골격이 S5·S7·S8 에서 10+회 반복 → `components/state-box.tsx` 로 추출. 인터페이스는 tone(neutral/failed)→role(status/alert)+클래스 파생 1개로 얕지 않게. DOM 바이트 보존으로 소비처 테스트 무변경. **미이관 잔여**(trades 표 S6 · session-diagnostics · exchange-accounts · kill-switch · live-session-table · route error.tsx)는 구조 편차/저반복이라 위험 대비 이득이 낮아 이연(remaining). InfoIcon 은 3벌 바이트 동일 → `components/info-icon.tsx`.
  - **가드 확장 스코프 결정.** "dashboard/·trading/ 라우트" = 두 라우트가 실제 렌더하는 트리로 해석 → `_components` + `features/trading/components` + `features/live-sessions/components` 추가. 확장 직후 RED(live-session-detail `{ev.status}` 1건만) 재현 = 반증 성공 후 SSOT 이관으로 그린.
  - **503 orphan 삭제.** MaintenanceCard/ProgressFill 프로덕션 소비자 0(not-found=404·error=500·maintenance=Illustration만). radius 래칫 4→2 cascade.

## codex 최종 누적 검증 (2026-07-21, S1b~S9 diff)

반증 축 7개 중 **래칫 우회(A)·훅 규칙(C)·테스트 정직성(F)은 반증 실패** — 게이트 체계가 유효했다. 발견 6건 전부 코드 대조로 사실 확인 후 픽스 (`0635e3c`~`41380a0`).

- **정직성(B) 4건** — ① backtest 상태 롤업이 페이지 집계를 전역처럼 표시(+cancelled 누락) ② 코크핏이 RQ 오류를 0/빈으로 평탄화 ("거래소 미등록"·"미해결 이벤트 없음"이 오류 시 거짓) → `StatValue` 프리미티브(오류=확인 불가) ③ "활성·비활성 전체 세션" 문구가 거짓 (API 는 is_active 만 반환) ④ 존재하지 않는 `GET /trading/sessions/{id}/positions·503` 을 실호출처럼 렌더 — 캐논 §6 표기보다 **실제 API 부재의 정직성이 우선**.
- **toast 중복(G)** — 셸 nav 배지 `useOrders(1)` 이 전환 toast 훅이라 중복 발화 → `notifyTransitions` opt-out.
- **잔존 주석(E)** — 삭제된 503 variant·ETA 충실도 주장 주석 갱신.
- **미픽스 잔여** — 전역 :focus-visible 의 P1 밖 이중 링 (MINOR, 캐논 전역 규칙 vs P1 한정 = 사용자 판단) · kpi-pnl 오류 표기 (aggregate 훅 시그니처 변경 필요).

## 변경 이력 (append)

- **2026-07-21** — **S1a~S9 완주 + codex 3회 검증.** 최종 게이트: vitest 164/904 · canon 29 · authed 5 · allowlist 전부 0. 상세는 HANDOFF 5판 §0.5.

---

## 잔여 완주 세션 (2026-07-21 착수) — 플랜 단계 결정 기록

### 사용자 확정 2건 (플랜 모드 AskUserQuestion, 실측 근거 동봉)

1. **`strategy.backtest_count` = 열 미렌더.** 실측: `StrategyResponseSchema` 에 대응 필드 자체가 0건(완료/전체 정의 이전 문제) + 원장 §4.2 가 스스로 "미해소 — 새 화면은 이 열을 다시 인쇄하지 않는 쪽이 기본"이라 명시. §4.9 보수 원칙 그대로. FE 파생 집계(N+1)·백엔드 필드 신설(범위 밖 수술)은 기각.
2. **OKX = FE 등록 폼에서 제거.** 실측: DB 5436 에서 okx 거래소 계정 0건·주문 0건 — "OKX 데모로 실제 주문이 오간 적" 없음. 캐논(Bybit 단일)과 화면 카피가 이김. 제거 범위 = `features/trading/schemas.ts:71` enum + `register-exchange-account-dialog.tsx` SelectItem/passphrase 게이팅 + superRefine 분기 + `zod-v4-resolver.ts:9` 주석. **백엔드 불변**(git 가역). 마케팅 화면의 OKX 로드맵 표기(§4.8 5행 표)는 유지. terminology-ssot §6-4 해소.

### 플랜 단계 실측이 교정한 것

- **HANDOFF §3-1 "반경/stale-var 15파일" 은 부정확.** 실측 = stale `var(--radius…,폴백)` 콤마 폴백 **4파일 5건**(전부 strategies 슬라이스: parse-result-panel 2 · step-code 1 · parse-panel 1 · editor-monaco-wrapper 1) + 리터럴 반경은 P1 밖 **50+파일**. 후자는 각 화면 이식 시 시맨틱 CSS 소비로 자연 소멸이 원칙(S9 실증), 화면 밖 잔여만 W-final sweep.
- **baseline 재현 부분 실패의 원인 = Turbopack stale 캐시 (코드 회귀 아님).** dev 서버 컴파일 CSS 에 `--text-muted:#7a828c`(커밋 소스에 없는 구 다크 값) 실측. `/` contrast 2 · trades focus 2 · 전 라우트 canon=2 가 전부 이것으로 설명. 교훈: **baseline 3종 동시 발사 금지 — 게이트 재현은 항상 직렬** (동시 부하 시 authed 4 FAIL 위양성 실측).
- **fixture 갭 1건: optimizer 완료 run 0** (유일 run = GRID_SEARCH FAILED). /optimizer/[id] 완료 상태 게이트 침묵 skip 방지 위해 W0 에서 실제 엔진으로 grid search 1건 완주 시딩.
- **/pricing 은 현재 `redirect("/#pricing")` 7줄** — screen-16 이식 시 실페이지 신설 + 리다이렉트 제거 + public spec/live-smoke 편입.
- **Clerk sign-in**: colorPrimary 는 `clerk-theme-bridge.tsx` 단일 소스(하드코딩 금지 주석 실존). 이식 범위 = split-screen-shell + appearance 토큰 정렬. Clerk 내부 DOM 재구성 불가.
- **`/backtests/[id]` 는 lwc + recharts 5플롯 이중 스택.** recharts 유지(교체 금지), SVG 공선성 검사 신설은 W2 에서 반증 절차로 검토.

### codex 플랜 검증 (W0, 8건 — BLOCKER 0 · MAJOR 6 · MINOR 2, 전건 코드 대조 후 처분)

- **채택 6.** ① G/H 가 `app/_components/error-*` 를 공유(3파일 import 확인) → error-\* 는 H 로 명시 배정. ② `/backtests/[id]` authed 케이스는 완료 상태 행만 선택 + fixture 부재 시 skip 아닌 expect FAIL + ReportShell 렌더 대기. ③ coverage 매트릭스 신설(checklist 표) — canon 29→33 · authed 5→14 추적. ④ CI 는 authed 캐논을 안 돌므로 PR 본문에 직렬 e2e:authed 로그 + --list 증빙 의무. ⑤ no-raw-enum 가드는 status/state 만 감시(확인) → W1 에서 kind/direction/objective_metric/prior/phase + 템플릿 보간 확장, 유형별 RED 반증. ⑥ OKX 제거 시 register-exchange-account-dialog.test 의 okx 케이스 파손 → 테스트 정리 + bybit 단일/passphrase:null 회귀 테스트 교체를 W3-F 범위에 포함.
- **교정 채택 1.** ⑦ ~~share 가 report 컴포넌트 공유~~ — 실측 반증: share 페이지는 스키마 + 자체 `_components` 만 import. 플랜의 blast radius 전제를 삭제하고 share 는 전역 토큰 계약 관점만 유지.
- **부분 채택 1.** ⑧ Tab 30회 한계 + box-shadow 링 인정 — **감사 코어는 불변으로 둔다.** 코어를 바꾸면 S0 캘리브레이션(프로토타입 22 PASS 재현)의 동등성이 깨진다. 대신 대형 신규 화면 워커에 30탭 밖 핵심 인터랙티브 요소 포커스 링 수동 확인 + 요소 목록 falsifiable 보고를 의무화.

### 통합(cherry-pick) 루틴에서 실측한 함정 3건 (2026-07-21, W2~C 통합)

1. **cherry-pick 도 Turbopack stale 을 유발한다.** W2 통합 직후 `/backtests/:id` 가 contrast=4 로 FAIL — 컴파일 CSS 가 여전히 구 `--muted-foreground #7a828c` 를 서빙(소스는 `#8b939c`). 서버 재기동으로도 무효. **확정 루틴 = 서버 정지 → globals.css 캐시 무효화 주석(r 카운터) 갱신 → 기동 → 컴파일 CSS 에 신규 값/클래스 curl 확인 → 게이트.** 슬라이스 통합마다 의무.
2. **CSS 주석 안 `*/` 연쇄 = 주석 조기 종결 → 전 라우트 500.** W3-B 블록 주석의 `.trust-*/` 가 PostCSS 파스를 깨뜨렸다(에러 좌표는 생성 코드 기준 8497줄이라 소스 대조가 오도됨). 워커 게이트에 build/컴파일 확인이 없어 통과 — 이후 웨이브부터 주석 `*/` 스캔 + 자기 포트 dev 200 확인을 워커 게이트에 추가.
3. **fresh 서버 첫 방문(콜드 컴파일) 중 canon 감사는 콘솔/발견 flake 를 낸다.** /optimizer console=10 → 단독 재실행 0. 판정은 warm 재실행으로.

### 2차 웨이브(A/D/E/F/G + FIX + 부채) 통합 판단 기록 (2026-07-21)

- **G(마케팅) 는 net-diff squash 로 통합.** 워커 7커밋 중간에 prettier 전체 재포맷 사고→되돌림 커밋이 껴 있어 per-commit 재생이 오염을 재재생한다 — `git diff base..tip` 3-way 적용 + squash 1커밋. kit-port 무결성 테스트가 재포맷 잔재 0 을 증명.
- **감사기 WCAG 1.4.3 비활성 컨트롤 예외는 hard 축만.** /trading 의 disabled `.btn-primary`(opacity .5) 텍스트 3.21:1 이 하드 실패로 잡혔으나 WCAG 1.4.3 은 비활성 컨트롤을 대비 요구에서 제외한다. canon(soft) 까지 빼면 프로토타입 screen-05 의 disabled 버튼이 canon-7 에서 2건을 차지해 **캘리브레이션 기준선이 깨진다** — 실측으로 증명하고 hard 축만 예외. 반증 2종(비활성 제외 작동 + 활성 저대비는 여전히 검출) 통과.
- **콘솔 429 는 캐논 위반이 아니다.** 전체 authed 스위트 연속 실행이 백엔드 레이트리밋을 쳐 "Failed to load resource: 429" 가 콘솔 하드 실패로 위양. EXPECTED_CONSOLE 에 429 예외 추가 (p1 + remaining 양쪽).
- **정직 미렌더 추가 사례(전부 워커 §4.9 보고).** orders: 브로커/모의 출처 배지(스키마 무필드)·취소 액션 열(취소 API 부재 — 가짜 어포던스 금지). backtests/new: ETA·예상 수수료 휴리스틱·실시간 배지 제거(가짜 라이브). onboarding step-4: 스키마 backed 3지표만.
- **부채 마감 실측이 S9 판단을 뒤집었다.** S9 가 "구조 편차라 이연"한 StateBox 6곳이 **인터페이스 확장 0 으로 전량 이관 가능**했다(children 슬롯이 흡수) — 9파일 13곳, DOM 바이트 보존. 이연 사유가 프리미티브 성숙(className prop 추가)으로 소멸한 사례.
- **잔여 관측 3종(후속 판단).** hand-rolled state-box 3건(trade-ledger-table:71·parse-result-panel:205·new-strategy-wizard:463 — 시각 동일) · backtest-history-card.tsx = dead(소비자 0) · KPI 미터 미렌더(W2 결정)와 히트맵 기본 접힘(C 결정)은 프로토타입 대비 의도적 편차로 사용자 보고 대상.

### W-final 마감 기록 (2026-07-21)

- **교차 감사 8건**: 7픽스(title.template '%s · QuantBridge' 통일+누락 3라우트 · 코크핏 §03 영문 잔재 SSOT 화 · Live Session 영문 혼입 · woosung 하드코딩 칩 제거 · 로컬 tz 잔재 → UTC 포맷터 · hand-rolled state-box 3건 이관) + 1기결(주문 nav-count = 전체+툴팁, S9 판정 유지 — 캐논 §4.6 과의 차이는 문서 소관).
- **codex 최종 8건**: 7픽스(429 필터를 리소스 메시지로 좁힘 — pageerror 429 는 계속 하드 · tab-webhook 테스트 4행동 복구 · authed spec 침묵 skip → 시끄러운 사전조건 · 리포트 데모 CTA /onboarding→/trading · '3 x 3' 고정 표기 제거 · globals 중복/죽은 규칙 정리) + 1기각(labels 미소비 export = terminology-ssot §4 전문 그대로 정책의 의도 산물, 유지).
- **레거시 authed 스펙 수리**: 8스펙 12+ 실패 전부 테스트측 staleness(구 5탭 IA·구 카피·z.uuid 위반 mock id·셀렉터 다중 매칭). 앱 결함 0. KS resolve un-skip(기능이 이식 중 구현돼 skip 사유 소멸) → **전체 56 passed / 0 failed / 0 skipped**.
- **감사기 결함 2종 수리** (화면이 아니라 자의 결함): ① WCAG 1.4.3 비활성 컨트롤 예외(hard 축만 — canon 까지 빼면 프로토 screen-05 disabled 버튼이 캘리브레이션 기준선을 깬다는 실측으로 스코핑) ② 대비 샘플링을 reduced-motion 정지 상태로 — /trading §05 버튼(.rise 스태거 최말단)이 스위트 문맥에서만 1.11:1 로 결정적 FAIL 하던 knife-edge 는 입장 애니메이션 opacity 램프를 찍던 표본 타이밍 결함. 두 건 모두 캘리브레이션 22 동등성 재현 + 양방향 반증 통과.

### W0 환경 복구·시딩 기록

- stale Turbopack 캐시: globals.css 내용 변경(주석 1줄, `1a8addb`) + 재기동으로 해소. 컴파일 CSS 에 `#8b939c` 존재·`#7a828c` 부재 curl 확인 후 baseline 재현 (vitest 164/904 · canon 29 · authed 5).
- ★fixture 함정 재확인: `FixtureProvider` 는 `{root}/{symbol}_{tf}.csv` 에 심볼 슬래시가 경로로 들어간다 (`BTC/USDT` → `root/BTC/USDT_1h.csv`). 레포 커밋본은 평면 `BTCUSDT_1h.csv` 뿐이라 그대로는 miss — **스크래치패드에 `ohlcv-root/BTC/USDT_1h.csv` 심링크 트리를 만들어 worker 에 `OHLCV_FIXTURE_ROOT` 절대경로로 주입** (레포 오염 0). celery worker 는 `-Q celery,optimizer_heavy` (optimizer.run 라우팅) + DATABASE_URL 5436 오버라이드.
- 옵티마이저 완료 run 시딩: 실 API(`POST /api/v1/optimizer/runs/grid-search`, Clerk JWT 는 storageState→`window.Clerk.session.getToken()`) → grid 2x2, run `47ab18b7` **COMPLETED** (result 1.3KB). 실패 상태 fixture 도 자연 확보(`776ad44a` FAILED — fixture miss 시절).

### MCP playwright 실브라우저 검증 (2026-07-22, PR #464 위 후속 브랜치)

- **계기**: 기존 게이트는 전부 Playwright CLI(e2e·canon) — 실브라우저 대화형(MCP) 육안 검증 기록이 없어, 이식 화면 15+ 를 라이트·다크·모바일(390px)로 실주행. 세션 주입은 e2e storageState 쿠키 재사용(전부 non-HttpOnly).
- **결함 2건 발견·수정** (둘 다 CLI 게이트의 사각).
  1. `/optimizer/:id` grid 완료 화면 섹션 번호 03 중복 — 03 파라미터 안정성 + 03 OOS 검증. OOS 는 grid 에서 04, bayesian/genetic 에선(안정성 섹션 부재) 03 이어야 해 `sectionNum` prop 주입으로 동적화. 유닛 회귀 2건 추가(순차·유일 ["01","02","03","04"]). CLI 사각 사유: canon 은 하드페일 카운트만 대조, 유닛은 번호를 단언하지 않았다.
  2. `.topbar` 배경 `rgba(11,13,15,.86)` 하드코딩 — 라이트 테마에서 다크 바 위 라이트용 crumbs 잉크(#171a1e) = **1.1:1 판독 불가** (데스크탑·모바일 동일). `--topbar-bg` 토큰(:root/.dark) 신설로 해소. CLI 사각 사유: authed canon 은 다크 기본으로만 주행, public 라이트 감사엔 `.topbar` 셸이 없다. kit-port 무결성은 allowlist 2호(topbar 토큰화, \_kit.html 은 다크 단일 팔레트라 하드코딩이 정당) 등록 — silent no-op 방지 assertion 동반.
- **결함 아님 판정 3건**: 영어 Beta 배너 = Sprint 11 geo-block(미/EU 대상 의도적 영어, 한국어 재스킨된 것은 legal-notice-banner) · 404 콘솔 에러 2건 = 404 리소스 상태 로그 자체 · recharts "width(-1)" 경고 = ResponsiveContainer 초기 마운트 노이즈(기록된 비결정 사유와 동일 계열).
- **환경 함정 재확인**: 장수 dev 서버가 `.strat-name`/`.strat-id` 룰이 아예 없는 stale CSS 를 서빙(이름+ID 한 덩어리 렌더로 위장) — r 주석 루틴으로 즉시 해소. **MCP 육안 검증도 시작 전 stale CSS 무효화가 선행 의무.**
- **게이트 재현(수정 후)**: vitest 169/965 · tsc 0 · lint 0 · design-canon 32 · e2e:authed 56/0/0.

### D0 문서 토폴로지 재수확 (2026-07-23, PR #461 폐기 후속)

- **계기**: 이식 착수 시점(2026-07-20)에 열린 PR #461 이 유일한 open PR 로 남아 있었다. 21커밋 중 17커밋(S0/S2/S5)은 그 뒤 #463·#464 가 squash 로 더 진전된 형태를 main 에 넣어 **이미 죽었고**, 파일 대조로 확인했다. 고유분은 D0 문서 4커밋뿐. 그런데 그 문서의 전제("이식 3/11 진행 중")가 완주로 뒤집혀 그대로 머지하면 새 거짓 문서가 된다 → **#461 close, 유효분만 main 기준으로 재작성**.
- **#461 서술과 실측이 갈린 지점 3건** (지도를 옮기지 않고 다시 쓴 이유).
  1. 구세대 프로토타입 살아있는 인용 = **7건 아닌 4곳**. `INTERACTION_SPEC.md` 인용은 **0건**이 됐다 — 이식이 `kill-switch-modal.tsx` 등을 재작성했다.
  2. `schemas.ts:71` OKX 잔존 = **이미 해소**(`z.enum(["bybit"])`). W3-F 부채 처리분.
  3. "1세대 vs 2세대 중 어느 쪽을 따르나" 프레이밍이 **무효**. `DESIGN.md` §2.1 다크 팔레트가 C 캐논 `variant-c.html` 값과 **일치**한다(#0b0d0f/#101214/#141619/#1a1d21/#e8eaed/#f08c2e). 그래서 S1a 가 리네임 0 으로 끝났다. 둘은 경쟁이 아니라 **층이 다르다** — 토큰 층(DESIGN.md) vs 화면·용어 캐논 층(\_KIT+17벌). 지도를 그 축으로 다시 썼다.
- **★`OBJECTIVE_METRIC_ABBR` 삭제 — 이전 codex 기각과 충돌하지 않는다.** 잔여 완주 세션에서 codex 가 "labels 미소비 export" 를 지적했고 "terminology-ssot §4 전문 그대로가 정책의 의도 산물" 이라며 **기각**했다. 이번 삭제는 그 판정을 뒤집는 게 아니다. 기각 사유는 *미소비*였고, 이번 근거는 _캐논이 폐기한 규칙을 인코딩하고 있다_ 는 별개 사유다(`_KIT.md:532` `abbr="샤프"` 17벌 0건 폐기 · `:534` `수익률` 축약 금지). 그리고 정책("labels.ts = terminology-ssot 거울")을 지키려고 **거울의 원본인 terminology-ssot 의 해당 모듈도 같은 커밋에서 함께 제거**했다. 거울 관계는 유지된다.
- **축약 판정은 지표가 아니라 자리**다 — 좁은 칸이면 축약, 표 헤더·산문이면 완전형(`_KIT.md` §4.10). 지표 단위 3-키 Record 는 그 판정을 구조적으로 잘못 인코딩해서 금지된 `수익률` 축약을 되살린다. 그래서 `Partial<Record<>>` 로 좁히지 않고 매핑 자체를 없앴다.
- **prettier 분리**: `docs/prototypes/README.md` · `INTERACTION_SPEC.md` 는 main 에서 prettier-dirty 라 lint-staged 가 통째로 재포맷한다(#461 이 겪은 386줄 노이즈). 기계 재포맷을 **선행 독립 커밋**으로 빼서 배너 diff 를 읽히게 했다.
