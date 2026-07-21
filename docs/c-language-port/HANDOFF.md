<!-- C 언어 React 이식 작업의 세션 간 인수인계 문서 -->

# QuantBridge 핸드오프 — C 디자인 언어 React 이식

갱신 2026-07-21 (5판) · **S1a~S9 전부 완료** 세션에서 이어짐. **이 문서가 정본이다.**

---

## 0. 다음 세션이 할 일

**구현은 끝났다. 남은 것은 사용자 결정 2건 + 후속 부채다.**

1. **stage/c-language-port → main 머지는 사용자가 직접** (main 직접 push 영구 차단). CI 트리거는 `[main, "stage/**"]`.
2. §5 남은 부채에서 다음 슬라이스를 고른다 — P1 밖 화면 이식(strategies/optimizer/orders/onboarding/랜딩)이 큰 덩어리다.

## 0.5 이번 세션(2026-07-20~21)이 한 일 — S1a~S9 완주

이전 세션 미커밋 잔여물(S1a 절반)을 검증 후 수용하고, 전 슬라이스를 opus 워커 + fable 오케스트레이터(게이트 직접 재현) + codex 외부 검증 3회 구조로 완주했다.

| 슬라이스        | 커밋                            | 핵심                                                                                                                                |
| --------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| S1a 토큰 정합   | `ab2ea24`~`fdd9294` + `c1d9531` | ★리네임 0 — **캐논 별칭 브리지**로 확정 (실소비 100+파일 실측, codex 검증과 독립 일치). 비색상 9종 브리지 + Tailwind 유틸 가드 신설 |
| S1b 슬롭 9종    | `3e01d22`~`72af970`             | 8건 처리 (⑦ 기해결). em-dash 래칫 100→95                                                                                            |
| S2 공용 CSS     | `e10af86`, `63523ca`            | 972줄 `@layer components` + KITPORT 센티넬 무결성 가드(정규화 비교 + td.num 의도 편차 allowlist)                                    |
| S3 셸           | `bde094a`, `650efdc`            | fixed 사이드바 + CSS 레일 + nav-count 3종. ★`--sidebar-w` 미디어 오버라이드는 @layer 밖 언레이어드에 (캐스케이드)                   |
| S4 용어 SSOT    | `ef158db`~`eacfb36` + `8f89a4e` | labels 모듈 3종 + 복제 Record 3곳 이관 + 원시 enum 가드 (worktree 병렬 → cherry-pick)                                               |
| S5 /backtests   | `378b7d7`                       | 시맨틱 CSS 사용 패턴 확립 (이후 화면의 준거). allowlist 1→0                                                                         |
| S6 /trades      | `0a3a404`~`31b058a`             | 표·페이저·필터 프리미티브. allowlist 3→0                                                                                            |
| S7 /dashboard   | `f788325`, `ab12bdf`            | 차트 축 가드(BL-407 부류) + LiveSessionTable 디커플 (worktree 병렬)                                                                 |
| — focus 픽스    | `9d3cce9`                       | ★kit:100 전역 :focus-visible 이 S2 이식에서 빠졌던 것 복원 + date input :focus-within 보강                                          |
| S8 /trading     | `c62a50a`~`9fb03b8`             | 코크핏 재구축 + KS 3겹 재도입 + LiveSessionTable→features 이동 + 죽은 코드 삭제. allowlist 1→0                                      |
| S9 교차 감사    | `e0e1ee0`~`7351195`             | ★사실 모순 0건 (SSOT 효과). StateBox/InfoIcon 추출, 가드 스코프 확장, min() 클램프 제거                                             |
| codex 최종 픽스 | `0635e3c`~`41380a0`             | 정직성 4건(오류 0화·허위 문구·가짜 API 표기·페이지 집계) + toast 중복 + 잔존 주석                                                   |

**최종 게이트 (오케스트레이터 직접 재현):** vitest **164파일/904** · tsc/lint/build 0 · design-canon **29** · authed-canon-p1 **5 (skipped 0)** · live-smoke 2 · **HARDFAIL_ALLOWLIST 4라우트 전부 0 · KNOWN_MISMATCHES 0**.

**codex 외부 검증 3회:** 플랜(5건 반영) · S1a diff(BLOCKER 2 적중) · 누적 diff(MAJOR 5 — 전부 사실 확인 후 픽스, 래칫 우회·훅 규칙·테스트 정직성 축은 반증 실패).

## 1. 먼저 읽을 것

`checklist.md`(전 항목 체크됨) · `context-notes.md`(결정 근거 — S9 절 + 교차 감사 결과 포함) · `docs/prototypes/shotgun-2026-07/_KIT.md` + `terminology-ssot.md` · 프로토타입 뷰어 `python3 serve.py` → 4173.

## 2. 확정된 것 (재론 금지)

4판의 확정 사항 전부 유지 (시맨틱 CSS 이식 · 라이트 캐논 미적용 · B2 팔레트 · Bybit 단일 · 프로토타입 = 시각 정본). 추가 확정:

- **S2/S5 되돌림 사유 = 순서 위반** (사용자 확인). 정순 재진행으로 완료.
- **토큰 리네임 대신 캐논 별칭 브리지** — `--copper: var(--primary)` 등. @theme 키(Tailwind 유틸 이름)는 유지.
- **codex = 2지점** (2026-07-21 사용자 확정 — 플랜 확정 직후 1회 + 최종 누적 diff 1회, 내부 게이트는 유지). 5판까지의 "마지막 1회로 모은다"는 슬라이스-사이 codex 게이트 제거를 뜻한 것이며 이 정의로 동기화됐다 (`operating-contract.md` §1-4).

## 3. 남은 부채 (후속 세션용)

1. **P1 밖 화면 이식** — strategies(2)/optimizer(2)/orders/onboarding/랜딩·waitlist·share·error 류. 반경 리터럴·stale var() 폴백 15파일 목록은 context-notes S9 절.
2. **§05 trading form/list/detail 심층 재스킨** — shadcn 내부 구조 + `toLocaleString` 날짜(비결정적) + English dt 라벨. 하드 게이트는 0.
3. **StateBox 미이관 6곳** (구조 편차 — 인터페이스 확장 판단 필요).
4. **전역 :focus-visible 카퍼 링의 P1 밖 이중 링** (codex MINOR) — share copy button 등 자체 ring 과 중첩. 캐논 전역 규칙 vs P1 한정은 **사용자 판단**.
5. **kpi-pnl 오류 표기 미배선** — `useLiveSessionsAggregate` 가 isError 를 노출하지 않음 (훅 시그니처 변경 필요).
6. **라이트 화면 외관 무책임 상태** 명시적 잔존 (사용자 확정 트레이드오프).
7. 미해결 질문 2건 유지 — `strategy.backtest_count` 정의 · OKX enum 제거 여부.

## 4. 함정 (전부 실측 — 4판 목록에 추가)

1. ★**Turbopack CSS 캐시가 재기동을 넘어 산다** (4판 §6-1). 이번 세션에도 재확인 — 수정 직후 playwright 실행은 stale 청크를 받을 수 있다. 재실행으로 판별.
2. ★**KITPORT 무결성 가드는 `.mono` 이전 전역 리셋 구역을 대조에서 제외한다** — kit:100 전역 :focus-visible 이 그래서 빠졌었다. 전역 구역 규칙은 별도 이식 필요.
3. ★**Chromium date input 은 내부 tab stop 4개** — 피커 버튼 포커스 시 :focus-visible 이 input 에 미매치. `:focus-within` 링으로 보강해야 audit 이 통과한다.
4. ★**Workflow worktree 격리는 main 베이스로 생성된다** — stage 위 작업이 필요하면 워커 첫 스텝에 `git checkout -b <branch> <stage-HEAD>` 지시. worktree 의 tsc 결과가 stage 와 다를 수 있다(TS 해석 차이 실측 — cherry-pick 후 원본에서 재검증 필수).
5. ★**@layer components 안의 `:root` 미디어 오버라이드는 언레이어드 base 에 항상 진다** — 반응형 토큰 오버라이드는 언레이어드에.
6. **git 병렬 커밋 경합** — 같은 트리에 두 워커 커밋 금지 (lint-staged stash). worktree 격리 또는 직렬.
7. **임시 distDir 빌드**(`.next-*`) — eslint/gitignore 는 `.next*` 글롭으로 일반화해 뒀다. next.config/tsconfig 자동 변경은 즉시 원복.
8. lint-staged 훅 출력 불신(`git show --stat` 확인) · 에러 전문 읽기 · 워커 자기보고는 게이트 재현 후 신뢰 (S6 이 focus=0 을 보고했지만 재현에서 focus=2 — 재현이 진실이었다).

## 5. 환경 메모 (4판 유지)

- dev 3000 · 백엔드 8000 (QuantBridge — cookmark 점유 여부는 openapi title 로 판별) · DB 5436 (`.env.local` 의 5433 은 남의 DB) · Redis 6380.
- authed 검사 전 storageState 신선도 (전부 sign-in 리다이렉트 = 만료, `--project=setup` 재발급).
- `rm -rf` 권한 차단. 프로토타입 뷰어 4173.

---

**민감정보 점검.** 이 문서와 참조 산출물에 API 키·비밀번호·토큰 없음.
