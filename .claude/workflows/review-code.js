export const meta = {
  name: 'review-code',
  description: '차원별 병렬 서브에이전트로 변경분을 리뷰하고 각 발견을 adversarial 검증',
  phases: [
    { title: 'Review', detail: '차원별(correctness·security·conventions) 병렬 리뷰' },
    { title: 'Verify', detail: '각 발견을 3명 skeptic이 반박, 2/3 다수결로 false positive 제거' },
  ],
}

// ── 입력 ─────────────────────────────────────────────────────────────────────
// args = { diff: string, files: string, repoDocs: string, scope?: string }
//   diff:     통합 diff 텍스트 (변경 라인 번호 포함)
//   files:    변경 파일 목록(개행 구분)
//   repoDocs: AGENTS.md + CONTEXT.md + apps/api/AGENTS.md + apps/web/AGENTS.md 본문(가드레일)
//   scope:    리뷰 범위 설명 (예: "main...HEAD") — 표시용
let input = args
if (typeof input === 'string') {
  try {
    input = JSON.parse(input)
  } catch {
    input = {}
  }
}
const diff = input?.diff ?? ''
const files = input?.files ?? ''
const repoDocs = input?.repoDocs ?? ''

log(`[review-code] args=${typeof args} diffLen=${diff.length} filesLen=${files.length} docsLen=${repoDocs.length}`)

if (!diff.trim()) {
  log('[review-code] diff가 비어 종료 (입력 전달 확인 필요)')
  return { confirmed: [], stats: { total: { raw: 0, confirmed: 0 }, byDim: {}, bySeverity: {} } }
}

// ── 스키마 ───────────────────────────────────────────────────────────────────
const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['severity', 'file', 'line', 'title', 'tldr', 'good', 'fix'],
        properties: {
          severity: { type: 'string', enum: ['critical', 'major', 'minor', 'nit'] },
          file: { type: 'string', description: '저장소 루트 기준 경로 (예: apps/api/src/trading/service.py)' },
          line: { type: 'number', description: 'diff 신규(RIGHT) 측 라인 번호 — 인라인 코멘트 게시용' },
          title: { type: 'string', description: '한 줄 제목' },
          tldr: { type: 'string', description: '무엇이/왜 문제인가 한 줄' },
          good: { type: 'string', description: '잘 지킨 맥락/규칙 (없으면 빈 문자열)' },
          fix: { type: 'string', description: '수정 방안 — 가능하면 코드 스니펫' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['isReal', 'reason'],
  properties: {
    isReal: { type: 'boolean', description: '진짜 문제이며 보고할 가치가 있으면 true' },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    reason: { type: 'string', description: '판단 근거 한 줄' },
  },
}

// ── 차원 정의 (MVP 3개) ──────────────────────────────────────────────────────
// 향후 확장: 이 배열에 { key, prompt } 항목을 추가하기만 하면 된다.
const common = (dimensionName) =>
  `너는 QuantBridge 코드 리뷰어다. 아래 diff에서 **${dimensionName}** 차원만 검토한다.\n` +
  `\n규칙:\n` +
  `- 이 차원에 해당하는 위반·버그만 보고하라. 다른 차원·스타일 취향·범위 밖 개선은 무시하라.\n` +
  `- 추측성 지적 금지. diff와 가드레일 문서로 확인 가능한 것만 보고하라.\n` +
  `- 발견이 없으면 findings를 빈 배열로 반환하라. 억지로 만들지 마라.\n` +
  `- 각 발견의 file은 저장소 루트 기준 경로, line은 diff 신규(RIGHT) 측 라인 번호로 적어라(인라인 코멘트 게시에 쓰인다).\n` +
  `- good은 해당 위치에서 잘 지킨 규칙/맥락(없으면 빈 문자열), fix는 수정 방안(가능하면 코드).\n` +
  `\nseverity 기준:\n` +
  `- critical: 보안 취약점 · 자금/주문 안전 훼손 · 데이터 무결성 훼손 · 명백한 런타임/로직 버그(머지 차단 수준)\n` +
  `- major: Golden Rules·CRITICAL 규칙 위반 · 잘못된 동작(머지 전 수정 필요)\n` +
  `- minor: 개선 권장(머지는 가능)\n` +
  `- nit: 취향/사소\n`

const DIMENSIONS = [
  {
    key: 'correctness',
    prompt:
      common('correctness (정확성·데이터 무결성)') +
      `\n이 차원의 집중 검사 항목(QuantBridge CRITICAL 규칙):\n` +
      `- Decimal-first — 사거리는 BE(Python)다: 가격·수량·수익률·레버리지 등 금융 숫자는 Decimal 사용, float 금지. 합산은 Decimal(str(a)) + Decimal(str(b)) — float 공간에서 합산 후 변환하면 위반. FE(TS)에서 zod transform 등의 Number/parseFloat 사용은 정상 패턴이므로 그것만으로 위반으로 잡지 마라.\n` +
      `- 멱등성: 주문 발주는 orders.idempotency_key 계약을 지나는가 — DB 계약은 partial unique index uq_orders_idempotency_key(WHERE idempotency_key IS NOT NULL, src/trading/models.py)이고 발주 경로는 OrderService.execute(req, idempotency_key=...)가 RedisLock("idem:trading:{key}") + get_by_idempotency_key 재사용으로 지킨다(src/trading/services/order_service.py). 이 계약(partial WHERE 포함)을 약화하거나 이를 우회하는 발주 경로를 만들면 위반. Order 상태 전이(pending → submitted → filled/rejected/cancelled)는 조건부 UPDATE race-winner인가. LiveSignalEvent는 transactional outbox(pending → dispatched/failed)로만 dispatch되는가.\n` +
      `- Celery prefork-safe: task entry는 asyncio.run() 대신 run_in_worker_loop() 사용. run_in_worker_loop 중첩 호출 금지. per-call engine 생성 후 finally에서 dispose. module-level asyncio 객체(Semaphore/Lock/Event/Queue) 신규 추가는 allowlist 절차 필요. 백테스트·최적화·스트레스 테스트는 반드시 Celery 비동기 — API 핸들러 직접 실행 금지.\n` +
      `- pine_v2 시맨틱: exec()/eval() 절대 금지(인터프리터 패턴, ADR-003). 미지원 Pine 함수가 1개라도 포함되면 전체 Unsupported — 부분 실행 금지(all-or-nothing). pine_v2는 신호의 SSOT이지 체결이 아니다 — 라이브 조건부 진입 체결 권한은 주문 원장에 있고(ADR-025) 엔진이 원장 없이 체결을 만들면 위반. 백테스트 경로는 인자 기본값으로 byte-identical이 유지돼야 한다.\n` +
      `- 비동기 SQLModel: session.exec() 절대 금지 — await session.execute(select(...)) 후 .scalars(). N+1은 selectinload로 방지.\n` +
      `- commit 보장(LESSON-019): service mutation(repo.save/update/delete + commit 책임)이 추가/수정되면 동일 PR에 commit-spy 회귀 테스트(tests/<domain>/test_*_commits.py)가 있는가.\n` +
      `- 그 외 일반 로직 버그(off-by-one, null/None 처리, 잘못된 비교, await 누락 등).`,
  },
  {
    key: 'security',
    prompt:
      common('security (보안·거래 안전)') +
      `\n이 차원의 집중 검사 항목(QuantBridge Golden Rules):\n` +
      `- 시크릿 하드코딩 절대 금지: API 키·DB 패스워드 등은 SecretStr 타입 + .get_secret_value(). 거래소 API Key는 AES-256(Fernet) 암호화 후 DB 저장 — 평문 컬럼 금지. 응답·로그·에러 body에 시크릿 평문 반사 금지.\n` +
      `- Repository layer 밖 DB 접근 금지: AsyncSession은 Repository만 보유한다. service.py에 AsyncSession import가 보이면 위반, router에서 DB 접근도 위반.\n` +
      `- .env.example에 없는 환경 변수를 코드에서 참조하면 위반.\n` +
      `- 인증: JWT 검증기는 realtime/auth.py 한 곳(EdDSA 단일 알고리즘, exp/sub/iss/aud 필수) — 새 검증 경로를 만들면 위반. FE는 useAuthCtx() 단일 seam — useSession()/getAuthToken() 직접 호출·직접 JWT 파싱 금지. getSessionCookie()를 인증 게이트로 쓰면 위반(쿠키 존재만 본다 — UX 리다이렉트 전용). 보호 라우트는 proxy.ts의 auth.api.getSession() 완전 검증.\n` +
      `- CORS/Origin: BETTER_AUTH_URL·FRONTEND_URL 등 origin 설정이 어긋나면 전건 401/CORS 침묵 거부 — origin·URL 하드코딩이나 파생 경로 우회를 의심하라.\n` +
      `- 거래(실주문) 안전: 계정 모드는 Bybit demo만 허용 — live 경로를 여는 변경(AccountModeNotAllowed 우회)은 critical. Kill Switch 게이트를 우회하는 발주 경로 금지. trailing stop은 entry 주문에 주입 금지 — 체결 후 set_trading_stop으로 포지션에 부착.`,
  },
  {
    key: 'conventions',
    prompt:
      common('conventions & architecture (컨벤션·아키텍처)') +
      `\n이 차원의 집중 검사 항목(QuantBridge 규칙):\n` +
      `- BE 3-Layer: 도메인은 router/service/repository/schemas/models/dependencies/exceptions 구조. Router는 HTTP 전용(비즈니스 로직 금지), Service는 Repository만 주입, Depends() 조립은 dependencies.py에서만. Pydantic V2 패턴(.model_dump(), @model_validator) 준수.\n` +
      `- FE FSD Lite: 화면 컴포넌트의 기본 자리는 features/<domain>/components/다(ADR-035) — app/**/_components/는 한 라우트 전용 + 순수 표현 + 5파일 미만만 허용. features/·components/·lib/·hooks/·store/에서 @/app/* import 금지.\n` +
      `- React Hooks 안전 H-1~H-3: (H-1) useEffect dep에 불안정 참조(React Query data·Zustand selector·watch()·parse() 결과) 금지. (H-2) queryKey에 getToken 포함 금지 — userId를 key factory 첫 인자로. (H-3) render body에서 ref.current 대입 금지 — deps 없는 sync useEffect로.\n` +
      `- error.tsx 의무: 주요 dashboard route마다 error.tsx("use client" + reset 버튼) 필요. if (isLoading)/if (error) 워터폴 대신 Suspense + ErrorBoundary.\n` +
      `- FE 기타: zod는 "zod/v4" 경로 import(v3 "zod" 금지). components/ui/(shadcn) 직접 수정 금지 — 래핑으로 확장. any 금지(unknown + Type Guard). "use client"는 말단 컴포넌트에만.\n` +
      `- 소스 첫 3줄 한국어 주석 헤더(구 header-audit 흡수, BL-307): apps/api/src/**/*.py · apps/web/src/**/*.{ts,tsx} 신규/변경 파일은 첫 3줄 안 **주석/독스트링 구간**에 한글이 1자 이상 있어야 한다. 문자열 리터럴 안 한글은 미충족. 면제: components/ui/**(shadcn 벤더) · 테스트 파일(test_*.py/*_test.py/*.test.ts(x)/*.spec.ts(x)/conftest.py, /tests/·/__tests__/ 경로) · __init__.py · index.ts(x) · *.d.ts · config·generated 파일.`,
  },
]

// ── 검증 폭발 방지 ───────────────────────────────────────────────────────────
const MAX_PER_DIM = 8 // 차원당 검증 대상 finding 상한. 초과분은 log로 고지(silent cap 금지).
const SEVERITY_RANK = { critical: 0, major: 1, minor: 2, nit: 3 } // slice 전 정렬용 — 잘리는 것이 nit 쪽이 되게.

// ── Review → Verify 파이프라인 ───────────────────────────────────────────────
// pipeline: 한 차원의 발견이 검증되는 동안 다른 차원은 아직 리뷰 중이어도 됨(barrier 불필요).
const results = await pipeline(
  DIMENSIONS,
  // 1단계: 차원별 리뷰
  (d) =>
    agent(
      `${d.prompt}\n\n## 가드레일 문서\n${repoDocs}\n\n## 변경 파일\n${files}\n\n## diff\n${diff}`,
      { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA },
    ),
  // 2단계: 각 발견을 3명 skeptic이 반박 → 2/3 다수결
  (review, dim) => {
    const found = (review?.findings ?? [])
      .map((f) => ({ ...f, dimension: dim.key }))
      .sort((a, b) => (SEVERITY_RANK[a.severity] ?? 4) - (SEVERITY_RANK[b.severity] ?? 4))
    if (found.length > MAX_PER_DIM) {
      log(`${dim.key}: 발견 ${found.length}건 중 상위 ${MAX_PER_DIM}건만 검증(상한). 나머지는 미검증으로 제외.`)
    }
    return parallel(
      found.slice(0, MAX_PER_DIM).map((f) => () =>
        parallel(
          Array.from({ length: 3 }, (_, i) => () =>
            agent(
              `다음 리뷰 발견이 진짜 문제인지 반박하라. 의심부터 하고, 확신이 없으면 isReal=false를 기본값으로 삼아라.\n\n` +
                `[${f.severity}] ${f.title}\n위치: ${f.file}:${f.line}\nTL;DR: ${f.tldr}\n제안된 수정: ${f.fix}\n\n` +
                `아래 diff·가드레일·차원 리뷰 기준으로 교차검증하라. 발견이 실제 변경된 코드에 근거하는지, 오해/허위(예: 존재하지 않는 라인, 이미 처리된 케이스)는 아닌지 확인하라. 차원 리뷰 기준에만 명시된 규칙도 유효한 근거다 — 가드레일 문서에 없다는 이유만으로 기각하지 마라.\n\n` +
                `## 이 차원(${dim.key})의 리뷰 기준\n${dim.prompt}\n\n## 가드레일 문서\n${repoDocs}\n\n## diff\n${diff}`,
              { label: `verify:${dim.key}:${i}`, phase: 'Verify', schema: VERDICT_SCHEMA },
            ),
          ),
        ).then((votes) => {
          const yes = votes.filter(Boolean).filter((v) => v.isReal).length
          return { ...f, real: yes >= 2, votes: yes }
        }),
      ),
    )
  },
)

// ── 집계 ─────────────────────────────────────────────────────────────────────
const all = results.flat().filter(Boolean)
const confirmed = all.filter((f) => f.real)

const byDim = {}
for (const f of all) {
  byDim[f.dimension] = byDim[f.dimension] ?? { raw: 0, confirmed: 0 }
  byDim[f.dimension].raw++
  if (f.real) byDim[f.dimension].confirmed++
}

const bySeverity = { critical: 0, major: 0, minor: 0, nit: 0 }
for (const f of confirmed) bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1

log(
  `검증 완료: 후보 ${all.length}건 → 확정 ${confirmed.length}건 ` +
    `(critical ${bySeverity.critical} · major ${bySeverity.major} · minor ${bySeverity.minor} · nit ${bySeverity.nit})`,
)

return {
  confirmed,
  stats: { total: { raw: all.length, confirmed: confirmed.length }, byDim, bySeverity },
}
