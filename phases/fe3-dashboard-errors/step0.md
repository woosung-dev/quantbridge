# Step 0: dashboard-error-boundaries

## 읽어야 할 파일

- **대상 7개** — `apps/web/src/app/(dashboard)/error.tsx`(35줄) ·
  `(dashboard)/{backtests,dashboard,orders,strategies,trading}/error.tsx`(39~43줄) ·
  `apps/web/src/app/invite/[token]/error.tsx`(23줄)
- `apps/web/src/app/(dashboard)/backtests/[id]/__tests__/error.test.tsx` —
  ★**이 회차의 관용구 정본이다. 먼저 읽고 같은 모양으로 써라**(`render` + `reset` mock +
  `fireEvent` + `digest` 단언). 그 파일은 **고치지 마라** — 이 lane 소유가 아니다
- `apps/web/AGENTS.md` §3/§6 — `error.tsx` 가 **의무**인 근거

## 배경

`error.tsx` 는 이 앱에서 **규칙으로 강제된 파일**이다(`apps/web/AGENTS.md` §3/§6).
그런데 9개 중 **테스트가 있는 것은 2개뿐**이고(`app/error.tsx` · `backtests/[id]/error.tsx`),
나머지 **7개는 어떤 테스트도 import 하지 않는다**(전이 폐포 실측 2026-08-21).

★**에러 경계가 조용히 깨지면 사용자는 흰 화면을 본다** — 그 화면은 정의상 **이미 뭔가 실패한
뒤**라 아무도 신고하지 않는다. 그래서 이 축은 다른 어떤 화면보다 **자동 검증에 의존한다.**

★**일곱은 서로 다른 파일이지만 계약은 같다** — Next.js 는 `{ error: Error & { digest?: string },
reset: () => void }` 를 준다. 이 lane 은 **그 계약이 일곱 곳에서 지켜지는지**를 한 파일로 잰다.

## 작업

`apps/web/src/app/(dashboard)/__tests__/error-boundaries.test.tsx` **하나**를 신설한다.
일곱을 각각 default import 해서(상대 경로 — `../error` · `../backtests/error` ·
`../../invite/[token]/error` 등) `it.each` 로 돌린다.

★**경로에 `(dashboard)`·`[token]` 같은 괄호가 들어간다** — **import 문에서는 문제없다**(CONTROL
실측). 문제가 되는 것은 vitest **CLI 필터**뿐이고 AC 는 이미 작은따옴표로 감싸 뒀다.

### 최소한 이 열넷을 덮어라 (케이스 ≥14 — parametrize 전개 포함)

★**공통 계약 5축을 일곱 전부에 parametrize 로 돌려라.** 아래 1~5 가 그것이다.

1. ★**던지지 않고 렌더된다** — 일곱 각각 `render(<E error={err} reset={vi.fn()} />)` 가 성공하고
   `document.body.textContent` 가 **비어 있지 않다**. ★양성 대조다
2. ★★**`reset` 이 실제로 배선돼 있다** — 일곱 각각에서 **버튼을 클릭하면 `reset` 이 1회 불린다**.
   ★**이것이 이 lane 의 핵심이다** — 「다시 시도」가 아무것도 안 하는 경계는 **없는 것보다 나쁘다**
   (사용자가 고칠 수 있다고 믿게 만든다). 버튼을 못 찾으면 그 파일은 결함이니 `summary` 에 적어라
3. ★**사람이 읽을 수 있는 헤더가 있다** — 일곱 각각 `heading` role 이 1개 이상이고 텍스트가
   비어 있지 않다. ★문구 전문은 단언하지 마라
4. ★★**`digest` 가 화면에 나온다** — `error.digest = "ref-xyz-123"` 를 주면 그 문자열이
   화면 어딘가에 있다. **없으면 사용자가 신고해도 로그를 못 찾는다**(observability 계약).
   ★**일곱 중 digest 를 안 찍는 것이 있으면 고치지 말고 `summary` 에 파일명을 적어라**
5. ★**`digest` 가 없어도 죽지 않는다** — `digest` 를 **주지 않고** 렌더해도 던지지 않는다
   (`error.digest` 는 optional 이다 — `undefined` 를 그대로 출력해 `undefined` 가 화면에
   나가는지도 함께 보고 `summary` 에 적어라)
6. ★**음성 대조 — 서로 다른 경계는 서로 다른 화면이다** — 일곱의 `textContent` 를 모아
   **Set 크기가 5 이상**인지. 전부 같은 문자열이면 누군가 복사만 하고 문구를 안 고친 것이다
   (숫자는 하한이다 — 일부가 같아도 되지만 **전부 같으면 안 된다**)
7. ★**`cleanup()` 을 `afterEach` 에 걸어라** — 일곱을 연속 렌더하므로 안 걸면 6번이 거짓 통과한다

★**`console.error` 를 스파이로 막아라** — React 가 에러 컴포넌트 렌더 시 경고를 찍으면 로그가
지저분해지고, 다른 lane 과 같은 프로세스를 공유하지는 않지만 실패 원인 판독을 방해한다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/(dashboard)/__tests__/error-boundaries.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/(dashboard)/__tests__/error-boundaries.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 14
cd apps/web && pnpm exec eslint 'src/app/(dashboard)/__tests__/error-boundaries.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★★**경로를 작은따옴표로 감싼 것은 의도다** — `(dashboard)` 의 괄호를 셸이 서브셸로 읽는다.
★큰따옴표 이스케이프(`\"`)로 바꾸지 마라 — 러너는 AC 를 `bash -c` 로 돌리는데 거기서 깨진다
(2026-08-21 CONTROL 이 착수 전에 밟았다).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수 · **4번에서 digest 를 안 찍은 파일 목록** · **6번 Set 크기 실측값**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **일곱 `error.tsx` 를 수정하지 마라.** 결함(reset 미배선 · digest 미출력)은 `summary` 한 줄로
- ★**`backtests/[id]/__tests__/error.test.tsx` 를 고치지 마라** — 선례이고 이 lane 소유가 아니다
- ★**`app/__tests__/error.test.tsx` 도 건드리지 마라** — 이미 있고(4 케이스) 다른 파일이다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
