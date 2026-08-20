# Step 1: vitals-verdict-and-rc

## 읽어야 할 파일

- `tools/scripts/ledger-vitals.sh` — 특히 축 ③ 블록(74~111행)의 `lead()` / `verdict_of()` awk 함수
- `apps/api/tests/scripts/test_ledger_vitals.py` — **앞 step 이 만든 파일. 여기에 이어 붙인다**
- `docs/decisions/028-backlog-deferred-verdict.md` — 판정어 5종의 정본 (DEFERRED 가 왜 있나)

## 배경

축 ③ 은 「`backlog.md` 안에 RESOLVED 상태줄 섹션이 0건인가」다 — 원장 3분할([BL-779])에서
RESOLVED 는 `backlog-resolved.md` 소관이라, backlog.md 에 남아 있으면 **역류**다.
실제 사고: 2026-08-16 이후 닫힌 RESOLVED **13건이 전부 backlog.md 에 다시 쌓였고**
규칙이 산문이라 아무 게이트도 안 읽었다.

판정은 `verdict_of()` 의 **어휘 우선순위**다 — `DEFERRED` → `ACTIVE` → `PARTIAL` →
`RESOLVED` 순으로 대조하고 **앞이 이긴다**. 그래서 「부분 RESOLVED」는 PARTIAL 로 잡혀
역류로 안 세진다. 이 순서가 뒤집히면 정상 원장이 통째로 red 가 된다.

## 작업

`apps/api/tests/scripts/test_ledger_vitals.py` 에 **축 ③ + rc 계약**을 이어 붙여라.
앞 step 의 호출 헬퍼를 그대로 재사용한다(새 헬퍼 모듈 금지).

축 ③ 은 `### BL-<번호>` 섹션의 **첫 유효 `**상태:**`/`**Status:**` 줄**만 본다:

1. **역류 1건이면 rc=1** — stdout 에 `✗ ③` 과 건수, 그리고 stderr 에서 수집한 BL 번호가
   실린다. 최소 `BL-` 번호 문자열이 stdout 메시지에 실리는지 단언해라
2. **역류 0건이면 rc=0**
3. **우선순위 — 「부분 RESOLVED」는 PARTIAL 이라 안 센다** (`RESOLVED` 문자열을 포함하는데도
   세지 않는다는 것이 이 축의 핵심 반례다)
4. **DEFERRED 가 이긴다** — `⏳ **대기 (트리거 미도래)**` 형태의 상태줄은 RESOLVED 로 안 센다
5. **대소문자 무관** — 소문자 `resolved` 로 쓴 상태줄도 역류로 센다(`toupper` 수리)
6. **취소선 상태줄은 근거에서 빠지고 자리를 소비하지 않는다** — `~~` 가 든 상태줄 **다음**의
   상태줄이 그 섹션의 판정이 된다. 취소선 줄이 RESOLVED 이고 다음 줄이 ACTIVE 면 rc=0,
   반대면 rc=1 이어야 한다
7. **한 섹션은 한 번만 센다** — 같은 `### BL-` 아래 RESOLVED 상태줄이 둘이어도 1건이다
   (`seen` 플래그). 그리고 `### BL-` 헤딩 밖의 상태줄은 아예 안 본다
8. **코드펜스 제외는 축 ③ 에 없다** — 이것은 축 ①·② 와 다른 계약이다. 지금 스크립트가
   무엇을 하는지 **읽고** 그 사실을 그대로 고정해라(코드가 정본이다). 네가 옳다고 여기는
   쪽으로 바꿔 쓰지 마라

rc 계약 — 이 스크립트가 무엇으로 실패를 말하는가:

9. **대상 파일 부재 → rc=3** (`--status-file` 이 없는 경로일 때 · `--backlog-file` 이
   없는 경로일 때 각각). ★「측정불가는 통과가 아니다」가 이 rc 의 존재 이유다 — rc=0 이 아님을
   단언하는 것으로 만족하지 말고 **정확히 3** 을 단언해라
10. **알 수 없는 인자 → rc=1** · **플래그에 값이 없으면 rc=1** (`--status-file` 만 주고 값 생략)
11. **test-mode 표기** — 플래그를 쓰면 stderr 에 `test-mode` 가 실린다(집행 로그와 구분하는 장치)
12. **전건 통과 → rc=0 이고 stdout 에 `✓ ledger-vitals 3축 통과`** 와 세 수치가 실린다
    (양성 대조 — 「항상 rc=1」인 판정기도 위 케이스 절반을 통과한다)

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_ledger_vitals.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_ledger_vitals.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. 축 ③ 케이스에서 **축 ①·② 가 조용한지** 확인해라 — status 픽스처는 「다음 행동 =」 1개 +
   ⓪ 표 3행을 유지해야 rc=1 이 축 ③ 때문임이 증명된다. stdout 의 `✗ ③` 단언이 그 증거다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/ledger-vitals.sh` 를 **수정하지 마라** (step0 과 같은 이유)
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. 커밋하지 마라
- 진짜 `docs/backlog.md` 를 겨누지 마라 — 반드시 `tmp_path` + `--backlog-file`
- 앞 step 이 만든 테스트를 **지우거나 이름을 바꾸지 마라.** 이유: AC 의 수집 개수 하한이
  누적값(≥10)이라, 앞 것을 지우면서 새로 쓰면 판별력이 사라진다
