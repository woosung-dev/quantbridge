# Step 3: 종결 — 위반 0 과 판별력을 함께 증명한다

## 읽어야 할 파일

- `tools/scripts/doc-coord-audit.py` — 감사기
- 이전 step 들의 `summary` — 무엇을 어떻게 바꿨는지

## 배경

앞 step 들이 인용을 앵커로 바꿨다. 이 step 은 **두 가지를 동시에 증명**한다:

1. **위반이 0 이다** — `--check` · `--dead-paths` 가 rc=0
2. ★**감사기가 여전히 판별력을 갖는다** — 위반이 0 인 것과 **감사기가 죽은 것**은 rc 로 구별되지 않는다.
   이 레포는 「빈 입력이 초록으로」를 여러 번 밟았다.

## 작업

### ⑴ baseline 을 종결한다

`--baseline` 이 참조하던 동결 파일을 **0 위반 상태로 갱신**하거나, 더 이상 의미가 없으면 제거하고
`--check` 를 기본 판정으로 남겨라. 어느 쪽이든 **`--baseline` 플래그가 계속 동작해야 한다**
(AC 가 그것을 부른다). 선택한 이유를 스크립트 주석에 남겨라.

### ⑵ 판별력을 다시 증명한다

`--selftest` 가 여전히 **양성 2 · 음성 2** 를 전부 통과하는지 확인해라. 그리고 **실트리 변이**를
한 번 해라:

- `DESIGN.md` 에 `globals.css:999` 를 임시로 한 줄 심는다 → `--check` 가 **rc=1**
- 되돌린다 → `--check` 가 **rc=0**
- 원복은 `git diff --stat` 으로 확인한다

★앵커가 1건인지 먼저 세라 — 0 이면 못 심은 것이고, 2 이상이면 어디가 바뀌었는지 모른다.

### ⑶ 회차 총결산을 `summary` 에 남긴다

CONTROL 이 이것으로 원장을 닫는다. 담을 것:

- 바꾼 인용 수(파일별) · 죽은 경로 정정 수
- **CONTROL 로 넘긴 항목** — 특히 가드레일 4축에 남은 줄 번호 인용(있다면 그 목록)
- 변이 결과(심었을 때 red · 원복 시 green)
- 감사기의 **알려진 사각** — 무엇을 못 잡는가(다음 사람이 초록을 과신하지 않도록)

## Acceptance Criteria

```bash
python3 tools/scripts/doc-coord-audit.py --selftest
python3 tools/scripts/doc-coord-audit.py --check
python3 tools/scripts/doc-coord-audit.py --dead-paths
cd apps/web && pnpm exec biome check .
cd apps/web && pnpm exec vitest run --silent
```

마지막은 **광역 회귀**다 — 주석·문서만 바꿨어도 FE 테스트가 문자열을 읽는 검사기를 갖고 있다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ⑵ 의 변이를 **실제로 하고 원복**했는지 `git diff --stat` 으로 확인해라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`--selftest` 를 약화시켜 통과시키지 마라.** 이유: 그것이 이 회차 산출의 유일한 판별력 증거다.
- **감사기의 대상 목록을 좁혀 위반을 0 으로 만들지 마라.** 이유: 그것은 수리가 아니라 은폐다.
  대상을 좁혀야 할 이유가 있으면 `summary` 에 적고 CONTROL 판단으로 넘겨라.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
