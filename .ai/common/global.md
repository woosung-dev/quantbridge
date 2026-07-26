---
description: 전역 규칙 — 워크플로우, 문서화, Git, 환경변수, 자기개선 루프 (항상 로드)
---

# 전역 규칙 (모든 스택 공통)

---

## 1. 개발 워크플로우

새로운 기능이나 주요 변경 사항은 아래 루프를 따른다:

1. **계획 (Plan)** — 작업 범위와 영향 분석, 관련 규칙·설계 문서 참조
2. **문서화 (Docs)** — 구현 계획을 `docs/` 적절한 위치에 작성
3. **리뷰 (Human Review)** — 사용자 피드백, 만족할 때까지 반복
4. **구현 (Implement)** — 확정된 문서 기반 코드 작성, 중단 없이 끝까지

---

## 2. 문서화 규칙

> **"문서가 없으면 기능도 없다."**
> docs/ 디렉토리 상세 구조는 `AGENTS.md` 섹션 4 참조. 아래는 ID 체계와 TODO.md 운영 규칙:

`00_project/` · `01_requirements/` · `02_domain/` · `03_api/` · `04_architecture/` · `05_env/` · `06_devops/` · `07_infra/` · `dev-log/` · `guides/` · `TODO.md`

### ID 체계

| 대상 | 접두사 | 예시 | 규칙 |
|------|--------|------|------|
| 화면 | `SCR-` | `SCR-001` 로그인 화면 | ID 변경·재사용 금지 |
| API | `API-` | `API-012` 사용자 목록 조회 | |
| 엔티티 | `ENT-` | `ENT-003` Order | |
| 기능 명세 | `REQ-` | `REQ-007` 알림 발송 | |

### TODO.md 운영

프로젝트 루트에 `docs/TODO.md`를 유지하며, 주요 작업 후 아래 4가지 섹션을 업데이트한다.

```markdown
## Completed
- [x] SCR-001 로그인 화면 구현

## Blocked
- [ ] API-005 결제 연동 — PG사 API 키 미발급 [확인 필요]

## Questions
- ENT-003 Order 엔티티에 `canceled_at` 필드가 필요한가? [확인 필요]

## Next Actions
- [ ] SCR-002 대시보드 화면 설계
```

- AI가 사용자에게 빈번하게 질문하는 대신, 이 파일에 기록하고 자연스러운 타이밍에 전달한다
- 차단(Blocked) 항목은 이유와 필요한 조치를 함께 기록한다

---

## 3. Git Convention

### 커밋 메시지

```
feat: 새로운 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링 (기능 변경 없음)
docs: 문서 수정
chore: 빌드, 설정 파일 수정
test: 테스트 추가/수정
```

### 브랜치 전략

- main에 직접 커밋/푸쉬하지 않는다
- 기능 브랜치를 만들고 PR을 통해 merge한다
- 브랜치 네이밍: `{type}/{짧은-설명}` (예: `feat/user-auth`, `fix/cache-bug`)
- Claude Code 사용 시: `claude --worktree feat/기능명`으로 시작하면 독립 브랜치에서 바로 작업 가능

---

## 4. 환경 변수 관리

- 모든 환경 변수는 `.env.local` (로컬) 또는 배포 플랫폼 대시보드에서 관리한다.
- 코드에 하드코딩 절대 금지
- 민감 값은 반드시 `SecretStr` 타입으로 선언 (backend rules 참조)
- `.env.example` 파일을 항상 최신 상태로 유지한다
- 구체적 변수 목록은 프로젝트의 `.env.example` 파일을 Single Source of Truth로 유지한다

---

## 5. 규칙 파일 크기 가이드라인

> 토큰 효율성과 에이전트 성능을 위해 규칙 파일 크기를 관리한다. (ETH Zurich 2026 연구 근거: 긴 컨텍스트 파일은 비용을 20%+ 증가시키고 성능 개선은 미미)

- **AGENTS.md (루트 진입점):** 150라인 이하 — 핵심 원칙과 참조만
- **개별 스택 규칙 (`.ai/stacks/`):** 400라인 이하 — non-inferable 패턴 위주
- **추론 가능한 정보 제외:** 에이전트가 `ls`, `cat`으로 발견할 수 있는 폴더 구조·파일 목록은 규칙 파일에 넣지 않음
- **LLM 무검토 사용 금지:** AI가 초안을 작성할 수 있지만, 사람이 검토·확정하지 않은 규칙 파일을 그대로 적용하면 성능이 오히려 저하됨

---

## 6. 자기개선 루프

- AI가 실수를 교정받을 때마다 `.ai/project/lessons.md`에 교훈 기록
- 반복되는 교훈은 해당 규칙 파일(`.ai/common/` 또는 `.ai/stacks/`)로 승격
- `lessons.md`는 주기적으로 정리 — 이미 규칙화된 항목은 제거

### 승격 경로
lessons.md → `.ai/project/` (3회 반복) → `.ai/stacks/` 또는 `.ai/common/` (프로젝트 간 공통) → 삭제 (모델 개선으로 불필요 시)

모든 규칙은 "모델이 못하는 것"에 대한 가정이므로, 모델 업그레이드 시 주기적으로 검증하여 불필요한 규칙을 제거한다.

---

## 7. 메타-방법론 영구 규칙 (BL-146, 2026-05-09 Sprint 46 W1 승격)

> 3/3 검증 통과한 sprint kickoff / mid-dogfood / post-merge 프로세스 규율 4종. lessons.md 의 LESSON-037/038/039/040 에서 승격. 위반 시 silent failure → wrong premise surgery → false PASS 누적 위험.

### 7.1 Sprint kickoff 첫 step = baseline 재측정 preflight (LESSON-037)

> Sprint kickoff 의 **첫 step = baseline 재측정 preflight 의무**. 본인 dogfood 인상 + plan 가정 + 사용자 prompt 가정 — 모두 실측 전 신뢰 금지.

- plan 작성 직후 codex G0 1회 + fresh-context subagent 2-검토 권장.
- frame change 1회+ 발견 시 plan revision 의무.
- Type A (신규 기능) 의무 / Type B (risk-critical) 권장 / Type C (hotfix) 면제 가능 / Type D (docs only) 면제.
- 검증 누적: Sprint 29 first/second/third validation 통과 (3/3).

### 7.2 Docker worker auto-rebuild on PR merge (LESSON-038)

> 모든 worker process (celery worker / beat / ws-stream / 기타 prefork-safe pool) 코드 변경 영향 시 PR 머지 후 자동 rebuild 의무.

- 가능한 mechanism: (a) `docker-compose.dev.yml` override volumes mount (dev) + image baked-in (prod), (b) GitHub Actions image push + 환경 안 image pull + restart 자동화, (c) Makefile post-merge target + post-merge git hook.
- **첫 단계 = sentinel function 존재 startup health check** — silent failure 자동 detection (e.g. `_v2_buy_and_hold_curve` `hasattr` 검증).
- 검증 누적: Sprint 35 Slice 1a + Slice 4a + Sprint 38 BL-181 fix (3/3).

### 7.3 Surface Trust 차단 ≠ 기능 작동 (LESSON-039)

> Surface Trust 차단 (UI false positive 차단) 과 기능 작동 (backend 정확 계산) 두 mechanism 분리 의무. mid-dogfood verification 시 양쪽 의무.

- (a) Surface Trust 차단 작동 검증 (e.g. BH null → 미렌더 + Legend hide).
- (b) **기능 작동 직접 검증** — hand-computed minimal oracle 또는 deterministic test fixture 으로 외부 진실 도입.
- engine 자체 generated 결과를 같은 engine 으로 검증 = circular oracle 함정 (금지).
- 검증 누적: Sprint 35 Slice 1a + Slice 1.5a oracle + Sprint 38 BL-189 falsification (3/3).

### 7.4 codex G.0 직후 rapid prereq verification spike (LESSON-040)

> codex G.0 master plan validation 직후 + Sprint 진입 전 = **rapid prereq verification spike (10-30분)** 의무.

- 가설별 1줄 query (DB SQL / Python diagnostic / runtime check) 으로 surgery premise 검증.
- wrong premise 발견 시 plan footnote 추가 + Slice scope 즉시 갱신.
- worker/runtime version 검증 (sentinel function 존재 / git commit hash 비교) Sprint 진입 첫 step 추가 권장.
- 검증 누적: Sprint 35 Slice 1a 1차 + Sprint 35 전체 + Sprint 38 codex iter 2 (3/3).

### 7.5 신규 도메인 / 큰 모듈 신설 직후 = `/deepen-modules` 1회 권장 (Sprint 46 pilot 채택)

> AI 누적 작성 코드는 **shallow module + locality 깨짐** 을 누적시킨다 (Ousterhout, *A Philosophy of Software Design*). 신규 도메인 / 5+ 파일 모듈 신설 직후, stage→main 진입 전, `/deepen-modules` 1회 호출로 사전 차단.

- **호출 시점:** Sprint kickoff 가 아니라 **신규 도메인/모듈 신설 직후 + stage→main 진입 전**. 또는 PR 30+ 누적 후 architectural debt 점검.
- **Iron Law:** 1회 호출 = 1 도메인만 audit. 전체 코드베이스 동시 audit 금지.
- **Phase:** Module Inventory & Depth Mapping → Locality & Coupling Analysis → Grilling Session (사용자 ↔ AI) → BL Registration & Sprint Recommendation.
- **Phase 3 사용자 승인 전 코드 수정 금지** — BL 등재만 허용. 인간 = 전략(Strategist) / AI = 전술(Tactician) 분업 강제.
- **STOP conditions:** 해당 모듈 test coverage <70% → "test 우선" 권고로 종료 / Deep module 을 더 deep 화하지 않음 (over-engineering 함정).
- **검증 누적: 3/3 완료 (2026-05-09 same-session pilot)** — pine_v2 SSOT (1/3, BL-200/201) + trading (2/3, BL-202/203/204/205) + frontend cross-page primitive (3/3, BL-206). **LESSON-063 정식 승격** = AI 누적 코드의 3 패턴 (Triple SSOT / Cross-module dispatcher 분산 / Cross-page primitive 우회). Sprint 47 = 7 BL 대형 deepening 권고.
- **2026-06-30 verification loop — methodology Stage 0/4 도구 invocable 화:** mattpocock `/grill-with-docs`(Stage 0 헌법) + `/improve-codebase-architecture`(Stage 4, CONTEXT.md-informed) + `/zoom-out`(Stage 6) 을 `~/.claude/skills/` 로 symlink 설치 → quant-bridge 호출 가능. **루트 `CONTEXT.md`(Stage 0 도메인 헌법) 신설 완료** → grill-with-docs cadence = **프로젝트 1회 ✅ + 새 도메인 등장 시 재실행**. `/improve-codebase-architecture`(Sprint 마무리/신규 모듈 직후, 화이트리스트 외)는 `/deepen-modules` 와 상호보완 — deepen-modules = 프로젝트 BL 포맷 SSOT, improve-codebase-architecture = CONTEXT.md 도메인 용어 기반. backtest 1차 deepen 으로 검증(BL-387~391 + ADR-021). codex challenge 의 finding 도 코드 대조 검증 의무(§7.3, phantom `metrics.py` 오인 차단 사례).

### 적용 의무 시점

| 시점 | 적용 규칙 |
|------|----------|
| Sprint kickoff (Type A/B) | §7.1 |
| codex G.0 master plan validation 직후 | §7.4 |
| PR 머지 후 (worker 코드 영향 시) | §7.2 |
| Mid-dogfood verification | §7.3 |
| 신규 도메인 / 큰 모듈 신설 직후 (권장) | §7.5 |

위반 detect: codex G.X gate / sprint close-out audit / dual metric (LESSON-035) cross-check.
