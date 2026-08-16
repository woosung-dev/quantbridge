# ADR-036: 도구 버전 SSOT — `mise.toml` 하나로 모으고 네이티브 핀 파일을 없앤다

- **날짜:** 2026-08-16
- **상태:** Accepted
- **관련:** [ADR-026](026-documentation-ssot.md)(SSOT 7축 — 같은 사실을 두 곳에 적지 않는다) · [ADR-029](029-monorepo-standard-layout.md)(레포 배치) · [BL-587](../backlog.md)(python 핀의 최초 도입 근거 — 본 ADR 이 그 위치를 옮긴다)

## Context

태스크 러너 전환(Just / go-task / mise)을 검토하다 **버전 관리 쪽이 실제 문제**임이 실측으로 드러났다.
러너는 바꾸지 않는다 — 우리 Makefile 은 조건부 선행조건(`ifndef QB_MIGRATE_DONE` + `ifeq ($(QB_SLOT),0)`)을
선언적으로 쓰는데 Just·mise·go-task 중 그것을 표현하는 도구가 없다. 아래는 **버전 축에 한정한** 결정이다.

### 실측한 드리프트 (2026-08-16)

| 도구   | 로컬 PATH                     | CI 선언                  | 프로덕션 이미지    | 판정                       |
| ------ | ----------------------------- | ------------------------ | ------------------ | -------------------------- |
| node   | v22.23.1                      | `node-version: 20`       | `node:22-alpine`   | ✗ **CI 만 20**             |
| pnpm   | 루트 8.15.9 / apps/web 9.12.0 | `version: 9`             | —                  | ✗ **한 레포에 메이저 2개** |
| python | venv 3.12.12                  | `python-version: "3.12"` | `python:3.12-slim` | ✓                          |
| uv     | 0.10.4 (수동 설치)            | `setup-uv` = **latest**  | —                  | ✗ **핀 0건**               |

- node 20 은 **2026-04-30 EOL** 이다. 3면 중 낡은 쪽이 CI 였다.
- 루트 `package.json` 에 `packageManager` 가 없어 루트 pnpm 이 8 로 떨어져 있었다
  (루트 `pnpm-lock.yaml` = lockfileVersion 6.0, `apps/web` = 9.0).
- `ci-cd.md` 에 **「CI Node 버전은 20, 로컬 권장은 22+. 향후 일치시킬지 검토」** 가 Sprint 5 부터 남아 있었다.

### 갈래

- ⓐ **mise 를 버전 핀 전용으로 얇게 도입** — `mise.toml` 에 node 만 넣고 python 은 `.python-version`,
  pnpm 은 `packageManager` 에 그대로 둔다. 이식 비용 0.
- ⓑ **mise.toml 을 유일 소유자로** — 네이티브 핀 파일을 없애고 CI 도 `mise.toml` 을 읽게 한다.

평가자는 ⓐ 를 추천했다(위험 0). **사용자 결정은 ⓑ 다**(2026-08-16) — 「파일은 하나로 유지하고 싶다,
여러 곳에서 관리하고 싶지 않다」. ⓐ 는 값이 적힌 곳을 3곳으로 **분산한 채 유지**하므로 요구와 반대다.

## Decision

**버전 숫자를 적는 곳은 루트 [`mise.toml`](../../mise.toml) 하나다.**

1. `[tools]` 에 node · python · pnpm · uv 4종을 핀한다.
2. `apps/api/.python-version` 을 **삭제**한다.
3. `apps/web/package.json` 의 `packageManager` 필드를 **삭제**한다.
4. CI 워크플로 4개(8 job)의 `setup-node` · `setup-python` · `setup-uv` · `pnpm/action-setup` 을
   `jdx/mise-action` 으로 교체한다. 워크플로에 남은 버전 숫자는 **0건**이다.
5. 배선은 shim 을 PATH 앞에 세우는 **한 줄**로 한다 — `Makefile`, `.husky/pre-commit`, `.husky/pre-push`.

### 남는 예외 2곳 — 없앨 수 없다

`apps/web/Dockerfile:15` 의 `FROM node:22-alpine` 과 `apps/api/Dockerfile:13,38` 의
`FROM python:3.12-slim` 은 `mise.toml` 을 읽을 수 없다. **6곳 → 3곳**이 도달 가능한 최소이고,
`ARG` + build-arg 주입으로 더 줄이는 것은 얻는 것보다 배선이 비싸다. 버전을 올릴 때 이 둘을 같이 봐라.

## Consequences

### 얻는 것

- 로컬·CI·프로덕션 이미지가 같은 node 를 쓴다. EOL 런타임이 CI 에서 빠졌다.
- uv 가 처음으로 핀됐다. 종전에는 **밤마다 다른 uv** 로 실주문 스모크(`nightly-real-broker.yml`)가 돌았다.
- 루트/`apps/web` 의 pnpm 메이저 분열이 없어졌다.
- 온보딩이 `brew install mise && mise install` 두 줄이다.

### 잃는 것 / 새 의무

- **mise 가 사실상 필수 의존성이 됐다.** 미설치 시 깨지지는 않지만(PATH 의 없는 디렉터리는 무시된다)
  버전이 안 정해진 상태로 되돌아간다.
- `setup-node` 의 `cache: pnpm` 과 `setup-uv` 의 `enable-cache` 를 잃어, pnpm store 와 `~/.cache/uv` 를
  `actions/cache` 로 **직접** 잡는다. 캐시 키가 각각 `apps/web/pnpm-lock.yaml`·`apps/api/uv.lock` 이다.
- 버전을 올릴 때 볼 곳이 3곳이다 — `mise.toml` + Dockerfile 2개.

### 실측으로 확정한 함정 3건

1. ★**mise 는 네이티브 버전 파일을 기본으로 읽지 않는다.** `idiomatic_version_file_enable_tools = []`
   이 기본값이라 `.python-version` 단독·`packageManager` 단독은 **둘 다 무시**된다(실측). 그리고
   `mise.toml` 과 `.python-version` 이 함께 있으면 **`mise.toml` 이 이긴다.**
   ⇒ 둘을 같이 두면 값이 갈렸을 때 mise 와 uv 가 **서로 다른 python 을 조용히** 고른다. 그래서 삭제다.
2. ★**`.python-version` 을 지우면 uv 가 더 높은 것을 고른다.** `requires-python = ">=3.12"` 만 남기고
   실측하니 uv 는 **3.13.12** 를 골랐다. 그래서 `requires-python` 에 **상한**(`<3.13`)을 넣었다.
   이 상한은 mise 없이 uv 만 도는 경로의 안전망이지 두 번째 핀이 아니다.
3. ★**핀의 위치를 옮기면 그것을 가리키는 문장도 같이 옮겨야 한다.** [BL-587] 이 세운 탐지기
   `test_envelope_python_minor_matches_runtime` 은 삭제 후에도 **동작한다** — 런타임과 정답지를 비교하지
   파일을 읽지 않기 때문이다. 하지만 그 docstring 과 assert 메시지가 `apps/api/.python-version` 을
   **명시적으로 가리키고 있었다.** 방치했으면 red 를 만난 다음 사람이 없는 파일을 찾는다
   (`apps/api/AGENTS.md` §10 — 「주석에 적는 근거 문장도 실측 대상이다」).

## 검증

- `mise ls` — 4종 전부 출처가 레포 `mise.toml` 이고 실행 경로가 mise 설치 디렉터리다.
- **음성 대조** — `node = "20"` 인 별도 디렉터리는 v20.20.2, 레포는 v22.23.2. 값이 출력을 실제로 바꾼다
  (같은 값이 우연히 나온 것이 아님을 이것으로 가른다).
- `grep -rE 'node-version:|python-version:|setup-node|setup-python|setup-uv|pnpm/action-setup' .github/workflows/`
  → 주석을 뺀 실효 선언 **0건**.
- 루트는 lockfileVersion 6.0 이지만 pnpm 9 의 `pnpm exec` 는 rc=0 이다(실측) — 루트 lock 재생성은 불필요.

## 대안 기각 사유

- **태스크 러너까지 mise 로 이전** — 기각. 러너 축 점수(셸 오케스트레이션·조건부 선행조건·
  discoverability)에서 mise 는 Make 에 진다. `ifndef`/`ifeq` 로 의존성을 붙였다 뗐다 하는
  `be-isolated` 를 선언적으로 못 쓴다. 그것을 레시피 본문 `if` 로 내리면 **워크트리에서 남의 DB 에
  migration 을 거는 사고 경로가 코드 안쪽으로 숨는다.**
- **Just / go-task** — 기각. 둘 다 버전 관리가 없어 이 ADR 이 푸는 문제를 아예 안 푼다.
