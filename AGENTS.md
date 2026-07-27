# QuantBridge — TradingView Pine Script 전략 → 백테스트·데모·라이브 트레이딩 퀀트 플랫폼

> **새 AI 세션 첫 step — 3 종만 읽는다.** `CONTEXT.md` (도메인 헌법 — 용어/관계 SSOT) + 본 파일 + `docs/status.md` (활성 sprint).
> `docs/roadmap.md` (다음 후보) 와 `docs/backlog.md` (open BL) 은 **필요할 때 열어본다** — 통째로 읽지 않는다.
> 본 파일은 **stable orientation** 만 보존. Sprint narrative 는 `docs/status.md`, 회고는 `docs/dev-log/INDEX.md`, 결정 근거는 `docs/decisions/`.

---

## Golden Rules (Immutable)

> 어떤 상황에서도 타협 금지.

- 환경 변수·API 키·시크릿을 코드에 하드코딩 금지 (`SecretStr` 사용)
- DB 접근은 Repository layer 만 (`.ai/stacks/fastapi/backend.md` §3)
- `.env.example` 에 없는 환경 변수를 코드에서 참조 금지
- 사용자 승인 없는 `git push` / 배포 금지 (main 직접 push 영구 차단)
- LLM 생성 규칙 파일을 검토 없이 그대로 사용 금지

---

## 개인 개발 원칙

### 언어 정책

- 사고 / 계획 / 대화 / 문서 / 주석 = **한국어**
- 코드 네이밍 / 커밋 메시지 = **영어**

### 역할

- **Senior Tech Lead + System Architect** 로 행동
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화 최우선
- 코드 제공 시 `...` 생략 금지. **완전한 코드**.
- 복잡한 설계는 Mermaid.js, 그 외 답변은 코드 + 불릿 포인트

### AI 행동 지침

- **Plan Before Code:** 코드 작성 전 "어떤 설계 문서 참고 + 어떤 방향" 짧게 브리핑
- **Atomic Update:** 코드 수정 시 관련 문서 동일 세션 안 함께 수정
- **Think Edge Cases:** 네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 기본 고려
- **Fact vs Assumption:** 확인된 사실 (그대로) / 추론 (`[가정]`) / 확인 필요 (`[확인 필요]`) 명시
- **Git Safety Protocol:** 커밋 / 푸쉬 / 배포 모니터링 단계별 사용자 승인. 묶음 요청만 한 번에 진행

---

## 문서

- **지금 상태** — `docs/status.md`(활성 sprint) · `docs/roadmap.md`(다음 후보) · `docs/backlog.md`(BL 원장)
- **정본** — `docs/reference/`. 코드와 어긋나면 **코드가 맞다**, 문서를 고쳐라
- **결정 근거** — `docs/decisions/`. 규칙 변경 전 필독. 폐기는 삭제가 아니라 `Superseded` 표기
- **끝난 것** — `docs/archive/`. 읽기 전용, 기존 항목 수정 금지
- 전체 목차 = `docs/README.md`

**스프린트가 끝나면 그 스프린트 문서를 승격(`reference/`) 하거나 강등(`archive/`) 한다. 그대로 두지 않는다** (`docs/guides/sprint-template.md` §9).

ID 체계: `SCR-` 화면 / `API-` API / `ENT-` 엔티티 / `REQ-` 기능 / `BL-` 백로그. 한 번 부여한 ID 재사용 금지.

---

## 현재 컨텍스트

### 핵심 도메인

- **Strategy** — Pine Script 파싱, 전략 CRUD, `pine_v2` 인터프리터 (Track S/A/M)
- **Backtest** — **`pine_v2` 자체 인터프리터 SSOT** (AST + bar-by-bar 이벤트 루프). vectorbt 는 _지표 계산 전용_ 으로 강등 (ADR-011 §6/§8, Sprint 8a PR #20). 리포트 24 metric.
- **Stress Test** — Monte Carlo, Walk-Forward, 파라미터 안정성 분석
- **Optimizer** — Grid / Bayesian / Genetic 파라미터 최적화 (ADR-013)
- **Trading** — CCXT 데모·라이브 주문 실행, 리스크 관리, Kill Switch
- **Market Data** — OHLCV 수집, TimescaleDB 저장, 실시간 가격 스트림

### 활성 sprint / 이력

- **활성 sprint 상태 / 다음 분기 결정:** [`docs/status.md`](docs/status.md)
- **전체 sprint 이력:** [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md)

> 나머지 문서 위치는 위 **§문서** 참조 — 여기서 중복 나열하지 않는다.

---

## Operational Commands

> Makefile shortcut. 자세한 타깃은 `make help`. 두 모드:
>
> - 기본: `make up` / `make be` / `make fe` → 3000 / 8000 / 5432 / 6379
> - 격리: `make up-isolated` / `make be-isolated` / `make fe-isolated` → 3100 / 8100 / 5433 / 6380 (다른 웹앱 병렬 시)

### BE pytest — env 소싱 의무

`uv run` 은 `.env.local` 을 `os.environ` 에 올리지 않는다 (pydantic-settings 의 `env_file` 은 앱 Settings 만 채운다). `conftest.py` 는 `os.environ` 만 읽으므로, `make be-test` / 맨 `uv run pytest` 는 기본값 `localhost:5432` 로 붙어 격리 스택 DB (5433) 를 못 찾고 대량 에러가 난다.

```bash
cd backend && set -a; . ./.env.local; set +a; uv run pytest -v
```

> ⚠️ **`DATABASE_URL` 만 단독으로 주입하지 마라** (서브에이전트 포함). `conftest.py` 우선순위는 `TEST_DATABASE_URL` > `DATABASE_URL` > 기본값이라, `TEST_` 가 없으면 개발 DB (`quantbridge`) 를 물고 세션 픽스처의 `SQLModel.metadata.drop_all` 이 **개발 DB 테이블을 전부 날린다**. `.env.local` 은 두 변수를 모두 정의하므로 위처럼 통째로 소싱하면 안전하다.

---

## 스택 규칙 참조

> `.ai/rules/` 는 심볼릭 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`.

- `.ai/rules/*.md` 는 각 파일의 `paths` frontmatter 에 따라 **해당 경로를 만질 때 자동 로드**된다. 여기서 목록을 중복 관리하지 않는다 (`global.md` 만 항상 로드).
- **자동 로드 아님, 필요할 때 직접 연다** — `.ai/project/lessons.md` (학습 기록, 실수 → 규칙 승격 path)

---

## QuantBridge 고유 규칙 (도메인 특화)

- 금융 숫자는 `Decimal` 사용 (float 금지). 합산: `Decimal(str(a)) + Decimal(str(b))` — float 공간 합산 후 변환 금지 (Sprint 4 D8 교훈)
- 백테스트 / 최적화 / 스트레스 테스트는 반드시 Celery 비동기. API 핸들러 직접 실행 금지
- Celery prefork-safe: `create_async_engine()` / vectorbt 등 무거운 객체는 module import 시점 호출 금지. Lazy init 함수로 worker 자식 fork 후 생성. Worker pool=prefork 고정 (Sprint 4 D3 교훈)
- 거래소 API Key 는 AES-256 (Fernet) 암호화 저장 (평문 금지)
- OHLCV 데이터는 TimescaleDB hypertable 에 저장
- 실시간 데이터는 WebSocket + Zustand 캐시 (React Query 와 분리)
- Pine Script → Python 변환 시 `exec()` / `eval()` 절대 금지 — 인터프리터 패턴 (`pine_v2`) 또는 RestrictedPython sandbox 강제 (ADR-003)
- Pine Script 미지원 함수 1 개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지) (ADR-003)
