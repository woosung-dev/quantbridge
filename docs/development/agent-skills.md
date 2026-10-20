# 에이전트 스킬 설치 계약

이 문서는 프로젝트에 도입한 외부 에이전트 스킬의 출처, 재현 가능한 설치 기준, 적용 범위를 기록한다. 완료 일지나 추가 실행 하네스가 아니다.

## 출처와 고정 버전

두 스킬은 Matt Pocock의 공개 저장소 [`mattpocock/skills`](https://github.com/mattpocock/skills)에서 가져왔다. 저장소와 원문은 아래 커밋에 고정한다.

- 커밋: `5beb35b040e3de97e54fa9e386d7e42d15c295c2`
- TDD: [`skills/engineering/tdd`](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/tdd)
- Codebase Design: [`skills/engineering/codebase-design`](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2/skills/engineering/codebase-design)
- 라이선스: 같은 커밋의 [MIT LICENSE](https://github.com/mattpocock/skills/blob/5beb35b040e3de97e54fa9e386d7e42d15c295c2/LICENSE)

각 설치 폴더에는 해당 LICENSE 원문을 복사해 두었다. LICENSE SHA-256은 `0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5`이며 두 사본 모두 이 값과 일치해야 한다.

## 설치 재현

설치에 사용한 로컬 Codex skill-installer 스크립트 경로와 인자를 기록한다. 실행 위치는 저장소 루트다.

```bash
python /Users/woosung/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo mattpocock/skills \
  --ref 5beb35b040e3de97e54fa9e386d7e42d15c295c2 \
  --path skills/engineering/tdd \
  --path skills/engineering/codebase-design \
  --dest .agents/skills
```

재현성을 확인할 때는 아래 파일들의 SHA-256을 로컬 파일에서 계산해 고정값과 비교한다. 해시 계산은 별도 설치나 네트워크 접근 없이 수행할 수 있다.

| 저장 경로 | SHA-256 |
| --- | --- |
| `.agents/skills/tdd/SKILL.md` | `5505d25bbaa8fc14a79e4d20163936958992a2995b7f1dd1d6197edc9ed722e0` |
| `.agents/skills/tdd/tests.md` | `859f9e592c188fda4fc7277dd180e4ce9c7a2e13f6efe1f6f29eccc9d28c106a` |
| `.agents/skills/tdd/mocking.md` | `3ceb807fdf4a47d6a93d4d9a891e5ba6d362a6247bd08adc451feebfc17361ef` |
| `.agents/skills/tdd/agents/openai.yaml` | `ea6f01cf1b8c06a4b0f5b649d74b1b8ce8685e72af1b38d70d877693e092af0b` |
| `.agents/skills/codebase-design/SKILL.md` | `2c20617f87ec8af6a434859f381b2f061a69b530444e74eb39e78bb016a6d1e2` |
| `.agents/skills/codebase-design/DEEPENING.md` | `f3dd099ce99289bd213914d8ee3e2429b78309c3957ca4583f7659551b1d53c1` |
| `.agents/skills/codebase-design/DESIGN-IT-TWICE.md` | `52b52e75655a27aea59c6966b410bac82448968ad46ef1ebb9f07c274e3ae010` |
| `.agents/skills/codebase-design/agents/openai.yaml` | `edebc9e4fcfe102114012575eaa9600b9b5fd08c311664f389c36e7bc717740f` |

`.agents/`는 기존 `.gitignore` 규칙대로 무시한다. 이 저장소의 설치본은 로컬 작업용이며, 스킬 원문이나 LICENSE를 공유하기 위해 ignore 규칙을 바꾸거나 강제 stage하지 않는다.

## 프로젝트 규칙과 우선순위

프로젝트의 `AGENTS.md`, `CONTEXT.md`, 관련 하위 지침과 사용자의 구체적인 지시가 upstream 스킬 문구보다 우선한다. 스킬은 참고 자료이며 프로젝트 규칙을 대체하지 않는다. 따라서 DB 접근은 Repository 경계 안에서만 하고, 테스트 실행 시 프로젝트의 환경·DB 안전 규칙을 따르며, 대화와 문서는 한국어로 쓴다. 파인 인터프리터 실행에서 금지된 `exec`/`eval` 사용 금지 등 기존 보안 규칙도 그대로 적용한다.

TDD 원문은 테스트 seam을 사용자와 사전 합의하라고 권한다. 이 작업에서는 사용자가 구현 자율성을 위임했으므로, 적절한 단위 테스트 seam을 고르는 일마다 별도 재승인을 요구하지 않는다. 변경 범위와 위험이 지시 범위를 벗어나면 기존 프로젝트 규칙에 따라 질문한다.

## 이번 적용 범위

이번 작업에서 스킬은 `run_backtest_v2` 경로와 Wizard UI 변경의 모듈 경계 및 단위 테스트 설계를 보조하는 참고 기준이다. 단위 검증 통과는 TradingView 원본 전체와의 동등성이나 실제 거래소 API 전체 동작을 증명하지 않는다. 그런 보장은 별도의 범위와 검증 근거가 있어야 한다.

설치 과정에서 외부 LLM API 호출은 하지 않았다. 이 사실은 이번 설치 과정에만 해당하며, 이 문서는 이후 사용의 비용이나 외부 호출 여부를 강제하거나 보장하지 않는다. 또한 스킬의 예시나 지침은 자동으로 별도 하네스, 쉘 반복 루프, 하위 에이전트 작업 또는 킥오프 문서를 만들라는 프로젝트 요구가 아니다. 필요한 작업은 기존 프로젝트의 요청과 승인 범위에서 판단한다.
