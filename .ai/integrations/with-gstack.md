# gstack과 함께 사용하기

> [gstack](https://github.com/garrytan/gstack) — 가상 엔지니어링 조직.
> 29개 스킬로 혼자서 팀처럼 개발. "That is not a copilot. That is a team."

## 설치

```bash
# 글로벌 설치 (모든 프로젝트에서 사용)
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup

# 또는 프로젝트별 설치
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  .claude/skills/gstack && cd .claude/skills/gstack && ./setup
```

## 핵심 개념: 역할 분리

각 스킬이 다른 전문가 역할. 각 단계의 산출물이 다음 단계의 입력.

> "Planning is not review. Review is not shipping. Founder taste is not engineering rigor."

## 워크플로우 파이프라인

```
/office-hours → /autoplan → 구현 → /review → /qa → /ship → /document-release
  (기획)     (CEO+Design+Eng) (코드)  (리뷰)   (QA)  (배포)    (문서 동기화)
```

**빠른 시작:** `/autoplan`이 CEO → Design → Eng 리뷰를 자동 순차 실행 (Garry Tan 추천)

## 스킬 맵 (역할별)

### 기획·리뷰

| 스킬 | 역할 |
|------|------|
| `/office-hours` | 제품 리더 — 6가지 강제 질문으로 문제 재정의 |
| `/plan-ceo-review` | CEO — 스코프, 차별점, 10-star product 검증 |
| `/plan-eng-review` | EM — 아키텍처, 데이터 플로우, 에지 케이스 |
| `/plan-design-review` | 디자이너 — UI/UX 감사 |
| `/autoplan` | 파이프라인 — CEO → Design → Eng 자동 순차 실행 |

### 디자인

| 스킬 | 역할 |
|------|------|
| `/design-consultation` | 디자인 시스템 구축 (색상, 타이포, 간격, 모션) |
| `/design-review` | 라이브 사이트 80항목 시각 감사 + atomic commit 수정 |
| `/design-shotgun` | 여러 AI 디자인 변형 생성 + 비교 보드 |

### 구현·테스트

| 스킬 | 역할 |
|------|------|
| `/review` | Staff Engineer — CI 통과 코드의 프로덕션 버그 탐지 |
| `/investigate` | 디버거 — 체계적 근본 원인 분석 |
| `/qa` | QA Lead — diff-aware 브라우저 자동 테스트 + 수정 |
| `/qa-only` | QA 리포터 — 보고만, 수정 안 함 |
| `/browse` | Playwright 기반 실제 브라우저 조작 |
| `/codex` | OpenAI Codex 크로스 모델 독립 리뷰 |

### 배포

| 스킬 | 역할 |
|------|------|
| `/ship` | Release Engineer — 테스트 + 리뷰 + PR 생성 |
| `/land-and-deploy` | 배포 매니저 — PR 머지 + CI + 헬스체크 |
| `/document-release` | 문서 동기화 — 배포 후 README/ARCHITECTURE 자동 갱신 |
| `/canary` | SRE — 배포 후 모니터링 (콘솔 에러, 성능 회귀) |
| `/benchmark` | 성능 엔지니어 — 기준선 비교 |

### 안전·유틸리티

| 스킬 | 역할 |
|------|------|
| `/careful` | 파괴적 명령 경고 (rm -rf, force-push 등) |
| `/freeze` | 편집 범위를 단일 디렉토리로 제한 |
| `/guard` | `/careful` + `/freeze` 결합 (최대 안전 모드) |
| `/cso` | 보안 감사 (OWASP Top 10 + STRIDE) |
| `/health` | 코드 품질 대시보드 (린터, 테스트, 커버리지) |
| `/retro` | Sprint 회고 (커밋 분석 + 메트릭) |
| `/learn` | 프로젝트 교훈 관리 |
| `/setup-browser-cookies` | Chrome/Arc/Brave 쿠키 임포트 (인증 페이지 QA용) |

## ai-rules와의 관계

| 영역 | ai-rules | gstack | 관계 |
|------|----------|--------|------|
| 기본 역할 | Senior Tech Lead | 없음 (커맨드 호출 시에만 활성) | **ai-rules 기본값** |
| 코딩 규칙 | 스택별 상세 규칙 | 없음 | **ai-rules 전담** |
| 아키텍처 패턴 | FSD, 레이어 분리 등 | 없음 | **ai-rules 전담** |
| 코드 리뷰 | 없음 | `/review` | gstack 추가 |
| QA 테스트 | 없음 | `/qa`, `/browse` | gstack 추가 |
| 보안 감사 | 없음 | `/cso` | gstack 추가 |
| 기획 검토 | 없음 | `/office-hours`, `/autoplan` | gstack 추가 |

**충돌이 거의 없습니다.** gstack은 "관점(역할)"을 추가하고, ai-rules는 "규칙(코딩 컨벤션)"을 정의합니다.

## 사용 패턴

### 기본 개발 시

ai-rules의 규칙을 따라 코드 작성. gstack 커맨드 불필요.

### 기획·설계가 필요할 때

```
/office-hours        → 제품 정의
/autoplan            → CEO + Design + Eng 리뷰 자동 실행
```

### 검토가 필요할 때

```
/review              → 코드 리뷰
/qa                  → QA 자동 테스트
/design-review       → UI/UX 시각 감사
/codex review        → 크로스 모델 검증
```

### 배포 전

```
/cso                 → 보안 검토
/ship                → PR 생성 + 릴리스
/canary              → 배포 후 모니터링
```

## 조정이 필요한 부분

### Git Safety Protocol

gstack의 `/ship`은 배포 프로세스를 안내하지만,
ai-rules의 Git Safety Protocol(커밋/푸쉬 전 사용자 승인)이 여전히 우선합니다.

### 역할 전환

ai-rules의 "Senior Tech Lead"는 **기본 역할**입니다.
gstack 커맨드를 호출하면 해당 역할로 전환되고, 커맨드 완료 후 기본 역할로 돌아옵니다.

## 요약

- **설치만 하면 됩니다.** ai-rules 파일 수정 불필요.
- gstack은 필요할 때 슬래시 커맨드로 호출. 항상 활성화되지 않음.
- ai-rules가 코딩 규칙을, gstack이 다양한 역할 관점 검토를 담당합니다.
