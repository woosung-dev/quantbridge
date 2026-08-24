# phases/ — 하네스 러너의 회차 정의

> **용도.** `tools/harness/execute.py` 가 `phases/<회차>/index.json` + `step*.md` 를 읽어 lane 을 실행한다.
> 산출물은 `phases/<회차>/runs/` 에만 남기고 그 디렉터리는 gitignore 다.

## 새 회차를 만들 때

```
phases/<회차명>/
├── index.json     # {"steps":[{"id":"step0", ...}]}
└── step0.md …     # step 별 지시서
```
`phases/index.json` 의 `phases` 배열에 **사전 등록**해라 — 나중에 각자 추가하면 배열 끝에서 병합 충돌이 난다.

---

## ★2026-08-23 다이어트 tombstone

> **끝난 회차 64개 + 공통 규약 1개(파일 190개 · 868 KB)를 삭제했다.** `phases/index.json` 이 **64건 전부 `completed`**
> 였다 — 즉 전량이 이미 실행되고 PR 까지 머지된 **작업 지시서**다. 러너는 완료된 회차를 다시 읽지 않는다.
> **원문 = `git show 4c65bc0e:phases/`**. 어느 회차가 무엇을 했는지는 **커밋 메시지와 PR** 이 정본이다.
>
> ★**회차가 끝나면 그 디렉터리를 지워라.** 남겨 두면 여기가 두 번째 changelog 가 된다 —
> 이 레포는 `status.md`(124KB)·`roadmap.md`(550줄)·ADR-024(72KB)에서 같은 병을 이미 겪었다.

## ★2026-08-24 n7 tombstone

> **n7 4 lane(14 step) + `n7-common.md` 삭제.** 전량 `completed` — PR #793~#796 → 통합 #797(`159745b7`) 머지.
> **원문 = `git show 159745b7:phases/`**. 무엇을 했는지는 커밋 메시지와 PR, 반증은 [`docs/lessons.md`](../docs/lessons.md) LESSON-128 이 정본이다.
