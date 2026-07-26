<!-- C 이식 잔여 완주 세션(2026-07-21~)의 운영 계약 — compaction 후에도 이 파일이 프롬프트를 대신한다 -->

# C 이식 잔여 완주 — 운영 계약 (2026-07-21 확정)

> 이 문서는 세션 프롬프트의 운영 정책을 영속화한 것이다. 컨텍스트 요약(compaction)이 지나가면
> **이 파일 + 정본 3종(HANDOFF/checklist/context-notes) + 플랜(`~/.claude/plans/c-react-greedy-stardust.md`)** 을 다시 읽고 이어간다.
> 프롬프트에만 사는 정책이 없어야 한다.

---

## 0. 세션 구성 (불변)

- 오케스트레이터 = fable. **직접 코드 수정 금지.** 예외 3종만: cherry-pick 충돌 union 해소 · 1줄급 통합 마찰 · 문서.
- 구현은 전부 opus 워커: Workflow `agent()` 에 `opts.model:'opus'` + `opts.agentType:'general-purpose'`.
- 워커 산출 = 래칫 숫자·exit code·변경 파일·커밋 해시·falsifiable 스킬 보고만. 파일 덤프 금지.
- 워커 자기보고는 게이트 직접 재현 후에만 신뢰 (S6 focus=0 보고 → 재현 focus=2 실측 선례).
- 브랜치 `stage/c-port-remaining` (main `123ba7f` 베이스). 슬라이스 단위 커밋.

## 1. 사용자 사전 확정 4건 (재론 금지)

1. **범위 = 전부.** 13벌(screen-05~17) + variant-c(→ /backtests/[id]) + 부채(trading §05 재스킨 · StateBox 6곳 · kpi-pnl 오류 표기 · P1 밖 반경/stale-var).
2. **전역 카퍼 :focus-visible 링 = 유지.** 각 페이지 이식 시 그 페이지의 자체 링을 제거해 이중 링 해소.
3. **머지 정책 = PR까지만.** 중간 슬라이스는 로컬 커밋만. 전부 끝나면 푸시(`QB_PRE_PUSH_BYPASS=1`) → stage→main PR → CI 6체크 통과 확인까지 자동. squash 버튼은 사용자.
4. **codex 정책 = 2지점.** 플랜 확정 직후 1회 + 최종 누적 diff 1회. (HANDOFF 5판 §2 의 "마지막 1회로 모은다"는 슬라이스-사이 게이트 제거를 뜻함 — 본 정의로 동기화됨.)

## 2. 본 세션 사용자 확정 2건 (2026-07-21 플랜 단계)

- **strategy.backtest_count = 열 미렌더** (§4.9 + 원장 §4.2 미해소 지침).
- **OKX = FE 등록 폼에서 제거** (schemas.ts:71 enum + SelectItem + passphrase superRefine + zod-v4-resolver 주석. 백엔드 불변. 마케팅 화면 로드맵 표기는 유지).

일반 규칙: 스키마·원장을 건드리는 비가역 결정이 실행 중 새로 나오면 가정으로 밀지 말고 **보수 기본값 + context-notes 기록**으로 진행하고, 사용자 보고 시점에 배칭해 묻는다.

## 3. 게이트 판정 3분류 (혼용 금지)

- **ⓐ hard-fail** (overflow·대비 AA·포커스링·콘솔·reduced-motion): 증가 금지, **신규 화면은 0 으로 진입**. allowlist 등재 시 사유 명기 + 해소 슬라이스 지정. canon 카운트는 soft 지표 — 게이트 아님.
- **ⓑ 래칫** (KNOWN_MISMATCHES·radius/hex/em-dash·HARDFAIL_ALLOWLIST): **감소 또는 유지+사유.** 이미 0 인 것은 0 유지 확인. "무조건 감소"를 무결함 슬라이스에 요구하지 않는다.
- **ⓒ coverage** (게이트 탈출 방지 — 본 세션 신설): **단조 증가만 허용.** 화면 슬라이스마다 오케스트레이터가 직접
  ① `pnpm exec playwright test --list` 로 신규 라우트 케이스가 실제 등장하는지 확인 — testMatch 함정 2종: canon 은 `design-canon-.*\.spec\.ts$` 정규식, **authed 는 열거식**(신규 spec 파일명은 config testMatch 에도 추가해야 발견됨).
  ② 기대 passed 수를 슬라이스마다 +N 으로 갱신 추적 (baseline: canon 29 · authed 5).
  ③ 신규 공개 라우트는 design-canon-public + live-smoke 방문 목록에, authed 라우트는 authed spec 라우트 배열에 실제 등장하는지 grep 확인. 개수가 안 늘었으면 그 화면은 게이트 밖 — 통과시키지 않는다.
- 공통: passed 수와 함께 **skipped=0** 확인. 판정은 반증 형식. **게이트 재현은 항상 직렬 실행** (동시 발사 시 dev 서버 부하 위양성 — 2026-07-21 실측).
- 검사기 신설·스코프 확장 시: known-good 그린 재현 → 반증 1회(결함 주입→FAIL→복원) → 적용.

## 4. 스킬 게이트 (화면 슬라이스마다, 워커가 직접 — falsifiable 형식 강제)

워커 프롬프트에 그대로 지시한다 — "구현 완료 후 Skill 툴로 아래 스킬을 정확히 이 이름으로 순서대로 호출하고, 각 결과를 falsifiable 형식으로 보고하라. '통과' 한 단어 보고는 무효다":

1. `design-taste-frontend` — 판정 축 하나: "이식하며 슬롭 패턴(가짜 라이브 신호·무의미 그라디언트·템플릿 냄새·과장 카피·em-dash 산문)을 새로 들여왔는가". 발견 시 항목+파일:줄, 0건이면 검사한 패턴 목록 열거. 프로토타입 "개선" 제안은 불채택.
2. `vercel-react-best-practices` — 위반 시 rule 이름+파일:줄+수정, 0건이면 검토 카테고리(리렌더·번들·데이터페칭·차트 identity) 열거. React Compiler 비활성 전제.
3. `code-review` 자가 2축 — Standards: 레포 규칙(.ai/rules/\*) 하드 위반 0(위반 시 파일:줄) / Spec: checklist 해당 슬라이스 요구 대비 누락 0(누락 시 항목 명시).

가드 신설 시 tdd(red 대체 = 반증). 마케팅 4벌 완료 후 `ui-ux-pro-max` 1회.

**오케스트레이터 재현 규칙:** 시각 정본 충실도는 자동 게이트가 못 본다(canon 은 대비·오버플로만 — 전혀 다른 레이아웃도 통과 가능). 화면 슬라이스마다 오케스트레이터가 ① 1440px 스크린샷을 직접 찍어 프로토타입과 육안 대조(구조·섹션 순서·칩·표 — 공식 게이트) ② 워커에게 프로토타입 유래 핵심 시맨틱 클래스 구조를 assert 하는 컴포넌트 테스트를 요구. 스킬 게이트 1·2·3 자체는 워커 자기보고를 신뢰하는 명시적 예외이며 그 대가가 falsifiable 형식이다.

## 5. 병렬 규칙

- 병렬은 **라우트 디렉터리 + features 소유권이 분리된 도메인끼리만.** 조 편성·소유권은 플랜 W3 표.
- 병렬 워커는 worktree 격리. ★Workflow worktree 는 **main 베이스로 생성**된다 — 워커 첫 스텝에 `git fetch 없이 git checkout -b <슬라이스명> <stage-HEAD 커밋해시>` 지시. worktree tsc ≠ stage tsc 실측 — cherry-pick 후 **원본 트리에서 전 게이트 재검증 의무**.
- 같은 트리 병렬 커밋 금지(lint-staged stash 경합). globals.css 페이지 블록·spec 라우트 배열 충돌은 오케스트레이터가 union 해소.
- 교차 감사는 마지막 직렬 — 파일 단위 통과 ≠ 전체 정합.

## 6. 워커 프롬프트 필수 동봉 3종

① 해당 프로토타입 HTML **절대경로** (`docs/prototypes/shotgun-2026-07/…`) — 직접 열어 마크업·클래스·간격을 읽는다. 요약·기억 금지.
② 해당 도메인 `frontend/src/features/<도메인>/schemas.ts` + `api.ts` **절대경로** — §4.9(스키마가 받치지 않는 값은 그리지 않는다)는 워커가 스키마를 직접 읽어야 실행 가능. unbacked 필드는 미렌더 + 근거 보고.
③ S5 확립 패턴 참조 구현: `frontend/src/app/(dashboard)/backtests/_components/backtest-list.tsx`.

- 자기 페이지의 자체 focus ring 제거(§1-2) + 페이지 전용 CSS 는 KITPORT 센티넬 밖 언레이어드만 + KITPORT 센티넬 수정 금지.

## 7. 함정 (전부 실측 — HANDOFF 5판 §4 원문 필독)

- Turbopack CSS 캐시가 재기동을 넘어 산다. 수정 직후 playwright 는 stale 청크 가능 — 이상하면 앱 의심 전에 **컴파일 CSS 응답부터**, 판정은 재실행으로. 복구는 cp/checkout 아닌 **내용 변경**으로 재컴파일 강제.
- KITPORT 센티넬 수정 금지. @layer 안 :root 미디어 오버라이드는 언레이어드 base 에 진다.
- Chromium date input 내부 tab stop 4개 — :focus-within 보강.
- 공유 프리미티브(button/skeleton/input)는 토큰 층만. tick-ruler·pnl-tape 불가침.
- lint-staged 출력 불신(git show --stat 확인) · rm -rf 차단 · 임시 distDir 후 config 원복(`.next*` ignore).
- H-1(useEffect 불안정 dep — hooks diff 시 live smoke 의무) · H-2(queryKey getToken 금지) · 실시간 = WebSocket+Zustand, RQ 분리. Monaco hex allowlist 4건 유지.
- 에러 전문 읽기 · `2>/dev/null` 금지 · 빈 출력 ≠ 부재의 증거 · 문서 줄번호 좌표는 전부 재확인.
- 백엔드 8000 은 openapi title 로 QuantBridge 판별(cookmark 점유 함정). DB 는 5436 (`.env.local` 의 5433 은 남의 DB).
- codex 호출: `timeout 900 codex exec --skip-git-repo-check "<프롬프트>" < /dev/null`. `-m sol` 금지(400 실측). hang(CPU≈0) 시 적대적 opus 워커로 대체.

## 8. Goal 규율 + 종료 조건

- 슬라이스 완료 → 게이트 3분류 재현 → 다음 발사를 ScheduleWakeup 루프로. 문서 갱신(Atomic Update) 미루지 않는다.
- 같은 문제 3회 실패 시에만 사용자 보고. **예외 = 환경 preflight 실패(서버·인증·데이터)와 baseline 재현 실패는 즉시 보고.**
- 종료 조건 (전부 충족해야 끝):
  ① 17벌+리포트 정본 전 화면 이식 ② hard-fail 전 라우트 0 ③ 래칫 전부 0 또는 근거 있는 정당 잔여
  ④ coverage — 전 신규 라우트가 canon/authed/public spec 과 live-smoke 방문 목록에 편입(--list 검증)
  ⑤ 전 화면 교차 정합 감사 통과 ⑥ codex 최종 누적 검증 반영 ⑦ 문서 3종 + 본 계약 갱신
  ⑧ 전체 스위트 그린 + 푸시 + stage→main PR + CI 6체크 통과 확인 → 머지 대기 상태로 최종 보고. 이 보고까지가 이 세션의 일이다.
