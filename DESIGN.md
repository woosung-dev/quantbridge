# QuantBridge — 디자인 시스템

> **상태:** 확정 — "Precision Instrument" v3
> **일자:** 2026-07-06 (v3 초판, W1 PR-2)
> **구현 SSOT:** `apps/web/src/styles/globals.css` (토큰) + `apps/web/src/lib/brand-palette.ts` (hex 상수, CSS 변수 못 읽는 소비자용) — 두 파일과 본 문서는 항상 같은 커밋에서 동기.

---

## 0. 방향 v3 — "Precision Instrument" (2026-07-06, 본 섹션이 v2 "Terminal Tape"를 supersede)

> 전면 리디자인. 작업 SSOT 였던 `docs/archive/sprints/redesign-precision-instrument/` 는 2026-08-06 문서 대개편에서 삭제됐다 — 원문은 `git show 0f0f0b06:docs/archive/sprints/redesign-precision-instrument/<파일>` 로 연다(태그 `docs-pre-overhaul` — `checklist.md`·`context-notes.md`·`testid-baseline.txt` 3파일). 그 외 `~/.claude/plans/golden-enchanting-teacup.md`. 채택 근거: v2의 웜크림+코퍼 조합이 AI 생성 디자인 기본값 클러스터(웜크림+테라코타)와 인접 → 뉴트럴 전면 교체로 브랜드 확보.

- **컨셉:** QuantBridge = **전략을 정직하게 계측하는 정밀 계측기.** 제품의 영혼(TV-parity·oracle 검증·honesty gate)과 일치하는 시각 언어 — 측정, 교정(calibration), 검증.
- **테마:** **다크 디폴트** (카본/스틸 — 트레이딩 표준, 차트 몰입). 라이트(쿨 페이퍼) 완전 지원, `next-themes` 토글 유지. `enableSystem` 유지 — 기존 사용자 localStorage 선택 우선.
- **정체성:** 뉴트럴 = **쿨 카본/스틸**(웜크림·웜니어블랙 폐기). 액센트 = **시그널 코퍼 유지**(라이트 `#b45309` / 다크 `#f08c2e`) — 브랜드 연속성 + 차트 equity 히어로 시리즈.
- **시그니처 2종 (볼드함은 여기에만, 나머지는 절제):**
  1. **계측 눈금(tick ruler)** — `components/tick-ruler.tsx` + `.qb-ruler-x/-y` + 사이드바 active 노치(`.qb-tick-active`). 구조적 경계에만.
  2. **P&L Tape 모티프 승격** — `components/tape/` (pnl-tape `size:micro|default`, tape-progress, skeleton `variant:"tape"`). 테이블 인라인·진행률·스켈레톤까지.
- **컴포넌트 무드:** **플랫 + 1px 보더가 주인공.** hover 만 미세 lift(1px)·보더 강조. 코퍼 글로우/그라디언트/3px lift 폐기. radius 타이트닝(md 6px). focus ring 2px 정밀 링.
- **폰트:** **Archivo**(display, wdth 축) + **Pretendard Variable**(body — 한국어 UI 품질) + **IBM Plex Mono**(숫자/터미널 레이블). 숫자 = mono tabular 이 주인공. `font-stretch` 는 라틴 전용 유틸(`.qb-display-wide/-expanded`)로만 — 한글 폴백 혼합 폭 방지, h1-h6 블랭킷 금지.
- **정규 어휘:** 테마 인지 시맨틱 토큰(shadcn + 금융 확장 `success/destructive/bullish/bearish` + `-subtle` + `--card-raised`), `:root`/`.dark` 양쪽 정의. 차트 토큰도 테마 인지(다크에서 자동 flip).

### 0.1 시그니처 모티프 사용처 매트릭스

| 모티프                                     | 사용                                                    | 금지                                       |
| ------------------------------------------ | ------------------------------------------------------- | ------------------------------------------ |
| tick ruler (`<TickRuler>`/`<SectionRule>`) | 섹션 헤더 경계, 키 스탯 스트립 상단, 사이드바 로고 하단 | 카드마다 도배, 본문 중간, 모바일 협소 영역 |
| tick notch (`.qb-tick-active`)             | 사이드바/수직 nav active                                | 버튼·탭(탭은 2px 코퍼 underline)           |
| P&L tape (`<PnlTape>`)                     | 대시보드 hero, 테이블 수익 셀(micro), 리포트 요약       | 손익 무관 데이터                           |
| tape progress (`<TapeProgress>`)           | 백테스트/최적화 진행률                                  | 일반 로딩 스피너 대체 전부                 |
| tape skeleton (`variant:"tape"`)           | 차트/스탯 스트립 로딩 자리                              | 텍스트/폼 스켈레톤                         |
| mono 터미널 레이블                         | 섹션/컬럼 레이블 = mono 11px uppercase tracking 0.14em  | 본문 문장                                  |

---

## 1. 디자인 원칙

| 원칙                            | 설명                                                                        |
| ------------------------------- | --------------------------------------------------------------------------- |
| **명료성 우선**                 | 금융 데이터는 장식보다 가독성. 모든 숫자는 모노스페이스, 충분한 대비        |
| **라이트 바디 + 다크 대시보드** | 마케팅/설정 화면은 라이트, 트레이딩 대시보드는 다크 — 맥락에 맞는 테마 전환 |
| **일관된 토큰**                 | 색상·간격·타이포를 CSS 변수로 관리, 하드코딩 금지                           |
| **접근성 기본**                 | WCAG AA 이상 (4.5:1 텍스트 대비), 키보드 네비게이션, reduced-motion 지원    |
| **이모지 금지**                 | 모든 아이콘은 SVG (Lucide 스타일). 이모지를 구조적 아이콘으로 사용 금지     |

---

## 2. 색상 토큰

> 값 SSOT 는 `globals.css`. 아래 표는 헌법 사본 — 변경 시 같은 커밋에서 동기.
>
> ★**2026-08-08 전면 재동기 (fe-canon-and-responsive).** 이 절은 **11셀 이상이 낡아 있었다** —
> 2026-08-07 B2 라이트 팔레트(WCAG AA 하드 실패 116건 수리)와 2026-08-08 [BL-628] 이
> `globals.css` 만 옮기고 이 표를 안 옮겼다. 위 「같은 커밋에서 동기」를 **집행하는 것이
> 없었기 때문**이다. 지금은 라이트 값의 대비를 `src/__tests__/light-canon-contrast.test.ts`
> 가, 양쪽 테마 값의 일치를 `src/__tests__/brand-palette-css-sync.test.ts` 가 문다 —
> 단 **이 표 자체를 집행하는 게이트는 여전히 없다.** 여기 수치를 근거로 쓰지 말고
> `globals.css` 를 열어라. 아래 대비 수치는 `globals.css` 주석의 실측치를 옮긴 것이다.

### 2.1 서페이스 / 텍스트 / 보더

| 토큰                             | Light (쿨 페이퍼)      | Dark (카본/스틸, 기본)            |
| -------------------------------- | ---------------------- | --------------------------------- |
| `--bg`                           | `#f4f5f6`              | `#0b0d0f`                         |
| `--bg-alt`                       | `#edeff1`              | `#101214`                         |
| `--card`                         | `#fdfdfc`              | `#141619`                         |
| `--card-raised` (popover/dialog) | `#fdfdfc`              | `#1a1d21`                         |
| `--border` / `--border-dark`     | `#e2e5e9` / `#cbd1d7`  | `#22262b` / `#31363d` (solid hex) |
| `--text-primary`                 | `#171a1e` (card 17.15) | `#e8eaed`                         |
| `--text-secondary`               | `#4b535c` (card 7.67)  | `#a6adb5`                         |
| `--text-muted`                   | `#585f68` (card 6.35)  | `#8b939c` (캐논 `--ink-3` 정의값) |

★순백·순흑을 쓰지 않는다 — `--card` 는 `#ffffff` 가 아니라 `#fdfdfc`, `--bg` 는 `#f6f7f8` 가
아니라 `#f4f5f6` 다(근거 주석 `globals.css:17-19`). 다크 `--text-muted` 는 캐논 5.82 의
**정의 토큰**이라 함부로 옮기면 임계 자체가 움직인다.

### 2.2 브랜드 / 시맨틱

| 토큰                                | Light                 | Dark                                   |
| ----------------------------------- | --------------------- | -------------------------------------- |
| `--primary` / `--primary-hover`     | `#883e07` / `#743405` | `#f08c2e` / `#f79d4d` (밝아지는 hover) |
| `--primary-light` / `--primary-100` | `#f8ede0` / `#efdcc3` | copper 12% / 30% rgba                  |
| `--primary-foreground`              | `#ffffff`             | `#1a1006` (코퍼 버튼 잉크 텍스트)      |
| `--bullish` / `--bearish`           | `#074b34` / `#ad322a` | `#2dd4a7` / `#f6685e`                  |
| `--success` (+`-subtle`)            | `#034a35` / `#e4f3ec` | `#34d399` / bullish 12% rgba           |
| `--destructive` (+`-subtle`)        | `#a72424` / `#fae9e8` | `#f6685e` (bearish 통일) / 12% rgba    |
| `--warning` (+`-subtle`)            | `#824e05` / `#f7efdc` | `#e5a93d` / **10%** rgba               |

★라이트 `--warning` 은 [BL-628] 로 `#875206` → `#824e05` 다 — `--warning-subtle` 위에서
5.66 이라 캐논 5.82 에 미달했다(AA 는 통과). 다크 `--success-subtle` 은 `--success` 가 아니라
**`--bullish` 파생**이다(구값은 앱 내부 모순이었다, `globals.css:441`).

★**2026-08-08 [BL-649] — `--accent-amber` / `--accent-amber-light` 를 삭제했다**(라이트·다크·
`@theme inline` 3면 6줄). 종전 이 자리는 「`--accent-amber` 는 라이트에서 `--warning` 과
**바이트 동일**을 유지한다」였는데, 그 문장이 곧 삭제 사유다 — TSX 소비가 **0건**인데 같은
값을 두 이름으로 들고 있었고, 다크에서는 이미 갈려 있었다(`-light` 0.12 vs
`--warning-subtle` 0.10). 앰버가 필요하면 `--warning` / `--warning-subtle` 하나뿐이다.
툼스톤은 `globals.css:57`.

### 2.3 차트 (테마 인지 — `:root`/`.dark` 양쪽 정의)

| 토큰                                    | Light                 | Dark                  | 비고                                    |
| --------------------------------------- | --------------------- | --------------------- | --------------------------------------- |
| `--chart-equity`                        | `#883e07`             | `#f08c2e`             | **equity = 코퍼, 브랜드 히어로 시리즈** |
| `--chart-benchmark` / `--chart-compare` | `#1452db` / `#7c3aed` | `#6aa2f7` / `#a78bfa` | compare 는 기준색 아님 (card 5.60)      |
| `--chart-dd-*`                          | bearish 계열 rgba     | bearish 계열 rgba     | drawdown                                |

★**2026-08-08 [BL-629] — 데드 `--chart-*` 7종을 삭제했다**: `--chart-bullish` ·
`--chart-bearish` · `--chart-line` · `--chart-area-top` · `--chart-area-bottom` ·
`--chart-grid` · `--chart-axis`. 정의만 있고 **참조가 0건**이었다 — `lib/chart-tokens.ts` 는
축을 `--text-muted`, 그리드를 `--border`, 상승/하락을 `--bullish`/`--bearish` 로 읽는다.
다크 `--chart-axis` 는 캐논 교정이 `--text-muted` 를 옮길 때 따라오지 못해 구값에 남아
있었고 **아무 검사도 그것을 못 봤다.** 이제 `--chart-*` 정의 집합을
`src/__tests__/chart-tokens-contract.test.ts` 가 동결한다 — 늘리려면 「이 토큰을 읽는 코드가
어디 있는가」를 먼저 답해야 한다.

★**2026-08-08 [BL-649] — shadcn 카테고리 슬롯 `--chart-1..5` 도 삭제했다**(3면 15줄). 종전
이 자리는 「별개로 존속한다」였으나 존속시킬 이유가 소멸했다 — `--color-chart-N` 유틸 소비가
**0건**이고, `--chart-4` 는 구 `--warning`(`#875206`) 사본이라 [BL-628] 이후 **드리프트한
복사본**이었다. 삭제하려면 `chart-tokens-contract.test.ts` 의 역방향 래칫
`CHART_VARS_FROZEN` 을 먼저 고쳐야 했다(래칫이 설계대로 물었다). 툼스톤은 `globals.css:118`.

CSS 변수를 못 읽는 소비자(차트 SSR 폴백 / Monaco / OG 이미지)는 `lib/brand-palette.ts` 상수를 import — 하드코딩 hex 신규 작성 금지.

### 2.4 색상 사용 규칙

| 용도                                                  | 규칙                                                                                |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 수익/이익                                             | text `--bullish` (시스템 성공 상태는 `--success`)                                   |
| 손실/위험                                             | text `--bearish` (파괴적 액션은 `--destructive`)                                    |
| Long/Short 배지                                       | `data-tone` success/destructive (subtle bg + 시맨틱 text)                           |
| CTA 버튼                                              | bg `--primary`, text `--primary-foreground` (다크는 잉크 — white 금지)              |
| 비활성/활성 탭                                        | text `--text-muted` → active text `--foreground` + 2px 코퍼 underline(line variant) |
| Tailwind 팔레트 클래스 직접 사용(`text-green-600` 등) | **금지** — 시맨틱 토큰 경유                                                         |

---

## 3. 타이포그래피

### 3.1 폰트 패밀리 (Precision Instrument v3)

| 용도         | 폰트                | Weight        | 로딩                                                         |
| ------------ | ------------------- | ------------- | ------------------------------------------------------------ |
| 제목 (h1~h6) | Archivo (wdth 축)   | 500, 600, 700 | next/font — `lib/fonts.ts` SSOT                              |
| 본문         | Pretendard Variable | variable      | `pretendard` 패키지 dynamic-subset CSS @import (globals.css) |
| 데이터/숫자  | IBM Plex Mono       | 400, 500, 600 | next/font — `lib/fonts.ts` SSOT                              |

- **Pretendard 는 next/font/local 금지** — 한글 variable 단일 woff2 2.3MB preload 가 LCP 를 해침. dynamic-subset(unicode-range 분할)이 표준.
- **Archivo 는 라틴 전용** — 한글 제목은 Pretendard 로 자동 폴백. 따라서 `font-stretch` 를 h1~h6 에 블랭킷 적용 금지(라틴만 늘어나는 혼합 폭). 라틴 전용 요소(로고 워드마크, 영문 eyebrow, KPI 레이블)에만 `.qb-display-wide`(112.5%) / `.qb-display-expanded`(125%) 유틸.
- Monaco 에디터는 CSS 변수를 못 읽음 — `ibmPlexMono.style.fontFamily` 를 옵션으로 직접 주입.
- 본문 숫자에 mono 없이 열 정렬만 필요하면 `.qb-tnum`(Pretendard tnum).

### 3.2 타입 스케일

| 레벨       | 사이즈                         | Weight | Line Height | 용도                   |
| ---------- | ------------------------------ | ------ | ----------- | ---------------------- |
| Display    | `clamp(2.5rem, 5vw, 3.75rem)`  | 800    | 1.15        | 히어로 헤드라인        |
| H2         | `clamp(1.75rem, 3vw, 2.25rem)` | 700    | 1.2         | 섹션 타이틀            |
| H3         | `1.05~1.15rem`                 | 600    | 1.3         | 카드 제목, 서브 타이틀 |
| Body       | `1rem (16px)`                  | 400    | 1.6         | 본문                   |
| Body Small | `0.875rem`                     | 400    | 1.6         | 카드 설명, 피처 리스트 |
| Caption    | `0.8rem`                       | 500    | 1.5         | 레이블, 배지           |
| Mono Data  | `0.85~2rem`                    | 700    | 1.2         | 숫자, 가격, 통계       |

### 3.3 타이포 규칙

- 제목 letter-spacing: `-0.01em` (v3 — Archivo 는 -0.02em 이 과함)
- 본문 letter-spacing: `0` (기본)
- 금융 숫자는 **반드시** JetBrains Mono — 탭룰러 피겨로 열 정렬 유지
- 코드 스니펫 (Pine Script 등): JetBrains Mono, `0.75rem`, line-height `1.7`
- 최소 본문 크기: `16px` (모바일 iOS 자동 줌 방지)
- 줄 길이: 모바일 35~60자, 데스크톱 60~75자 (`max-width: 520px` 설명 텍스트)

---

## 4. 간격 & 레이아웃

### 4.1 Spacing Scale (8px 베이스)

```
4px  — 아이콘 내부 간격
8px  — 밀접 요소 gap
12px — 소형 gap (배지, 필)
16px — 기본 gap (카드 내부 요소)
20px — 카드 그리드 gap
24px — 컨테이너 좌우 패딩, 카드 패딩 기본
28px — 카드 패딩 (데스크톱)
32px — 섹션 내 블록 간격
48px — 섹션 헤더 → 콘텐츠
56px — 푸터 상단 패딩
72px — CTA 섹션 패딩
80px — 섹션 상하 패딩 (데스크톱)
```

### 4.2 Max Width & Container

**정본 = `apps/web/src/styles/globals.css`.** 아래는 사본이다.

| 컨테이너                | max-width  | 정의 위치                                          |
| ----------------------- | ---------- | -------------------------------------------------- |
| `.page` (앱 셸 공용)    | **1240px** | `globals.css:1210` (`@layer components`, KITPORT)  |
| `.lp-page .page` (랜딩) | **1120px** | `:3328`                                            |
| `.pricing-page .page`   | 1240px     | `:3541`                                            |
| `.waitlist-page .page`  | 1240px     | `:3690`                                            |
| 대기자 명단 어드민      | 1200px     | `waitlist-admin-view.tsx:47` `max-w-[1200px]` (TW) |

★`.page` 의 max-width 는 **모든 뷰포트에서 고정**이다. 폭에 따라 바뀌는 것은 패딩뿐
(`≤768px` → `18px 14px 48px`, `globals.css:1863`). 경계 실측 집행 = `e2e/design-canon-responsive.spec.ts`.

> ~~`.container` 1200px / `.dash-container` 1000px / `.narrow` 720px~~
> ★**2026-08-08 삭제 — 셋 다 이 레포에 존재하지 않았다(v2 잔재).** 실측:
>
> - `.dash-container` · `.narrow` — CSS 정의 **0건**, 마크업 사용 **0건**. 유령 규정이었다.
> - `.container` — 유령이 아니라 **Tailwind v4 내장 유틸리티**이고 `loading.tsx` 3곳이
>   `container mx-auto` 로 쓴다. 다만 최대폭은 1200px **고정이 아니라** `@theme`
>   브레이크포인트 사다리(§4.3)를 따른다 — 「1200px」라는 기술이 거짓이었다.

### 4.3 반응형 브레이크포인트

**정본 = `globals.css:204-211` 의 `@theme` 블록.** ★Tailwind v4 **기본값이 아니다** —
`sm:` 과 `xl:`, `2xl:` 이 재정의돼 있다. 전문·사용 건수는 `apps/web/AGENTS.md` §10.

| 접두사 | 이 레포    | Tailwind v4 기본 | 그리드 변경 / 용도                                        |
| ------ | ---------- | ---------------- | --------------------------------------------------------- |
| `sm:`  | **375px**  | ~~640px~~        | 패딩 축소, CTA 풀와이드, 스텝 1열                         |
| `md:`  | 768px      | 768px            | 전체 1열, 히어로 스택, 가격 1열 · **앱 셸 사이드바 숨김** |
| `lg:`  | 1024px     | 1024px           | 기능 카드 3→2열, 벤토 3→2열 · **앱 셸 아이콘 레일**       |
| `xl:`  | **1200px** | ~~1280px~~       | 콘텐츠 그리드 2열화 (KPI·메트릭·설정 폼) — 셸 미개입      |
| `2xl:` | **1440px** | ~~1536px~~       | 유틸 사용 0건 · raw `@media` **0건**                      |

★**raw CSS 미디어는 전부 `max-width`(desktop-first)이고 `min-width` 는 0건**이다. 위 표는
Tailwind 유틸 접두사(min-width)와 CSS 미디어(max-width)가 **같은 숫자를 반대 방향으로** 쓴다는
뜻이다 — 섞어 읽지 마라.

#### 4.3.1 `900px` — 콘텐츠 그리드 전용 6번째 경계 (★[BL-646] 2026-08-08 등재)

**정본 사다리에 900 을 추가한다.** 위 표(셸·유틸 사다리)와는 **다른 축**이라 행으로 넣지 않는다 —
Tailwind 접두사가 없고(`--breakpoint-*` 미정의) raw CSS 전용이며, **셸에는 개입하지 않는다.**

적용처 5곳 = `.perf-row` · `.trade-detail-metrics` · `.session-manage` · `.report-analysis-grid` ·
`.ob-panel`/`.ob-illus`. 전부 화면 전용 그리드 축소다.

**왜 900 이고 왜 1024·768 로 흡수하지 않는가 — 실측(2026-08-08, dev 서버 + Playwright 하네스).**
그리드가 실제로 받는 폭은 뷰포트가 아니라 `.page` 콘텐츠 박스이고, 이 값은 뷰포트에 대해
**단조가 아니다**. `--sidebar-w` 가 1024 에서 `232 → 64` 로 계단을 밟기 때문이다.

| 뷰포트         | 769 | 899 | 901 | 1023    | **1025** | 1200 |
| -------------- | --- | --- | --- | ------- | -------- | ---- |
| 콘텐츠 박스 px | 657 | 787 | 789 | **911** | **745**  | 920  |

⇒ 뷰포트가 1023 → 1025 로 **늘어나는데** 콘텐츠 박스는 911 → 745 로 **166px 줄어든다.**

- **1024 로 흡수 = 기각.** 콘텐츠 911(전 구간 최대급)에서 1열로 접으면서 콘텐츠 745 에서는
  2·3열을 유지한다 — **가장 넓을 때 접는다.** 같은 콘텐츠 폭이 접힘/펼침 양쪽에 나타나는
  모순 구간이 **166px**(745~911).
- **768 로 흡수 = 기각.** 콘텐츠 657(전 구간 최소)까지 3열을 끌고 간다. 뷰포트 769 에서
  `.trade-detail-metrics` 가 `219+219+219` 가 되고 `.metric` 2건이 **+6px 넘친다** — 실제 파손.
- **900 유지 = 채택.** 모순 구간이 **42px**(745~787)로 셋 중 최소다.

★근본 해는 뷰포트 미디어쿼리가 아니라 **컨테이너 쿼리**다(그리드가 뷰포트가 아니라 자기 컨테이너를
봐야 한다). 900 은 그 전까지의 최선일 뿐 옳은 축이 아니다 — 전환은 [BL-647] 과 함께 다룬다.

### 4.4 Z-Index 스케일

```css
--z-base: 0; /* 기본 콘텐츠 */
--z-card: 1; /* 플로팅 카드 */
--z-sticky: 10; /* sticky 요소 */
--z-overlay: 50; /* 오버레이 배경 */
--z-modal: 60; /* 모달 */
--z-nav: 100; /* 네비게이션 */
```

---

## 5. Border Radius 토큰 (v3 타이트닝)

```css
--radius-sm: 4px; /* 인풋, 계측기 태그(배지) */
--radius-md: 6px; /* 버튼, 탭 세그먼트 */
--radius-lg: 10px; /* 카드 */
--radius-xl: 14px; /* 시트 상단, 다이얼로그 */
--radius-full: 50%; /* 아바타, 아이콘 원형 */
```

---

## 6. 그림자 (Elevation) — v3 플랫화

> **원칙: 1px 보더가 주인공, 그림자는 조연.** 글로우(코퍼/인디고) 전면 폐기.
> 기본 상태 = 헤어라인 그림자, hover(opt-in) 만 미세 승격.

```css
/* Light */
--card-shadow: 0 1px 2px rgba(23, 26, 30, 0.06);
--card-shadow-hover: 0 4px 12px rgba(23, 26, 30, 0.08);
--nav-shadow: 0 1px 2px rgba(23, 26, 30, 0.05);
--btn-primary-shadow: 0 1px 2px rgba(23, 26, 30, 0.18);
--btn-primary-shadow-hover: 0 2px 4px rgba(23, 26, 30, 0.2);

/* Dark (.dark) */
--card-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
--card-shadow-hover: 0 4px 16px rgba(0, 0, 0, 0.45);
--nav-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
--btn-primary-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
--btn-primary-shadow-hover: 0 2px 4px rgba(0, 0, 0, 0.4);
```

컴포넌트 규칙: 카드/팝오버는 `border border-border`(popover 는 `--card-raised` 표면) — `ring-1 ring-foreground/10` 패턴 폐기. hover lift 는 `data-hoverable` opt-in 1px + 보더 강조만.

---

## 7. 컴포넌트 패턴

> **v3 note:** 아래 코드 샘플 일부는 v2 시절 스냅샷. 구현 SSOT 는 `apps/web/src/components/ui/` — v3 원칙(플랫 + 1px 보더, hover 색 변화만, focus ring 2px, 배지 = 4px 태그)은 §0/§6 참조. 샘플과 코드가 다르면 코드가 정답.

### 7.1 버튼

| 타입              | 배경            | 텍스트             | 보더             | 용도                   |
| ----------------- | --------------- | ------------------ | ---------------- | ---------------------- |
| Primary           | `--primary`     | `#FFFFFF`          | 없음             | 메인 CTA, 폼 제출      |
| Secondary         | `#FFFFFF`       | `--text-secondary` | `1.5px --border` | 보조 액션              |
| Ghost             | 투명            | `--text-secondary` | 없음             | 네비 링크, 텍스트 버튼 |
| Destructive       | `--destructive` | `#FFFFFF`          | 없음             | 삭제, 위험 액션        |
| Outline (Pricing) | `#FFFFFF`       | `--text-secondary` | `1.5px --border` | 가격 카드 하단         |
| Filled (Pricing)  | `--primary`     | `#FFFFFF`          | 없음             | 추천 가격 카드         |
| Dark CTA          | `--dash-accent` | `#FFFFFF`          | 없음             | 다크 테마 CTA          |

**공통 속성:**

```css
min-height: 48px; /* 터치 타겟 */
padding: 14px 32px;
border-radius: 10px;
font-weight: 600;
font-size: 0.95rem;
transition: all 200ms ease;
cursor: pointer;
display: inline-flex;
align-items: center;
gap: 8px;
```

### 7.2 카드

```css
/* 기본 카드 (Light) */
.card {
  background: var(--card);
  border-radius: var(--radius-lg); /* 14px */
  padding: 28px;
  box-shadow: var(--card-shadow);
  transition:
    transform 200ms ease,
    box-shadow 200ms ease;
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--card-shadow-hover);
}

/* 글래스 카드 (Dark) */
.glass-card {
  background: var(--dash-surface); /* rgba(255,255,255,0.04) */
  backdrop-filter: blur(20px);
  border: 1px solid var(--dash-border); /* rgba(255,255,255,0.08) */
  border-radius: var(--radius-lg);
}

/* 강조 글래스 카드 */
.glass-card-elevated {
  background: var(--dash-surface-elevated); /* rgba(255,255,255,0.07) */
}
```

### 7.3 인풋

```css
/* Light Theme */
input {
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); /* 6px */
  padding: 14px 18px;
  font-size: 0.9rem;
  min-height: 48px; /* 터치 타겟 */
  transition: border-color 200ms ease;
}
input:focus {
  border-color: var(--primary);
  outline: 2px solid rgba(37, 99, 235, 0.15);
  outline-offset: 0;
}

/* Dark Theme */
.dash-input {
  background: var(--dash-surface);
  border: 1px solid var(--dash-border);
  color: var(--dash-text);
}
```

### 7.4 배지/필

```css
/* 공지 필 */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--primary-light);
  border: 1px solid var(--primary-100);
  color: var(--primary);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: var(--radius-sm); /* 4px — pill 반경 폐기, 태그로 타이트닝 */
}

/* 포지션 배지 */
.badge-long {
  background: rgba(52, 211, 153, 0.15);
  color: var(--dash-green);
}
.badge-short {
  background: rgba(248, 113, 113, 0.15);
  color: var(--dash-red);
}
```

### 7.5 아이콘 시스템

- **라이브러리:** Lucide 스타일 inline SVG
- **크기:** 기본 `22×22`, 네비/소형 `16×16`, 피처 아이콘 `22×22` (44px 원형 컨테이너)
- **스트로크:** `1.5px`, `stroke-linecap: round`, `stroke-linejoin: round`
- **색상:** Light에서 `stroke: var(--primary)`, Dark에서 `stroke: var(--dash-text)` 또는 `var(--dash-accent)`

```css
.icon {
  width: 22px;
  height: 22px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 피처 카드 아이콘 컨테이너 */
.icon-container {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## 8. 인터랙션 & 애니메이션

### 8.1 트랜지션

```css
/* 기본 — 모든 인터랙티브 요소 */
transition: all 200ms ease;

/* 카드 호버 */
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--card-shadow-hover);
}

/* 버튼 호버 */
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--btn-primary-shadow-hover);
}
```

### 8.2 키프레임 애니메이션

```css
/* 히어로 플로팅 카드 */
@keyframes heroFloat {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
/* 6s ease-in-out infinite */

/* 실시간 모니터링 도트 펄스 */
@keyframes livePulse {
  0%,
  100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}
/* 3s linear infinite, 도트 간 0.5s stagger */
```

### 8.3 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 9. 접근성 기준

| 항목                      | 기준               | 구현                                                      |
| ------------------------- | ------------------ | --------------------------------------------------------- |
| 텍스트 대비               | WCAG AA (4.5:1)    | `#0F172A` on `#FAFBFC` = 17.5:1 ✅                        |
| 보조 텍스트 대비          | WCAG AA (4.5:1)    | `#475569` on `#FFFFFF` = 7.1:1 ✅                         |
| 버튼 대비                 | WCAG AA            | `#FFFFFF` on `#2563EB` = 8.6:1 ✅                         |
| 다크 텍스트 대비          | WCAG AA            | `#EDEDEF` on `#0B1120` = 15.2:1 ✅                        |
| 포커스 표시               | `:focus-visible`   | `outline: 2px solid var(--primary); outline-offset: 2px;` |
| 터치 타겟                 | 최소 44×44px       | 버튼 `min-height: 48px`, 아이콘 버튼 `44px`               |
| 폼 레이블                 | 항상 존재          | 시각적 히든 가능하나 `<label>` 필수                       |
| 색상만으로 정보 전달 금지 | 텍스트/아이콘 보조 | Long/Short 배지에 텍스트 포함, 수익/손실에 +/- 기호 포함  |
| 키보드 내비게이션         | Tab 순서           | 시각적 순서와 일치                                        |
| 스크린 리더               | aria-label         | 아이콘 버튼에 `aria-label` 필수                           |

---

## 10. App Shell 패턴 (인증된 앱 페이지 공통)

**원칙:** 인증된 모든 앱 페이지는 동일한 App Shell 구조를 사용한다. 테마(라이트/다크)만 바뀌고 **구조·위치·동작은 동일**.

### 10.1 레이아웃 구조

```
┌─ Global Header (height 60px, sticky, z-index: 100) ──────────┐
│ [로고] [브레드크럼] ... [검색] [알림] [프로필]                   │
├─ Sidebar (232px expanded / 64px rail / 0 hidden) ┬─ 콘텐츠 ─┤
│                                           │               │
│  네비게이션 메뉴                             │  (페이지별    │
│                                           │   다름)       │
│                                           │               │
│  ─── divider ───                          │               │
│                                           │               │
│  설정 / 프로필 (하단 고정)                   │               │
└───────────────────────────────────────────┴───────────────┘
```

### 10.2 Sidebar 사양

**정본 = `globals.css`.** 기본 `:168` · 아이콘 레일 `:184-186` · 숨김 `:187-189`.
★이 세 곳은 **언레이어드**여야 한다 — KITPORT 사본(`:1846` 1024 / `:1856` 768)은
`@layer components` 소속이라 언레이어드 base 에 캐스케이드로 항상 진다(근거 주석 `:175-183`).
값은 `_kit.html` 실측(232 / 64 / 0)과 동일하다.

| 속성          | 확장 (기본, `>1024px`)                                                                                                 | 아이콘 레일 (`≤1024px`)                                              | 숨김 (`≤768px`)                                                                         |
| ------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `--sidebar-w` | **232px**                                                                                                              | **64px**                                                             | **0px** + `.sidebar { display: none }`                                                  |
| 표시          | 아이콘 + 레이블 + 계정 카드                                                                                            | 아이콘만 (브랜드명·nav 레이블·계정 텍스트·nav 카운트 `display:none`) | 셸에서 제거 → 햄버거 + 모바일 drawer                                                    |
| 토글          | **없음 — 순수 CSS 로 접힌다.** `sidebarOpen` 프롭·스토어는 삭제됐다 (`dashboard-sidebar.tsx:3`, `store/ui-store.ts:5`) | —                                                                    | drawer 만 JS. drawer 는 레일 collapse 를 받지 않고 항상 풀 라벨 (`globals.css:191-197`) |

> ~~기본 동작: 데스크톱 확장, **1200px↓ 축소**, 768px↓ 숨김+햄버거~~ · ~~Width 220px / 60px~~
> · ~~토글 = chevron 버튼~~
> ★★**2026-08-08 정정 — 1200px 는 셸 브레이크포인트가 아니다.** 코드의
> `@media (max-width: 1200px)` **5곳**(`globals.css:1836 · 2442 · 2531 · 2991 · 3503`)은
> 전부 **콘텐츠 그리드 열 수 축소**(`.kpi-row`·`.metric-groups`·`.diag-row`·`.cta-row` /
> `.create-grid` / `.strip-3` / `.setup-grid` / `.lp-hero`·`.lp-feat-grid`·`.lp-steps`)이고
> 사이드바·토프바·`.page` 폭에는 **개입하지 않는다**(5블록 전수 확인). 셸 경계는 **1024 와
> 768 둘뿐**이다. 220/60 과 chevron 토글은 v2 잔재였다.
> ★경계 4점(1025 / 1024 / 769 / 768)은 이제 `e2e/design-canon-responsive.spec.ts` 가 집행한다 —
> 그전까지 e2e 전체에서 `sidebar` grep 이 **0건**이라 이 표가 틀려도 게이트가 조용했다.

**네비게이션 항목 (순서 고정):**

```
순서  아이콘       레이블          경로
1     home        대시보드         /dashboard
2     code        전략            /strategies
3     layers      템플릿          /templates
4     bar-chart   백테스트         /backtests
5     zap         트레이딩         /trading
6     globe       거래소          /exchanges
───── divider ─────
7     bell        알림            /notifications  (뱃지 표시)
8     settings    설정            /settings       (하단)
9     user-avatar 프로필          /profile        (하단)
```

**활성 상태 스타일:**

```css
/* Light Theme */
.nav-item.active {
  background: var(--primary-light); /* #EFF6FF */
  color: var(--primary); /* #2563EB */
  border-left: 3px solid var(--primary);
}
.nav-item.active svg {
  stroke: var(--primary);
}

/* Dark Theme */
.nav-item.active {
  background: rgba(99, 102, 241, 0.12);
  color: var(--dash-accent); /* #6366F1 */
  border-left: 3px solid var(--dash-accent);
}
.nav-item.active svg {
  stroke: var(--dash-accent);
}
```

**Hover 상태:**

- Light: `background: var(--bg-alt);` (#F1F5F9)
- Dark: `background: rgba(255,255,255,0.04);`

### 10.3 Global Header 사양

**공통 요소 (좌→우):**

| 위치    | 요소                     | 설명                                                  |
| ------- | ------------------------ | ----------------------------------------------------- |
| Left 1  | Sidebar 토글 버튼        | 44×44, 햄버거 아이콘 (모바일) 또는 chevron (데스크톱) |
| Left 2  | 브레드크럼 / 페이지 제목 | 페이지 컨텍스트 표시                                  |
| Center  | 검색 바 (선택적)         | `⌘K` 글로벌 검색, 데스크톱만 표시                     |
| Right 1 | 페이지 컨텍스트          | 페이지별 고유 요소 (예: 실시간 잔고, DEMO/LIVE 토글)  |
| Right 2 | 알림 벨                  | 44×44, 새 알림 뱃지                                   |
| Right 3 | 프로필 아바타            | 36px 원형, 드롭다운 메뉴                              |

**높이:** `60px` 고정, `sticky`, `border-bottom: 1px solid var(--border)` (라이트) / `var(--dash-border)` (다크)

### 10.4 테마별 App Shell 색상

> **v3 note:** 아래 표의 구체 hex 는 v2 스냅샷 — v3 정본은 §2.1(카본/스틸/쿨페이퍼)과 `globals.css` `--sidebar*` 토큰. 사이드바 active 는 3px border-left 가 아니라 `.qb-tick-active` 캘리브레이션 노치(§0.1).

**Light Theme:**

```css
--shell-bg: #ffffff; /* 헤더·사이드바 배경 */
--shell-border: var(--border); /* #E2E8F0 */
--shell-text: var(--text-primary); /* #0F172A */
--shell-text-muted: var(--text-muted); /* #94A3B8 */
--shell-hover: var(--bg-alt); /* #F1F5F9 */
```

**Dark Theme:**

```css
--shell-bg: var(--dash-bg); /* #0B1120 */
--shell-border: var(--dash-border); /* rgba(255,255,255,0.08) */
--shell-text: var(--dash-text); /* #EDEDEF */
--shell-text-muted: var(--dash-text-muted); /* #8A8F98 */
--shell-hover: rgba(255, 255, 255, 0.04);
```

### 10.5 페이지별 차이 (허용 범위)

| 요소                            | 공통    | 페이지별 차이 허용                        |
| ------------------------------- | ------- | ----------------------------------------- |
| Sidebar 구조/항목               | ✅ 동일 | ❌                                        |
| Sidebar 활성 항목               | ❌      | ✅ (페이지마다 다름)                      |
| Header 높이/위치                | ✅ 동일 | ❌                                        |
| Header 공통 요소 (알림, 프로필) | ✅ 동일 | ❌                                        |
| Header 컨텍스트 영역            | ❌      | ✅ (대시보드는 잔고, 편집은 저장 버튼 등) |
| 콘텐츠 영역                     | ❌      | ✅ (완전 자유)                            |
| 테마 (라이트/다크)              | ❌      | ✅ (페이지 성격에 따라)                   |

### 10.6 반응형 동작

**정본 = `globals.css`. 셸에 실제로 존재하는 경계는 `1024` 와 `768` 둘뿐이다.**

```
>1024px : Sidebar 확장 232px · 브레드크럼 전체 표시
≤1024px : Sidebar 아이콘 레일 64px
          (브랜드명 · nav 레이블 · 계정 텍스트 · nav 카운트 display:none)
≤768px  : Sidebar 제거 0px → 햄버거 + 모바일 drawer(풀 라벨)
          · 브레드크럼 링크/구분자 숨김 · 토프바 좌우 패딩 14px
          · .page 패딩 18/14/48
```

★`.page` 의 max-width 는 **모든 폭에서 1240px** 고정이다(§4.2). 폭에 따라 바뀌는 것은 패딩뿐.
★경계 4점(1025 / 1024 / 769 / 768)은 `e2e/design-canon-responsive.spec.ts` 가 실측 집행한다.

> ~~`≥1440px` 행~~ · ~~`1200px~ 검색 축소` 행~~
> ★**2026-08-08 삭제.** raw CSS 미디어에 `min-width` 는 **0건**이고 1440px 미디어도 **0건**이다
> (30개 `@media` 전부 `max-width`). `--breakpoint-2xl: 1440px` · `--breakpoint-xl: 1200px`
> (`globals.css:204-211`)는 Tailwind 유틸 접두사용 값이지 셸 규칙이 아니다. 1200px 의 정체는
> §10.2 정정을 봐라 — 콘텐츠 그리드 축이다.
>
> ~~`1024px~ 검색 숨김`~~
> ★**검증 불가 — 검색창이 렌더되지 않는다.** `.searchbox` CSS(`globals.css:1146-1165` 정의,
> `:1840` 1024px 숨김)는 이식돼 있으나 **그것을 렌더하는 TSX 가 0건**이다
> (`components/layout/dashboard-header.tsx:5` — 「검색창은 백엔드 검색 기능이 없어 이식하지
> 않는다(가짜 UI 방지)」). 데드 CSS 의 처분은 [BL-645].
>
> ★**2026-08-09 (W3) 정정 — 위 줄 번호가 낡아 있었다.** 종전 표기 `1159-1178`·`:1853` 은
> 지금의 파일에서 각각 `.searchbox:hover` 중간과 `@media (max-width: 1024px)` 바깥을 가리켰다.
> 실측 재확인 = 정의 **1146-1165** · 1024px 숨김 **1840** · 렌더 TSX **0건**
> (`grep -rn searchbox apps/web/src --include=*.tsx` 의 유일한 히트는
> `app/__tests__/not-found.test.tsx` 의 ARIA role `searchbox` 로, 이 CSS 클래스가 아니다).
>
> ★**CSS 정의 자리에는 주석을 못 단다.** 그 구간은 `KITPORT-START`~`KITPORT-END` 센티넬
> 안이고, 무결성 가드가 `_kit.html` 과 **주석까지 포함해** 정규화 대조한다
> (`src/__tests__/design-canon-kit-port.test.ts` 의 `normalize` 는 공백만 접고 주석은 보존).
> 2026-08-09 실측 — 정의 바로 위에 주석 한 줄을 넣자 그 가드가 빨개졌다. ⇒ 「주석만 달면
> 끝」이 아니라 **삭제와 똑같이 allowlist 등재가 선행**이다. 그래서 근거는 이 문서와
> 센티넬 머리 주석에 남기고 `globals.css` 본문은 건드리지 않았다.

---

## 11. 페이지별 테마 적용

> **v3 note:** 아래 표의 페이지×테마 배정(예: "백테스트 결과 = Light")은 v2 "Terminal Tape" 스냅샷 잔재다. v3 "Precision Instrument"는 전면 뉴트럴이라 페이지별 라이트/다크 배정이 사라졌다 — 정본은 §0·§2.1·`globals.css` 이다.

| 페이지              | 테마                       | 비고                      |
| ------------------- | -------------------------- | ------------------------- |
| 랜딩 페이지         | Light + 다크 대시보드 섹션 | 프로토타입 완성           |
| 로그인/회원가입     | Light                      | 자체 폼 (ADR-034)         |
| 대시보드 (트레이딩) | **Dark**                   | `--dash-*` 토큰 전체 적용 |
| 전략 편집           | Light (에디터는 Dark)      | 코드 에디터 영역만 다크   |
| 백테스트 결과       | Light + 차트 영역 Dark     | 차트 카드만 다크 배경     |
| 설정/프로필         | Light                      | 기본 SaaS 스타일          |
| 문서/도움말         | Light                      | 가독성 최우선             |

---

## 12. 다크↔라이트 전환부

두 테마가 한 페이지에 공존할 때 부드러운 그라데이션 전환을 사용:

```css
/* Light → Dark */
.transition-to-dark {
  height: 120px;
  background: linear-gradient(to bottom, #f8fafc, #0b1120);
}

/* Dark → Light */
.transition-to-light {
  height: 120px;
  background: linear-gradient(to bottom, #0b1120, #fafbfc);
}
```

---

## 13. 앰비언트 이펙트 (다크 섹션 전용)

대시보드와 다크 섹션에서 깊이감을 위한 배경 글로우:

```css
/* 인디고 글로우 블롭 */
.ambient-indigo {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(
    circle,
    rgba(99, 102, 241, 0.06),
    transparent 70%
  );
  pointer-events: none;
}

/* 블루 글로우 블롭 */
.ambient-blue {
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.04), transparent 70%);
  pointer-events: none;
}
```

- 최대 2~3개만 사용 (과다 사용 금지)
- `pointer-events: none` 필수
- `overflow: hidden` 컨테이너 안에 배치

---

## 14. Tailwind CSS v4 매핑

프론트엔드 구현 시 Tailwind 토큰으로 매핑:

```ts
// tailwind.config.ts (참고용)
export default {
  theme: {
    extend: {
      colors: {
        // Light
        primary: {
          DEFAULT: "#2563EB",
          hover: "#1D4ED8",
          light: "#EFF6FF",
          100: "#DBEAFE",
        },
        success: { DEFAULT: "#059669", light: "#D1FAE5" },
        destructive: { DEFAULT: "#DC2626", light: "#FEE2E2" },
        // Dark Dashboard
        dash: {
          bg: "#0B1120",
          surface: "rgba(255,255,255,0.04)",
          "surface-elevated": "rgba(255,255,255,0.07)",
          border: "rgba(255,255,255,0.08)",
          text: "#EDEDEF",
          "text-muted": "#8A8F98",
          accent: "#6366F1",
          green: "#34D399",
          red: "#F87171",
        },
      },
      fontFamily: {
        heading: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        pill: "20px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04)",
        "card-hover":
          "0 2px 8px rgba(0,0,0,0.08), 0 16px 40px rgba(0,0,0,0.06)",
      },
    },
  },
};
```

---

## 15. 디자인 의사결정 기록

| 결정                               | 근거                                                 | 대안 (기각)                                                 |
| ---------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------- |
| 라이트 메인 + 다크 대시보드        | 가독성/접근성 최적, 트레이딩은 다크가 표준           | 전체 다크 (장시간 피로), 전체 라이트 (트레이딩 분위기 부족) |
| Plus Jakarta Sans 제목             | 모던+프리미엄 느낌, Google Fonts 무료                | Space Grotesk (덜 프리미엄), Cormorant (금융과 안 맞음)     |
| Inter 본문                         | 가독성 최고, 가변 폰트 지원                          | DM Sans (유사하나 가변폰트 미흡)                            |
| JetBrains Mono 데이터              | 탭룰러 피겨, 코드+숫자 겸용                          | Fira Code (리가처 불필요)                                   |
| Blue-600 (#2563EB) 프라이머리      | 금융 신뢰감, WCAG 대비 우수                          | 골드 (과한 느낌), 시안 (접근성 약함)                        |
| Indigo-500 (#6366F1) 다크 액센트   | Blue와 구분되면서 프리미엄                           | 동일 Blue (테마 구분 불가)                                  |
| 8개 디자인 변형 비교 후 Final 선택 | F(Light SaaS) 88.5점 + H(Glass) 83.5점 조합 → 91.0점 | A~E, G 변형 (각각 결함 존재)                                |
