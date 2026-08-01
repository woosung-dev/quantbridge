# GitHub 고스타 라이브러리의 추적 문서 구조 조사

> **일자:** 2026-08-01<br>
> **범위:** GitHub 1차 API와 각 저장소 기본 브랜치의 Git tree만 사용한 문서 구조 조사.<br>
> **판정:** QuantBridge가 줄여야 하는 것은 `docs/`의 안정된 분류 수가 아니라 **현재 작업·미해결 BL·과거 증거가 한 파일에 누적되는 live surface**다. 외부 라이브러리의 공개 문서와 같은 대형 분류·다국어·문서 사이트를 내부 운영 문서에 복제하지 않는다.

---

## 1. 결론

300개 문서 보유 고스타 저장소의 `docs/`는 하나의 정답으로 수렴하지 않았다.

- **61개(20.3%)**는 하위 디렉터리가 없는 flat 구조였고, **126개(42.0%)**는 1~4개 하위 디렉터리의 shallow 구조였다.
- 반면 공개 사용자 문서가 큰 프로젝트에는 5~15개 섹션이 있는 경우가 **92개(30.7%)**, 16개 이상 대형 taxonomy가 **21개(7.0%)** 있었다. 이 층은 API·튜토리얼·로케일·이미지·문서 빌드 자산을 함께 담는 경우가 많다.
- 그러므로 “고스타 프로젝트가 문서 수를 적게 둔다”가 아니라, **독자와 수명에 맞춰 top-level taxonomy의 깊이를 제한하고, 서로 다른 수명의 내용을 섞지 않는다**가 관찰 가능한 원칙이다.

QuantBridge는 공개 SDK 문서 사이트가 아니라 금융 실행 시스템의 **내부 개발·운영 문서**다. 현재의 `docs/README.md` 지도와 `reference/`·`decisions/`·`dev-log/`·`archive/`라는 수명 분리는 유지하는 편이 맞다. 정리의 우선순위는 다음이다.

1. `status.md`를 **현재 한 sprint의 작업 계약**으로만 유지한다.
2. `backlog.md`를 **열린 BL의 짧고 감사 가능한 queue**로 되돌린다.
3. 완료 판단·측정표·반증은 `dev-log/` 또는 `archive/`로 내린다.
4. 코드와 함께 오래 참이어야 하는 계약만 `reference/`에 둔다.

이는 기존 Harness 검토의 “작은 live surface, 보존된 evidence” 권고를 **300개 표본으로 보강**한다. 이 조사는 파일 이동이나 삭제를 수행하지 않는다.

---

## 2. 표본 정의와 실제 검증 수

### 2.1 전역 고스타 공개 저장소 표본

다음 GitHub GraphQL 검색 결과를 cursor pagination하여 처음 1,000개를 조사했다. 검색 응답에서 관찰된 별점 범위는 32,036~533,607이었고, 구조 분석 대상은 그 결과 중 `docs/` tree 보유군을 별점으로 다시 정렬해 선정했다.

```graphql
search(
  query: "stars:>5000 fork:false archived:false"
  type: REPOSITORY
  first: 100
  after: $cursor
) {
  nodes {
    ... on Repository {
      nameWithOwner
      stargazerCount
      docs: object(expression: "HEAD:docs") { __typename }
    }
  }
}
```

`Repository.object(expression: "HEAD:docs")`가 `Tree`인 경우만 **기본 브랜치에서 추적되는 `docs/` 디렉터리**로 판정했다. GitHub의 [`search` query](https://docs.github.com/en/graphql/reference/queries#search), [`Repository.object`](https://docs.github.com/en/graphql/reference/objects#repository), [`Tree`](https://docs.github.com/en/graphql/reference/objects#tree) 타입이 이 판정의 1차 근거다.

| 단계 | 수 | 의미 |
| --- | ---: | --- |
| 공개·non-fork·non-archived, `stars:>5000` 후보 | 1,000 | GitHub search 결과의 첫 1,000개 |
| `HEAD:docs`가 `Tree` | 447 | 실제 Git tree에 `docs/` 디렉터리가 존재 |
| `HEAD:docs`가 tree가 아닌 object | 1 | 이름이 `docs`인 파일/비디렉터리 — 구조 분석에서 제외 |
| 문서 tree 보유군 중 별점 상위 구조 분석 표본 | **300** | 별점 **40,299~393,464** |

300개에는 앱·프레임워크·교육 저장소도 섞인다. GitHub 검색 결과만으로 “라이브러리”를 엄격히 구분할 수 없으므로, 이 표본은 **고스타 공개 소프트웨어 저장소 benchmark**로 읽어야 한다.

### 2.2 `topic:library` 대조 표본

“라이브러리”라는 사용자 표현에 가장 가까운 GitHub 분류도 별도로 대조했다.

```graphql
search(
  query: "is:public fork:false archived:false topic:library sort:stars-desc"
  type: REPOSITORY
  first: 100
  after: $cursor
) {
  nodes {
    ... on Repository {
      nameWithOwner
      stargazerCount
      docs: object(expression: "HEAD:docs") { __typename }
      gitignore: object(expression: "HEAD:.gitignore") { __typename }
    }
  }
}
```

| 표본 | 별점 범위 | `HEAD:docs = Tree` | root `.gitignore` 존재 |
| --- | ---: | ---: | ---: |
| `topic:library` 상위 300 | 1,088~246,835 | 100 (33.3%) | 286 (95.3%) |
| 전역 고스타 후보 상위 300 (control) | 고스타 순 | 128 (42.7%) | 263 (87.7%) |

`topic:library` 상위 300에서 root `.gitignore` 안의 `docs` 무시 패턴을 정확히 찾은 것은 6개였다. 그중 `HEAD:docs`가 동시에 `Tree`인 것은 `jevonmao/PermissionsSwiftUI` 1개였다. 즉 root `.gitignore`의 존재와 `docs/` 추적 여부는 독립적인 질문이다.

### 2.3 “gitignore하지 않는 docs”의 정확한 해석

**확인된 사실:** `HEAD:docs`가 GitHub API에서 `Tree`로 보이면, 기본 브랜치의 Git object tree에 `docs/`가 존재한다. 따라서 그 디렉터리와 현재 보이는 항목은 추적 중이다.

**확인 불가/범위 밖:** 이것만으로 모든 중첩 `.gitignore`, path-specific 패턴, negation, 혹은 `docs/_build` 같은 **생성 하위 산출물까지 ignore되지 않는다**고 증명할 수는 없다. Git의 ignore 규칙은 이미 추적된 파일을 숨기지도 않는다. 따라서 이 조사는 “문서 원본이 Git으로 버전 관리되는가”에는 답하지만, “문서 하위의 생성물까지 모두 커밋하는가”에는 답하지 않는다.

완전한 ignore 감사가 필요할 때만 후보별로 기본 브랜치를 checkout하고 `git check-ignore -v`를 path별로 실행해야 한다. REST로 대체한다면 search 결과의 `default_branch`와 recursive tree를 읽되, tree 응답의 `truncated`가 true이면 하위 tree를 재귀 조회해야 한다. [GitHub REST repository search](https://docs.github.com/en/rest/search/search#search-repositories)도 검색 결과는 최대 1,000개라는 제한을 명시한다.

---

## 3. 300개 `docs/` tree 구조

각 표본의 `HEAD:docs` tree entry 이름·type을 읽어 최상위 하위 디렉터리 수로 분류했다. 파일과 디렉터리를 합친 docs root entry의 중앙값은 **10개**다.

| 구조 | 기준 | 저장소 수 | 읽는 법 |
| --- | --- | ---: | --- |
| Flat | 하위 디렉터리 0개 | 61 | 작은 API 문서, 단일 README형 문서, 혹은 아직 작은 문서 세트 |
| Shallow | 1~4개 | 126 | 공개 문서에서도 가장 흔한 실용 구간 — 2~4개의 독자/관심사 축 |
| Sectioned | 5~15개 | 92 | 가이드·API reference·릴리스·기여·자산을 한 docs site에 수용 |
| Large taxonomy | 16개 이상 | 21 | 제품·플랫폼·다국어·장기 릴리스 문서에 가까운 구조 |
| **합계** |  | **300** |  |

추가로 top-level에 locale 또는 i18n 축이 있는 저장소는 **40개**, docs root에서 검출 가능한 빌드 marker의 최소치는 VitePress **9**, VuePress **2**, Docusaurus **3**, Sphinx **15**, MkDocs **1**이었다. 이 수치는 docs 내부의 표지로만 센 **최소치**다. 설정이 repository root나 별도 docs repository에 있으면 세지지 않는다.

문서 원본 확장자(`.md`, `.mdx`, `.rst`, `.html`)가 docs root에 직접 있는 표본은 **262개**였다. flat인데 그런 문서 파일도 없어 구조상 scaffold에 가까운 경우는 **5개**였다. 즉 `docs/`라는 디렉터리명만 보고 문서량·문서 성숙도를 단정하면 안 된다.

### 대표 사례 — 구조는 독자·배포 모델에서 나온다

| 패턴 | GitHub tree에서 보이는 최상위 구조 | QuantBridge에 주는 의미 |
| --- | --- | --- |
| 제품 기능 문서 | [Ollama](https://github.com/ollama/ollama/tree/main/docs): `api`, `capabilities`, `integrations`, `tools` 등 | 외부 사용자가 많은 API 제품은 기능 축 taxonomy가 자연스럽다. 내부 운영 문서에 그대로 적용할 근거는 아니다. |
| API·개발·튜토리얼 분리 | [Electron](https://github.com/electron/electron/tree/main/docs): `api`, `development`, `tutorial`, `fiddles` 등 | 서로 다른 독자(사용자/기여자)의 문서를 같은 파일에 누적하지 않는다. |
| 레퍼런스·How-to·내부 문서 | [Django](https://github.com/django/django/tree/main/docs): `faq`, `howto`, `internals`, `intro`, `ref`, `releases`, `topics` 등 | “문서 종류”와 “도메인”을 한 폴더 이름에 혼합하지 않고, 독자 질문을 기준으로 분리한다. |
| 번역이 taxonomy를 키우는 경우 | [FastAPI](https://github.com/fastapi/fastapi/tree/master/docs): `de`, `en`, `es`, `fr`, `ja`, `ko` 등 | 다국어 축은 공개 제품 문서의 요구다. QuantBridge 내부 문서는 지금 별도 locale tree가 필요 없다. |
| docs가 웹사이트 source 자체 | [Hugo](https://github.com/gohugoio/hugo/tree/master/docs): `content`, `layouts`, `static`, `assets` 등 | 문서 배포 앱의 source와 문서 내용을 함께 둘 때만 `assets`·`layouts`·`static`이 정당하다. |
| builder source 중심 | [Hugging Face Transformers](https://github.com/huggingface/transformers/tree/main/docs): `source` | 문서 generator가 강한 프로젝트는 source tree를 유지한다. QuantBridge에는 docs generator 도입 요구가 없다. |

---

## 4. QuantBridge 적용안

### 4.1 채택할 것과 채택하지 않을 것

| 관찰 | QuantBridge 결정 | 이유 |
| --- | --- | --- |
| 62.3%가 flat 또는 1~4 하위 디렉터리 | **docs 최상위 taxonomy를 더 늘리지 않는다.** | 현재 문제는 최상위 분류 부족보다 live 문서 비대화다. |
| 30.7%의 sectioned 구조와 7.0%의 large taxonomy | **공개 docs site 구조는 도입하지 않는다.** | QuantBridge에는 다국어/API portal/문서 web app 요구가 없다. |
| docs tree 447/1,000 | **`docs/` 부재를 성숙도 부족으로 읽지 않는다.** | 인기 프로젝트도 external docs, README, 다른 경로를 사용한다. 문서의 공개 위치는 프로젝트 특성이다. |
| `docs/` tree와 `.gitignore`의 공존 | **문서 원본은 추적하되 생성 출력은 ignore 가능하게 둔다.** | `docs/` 전체를 ignore하지 않고 `_build/`, site output, 임시 이미지처럼 생성물만 제외하는 것이 정상적이다. |
| Django/Electron의 독자 분리 | **문서마다 독자·질문·수명을 하나로 정한다.** | reference, decision, sprint evidence를 한 문서에 섞는 것을 막는다. |

### 4.2 권장 live/cold 구조

이 구조는 새 폴더를 만드는 구현 지시가 아니라, 앞으로 파일을 놓을 때의 판단 기준이다. 현재 구조가 대체로 이 방향을 이미 가진다.

```text
docs/
├── README.md      # “어디를 읽는가” 단일 지도
├── status.md      # 현재 sprint의 작업 계약만
├── roadmap.md     # 다음 후보와 product trigger만
├── backlog.md     # 열린 BL의 짧은 ledger + evidence 링크
├── reference/     # 코드와 함께 오래 참인 domain/API/architecture/operation 계약
├── decisions/     # 주소가 안정적인 ADR
├── dev-log/       # 완료된 sprint의 판단·측정·결과
└── archive/       # 더 이상 기본 경로가 아닌 상세 증거
```

문서 사이트형 구조(`assets/`, `static/`, `layouts/`, `i18n/`, `versioned_docs/`)는 **문서 웹사이트를 실제로 빌드·배포하기로 결정한 경우에만** 추가한다. 지금의 내부 문서 정리 목적을 위해서는 오히려 노이즈다.

### 4.3 파일 생성·이동 전 체크

새 문서가 필요하면 먼저 다음 네 질문에 답한다.

1. 누가 어떤 질문에 답하려고 읽는가?
2. 코드와 함께 계속 참이어야 하는가(`reference`), 결정 기록인가(`decisions`), 이번 sprint의 결과인가(`dev-log`), 아니면 cold evidence인가(`archive`)?
3. 기존 `docs/README.md`의 질문-경로 지도에 이미 들어갈 수 있는가?
4. 완료 뒤 `status.md`나 `backlog.md`에 이 문단이 계속 남아야 하는가, 아니면 evidence 링크 하나면 충분한가?

네 번째에 “링크 하나면 충분하다”면 live 파일에 서술을 누적하지 않는다. 이 기준은 약 160행의 `status.md` 예산과 열린 BL 요약이라는 기존 Harness 검토의 운영 원칙을 지지한다.

### 4.4 이번 조사로는 결정하지 않는 것

- `README.md`, `AGENTS.md`, `CONTEXT.md`, legacy PRD, `DESIGN.md`의 **루트 배치**는 이 표본이 아니라 별도 Harness·로컬 inventory 검토의 판단 대상이다.
- 모든 `reference/` 파일을 하나로 합치거나, ADR/dev-log/archive를 삭제하는 것은 표본에서 지지되지 않는다. 주소 안정성과 금융 시스템의 증거 보존이 더 중요하다.
- 문서용 프레임워크, 다국어, 버전 문서, 자동 docs deploy는 현재 요구가 없으므로 채택하지 않는다.

---

## 5. 재현·한계

### 재현 절차

1. GitHub GraphQL search에 §2.1 query를 100개씩 cursor pagination하여 처음 1,000개를 고정한다.
2. 각 repository에서 `HEAD:docs`의 `__typename`을 읽고 `Tree`만 retained set으로 만든다.
3. retained set을 `stargazerCount` 내림차순으로 정렬해 처음 300개를 선택한다.
4. 그 300개에 아래 fragment를 추가해 docs root entry를 읽고, `type = tree`인 entry 수로 §3 bucket을 계산한다.

```graphql
docs: object(expression: "HEAD:docs") {
  ... on Tree {
    entries { name type }
  }
}
```

5. ignore 감사이 필요하면 `.gitignore` object 존재 여부만으로 결론내지 않고 checkout + `git check-ignore -v`로 실제 path를 판정한다.

### 한계와 누락 사유

- GitHub search의 1,000개 cap 때문에 “모든 고스타 저장소”가 아니라 **조건을 만족하는 별점순 첫 1,000개**다.
- 별점은 수시로 변하고, tree도 기본 브랜치 HEAD 기준 스냅샷이므로 재실행하면 경계 저장소와 수치가 달라질 수 있다.
- GitHub topic은 self-assigned metadata다. `topic:library` 대조는 좁은 해석일 뿐, 라이브러리의 완전한 정의가 아니다.
- `HEAD:docs`가 404/null인 저장소는 문서가 없다는 뜻이 아니라, README·wiki·외부 사이트·다른 경로에 있다는 뜻일 수 있다.
- 이 조사에서는 문서의 품질·최신성·내용 정확성을 등급화하지 않았다. **경로와 Git 추적 상태**만 정량화했다.
- 대규모 구조 판정은 인증된 GitHub GraphQL query로 수행했다. 비인증 REST로 재현할 경우 search·core rate limit이 더 낮으므로, 같은 규모의 조사는 인증된 GitHub token을 사용한다. 저장소별 raw tree 전체는 repo에 추가하지 않았다.

---

## 6. 최종 제안

QuantBridge는 고스타 공개 라이브러리의 문서 사이트를 모방하지 말고, 이미 가진 **질문별 지도 + 수명별 분리**를 끝까지 적용한다.

1. 루트 문서와 `docs/README.md`는 더 많은 내용을 담는 장소가 아니라 **입구**로 제한한다.
2. `status.md`와 `backlog.md`에서 완료된 narrative를 빼는 것을 가장 먼저 한다.
3. `reference/`의 계약 문서는 분리된 채 유지하되, 미래의 path 정리는 domain/architecture/operations처럼 **독자가 찾는 질문**을 기준으로만 한다.
4. sprint evidence는 삭제하지 않고 `dev-log/`·`archive/`로 cold path화한다.
5. 외부 문서 사이트가 실제 요구될 때까지 문서 프레임워크·locale tree·asset pipeline은 만들지 않는다.

이 선택은 문서 파일 수 자체가 아니라, 새 세션과 사람이 **지금 필요한 정본을 빠르게 찾고, 완료된 증거는 필요할 때만 여는 구조**를 목표로 한다.

---

## 변경 이력

- **2026-08-01** — GitHub GraphQL의 전역 고스타 1,000 후보와 `topic:library` 300 대조 표본을 기본 브랜치 `HEAD:docs` tree로 조사해 작성. 코드 및 기존 문서 변경 없음.
