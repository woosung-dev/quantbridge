# ADR-027: 스택 규칙의 자리 — `.claude/rules/` 대신 디렉터리별 `AGENTS.md`

> **상태:** 확정 (Accepted — 2026-08-07, 사용자 판정)
> **일자:** 2026-08-07
> **결정자:** woosung (기안: Claude)
> **대체:** [ADR-026](./026-documentation-ssot.md) **§2 「`.ai/` 를 해체한다」의 배치 결정만** 대체한다.
> ADR-026 의 §1 SSOT 7축 · §3 기록 정책 · §4 AGENTS.md 오리엔테이션 전용 · §5 tombstone 의무는 **그대로 유효**하다.
> **출처:** 2026-08-07 실측 3건 — 하위 `CLAUDE.md` 로드 재현 · Claude Code 공식 메모리 문서 · `agents.md` 스펙
> **관련:** [`AGENTS.md`](../../AGENTS.md) · `backend/AGENTS.md` · `frontend/AGENTS.md`

---

## Context — ADR-026 이 남긴 `[가정]` 이 검증 없이 통과했다

ADR-026 §2 는 스택 규칙을 `.claude/rules/*.md` 로 옮기고 `paths` frontmatter 로 조건부 로드시켰다.
그 결정의 Consequences 에 이렇게 적혀 있다:

> **Claude Code 밖의 도구(codex 등)는 `.claude/rules/` 를 못 읽는다.** [가정] 진입점이 AGENTS.md 하나로 좁아진다.

**이 레포는 codex 를 상시 evaluator 로 쓴다** — `generator-evaluator-pipeline.md` §8.3 이 codex finding 의
코드 대조를 의무로 규정할 만큼 워크플로에 박혀 있다. 그런데 codex 가 백엔드 규칙(Repository-only ·
Decimal-first · prefork-safe)을 못 읽으면 **리뷰 품질이 조용히 떨어진다** — 게이트는 여전히 green 이다.
「가정」으로 적고 넘어갈 축이 아니었다.

## 실측 — 두 배치는 로드 트리거가 **같다**

2026-08-07, `backend/CLAUDE.md`(`@AGENTS.md` 한 줄) + `backend/AGENTS.md`(sentinel) 를 임시로 두고
`backend/src/market_data/models.py` **하나를 Read** 했다. 세 파일이 **동시에** 컨텍스트에 들어왔다:

| 로드된 것                  | 경로                       |
| -------------------------- | -------------------------- |
| 하위 `CLAUDE.md`           | 디렉터리 진입 시 자동      |
| 하위 `AGENTS.md`           | `@` import 를 따라 확장    |
| `.claude/rules/backend.md` | `paths: backend/**/*` 매칭 |

⇒ **`@` import 는 하위 `CLAUDE.md` 에서도 작동하고, 발화 시점은 `paths` 규칙과 동일하다.**

공식 문서(`code.claude.com/docs/en/memory`)도 같은 말을 한다 —
「Claude also discovers `CLAUDE.md` files in subdirectories... they are included **when Claude reads files
in those subdirectories**」. 그리고 **본 결정의 배치가 곧 공식 권장 패턴**이다:

> Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository already uses `AGENTS.md` for other
> coding agents, create a `CLAUDE.md` that imports it so both tools read the same instructions without
> duplicating them.

`agents.md` 스펙 쪽 — 「Agents automatically read the **nearest** file in the directory tree, so the closest
one takes precedence and every subproject can ship tailored instructions」. 지원 목록 첫 줄이 **OpenAI Codex**
이고, OpenAI 자신의 레포가 이 패턴으로 88 개 `AGENTS.md` 를 운영한다.

---

## Decision

### 1. 스택 규칙은 그 스택의 디렉터리에 `AGENTS.md` 로 둔다

```
backend/AGENTS.md      # 구 .claude/rules/backend.md
backend/CLAUDE.md      # @AGENTS.md (한 줄)
frontend/AGENTS.md     # 구 frontend.md + nextjs-shared.md 병합 (§7~§11)
frontend/CLAUDE.md     # @AGENTS.md (한 줄)
```

`.claude/rules/` 는 **비운다.** `.gitignore` 의 `!.claude/rules/` 예외도 함께 지운다 — `.claude/*` 를 통째로
무시하는 정책에 구멍을 뚫을 이유가 없어졌다.

★**심볼릭(`ln -s AGENTS.md CLAUDE.md`)이 아니라 `@AGENTS.md` import 를 쓴다.** `.worktreeinclude` 가
심볼릭을 스킵한다는 사실을 이미 한 번 밟았고, Windows 는 심볼릭에 관리자 권한이 필요하다.

### 2. 하위 `AGENTS.md` 는 루트를 **덮어쓰지 말고 보강만** 한다

두 도구의 의미론이 다르다:

- **Claude Code** — 「All discovered files are **concatenated** into context rather than overriding each other」
- **codex(agents.md 스펙)** — 「the **closest** one takes precedence」

⇒ 하위에 루트와 **충돌하는 문장**을 쓰면 Claude 는 둘 다 보고 codex 는 하위만 본다. **같은 레포가 도구에
따라 다르게 행동한다.** 하위는 그 스택 고유 규칙만 담고, 루트 Golden Rules 를 반박하지 않는다.

### 3. `paths` glob 정밀도는 포기한다

구 `nextjs-shared.md` 는 `frontend/**/*.{ts,tsx}` 로 확장자까지 좁혔다. 새 배치는 **디렉터리 단위**다 —
`frontend/` 안의 `.md`·`.json` 을 열어도 프런트 규칙이 들어온다. 현행 규칙 3 종은 전부 디렉터리 경계와
일치하므로 실질 손실이 없다. ★**규칙이 디렉터리 경계를 넘어야 할 때**(예: `tests/**` 와 `backend/**` 를
함께 겨냥) 는 이 배치로 표현할 수 없다 — 그때가 재평가 시점이다.

---

## Consequences

**얻는 것**

- ★**codex 가 스택 규칙을 읽는다.** ADR-026 이 `[가정]` 으로 남긴 위험이 **문제 자체로 사라진다.**
- **규약이 하나로 준다.** 루트가 이미 `CLAUDE.md → @AGENTS.md` 다. 하위도 같은 형태라 「어디에 무엇을
  두나」에 답이 하나뿐이다.
- **`.gitignore` 예외와 워크트리 마찰이 사라진다.** 부트스트랩이 재생성할 심볼릭도, 기존 워크트리에 남은
  끊긴 링크도 없다.
- ★**「`paths` 없으면 매 세션 고정비」 함정을 구조적으로 저지를 수 없다.** 하위 `CLAUDE.md` 는 **항상**
  조건부다. 구 `global.md` 가 정확히 그 함정으로 6,736 자를 고정비에 얹고 있었다.

**치르는 것**

- 확장자 단위 glob 을 잃는다(§3).
- 파일이 스택당 2 개다. `CLAUDE.md` 는 한 줄이라 읽는 비용은 무시할 만하지만 **두 파일이 같은 자리에
  있어야 한다** — 하나만 옮기면 조용히 안 읽힌다.
- **`/compact` 후 재주입되지 않는다.** 단 이건 `.claude/rules` 의 `paths` 규칙도 똑같다(공식 문서 확인) —
  본 결정으로 나빠지는 축이 아니다. 압축 뒤 스택 규칙이 필요하면 그 디렉터리 파일을 한 번 더 열어라.

## 비고 — 재평가 트리거

⑴ 규칙이 **디렉터리 경계를 넘어야** 할 때(§3) · ⑵ 하위 `AGENTS.md` 가 루트와 충돌해야만 표현되는 규칙이
생길 때(§2) · ⑶ Claude Code 나 `agents.md` 의 로딩·우선순위 규약이 바뀔 때(**본 ADR 의 사실 근거는 두
도구의 현재 동작에 종속이다** — ADR-026 이 버전 종속으로 낡았던 것과 같은 이유) · ⑷ 스택이 3 개를 넘어
루트 AGENTS.md 의 포인터 목록이 길어질 때.
