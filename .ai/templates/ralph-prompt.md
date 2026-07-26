# PROMPT.md 템플릿 (Ralph Loop)

> 이 파일을 프로젝트 루트에 `PROMPT.md`로 복사하여 사용하세요.
> 매 루프 반복마다 `cat PROMPT.md | claude --print` 또는 `ralph.sh`를 통해 주입됩니다.
>
> `{{ }}` 부분을 프로젝트에 맞게 수정하세요.

---

아래를 프로젝트 루트에 `PROMPT.md`로 저장하세요:

```markdown
You are running in Ralph Loop mode — an autonomous implementation loop.
Each iteration starts with fresh context. Your progress is saved in git.

## Your Task

1. Read `fix_plan.md` and find the FIRST uncompleted task (marked `[ ]`)
   - If a task is marked `[blocked]`, skip it and move to the next `[ ]`
   - If no `[ ]` tasks remain, create a file `RALPH_DONE` and exit immediately

2. Read `AGENT.md` for build/test commands

3. Read relevant files referenced by the task (specs, existing source code)

4. Read `.ai/rules/` for coding conventions — follow them strictly

5. Implement the task following TDD:
   - If tests already exist for this task: make them pass
   - If no tests exist: write tests first, then implement to make them pass

6. Run the test command from `AGENT.md`. ALL tests must pass.
   - If a test fails, fix it before proceeding
   - If you cannot fix it after 3 attempts, mark the task as `[blocked] {{reason}}` in fix_plan.md

7. Mark the completed task as `[x]` in `fix_plan.md`

8. Commit all changes:
   ```
   git add -A && git commit -m "feat: {{task description}}"
   ```

## Rules

- **ONE task per iteration.** Do not attempt multiple tasks.
- **NEVER skip a failing test.** Fix it or mark the task as blocked.
- **ALWAYS commit before exiting.** Your work is lost if you don't commit.
- **ALWAYS follow `.ai/rules/`** for coding style, naming, and patterns.
- **Do NOT modify completed `[x]` tasks** in fix_plan.md.
- **Keep changes focused.** Only touch files relevant to the current task.
```
