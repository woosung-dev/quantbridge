<!-- C 언어 React 이식 작업의 세션 간 인수인계 문서 -->

# QuantBridge 핸드오프 — C 디자인 언어 React 이식

갱신 2026-07-20 (4판) · **S0 완료** 세션에서 이어짐
이전 판은 `/tmp/quantbridge-handoff-react-port-20260720.md` (2판, 휘발성). **이 문서가 정본이다.**

---

## 0. 다음 세션이 할 일

**S1a — 토큰 정합.** S0 검사 장치가 전부 섰다. 이제 안전망 아래에서 토큰을 고친다.

`checklist.md` 의 S1a 섹션이 작업 목록이다. 핵심은 `.dark` 색 5건 교정 + 토큰 13건 리네임 +
`chart-tokens.ts:60-69` 동반 수정(누락 시 조용히 깨짐) + `--r: 12px` 도입이다.

★S1a 착수 첫 step = **안전망이 실제로 지키는지 확인**. `pnpm test`(design-canon-tokens /
chart-tokens-contract / design-canon-source) + `pnpm e2e:design-canon`(27) 를 baseline 으로
돌리고 시작해라. 그리고 **함정 §6-1(Turbopack CSS 캐시)** 를 반드시 다시 만난다.

S1a 가 끝나면 두 래칫이 내려가야 한다 — `design-canon-tokens` allowlist 5건 → 0,
`design-canon-public` `/` 대비 결함 2 → 0 (`--text-muted`→#8b939c 가 같은 색을 고친다).

---

## 0.5 S0 에서 확정·측정된 것 (재론 금지)

- **감사 코어 = 공유 모듈** `e2e/design-canon-audit.ts` (`runtime-check.mjs` 이식). 캘리브레이션·
  공개라우트·P1 spec 이 **모두 이 하나를 import** 한다. 사본 만들지 마라.
- **검사기 3층.** `chromium-design-canon`(CI): 캘리브레이션(프로토타입 file://) + 공개라우트(`/`·
  `/waitlist`) + 런타임 토큰 = **27 passed**. `chromium-authed`(로컬): `authed-canon-p1` P1 4라우트.
  vitest: `design-canon-source`(정적 래칫) + 기존 토큰 가드 2종.
- **baseline 실측 = [`s0-baseline.md`](./s0-baseline.md).** 이 수치가 래칫 기준선이다.
- **canon 은 게이트 아니라 지표.** 하드 게이트 = overflow·대비 AA·포커스링·콘솔·reduced-motion.
- **고아 spec** `sprint55-optimizer-bayesian` = `test.describe.skip` + 미배선. 폼 UX 가 stale
  (텍스트 입력 → `useBacktests` 피커). optimizer 이식 때 재작성.
- **`nextjs-portal`** (next dev 오버레이)는 감사 코어 포커스 검사에서 tag 제외됨.

---

## 1. 먼저 읽을 것

요약은 여기 있고 **상세는 아래에 있으니 복제하지 말고 읽어라.**

| 순서 | 경로                                                                                | 내용                                           |
| ---- | ----------------------------------------------------------------------------------- | ---------------------------------------------- |
| 1    | `docs/c-language-port/checklist.md`                                                 | S0~S9 슬라이스 + **확정 seam 5개와 진행 상태** |
| 2    | `docs/c-language-port/context-notes.md`                                             | 결정 근거 + **함정 (Turbopack 캐시 포함)**     |
| 3    | `docs/c-language-port/light-palette-trilemma.md`                                    | 라이트 팔레트 B2 확정 근거                     |
| 4    | `docs/prototypes/shotgun-2026-07/_KIT.md`                                           | 하드제약 15 · §4 워크스페이스 캐논             |
| 5    | `docs/prototypes/shotgun-2026-07/terminology-ssot.md`                               | enum 대조표 + 이식용 labels 모듈               |
| 6    | `CONTEXT.md` · `.claude/CLAUDE.md` · `docs/TODO.md` · `docs/REFACTORING-BACKLOG.md` | 프로젝트 규칙                                  |

프로토타입 확인.

```bash
cd docs/prototypes/shotgun-2026-07 && python3 serve.py
# http://localhost:4173/viewer.html
```

★열려 있던 탭은 하드 리로드해야 한다. 하단 바 빌드 스탬프(`2026-07-20f`)로 확인하라.

---

## 2. 확정된 것 (재론 금지)

| 항목                  | 확정                                                                   |
| --------------------- | ---------------------------------------------------------------------- |
| 1차 슬라이스          | 셸 + 토큰 + P1 4화면                                                   |
| 토큰 적용             | `globals.css` 전면 교체                                                |
| 스타일 아키텍처       | 시맨틱 CSS 이식 (`_kit.html` 972줄 → `@layer components`)              |
| Track A 슬롭 9종      | 이식과 동시 처리                                                       |
| 거래소 표기           | Bybit 단일                                                             |
| 디자인                | **프로토타입 17벌이 시각 정본.** 재설계 금지                           |
| **라이트 팔레트**     | **B2 확정** — `--copper #883e07` · `--bull #074b34` · `--bear #ad322a` |
| **채움 토큰**         | **제거됨.** 텍스트와 채움이 같은 토큰을 쓴다                           |
| **CI 이빨**           | 병행안 — 프로토타입+공개라우트는 CI, authed 는 로컬                    |
| **고아 spec**         | `testMatch` 배선해 살린다 (아직 미이행)                                |
| **chart-tokens 가드** | S0 에 배치 (S1a 아님). Playwright 확정 — jsdom 불가                    |

### 확정된 seam 5개

`tdd` 스킬 규칙상 **승인 안 된 seam 에는 테스트를 쓰지 않는다.** 아래가 승인된 전부다.

1. URL 의 렌더된 DOM (4폭) — overflow · 대비 · 포커스링 · reduced-motion · 콘솔 · 11px 미만
2. `resolveChartTokens()` 계약 — **완료**
3. 커밋된 소스 텍스트 — 반경 · 하드코딩 hex · 노출 em-dash (토큰 부분만 완료)
4. 검사기가 스캔한 인벤토리 (위생 메타) — 완료
5. allowlist 래칫 — 완료

---

## 3. 이번 세션이 한 일

### 3.1 라이트 팔레트 B2 확정 (`48a87a6`)

핸드오프 2판의 트릴레마 표가 **두 군데 틀렸다.**

- 프로토타입 안의 감사표가 `--copper` 를 6.26(실측 **7.53**), `--bull` 을 6.33(실측 **9.99**)으로 기재.
  색상별 일정 배율 오차이고 색값 자체는 맞다. **이 오차가 "라이트 초록이 너무 어둡다"는 쟁점을 기록에서 지우고 있었다.**
- **A 안은 ② 를 만족하지 않았다.** 채움 3색이 L\* 56.2~56.3 으로 **완전 등광도(상호 1.00)** 라
  차트 범례 키끼리 구분되지 않는다. B1 이 기각당한 결함을 그래픽 레이어로 옮긴 것이었다.

**결정적이었던 것은 픽셀 실측이다.** 4안 중 어떤 두 개를 비교해도 최대 **0.61%**,
코크핏에서 A vs A′ 는 **픽셀 0개**. 사용자의 "다 비슷해 보인다"가 정확한 관찰이었다.

**교훈 — 차이의 크기를 먼저 재라.** 트릴레마의 무게를 과대평가한 채 4벌을 만들고 비교를 시켰다.

부수 작업. 채움 토큰 3개 제거 + 소비처 8곳 환원 · `td.num` 명시도 교정 ·
감사 블록 수치 전면 재계산(치환 26건 단언 통과) · 기각안 6벌 삭제.

### 3.2 S0 검사 장치 절반 (`302b040`, `9d77e17`)

| 파일                                          | 검사                                                          | 반증 |
| --------------------------------------------- | ------------------------------------------------------------- | ---- |
| `src/__tests__/design-canon-tokens.test.ts`   | 캐논 22종 ↔ `globals.css .dark`. 17 일치/5 불일치 재현 + 래칫 | 3/3  |
| `src/__tests__/chart-tokens-contract.test.ts` | `read()` 이름 ↔ 계약 ↔ `:root`/`.dark` 정의                   | 2/2  |
| `e2e/design-canon-runtime.spec.ts`            | 10개 변수가 구동 중인 앱에서 실제 해석되는가                  | 2/2  |

playwright project `chromium-design-canon` 신설 + `pnpm e2e:design-canon` 추가.

---

## 4. 레포 상태

브랜치 **`stage/c-language-port`** · 작업 트리 clean · **main 보다 12 커밋 앞**.

S0 세션이 얹은 6 커밋 (그 아래는 이전 세션):

```
fefde1a  test(frontend): audit public routes in CI + fix a stale doc reference
e8fc657  test(frontend): aim the canon auditor at the P1 routes and freeze a baseline
bcad78c  ci(frontend): gate the design-canon project in the e2e job
45d21d9  test(frontend): quarantine the stale sprint55 optimizer orphan spec
24fde4c  test(frontend): freeze source-text canon violations with a static ratchet
97941e6  test(frontend): port the prototype canon auditor and calibrate it on 17 screens
41556f4  docs(port): S0 handoff — seams confirmed, half the harness standing   <- 이전 세션 top
```

머지는 사용자가 직접 한다. **main 직접 커밋·푸시는 영구 차단.**

CI 트리거가 `[main, "stage/**"]` 라 그 밖의 브랜치로 PR 을 올리면 lint·tsc·test·build 가 통째로 침묵한다.

---

## 5. S0 잔여 작업 — ✅ 전부 완료 (2026-07-20)

> 아래는 S0 진입 시점의 잔여 목록이고 **전부 닫혔다.** 결과는 `checklist.md` S0 섹션 +
> `s0-baseline.md` + `context-notes.md` "S0 종료" 절에 있다. 이하는 착수 당시 기록으로 보존.

### 5.1 `e2e/design-canon.spec.ts` — 가장 큰 덩어리

`docs/prototypes/shotgun-2026-07/runtime-check.mjs`(212줄)를 옮긴다.

**이미 Playwright 기반이고 핵심 로직이 URL 무관한 순수 함수다.** HTML 전용인 부분은 셋뿐이다.

- `AUDIT` `:18-110` — overflow · 대비 · canon · 11px 미만. `page.evaluate` 안에서 돈다
- `MOTION_AUDIT` `:112-122` — reduced-motion
- 포커스링 검사 `:153-175` · 콘솔 수집
- 4폭 `[1440, 1024, 768, 375]`

HTML 전용 = 파일 탐색(`:13-15`) · `pathToFileURL`(`:110`) · 인증 부재.

**canon 은 하드 실패가 아니라 지표다.** 카드 표면 기준이라 중첩 표면에서는 다크 정본도 내려간다.
판정 기준은 **"라이트가 다크보다 나쁘지 않은가"** 라는 상대 비교다.

기준선 (2026-07-20 실측).

|                                              | canon 위반 |
| -------------------------------------------- | ---------- |
| 다크 리포트 `variant-c.html`                 | 33         |
| 다크 코크핏 `screen-01-trading-cockpit.html` | 41         |
| 라이트 2벌                                   | 13 / 13    |

### 5.2 ★캘리브레이션 — 이게 순서상 먼저다

**새 spec 을 React 에 대기 전에 프로토타입 17벌에 먼저 돌려 17/17 PASS 를 재현한다.**
출력을 그대로 기록해라. 재현이 안 되면 spec 이 틀린 것이지 React 가 틀린 게 아니다.

현재 기준선 — `node runtime-check.mjs` = **17/17 PASS**, 라이트 2벌 = **2/2 PASS**.

### 5.3 나머지

- 정적 검사 확장 — 반경 스케일 · 하드코딩 hex · 노출 em-dash
  (★em-dash 는 주석 치환 후 노출 마크업만. 원시 grep 1,461건 중 대부분이 주석이고
  `"—"` 플레이스홀더 113건은 정당하다)
- React 4라우트 baseline 측정 → allowlist 초기값 확정
- **CI 배선** — `chromium-design-canon` 을 `.github/workflows/ci.yml` 에 추가.
  현재 CI 는 `pnpm e2e` = `--project=chromium` = `smoke.spec.ts` **4케이스뿐**이다
- 고아 spec `sprint55-optimizer-bayesian.spec.ts`(181줄) `testMatch` 배선 후 **실행 결과 보고**.
  한 번도 안 돌았으니 실패 가능성이 있고 그러면 고칠지 지울지 판단이 한 번 더 필요하다
- `vercel-react-best-practices` + `code-review`

---

## 6. 함정 (전부 실제로 데인 것)

1. **★Turbopack CSS 캐시가 dev 서버 완전 재기동을 넘어 산다.** 이번에 거짓 결함을 보고할 뻔했다.
   `globals.css` 를 고쳤다 되돌리면 내용이 원본과 동일해져 캐시가 "변경 없음"으로 판단하고
   stale 청크를 계속 낸다. `touch` 무효 · 재기동 무효 · `rm -rf .next` 는 권한 차단.
   **내용 변경(주석 1줄 추가 후 삭제)만이 무효화시킨다.**
   런타임 검사가 이상하면 **앱을 의심하기 전에 컴파일된 CSS 를 먼저 확인해라**
   (`page.on('response')` 로 `.css` 응답 본문을 읽는 게 가장 빠르다).
   S1a 가 `globals.css` 를 대대적으로 고치므로 반드시 또 만난다.
2. **상대 경로 명령 + `2>/dev/null` 로 에러 삼키기 금지.** 빈 출력을 부재의 증거로 읽지 마라.
3. **검사기를 만들거나 고치면 known-good 산출물에 먼저 돌려라.** 캐논 임계를 5.83 으로 넣었더니
   다크 정본이 87건 걸렸다. 임계가 틀린 것이었다(정답 **5.82**, 정의값 5.827427).
4. **단일 지표 최적화는 다른 축을 부순다.** 라이트 1차 팔레트가 배경 대비만 보고 최적화해
   bull/bear 상호를 1.01 로 만들었고, A 안은 같은 함정을 채움 레이어에서 반복했다.
5. **grep 만으로 판정하지 마라.** 주석을 공백 치환한 뒤 노출 마크업만 봐라.
6. **자기보고도 검증자 보고도 재현하라.** 이번에 "17 일치/5 불일치"를 직접 재현했고 맞았다.
   재현 없이 받았으면 그것도 남의 자기보고다.
7. **파일 단위 통과 ≠ 전체 정합.** 17벌 개별 통과 뒤 교차 감사에서 49건(BLOCKER 3)이 나왔다.
   React 에서는 **컴포넌트 경계**에서 같은 일이 일어난다. S9 가 그 대응이다.
8. **`preflight.py` 의 `C19-dark`·`C16-kitdrift` 는 라이트 파일의 기존 실패다.**
   내 수정이 만든 것으로 오인해 `_kit.html` 을 고칠 뻔했다. `git show HEAD:` 로 대조해서 확인해라.
   `_kit.html` 을 고치면 **다크 17벌이 전부 kitdrift 로 깨진다.**
9. **lint-staged 훅이 "Reverting" 을 찍어도 커밋은 될 수 있다.** `prettier-plugin-tailwindcss`
   미설치로 `.md` 포맷팅이 실패한다. 훅 출력을 믿지 말고 `git show --stat` 으로 확인해라.
10. **워크플로 에이전트가 failed 여도 파일은 있을 수 있다.**

---

## 7. 남은 부채

- **`td.num` 명시도 교정이 라이트 2벌에만 있다.** `_kit.html` 과 다크 17벌에는 없다. **S2 가 반영해야 한다.**
- `strategy.backtest_count` 정의 (완료 기준 대 전체 실행 기준) — 전략 목록 이식 시 결정
- OKX 를 `frontend/src/features/trading/schemas.ts:71` enum 에서 뺄지 — 실측 후 판단

---

## 8. 환경 메모

- **dev 서버가 3000 에 떠 있을 수 있다** (이번 세션이 띄웠다). `lsof -ti:3000` 으로 확인하고
  `kill <PID>` 로 정리해라. Playwright 는 `PLAYWRIGHT_BASE_URL=http://localhost:3000` 을 주면
  기존 서버를 재사용한다.
- ★**백엔드 8000 함정 2건 (S0 에서 실측).** (a) 포트 8000 을 cookmark(냉파) 프로젝트가
  점유할 수 있다 — `curl -s localhost:8000/openapi.json | ...` title 로 판별하고 사용자에게
  정리 요청. (b) backend `.env.local` 의 `DATABASE_URL` 이 **5433(ffwpu, 남의 DB)** 을 가리킨다.
  QuantBridge DB 는 **5436**. `make be` 를 그냥 쓰면 남의 DB 에 붙는다. 기동은 오버라이드로:
  `DATABASE_URL=...@localhost:5436/quantbridge TIMESCALE_URL=... REDIS_URL=...6380/0 FRONTEND_URL=http://localhost:3000 uv run uvicorn src.main:app --port 8000`.
- ★**authed 검사 전 storageState 재발급.** `pnpm exec playwright test --project=setup` 1회.
  쿠키 만료 타임스탬프가 미래여도 Clerk 세션은 죽어 있을 수 있다 (전부 sign-in 리다이렉트로 판별).
- `rm -rf` 는 이 환경에서 권한 차단된다. 캐시 정리가 필요하면 사용자에게 `! rm -rf frontend/.next` 를 요청해라.
- 프로토타입 뷰어는 4173, `python3 serve.py`.

---

## 9. 다음 세션 첫 스텝 (S1a)

1. §0 + §0.5 + `checklist.md` S1a 섹션 + `context-notes.md` "S0 종료" 절 읽기
2. **안전망 baseline 재확인** — `cd frontend && pnpm test`(design-canon-tokens / chart-tokens-contract /
   design-canon-source 그린) + `pnpm e2e:design-canon`(27 passed). 남의 자기보고다, 재현하고 시작해라
3. S1a 착수 — `.dark` 색 5건 + 토큰 13 리네임 + `chart-tokens.ts:60-69` 동반 + `--r: 12px`.
   ★**함정 §6-1 (Turbopack CSS 캐시)** 를 반드시 다시 만난다
4. 두 래칫이 내려가는지 확인 — `design-canon-tokens` 5→0, `design-canon-public` `/` 2→0
5. `live-smoke` + `vercel-react-best-practices` + `code-review` (S1a 는 globals.css 를 대대적으로 고친다)

---

**민감정보 점검.** 이 문서와 참조 산출물에 API 키·비밀번호·토큰 없음.
개인 식별자는 워크스페이스 소유자 계정명 `woosung` 하나이며 프로토타입의 "가공 인물 금지" 규칙에 따른 의도된 실제 값이다.
