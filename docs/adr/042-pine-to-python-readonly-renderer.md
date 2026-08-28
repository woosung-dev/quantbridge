# ADR-042 — Pine AST → Python **읽기 전용** 렌더러. 실행 경로를 만들지 않는다

- **상태:** Accepted (2026-08-27, 사용자 결정)
- **범위:** `apps/api/src/strategy/pine_v2/py_renderer.py` (신규)
- **관련:** [ADR-004](./004-pine-parser-approach-selection.md)(§"접근 2가 탈락한 상세 근거" — 이 대안의 출처) · [ADR-003](./003-pine-runtime-safety-and-parser-scope.md)(exec/eval 금지) · [ADR-040](./040-strategy-brief-outside-trust-layer.md) · [ADR-041](./041-ai-strategy-generation.md)

## 결정

1. **pynescript AST 를 읽을 수 있는 Python 코드로 렌더한다.** 브리핑 안에서 읽기 전용으로 보여주고
   줄 단위로 원본 Pine 줄에 대응시킨다(`source_map`).
2. **그 출력은 어디서도 실행되지 않는다.** `exec`/`eval`/`import`/`compile` 경로를 만들지 않는다.
3. **부재를 테스트가 집행한다** — 관례가 아니라 집행이다:
   - 렌더러 산출물에 `import`/`exec`/`eval`/dunder 가 나타나지 않는다는 AST 단언
   - 렌더러 출력이 **어떤 실행 경로에도 배선되지 않는다**는 호출그래프 부재 단언
4. **Python 실행기는 만들지 않는다.** 사용자 Python 전략도, LLM 이 쓴 Python 도 실행하지 않는다.

## 이유

[ADR-004](./004-pine-parser-approach-selection.md) 가 「Pine → Python → `exec`」(접근 2)를
**「영구 불채택」**으로 닫으면서, 그 접근이 주장한 이점 중 **하나만은 살렸다**:

> | 생성 Python 을 사람이 읽을 수 있어 투명성 | **접근 2 실행이 아니라 "AST → Python 읽기 전용 렌더러"로 분리 구현 가능** |
> | AI 가 Python 을 잘 이해 | AST → Python 렌더러로 동등 효과 |

**그 렌더러는 2026-04-15 이후 구현된 적이 없다.** 이 ADR 이 그것을 발효한다.

렌더러가 생성보다 나은 이유가 하나 더 있다 — **보여주는 Python 이 실제로 실행되는 AST 에서
파생되므로 드리프트가 구조적으로 0 이다.** LLM 이 따로 쓴 Python 에는 그 보증이 없고,
그래서 [ADR-041] 결정 4 가 이 렌더러를 **드리프트 탐지기의 기준선**으로 쓴다.

## 왜 실행기를 만들지 않나 — 실측 (2026-08-27)

[ADR-003]·[ADR-004] 의 금지에 더해, 현재 태세에서 임의 Python 실행이 **즉시** 무엇을 여는지 쟀다.

| 축 | 실측 |
| --- | --- |
| API 프로세스 | 컨테이너가 아니라 **호스트 systemd uvicorn**(`tools/scripts/api-service.sh:144`, 사용자 `ubuntu`, cgroup·seccomp 없음) ⇒ RCE = VM 셸 |
| DB 접속 | **Postgres 슈퍼유저**(`infra/compose/docker-compose.yml:105`) ⇒ `COPY … FROM PROGRAM` 이 컨테이너 격리를 무효화 |
| 워커 env | **Fernet 마스터 키**(`:114,146,181,213`) ⇒ 전 사용자 거래소 API Key 평문 |
| 그 밖의 시크릿 | 루트 `.env` 의 Cloudflare 터널 토큰 · `~/quantbridge/.env.production` 의 mainnet 키 |
| 인증 경계 | **개방 가입**(`apps/web/src/lib/auth.ts` `requireEmailVerification: false`, allowlist 없음). Cloudflare Access 는 **FE 도메인에만** 걸려 있다 ⇒ 「실사용자 0명」은 「공격자 0명」이 아니다 |
| 자원 제한 | compose 전 파일에 `cpus`·`pids_limit`·`cap_drop`·`read_only`·`network internal` **0건**. `backtest.run` 에 시간 상한 **없음**(`src/tasks/backtest.py:20`) |
| 감지 | CPU·메모리·실행시간 알림 **0개**(`apps/api/prometheus/alerts.yml` 알림 2개, 둘 다 무관) |
| 호스트 | 2 OCPU 를 타 프로젝트와 공유하며 [BL-003] 소크 창이 도는 중 ⇒ CPU 폭주 1건이 mainnet 진입 게이트를 리셋한다 |
| 검증 수단 | CI 에 격리 판별력을 잴 전례 **0건**(docker-in-docker 스텝 없음), 로컬 격리 스택은 `assert-not-pinned` 로 소크 창과 배타 |

⇒ **선행 조건이 10건이고 전부 미충족이다.** 「나중에 열려면」 이 목록이 체크리스트다.

## 실측 — 렌더 범위 (2026-08-27, 구현 시점)

`pine_corpus_v2` 9건의 pynescript 노드 종류는 **42종**이고 전부 유한하다. 그중 문(statement) 9종
(`Expr`·`Assign`·`ReAssign`·`If`·`ForTo`·`FunctionDef`·`Switch`·`Break`·`Continue`)과 식 12종을 옮기고,
나머지는 `pynescript.ast.unparse` 로 **원본 Pine 을 되살려 주석으로 보존**한다.

| 항목 | 값 |
| --- | --- |
| corpus 렌더 성공 | **9/9** (예외 0) |
| 원문 보존 총계 | **1** (i3_drfx 의 `switch` 안 식 1건. 8/9 파일은 0) |
| 구현 규모 | `py_renderer.py` **약 330줄** |

★★**한 줄이 결과를 갈랐다** — pynescript 는 문 레벨 `if`/`for`/`switch` 도 **`Expr` 로 감싼다**
(Pine 에서 그것들이 식으로도 쓰이기 때문). 그대로 식으로 처리하면 블록이 통째로 폴백에 떨어져
**전략의 진입 조건이 주석이 된다.** 감싼 것을 벗기고 함수 본문 마지막 처리를 고쳐 보존 **48 → 1**.

★**`Assign.mode` 는 문자열이 아니라 노드다**(`Var()` / `VarIp()` / `None`). 문자열로 비교하면 조용히
항상 거짓이라 `var` 표시가 사라지는데, **봉을 넘어 유지되는 변수인지**는 전략 독해의 핵심이다.

## 트레이드오프

- 사용자는 **Python 을 쓰지 못한다** — 읽기만 한다. `pandas`/`numpy` 를 쓰는 전략은 이 제품에 없다.
  대가로 얻는 것은 위 10건을 안 지는 것이다.
- 렌더러는 **의미 보존을 보증하지 않는다** — 읽기용 근사다. 그래서 화면이 「읽기 전용 · 실행되지
  않음」을 명시하고 `source_map` 으로 **원본 Pine 줄을 항상 옆에 둔다.** 진실은 Pine 이다.
- Pine 문법이 늘면 렌더러도 따라가야 한다. 못 따라간 노드는 **주석으로 보존하고 지우지 않는다** —
  조용히 빠지면 사용자가 없는 로직을 없다고 믿는다.
