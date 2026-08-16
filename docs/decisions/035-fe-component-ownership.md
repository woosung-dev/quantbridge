# ADR-035: FE 컴포넌트 소유권 — 라우트 전용 `_components/` 를 feature 소유로 통일

- **날짜:** 2026-08-16
- **상태:** Accepted
- **관련:** [ADR-002](002-parallel-scaffold-strategy.md)(FSD Lite 초판) · [ADR-026](026-documentation-ssot.md) · [ADR-029](029-monorepo-standard-layout.md)(앱 경계는 불변 — 이 결정은 `apps/web/src` **내부**다)

## Context

`apps/web/AGENTS.md` §4(FSD Lite)는 도메인 UI 를 `features/[domain]/components/` 에 두라고 규정한다.
실측은 정반대였다 — 2026-08-16 기준 `app/**/_components/` **16개 디렉터리에 234파일**이 있었고,
`app/(dashboard)/backtests/_components` 하나가 **111파일**로 `features/backtest` 전체(27파일)의 4배였다.
`src/app` 294파일 vs `src/features` 165파일.

**즉 규정과 실재가 반대였고, 어느 쪽도 틀렸다고 말할 근거가 자동으로 나오지 않았다.**
`app/**/_components/` 는 Next.js App Router 의 정상 관례(밑줄 = private folder, 라우팅 제외)이기도 하다.
그래서 갈래는 둘이었다.

- ⓐ **규칙을 현실에 맞춘다** — `_components` 를 §4 트리에 공식화하고 승격 경계선만 정한다
- ⓑ **코드를 규칙에 맞춘다** — 234파일을 `features/` 로 옮긴다

평가자는 ⓐ 를 추천했다(위험 0·회귀 0). **사용자 결정은 ⓑ 다**(2026-08-16).

결정의 근거가 된 사실 3건:

1. **레포에 이미 같은 방향의 전례가 있다** — `features/live-sessions/components/live-session-table.tsx:6`
   이 "trading/\_components 에서 이 도메인 폴더로 옮겨 응집도를 회복했다"고 적고 있다.
2. **소유권이 이미 feature 쪽이었다** — feature 테스트 3건이 `@/app/(dashboard)/...` 를 SUT 로
   삼고 있었다(`features/backtest/__tests__/status-meta.test.ts:6` 등). 테스트가 역방향으로
   의존한다는 것은 그 컴포넌트의 주인이 라우트가 아니라는 신호다.
3. **경계를 강제하는 장치가 0개였다** — `eslint.config.mjs`(72줄)에 `no-restricted-imports` 가
   없었다. 규칙을 문서에만 두면 다음 회차가 되돌린다.

## Decision

### 1. 도메인 UI 의 주인은 feature 다

라우트 디렉터리(`app/`)는 **조립층**이다 — route/layout/loading/error/metadata 와 feature 조립만 둔다.
화면을 그리는 컴포넌트는 `features/<domain>/components/` 가 소유한다.

### 2. `_components/` 를 금지하지는 않는다 — 승격 경계선을 둔다

| 상황                                    | 자리                                                                               |
| --------------------------------------- | ---------------------------------------------------------------------------------- |
| 두 개 이상 라우트가 쓴다                | `features/<domain>/components/` (도메인이 있으면) 또는 `components/` (도메인 무지) |
| 한 라우트 전용 + 도메인 로직 있음       | `features/<domain>/components/`                                                    |
| 한 라우트 전용 + 순수 표현 + 5파일 미만 | `app/<route>/_components/` 허용                                                    |

★**의심스러우면 feature 로 보내라.** 되돌리는 비용보다 찾지 못하는 비용이 크다.

### 3. 이동 매핑 (2026-08-16, 234파일)

| 출발                                                    | 도착                                       |
| ------------------------------------------------------- | ------------------------------------------ |
| `app/(dashboard)/backtests/_components`                 | `features/backtest/components`             |
| `app/share/backtests/[token]/_components`               | `features/backtest/components/share`       |
| `app/(dashboard)/optimizer/_components`                 | `features/optimizer/components`            |
| `app/(dashboard)/trading/_components`                   | `features/trading/components`              |
| `app/(dashboard)/orders/_components`                    | `features/trading/components/orders`       |
| `app/(dashboard)/strategies/_components`                | `features/strategy/components`             |
| `app/(dashboard)/strategies/new/_components`            | `features/strategy/components/new`         |
| `app/(dashboard)/strategies/[id]/edit/_components`      | `features/strategy/components/edit`        |
| `app/(dashboard)/onboarding/_components`                | `features/onboarding/components`           |
| `app/(dashboard)/dashboard/_components`                 | **`features/dashboard/components`** (신설) |
| `app/(dashboard)/admin/waitlist/_components`            | `features/waitlist/components/admin`       |
| `app/waitlist/_components`                              | `features/waitlist/components`             |
| `app/_components/landing-*` · `app/pricing/_components` | **`features/marketing/components`** (신설) |
| `app/(auth)/_components`                                | **`features/auth/components`** (신설)      |
| `app/_components/legal-{callout,page-shell}`            | `components/legal/`                        |
| `app/maintenance/_components/maintenance-retry-button`  | `components/`                              |

**신설 feature 3종** — `dashboard`(여러 도메인을 합성하는 화면) · `marketing`(랜딩·가격) ·
`auth`(로그인 폼). 법무 셸 2종은 3개 형제 라우트가 `../` 로 공유하던 **레이아웃 셸**이라
도메인 UI 가 아니고 `components/legal/` 로 갔다.

### 4. 경계는 eslint 가 집행한다

`apps/web/eslint.config.mjs` 가 **`features/`·`components/`·`lib/`·`hooks/`·`store/` 에서 `app/` 을
import 하는 것**을 error 로 막는다. 이동 시점 위반 0건이고 양성 대조로 판별력을 확인했다.

> ★**초판은 두 갈래로 뚫려 있었고 codex 적대 리뷰가 잡았다**(2026-08-16). `@/app/*` 만 막아서
> ⑴ 상대경로 `../app/page` ⑵ 동적 `import("@/app/page")` 가 통과했다 — 탐침으로 **실측 확인**했다.
> 지금은 `no-restricted-imports` 패턴을 `**/app/**` 까지 넓히고, `no-restricted-imports` 가
> **동적 import 를 보지 않으므로** `no-restricted-syntax` 의 `ImportExpression` 선택자를 함께 둔다.
> 두 갈래 모두 양성 대조로 error 를 확인했고, 하위 층의 합법 `app/` import 는 0건이라 오탐도 0이다.

## Consequences

### ★ 이 이동의 진짜 위험은 파일이 아니라 **검사기의 스코프**였다

`src/__tests__/no-raw-enum-labels.test.ts` 는 스캔 대상을 **디렉터리 경로 배열**로 정의하고
`walk()` 는 `existsSync` 가 false 면 **조용히 건너뛴다**. 목록을 안 고쳤으면 스코프가 통째로 비고
**테스트는 초록으로 통과**했다 — 이 레포가 반복해 덴 「빈 입력이 원하는 답」이다.

그래서 이동 **전에** 스코프 파일 수를 재고 후에 대조했다:

| 검사기                | 이동 전 | 이동 후 | 판정                                                 |
| --------------------- | ------- | ------- | ---------------------------------------------------- |
| `no-raw-enum-labels`  | 111     | **116** | ✅ (share/ 4파일 신규 편입)                          |
| `no-internal-ids`     | 203     | 203     | ✅ (술어가 `/features/`·`/components/` 를 이미 포함) |
| `design-canon-source` | 336     | 336     | ✅ (`src` 전체 `.ts`+`.tsx`, `generated/` 제외)      |

> ★**이 표의 첫 판은 틀렸다** — 「112 / 236」으로 적었고 codex 적대 리뷰가 잡았다(2026-08-16).
> 계측기 초판이 ⑴ enum 목록에 `features/backtest·dashboard` 를 **미리 넣어** 과다 계상하고
> ⑵ design-canon 을 `.tsx` 전용으로 걸어 `.ts` 와 `generated/` 규칙을 놓쳤다.
> **계측기가 대상과 다른 것을 세면 「줄었는가」 판정 자체가 무의미하다.** 위 수치는
> `origin/main` 의 테스트 목록으로 다시 잰 값이다. 결론(스코프가 안 줄었다)은 그대로다.

계측기는 `apps/web/scripts/canon-scope-census.mjs` 로 남겼다 — **다음 재배치도 이걸 먼저 돌려라.**
그리고 `no-raw-enum-labels` 의 `getScopedFiles()` 에 **디렉터리 부재 시 throw** 를 넣어
같은 침묵이 다시 나지 않게 했다.

`design-canon-source` 는 화이트리스트가 **경로 키**라서 이동 즉시 **소리 내며 red** 가 났다
(4 failed). 침묵 초록보다 나은 실패 방식이고, 경로 10건을 같은 이동표로 옮겨 닫았다.

### ★ 열거식 치환은 또 샜다 — 해석식으로 바꿔서 닫았다

상대경로 importer 를 손으로 열거한 초판이 20곳 이상을 놓쳤다. 지정자를 **importer 기준으로
해석**해 옛 경로를 얻고 이동표에 통과시키는 방식으로 바꾸자 남는 것이 0이 됐다.
★그 과정에서 `path.resolve(__dirname, "…")` 의 **파일시스템 경로**를 import 별칭으로 바꾸는
실수를 했고, vitest 가 ENOENT 로 잡았다 — **tsc 는 문자열 경로를 못 본다.**

### 검증

- `tsc --noEmit` ✅ · `eslint` 0 error ✅ · vitest **1414/1414**(219 파일, 이동 전과 동일) ✅
- e2e `chromium-design-canon` **44/44** ✅ (`/`·`/pricing`·`/sign-in`·`/maintenance`·`/waitlist` 실제 렌더)
- e2e `chromium` smoke **4/4** ✅
- 파일 수 불변 — 소스 557=557, 테스트 219=219, 라우트 `page.tsx` 목록 diff 0
- ⚠ **`e2e:authed`(86건)는 이 회차에서 못 돌렸다** — 워크트리 env 가 격리 스택(5433/6380)을
  가리키는데 그 스택 기동은 메인 체크아웃 몫이다(ADR-029 워크트리 규약). 머지 전에 메인에서 돌려라.

### ★★ 게이트를 붙이는 회차가 게이트를 세 번 잘못 붙였다 (2026-08-16 적대 리뷰 2라운드)

**⑴ 면제를 주장한 산문이 면제를 깨뜨렸다.** `ci.yml` 의 OpenAPI 스텝에
「이 스텝은 `uv run pytest` 가 아니므로 감사 대상이 아니다」라고 **주석으로 적었더니**,
`test_ci_workflow_env_parity.py` 의 `text.find("uv run pytest")` 가 그 주석을 실행 스텝으로
세어 유령 블록을 만들었다 — CI `backend (c)` 가 red 였다. 감사가 텍스트 기반인 이상 재발하므로
**주석을 우회하는 대신 감사기가 주석 줄을 지우게** 고치고 회귀 테스트 2개를 붙였다
(변이 대조: 수리를 되돌리면 3건 red).

**⑵ 같은 구멍을 형제 배선에 남겼다.** `contracts/**` 를 `ci.yml` 필터에 넣으면서
`final-gates.sh` 의 `has_be` 판정은 그대로 뒀다 — 계약만 고친 회차가 로컬에서 `건너뜀` 으로
초록이 났다. **게이트의 발화 조건을 한 곳에서만 보면 짝이 남는다.**

**⑶ 1단만 막고 2단은 열어 뒀다.** `export_openapi.py --check` 는 전량 파일만 본다. orval 이
실제로 읽는 것은 `openapi.poc.json` 이고 **그것은 실제로 drift 해 있었다**(`warnings` 필드).
`interfaces/endpoints.md` 에 「보호된다」고 쓴 문장이 그 시점에 거짓이었다. 필터에 `--check` 를
만들고 같은 게이트 3곳에 배선했다.

부수로: eslint `**/app/**` 가 `@sentry/nextjs/app/router` 같은 **벤더 하위경로**까지 물었고
(오탐, 탐침으로 실측), 템플릿 리터럴 `import(\`@/app/${n}\`)`은 **뚫렸다**. 앵커를 상대경로로
좁히고`TemplateLiteral`선택자를 추가해 4갈래 전부 error·벤더 0건을 재확인했다.`export_openapi.py`는`APP_NAME`도 고정한다 —`info.title` 이 그 값이라 머신마다 판정이 갈렸다.

### ★ 남은 긴장 — `features/dashboard` 는 이 ADR 자신의 표를 아슬하게 어긴다

적대 리뷰(2026-08-16)의 지적이고, **반박하지 않는다.**
`features/dashboard/` 는 파일 3개뿐이고 `api.ts`·`hooks.ts`·`schemas.ts` 가 없으며 소비 라우트가
**하나**다. §2 표를 그대로 읽으면 「한 라우트 전용 + 5파일 미만」이라 `_components/` 허용 칸에 든다.
게다가 `dashboard-cockpit.tsx` 가 하는 일은 feature 5종을 합성하는 것이고, §1 은 그것을 **app 의
일**이라고 적었다.

그럼에도 features 에 둔 이유는 하나다 — **소유권이 화면이 아니라 합성 그 자체**이고, 그 합성 로직이
자라면 갈 곳이 필요하다. 즉 지금은 규칙 위반이 아니라 **베팅**이다.

**되돌리는 트리거:** `/dashboard` 가 6개월 안에 형제 라우트를 얻지 못하고 파일 수도 안 늘면,
3파일을 `app/(dashboard)/dashboard/_components/` 로 돌려보내라 — 그때는 표가 옳다.
(`auth` 는 `/sign-in`+`/sign-up` 2라우트, `marketing` 은 `/`+`/pricing` 2라우트라 승격 기준을 넘는다.)

### 비목표

- `(auth)/layout.tsx` 신설로 `split-screen-shell` 흡수 — **렌더 구조 변경**이라 234파일 이동에
  동승시키지 않았다. 하고 싶으면 별건으로.
- feature barrel(`index.ts`) 강제 — 현재 12개 중 2개만 갖고 있고 소비자는 3곳뿐이다.
  deep import 가 사실상의 관례이므로 이번에 바꾸지 않는다.
- `app/` 내부 라우트 그룹 재편(`(marketing)` 신설 등) — 라우트 경로가 바뀌면 공개 URL 이 바뀐다.
