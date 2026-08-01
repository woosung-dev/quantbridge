# LLM 개발사·대형 테크의 문서 정보구조 조사

> **일자:** 2026-08-01  
> **목적:** QuantBridge 내부 개발·운영 문서의 분류 체계를 다시 판단하기 위한 비교 조사.  
> **방법:** 각 조직의 공식 GitHub 저장소와 그 저장소가 가리키는 공식 문서만 사용했다. 제품 문서 사이트와 구현 저장소 문서는 역할이 다르므로 분리해 해석한다.

---

## 1. 먼저 구분해야 하는 두 문서 모델

| 모델 | 정본 위치 | 저장소 문서의 역할 | QuantBridge와의 관계 |
| --- | --- | --- | --- |
| 제품·플랫폼 문서 | 별도 공식 문서 사이트 또는 docs-site source | 설치, 제품 기능, API, 튜토리얼의 얇은 입구 | 현재 QuantBridge의 내부 개발·운영 문서와 직접 동형이 아니다. 공개 제품 문서를 만들 때 참고한다. |
| 구현·운영 문서 | 구현 저장소의 추적 Markdown | 기여, 로컬 개발, 코드와 함께 참이어야 하는 계약, 실행 증거 | 현재 QuantBridge가 우선 해결하려는 문제와 가깝다. |

Anthropic Claude Code와 OpenAI Codex는 첫 모델을 강하게 택한다. 반대로 OpenAI Agents SDK와 Google Gemini CLI는 코드 저장소 안에도 읽을 수 있는 docs source와 탐색 정의를 둔다. 따라서 특정 회사의 폴더 이름을 복제하기보다, **문서의 독자·수명·생성 여부를 먼저 가르는 것**이 공통 원칙이다.

---

## 2. 공식 사례

| 조직·대표 저장소 | 확인한 정보구조 | source / generated 경계 | QuantBridge에 주는 신호 |
| --- | --- | --- | --- |
| Anthropic — [claude-code](https://github.com/anthropics/claude-code) | 공개 저장소에는 큰 `docs/` tree나 사이트 nav가 없다. [README](https://github.com/anthropics/claude-code/blob/main/README.md)가 설치·시작 후 공식 Claude Code 문서 사이트로 연결하며, `plugins/README.md`는 플러그인 카탈로그용이다. | 이 저장소에서 문서 빌드 산출물 또는 생성 문서 정책은 확인되지 않는다. | repo를 제품 지식베이스로 키우지 않는다. 루트 README는 입구이고, 제품 정본은 별도 위치일 수 있다. |
| OpenAI — [codex](https://github.com/openai/codex) | `docs/`는 인증·설정·실행·skills 등 소규모 repo 보조 문서다. [AGENTS.md](https://github.com/openai/codex/blob/main/AGENTS.md)는 일반 사용자 문서를 이 `docs/`에 추가하지 말고 공식 Codex 문서를 따르도록 구분한다. [README](https://github.com/openai/codex/blob/main/README.md)는 공식 문서 사이트를 우선 링크한다. | 빌드·배포 산출물은 ignore하되, 공개 tree에는 문서 사이트 source/nav가 없다. | `docs/`를 모든 내용을 담는 곳으로 만들지 않고, repo 유지보수에 필요한 범위만 둔다. |
| OpenAI — [openai-agents-python](https://github.com/openai/openai-agents-python) | [mkdocs.yml](https://github.com/openai/openai-agents-python/blob/main/mkdocs.yml)의 최상위 탐색은 `Intro → Quickstart → Configuration → Documentation → API Reference`다. 기능·개념 문서와 코드 모듈별 API reference를 분리한다. | [AGENTS.md](https://github.com/openai/openai-agents-python/blob/main/AGENTS.md)는 `docs/`를 원본, `docs/ja·ko·zh`를 생성 번역본, `site/`를 빌드 출력으로 정의한다. [generate_ref_files.py](https://github.com/openai/openai-agents-python/blob/main/docs/scripts/generate_ref_files.py)는 API reference stub을 생성하고, [.gitignore](https://github.com/openai/openai-agents-python/blob/main/.gitignore)는 `/site`를 제외한다. | 같은 `docs/` 안에서도 **가이드/개념**과 **reference**를 섞지 않고, 사람 작성 원본과 생성물을 명시적으로 구분한다. |
| Google — [gemini-cli](https://github.com/google-gemini/gemini-cli) | [docs/sidebar.json](https://github.com/google-gemini/gemini-cli/blob/main/docs/sidebar.json)은 독자 탐색을 `Get started / Use / Features / Configuration / Development / Reference / Resources / Releases`로 선언한다. [docs/index.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/index.md)는 같은 지도를 사람이 읽는 landing page로 재현한다. 실제 파일 경로는 `cli/`, `core/`, `tools/`, `extensions/`처럼 capability 중심이다. | [package.json](https://github.com/google-gemini/gemini-cli/blob/main/package.json)의 docs scripts와 [generate-settings-doc.ts](https://github.com/google-gemini/gemini-cli/blob/main/scripts/generate-settings-doc.ts)는 configuration·settings reference의 제한된 `AUTOGEN` 구간만 갱신한다. | **파일 배치 축과 독자 탐색 축은 달라도 된다.** 사람이 읽는 지도는 과업 중심으로, 참조 문서는 코드·기능 중심으로 유지할 수 있다. |
| Microsoft — [TypeScript](https://github.com/microsoft/TypeScript) | [README](https://github.com/microsoft/TypeScript/blob/main/README.md)는 제품·언어 학습의 정본을 공식 handbook·웹사이트로 연결하고, 구현 저장소의 문서는 기여·빌드·테스트 중심이다. | 구현 산출물과 소스는 별도이며, README가 모든 제품 설명을 반복하지 않는다. | 루트 문서는 “무엇을 어디서 읽을지”를 제공하는 entrypoint여야지, 살아 있는 상세 명세의 저장소가 아니다. |
| Vercel — [next.js](https://github.com/vercel/next.js) | [README](https://github.com/vercel/next.js/blob/canary/readme.md)는 Learn/Docs를 공식 사이트로 안내한다. repo 내부는 기여와 개발을 위한 `contributing/`, `packages/` 인접 문서가 중심이다. | 공개 제품 문서와 구현의 운영 지식을 구분한다. | 내부 문서와 대외 제품 문서가 성장할 때 같은 최상위 taxonomy를 공유할 이유가 없다. |
| CNCF — [kubernetes/website](https://github.com/kubernetes/website) | 이 저장소 자체가 공식 docs-site source다. `content/`, `static/`, `layouts/` 등 문서 웹사이트를 빌드하기 위한 구조가 함께 존재한다. | 페이지 원본과 사이트 자산·빌드 체계가 함께 필요하다. | docs-site를 실제로 운영할 때만 이런 asset/layout/i18n 구조가 정당하다. 현 내부 운영 문서에는 과잉이다. |

### 사례에서 확인한 패턴

1. **제품 문서와 repo 문서를 먼저 분리한다.** Claude Code·Codex·TypeScript·Next.js는 README가 공식 문서의 입구이되 정본 내용을 복제하지 않는다.
2. **과업/개념과 reference를 분리한다.** Agents SDK는 기능 설명과 코드 모듈 reference를 다른 탐색 축으로 둔다.
3. **파일의 물리적 분류와 사람이 보는 navigation은 별개일 수 있다.** Gemini CLI가 가장 명확한 예다.
4. **생성물은 source와 섞지 않는다.** Agents SDK는 번역·site build를, Gemini CLI는 자동 생성 범위를 각각 명시한다.
5. **문서 사이트형 폴더는 배포 요구가 생길 때만 만든다.** Kubernetes website의 `content/static/layouts`는 콘텐츠가 아니라 사이트 앱을 운영하기 위한 구조다.

---

## 3. 기존 고스타 공개 저장소 표본과의 교차 확인

[기존 300개 구조 조사](2026-08-01-github-library-docs-structure-survey.md)는 GitHub 검색 후보 1,000개 중 `docs/` tree가 있는 별점 상위 300개를 구조 분석했다. “1,000개 문서 구조를 전수 분석”한 조사는 아니다.

| 구조 | 300개 중 | 의미 |
| --- | ---: | --- |
| Flat | 61 (20.3%) | 작거나 단일 목적 문서 |
| Shallow — 하위 폴더 1~4개 | 126 (42.0%) | 가장 흔한 실용 구간 |
| Sectioned — 5~15개 | 92 (30.7%) | 공개 docs site·다수 독자·API·릴리스가 섞인 경우가 많음 |
| Large taxonomy — 16개 이상 | 21 (7.0%) | 제품 플랫폼·다국어·대규모 docs site에 가까움 |

Flat+shallow가 **62.3%**이므로 “인기 프로젝트일수록 깊게 나눈다”는 근거는 없다. 위 대형 테크 사례까지 합치면 더 정확한 결론은 다음과 같다.

> **최상위 폴더 수가 아니라 문서의 역할 경계를 먼저 설계하고, 필요할 때만 각 역할 내부를 얕게 나눈다.**

---

## 4. QuantBridge에 적용할 수 있는 분류 모델

### 모델 A — 수명 우선, reference 내부만 질문·도메인별 분류

```text
docs/
├── README.md                # 지도
├── status.md                # 지금 하는 한 sprint
├── roadmap.md               # 다음 후보
├── backlog.md               # 열린 BL ledger
├── reference/               # 장기 계약; 내부에서 architecture/domain/operations…으로 분류
├── decisions/               # ADR, 결정 근거
├── dev-log/                 # 완료 sprint의 판단과 측정
└── archive/                 # 기본 경로에서 제외된 상세 증거
```

- 장점: QuantBridge의 현재 문제인 live 문서 누적을 직접 해결한다. 새 세션과 AI의 진입점도 작다.
- 위험: `reference/`의 하위 기준을 정하지 않으면 다시 평평한 잡동사니가 될 수 있다.
- 사례 적합성: OpenAI의 repo/product 경계, Agents SDK의 guide/reference 분리, Gemini의 nav/file-path 분리를 모두 수용한다.

### 모델 B — 전체를 독자·과업 우선으로 분류

```text
docs/
├── getting-started/
├── development/
├── operations/
├── product/
├── reference/
└── history/
```

- 장점: 새 팀원·외부 개발자 대상으로 문서 사이트를 만들 때 직관적이다.
- 위험: “이 문서는 개발·운영·제품 중 어디인가”가 반복되며, 현재 `status/backlog/dev-log`의 수명 경계가 약해진다.
- 적합한 조건: QuantBridge 문서를 대외 제품/개발자 문서로 확장하고 site navigation을 운영하기로 결정할 때.

### 모델 C — 비즈니스 도메인 우선으로 전체 분류

```text
docs/
├── strategy/
├── backtest/
├── trading/
├── market-data/
└── platform/
```

- 장점: 금융 도메인 탐색에는 자연스럽다.
- 위험: 한 도메인 안에 현재 작업, ADR, runbook, API 계약, 과거 회고가 다시 섞인다. 변화하는 문서와 안정 문서가 공존한다.
- 적합한 조건: 제품 기능 문서 사이트처럼 각 도메인이 독립적인 독자 여정을 가질 때. 현재 내부 운영 문서의 최상위 모델로는 부적합하다.

---

## 5. 조사 기반의 잠정 제안과 아직 결정할 것

### 잠정 제안

**모델 A를 최상위 구조로 유지하고, `reference/` 내부만 얕게 재분류하는 편이 가장 적합하다.**

이는 새로 만든 문서 구조가 아니다. 현재 가진 `status / roadmap / backlog / reference / decisions / dev-log / archive`라는 수명 경계를 존중하고, 문서가 많은 문제를 `reference`의 질문형 분류와 `docs/README.md` 탐색 지도로 해결하자는 제안이다.

`reference/`의 잠정 후보는 다음처럼 4~6개를 넘기지 않는 수준이다. 실제 이름과 파일 이동은 별도 결정 후에만 한다.

```text
reference/
├── architecture/     # system, data flow, execution architecture, ADR와 다른 현재 계약
├── domain/           # entities, ERD, states, Pine/Trading 의미
├── operations/       # setup, env, gates, CI, worktree, diagnosis/runbook
├── interfaces/       # API/endpoints, 외부 경계
└── product/          # requirements, screen/feature coverage, 지원 범위
```

`design/`, `prototypes/`, `observability/`는 위 축으로 흡수할지 별도 stable category로 유지할지의 **2차 선택**이다. 이 조사는 `docs/` 최상위에 모두 올려야 한다는 근거를 제공하지 않는다.

### 다음 결정에 필요한 질문

1. QuantBridge의 `docs/`는 앞으로도 내부 개발·운영 문서만 담는가, 아니면 외부 사용자/개발자 문서까지 담을 계획인가?
2. `reference/`에서 사람들이 가장 많이 찾는 첫 질문은 무엇인가: **도메인 의미**, **시스템 구조**, **운영 방법**, **API/화면 계약** 중 어느 것인가?
3. `prototypes`와 `design`은 아직 실행 중인 현재 설계인가, 아니면 이미 판단이 끝난 증거인가?

이 세 답이 정해지면, 파일 이동 전에 `docs/README.md`의 탐색 지도와 최상위·reference 내부 taxonomy를 한 번에 확정할 수 있다.

---

## 한계

- 각 조직은 공개 공식 GitHub tree와 공식 문서 연결만 관찰했다. 비공개 운영 문서의 실제 체계는 알 수 없다.
- 회사의 제품 규모·다국어·대외 API 계약은 QuantBridge와 다르다. 따라서 **폴더 이름**은 복사 대상이 아니며, 역할 경계만 전이한다.
- 이 조사는 구조 변경이나 파일 이동을 수행하지 않는다.

