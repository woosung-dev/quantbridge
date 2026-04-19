# Sprint FE-B Plan — `/trading` 모바일 overflow + 빈 상태 (ISSUE-005 / ISSUE-006)

> Worktree: `.claude/worktrees/feat+fe-b` · Branch: `feat/fe-b-trading-mobile-empty` · Base: `stage/fe-polish` (06f10f0)

---

## 1. 사전 확인 결과

코드 grep 결과 **ISSUE-005(overflow)는 부분 선반영** 상태:

- `frontend/src/features/trading/components/orders-panel.tsx`
  - 이미 `<div className="overflow-x-auto"><table className="... min-w-[600px]">` 적용됨
- `frontend/src/features/trading/components/exchange-accounts-panel.tsx`
  - 이미 `<div className="overflow-x-auto"><table className="... min-w-[520px]">` 적용됨

→ ISSUE-005 는 **추가 코드 변경 없음**. 단, 375 / 768 / 1024 px 3 viewport live smoke 로 실측 검증.

ISSUE-006(빈 상태)는 **둘 다 미반영**:

- `OrdersPanel`: `data.items` 가 비어 있을 때도 헤더 + 빈 `<tbody>` 만 렌더링.
- `ExchangeAccountsPanel`: `data` 가 빈 배열일 때도 헤더 + 빈 `<tbody>` 만 렌더링.

→ 빈 상태 분기 추가 필요. 기존 `strategy-empty-state.tsx` 의 시각 패턴(점선 보더 카드 + 아이콘 + copy + CTA Button)을 차용하되, **trading 도메인 스코프 안**에 배치.

기존 ui 컴포넌트:
- `src/components/ui/button.tsx` (shadcn `Button`, `render={<Link />}` + `nativeButton={false}` 패턴 사용 가능)
- `lucide-react` 아이콘 가용 (`PackageIcon`, `WalletIcon` 등)

라우트 확인:
- `/strategies` 존재
- `/trading/accounts/new` 미존재 → SSOT 명시: 폴백 `/trading`

---

## 2. 변경 사항

### 2.1 신규 컴포넌트

`frontend/src/features/trading/components/trading-empty-state.tsx` (신규)

- props: `{ icon, title, description, ctaLabel, ctaHref }`
- 시각: 점선 border + 중앙 아이콘 원 + h3 + p + Button(Link)
- 도메인 한정 재사용 (Recent Orders / Exchange Accounts 두 케이스)

### 2.2 `orders-panel.tsx` 수정

- `data.items.length === 0` 일 때 `<TradingEmptyState>` 분기 (헤더는 유지: "Recent Orders (0)")
  - title: `아직 주문이 없습니다.`
  - description: `전략을 실행하면 여기에 표시됩니다.`
  - ctaLabel: `전략 보기`
  - ctaHref: `/strategies`
- 기존 `overflow-x-auto` 래퍼는 그대로 유지

### 2.3 `exchange-accounts-panel.tsx` 수정

- `data.length === 0` 일 때 `<TradingEmptyState>` 분기 (헤더는 유지)
  - title: `연결된 거래소 계정이 없습니다.`
  - description: `계정을 추가하고 자동매매를 시작하세요.`
  - ctaLabel: `계정 추가`
  - ctaHref: `/trading` (SSOT 폴백 — accounts/new 라우트 미존재)
- 기존 `overflow-x-auto` 래퍼는 그대로 유지

### 2.4 단위 테스트

- `__tests__/OrdersPanel.test.tsx` — 기존 1건 그대로 통과 보장
- `__tests__/OrdersPanel.empty.test.tsx` (신규)
  - apiFetch mock → `{ items: [], total: 0 }` → empty state copy + CTA href 검증
- `__tests__/ExchangeAccountsPanel.empty.test.tsx` (신규)
  - apiFetch mock → `[]` → empty state copy + CTA href 검증

---

## 3. 규칙 준수 체크리스트 (LESSON-004~006 / TS strict / 반응형)

- [ ] `react-hooks/*` eslint-disable 없음 (LESSON-004)
- [ ] 신규 컴포넌트는 hooks 사용 안 함 (순수 presentational) → effect dep 이슈 없음
- [ ] TypeScript strict, `any` 금지 (LESSON / common typescript.md)
- [ ] 빈 상태 컴포넌트는 모바일 320px 부터 정상 (max-w + p-N + center align)
- [ ] CTA 는 shadcn `Button` 사용, 직접 ui 수정 없음
- [ ] queryFn / queryKey 변경 없음 (LESSON-005 영향 없음)
- [ ] render body ref.current 대입 없음 (LESSON-006)
- [ ] 모든 dev/mcp orphan 정리 (LESSON-007)

---

## 4. 검증 단계

### 4.1 Self-verification
```bash
cd frontend
pnpm lint                  # 0 / 0
pnpm tsc --noEmit          # 통과
pnpm test -- --run         # 신규 2건 + 기존 통과
pnpm build                 # 통과
```

### 4.2 Live smoke (Playwright MCP)
1. `pnpm dev &` → :3000 또는 :3001 대기
2. 3 viewport: 375 / 768 / 1024 px → `/trading` 가로 스크롤 행동 정상, 레이아웃 깨짐 0
3. 빈 상태 (mock 데이터로 trading 페이지가 빈 응답을 받게 하거나 dev 시드 비우기) → copy + CTA 표시 확인
4. Console error 0
5. CPU 6회 × 10s 샘플링 → 80% 초과 0건 (LESSON-004 재발 방지)
6. `pkill -f next-server` + mcp-chrome 정리

### 4.3 Evaluator dispatch
- subagent_type: `superpowers:code-reviewer` (fallback: `general-purpose`)
- isolation: `worktree`
- Worker 프롬프트 §6 의 Evaluator 프롬프트 그대로

### 4.4 PR
- base `stage/fe-polish` / head `feat/fe-b-trading-mobile-empty`
- title: `feat(fe-b): /trading 모바일 overflow + 빈 상태 UX (ISSUE-005/006)`

---

## 5. 위험 요소

| 위험 | 완화 |
|------|------|
| 빈 상태에서 dev 시드가 항상 채워져 있어 live 검증 어려움 | apiFetch mock 단위 테스트로 보강 + Playwright route mock 또는 DB seed 비움 |
| `Button` `render={<Link/>}` API 가 v4 에서 변경됐을 수 있음 | 기존 `strategy-empty-state.tsx` 패턴 그대로 차용 |
| `overflow-x-auto` 가 이미 적용돼 있어도 외곽 컨테이너 제약 (max-w-6xl + p-6) 으로 375 px 에서 다른 곳이 깨질 가능성 | live smoke 로 다른 영역까지 함께 검증 |

---

## 6. 커밋 계획 (Conventional)

1. `feat(fe-b): trading 빈 상태 컴포넌트 + Recent Orders/Exchange Accounts 분기` — 본 작업
2. `test(fe-b): trading 빈 상태 단위 테스트` — 신규 테스트
3. `chore(fe-b): live smoke 로그 + 플랜 정리` (필요 시)

총 2~3 커밋.
