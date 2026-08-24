# Step 1: `DESIGN.md` — 줄 번호를 앵커로

## 읽어야 할 파일

- `DESIGN.md` — 수리 대상
- `apps/web/src/styles/globals.css` — 인용 대상(앵커가 실제로 그것을 가리키는지 확인용)
- `tools/scripts/doc-coord-audit.py` — step 0 이 만든 감사기(위반 목록의 정본)
- 이전 step 의 `summary` — 파일별 위반 분포

## 배경

step 0 의 감사기가 `DESIGN.md` 에서 `globals.css` 줄 번호 인용을 잡고 있다.
**이 step 이 그것을 0 으로 만든다.** 재측정이 아니라 **전환**이다.

## 작업

감사기가 잡는 `DESIGN.md` 의 인용을 **전부 앵커로 바꾼다.**

| 지금 | 바꿀 형태 |
| --- | --- |
| `` `globals.css:204-211` 의 `@theme` 블록 `` | `` `globals.css` 의 `@theme` 블록 `` |
| `` 기본 `:168` · 아이콘 레일 `:184-186` `` | `` 기본 `:root` 의 `--sidebar-w` · 아이콘 레일 = `max-width: 1024px` 미디어 안의 재선언 `` |
| `` KITPORT 사본(`:1846` 1024 / `:1856` 768) `` | `` KITPORT 구간(`KITPORT-START`~`KITPORT-END` 센티넬) 안의 사본 `` |
| `` `.searchbox` CSS(`globals.css:1146-1165` 정의, `:1840` 1024px 숨김) `` | `` `.searchbox` 규칙과 그 `max-width: 1024px` 숨김 `` |

원칙 셋:

1. **앵커는 그 파일에서 유일해야 한다** — 선택자·CSS 변수명·센티넬 주석처럼 검색하면 바로 찾히는 것.
   유일하지 않으면 상위 블록을 함께 적어라(예: 「`@theme` 안의 `--breakpoint-sm`」).
2. **앵커가 실제로 존재하는지 확인해라.** 바꾼 뒤 그 토큰을 `globals.css` 에서 실제로 grep 해 봐라.
   존재하지 않는 앵커는 죽은 줄 번호보다 나쁘다.
3. **문장의 의미를 바꾸지 마라.** 좌표 표기만 바꾸는 것이고, 그 절이 주장하는 값(232/64/0 · 1240px 등)과
   근거는 그대로 둔다. ★단 **읽다가 사실이 틀린 것을 발견하면 고치고 `summary` 에 적어라** —
   좌표를 옮기며 값도 함께 틀린 자리가 있을 수 있다.

★**줄 번호를 「대략」으로 남기지 마라**(「`:169` 근처」 같은 표기). 감사기가 잡고, 잡는 것이 옳다.

## Acceptance Criteria

```bash
python3 tools/scripts/doc-coord-audit.py --selftest
python3 tools/scripts/doc-coord-audit.py --check --only DESIGN.md
python3 tools/scripts/doc-coord-audit.py --check --baseline
```

세 번째는 **나머지 대상의 위반 수가 줄지 않았는지**를 본다 — 이 step 은 `DESIGN.md` 만 만진다.
baseline 을 그에 맞게 갱신하는 것은 이 step 의 정상 산출이다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **앵커 실재 확인** — 바꾼 앵커 토큰을 전부 `globals.css` 에서 grep 해 1건 이상인지 확인해라.
   0건이면 그 앵커는 거짓이다.
3. `summary` 에 바꾼 인용 수와 **읽다가 발견한 사실 오류**를 적어라.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **감사기를 느슨하게 고쳐 통과시키지 마라.** 이유: 목적은 인용을 고치는 것이다.
  감사기 수정이 필요해 보이면 `blocked` 로 멈춰라.
- **문서의 주장(값·근거·실측 표)을 지우지 마라.** 이유: 이 회차는 표기 전환이지 내용 삭제가 아니다.
- **`globals.css` 를 고치지 마라.** 이유: KITPORT 구간은 `_kit.html` 과 주석까지 바이트 대조된다 —
  건드리면 `design-canon-kit-port.test.ts` 가 즉시 red 다.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
