#!/usr/bin/env python3
# 하네스 step 러너 — phase 의 step 을 codex 로 순차 실행하고, AC 는 러너가 직접 판정한다.
"""QuantBridge Harness Step Executor (ADR-037 이후 v2).

출처: jha0313/finsight `scripts/execute.py` (강의 자료 harness_framework 계보) 를
[ADR-030] 파일럿과 적대 검증이 확정한 결함을 고쳐 이식했다. 원본 대비 수리 4종:

  ① **AC 는 러너가 실행한다** — 원본은 step 세션(codex)이 써넣은 `"completed"` 를
     그대로 믿었다(코드를 쓴 쪽이 자기 채점). 여기서는 `index.json` 각 step 의
     `ac` 배열(실행 가능한 셸 커맨드)을 러너가 돌려 exit code 로만 판정한다.
     step 세션이 쓸 수 있는 것은 `summary`(산출 요약)와 `blocked`(+사유)뿐이다.
  ② **TimeoutExpired 포착** — 원본은 `subprocess.run(timeout=...)` 의 예외를 안 잡아
     30분 초과 시 러너가 크래시하고 트리가 dirty 로 남았다(파일럿 B 를 죽인 그 결함).
  ③ **가드레일 4축** — 원본은 `docs/*.md` 전량 glob 인데 우리 docs 최상위는 상태
     문서(상태/원장/교훈, 실측 814k자)라 주입하면 안 되는 것만 들어간다(ADR-030 ①).
     CONTEXT.md · AGENTS.md · apps/api/AGENTS.md · apps/web/AGENTS.md 4축으로 고정.
  ④ **커밋 1회/step + 산출물 비커밋** — 원본은 step 당 feat+chore 2커밋(우리 PR
     중앙값의 5배 노이즈)에 codex 트랜스크립트(step 당 0.5~1.2MB 실측)까지 커밋했다.
     산출물은 `phases/<dir>/runs/`(gitignore) 에만 남긴다.

사용:
    python3 tools/harness/execute.py <phase-dir> [--push]

phase 저작 규약(step 파일·index.json 형식)의 정본 = `.claude/commands/harness.md`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# 가드레일 4축 — 하나라도 없으면 시작하지 않는다 (무근거 주입 금지).
GUARDRAIL_FILES = ["CONTEXT.md", "AGENTS.md", "apps/api/AGENTS.md", "apps/web/AGENTS.md"]

# codex 실행 플래그. `--dangerously-bypass-approvals-and-sandbox` 는 무인 자동화 전용이고,
# `--dangerously-bypass-hook-trust` 는 `.codex/hooks.json`(위험명령 차단·Stop 경량 게이트)을
# trust 리뷰 없이 발화시킨다 — 훅을 끄는 것이 아니라 켜는 플래그다.
CODEX_CMD = [
    "codex",
    "exec",
    "--json",
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-bypass-hook-trust",
]

# 타임아웃(초). env 는 스모크 테스트 전용 오버라이드 — 운영 값을 낮출 이유가 없다.
CODEX_TIMEOUT = int(os.environ.get("QB_HARNESS_CODEX_TIMEOUT", "1800"))
AC_TIMEOUT = int(os.environ.get("QB_HARNESS_AC_TIMEOUT", "900"))


@contextlib.contextmanager
def progress_indicator(label: str):
    """터미널 진행 표시기. `.elapsed` 로 경과 시간을 읽는다."""
    frames = "◐◓◑◒"
    stop = threading.Event()
    t0 = time.monotonic()

    def _animate():
        idx = 0
        while not stop.wait(0.12):
            sec = int(time.monotonic() - t0)
            sys.stderr.write(f"\r{frames[idx % len(frames)]} {label} [{sec}s]")
            sys.stderr.flush()
            idx += 1
        sys.stderr.write("\r" + " " * (len(label) + 20) + "\r")
        sys.stderr.flush()

    th = threading.Thread(target=_animate, daemon=True)
    th.start()
    info = types.SimpleNamespace(elapsed=0.0)
    try:
        yield info
    finally:
        stop.set()
        th.join()
        info.elapsed = time.monotonic() - t0


class StepExecutor:
    """phase 디렉터리의 step 들을 순차 실행하는 러너. 판정 주체는 러너 자신이다."""

    MAX_RETRIES = 3
    TZ = timezone(timedelta(hours=9))

    def __init__(self, phase_dir_name: str, *, auto_push: bool = False):
        self._root = ROOT
        self._phases_dir = ROOT / "phases"
        self._phase_dir = self._phases_dir / phase_dir_name
        self._phase_dir_name = phase_dir_name
        self._top_index_file = self._phases_dir / "index.json"
        self._runs_dir = self._phase_dir / "runs"
        self._auto_push = auto_push

        if not self._phase_dir.is_dir():
            sys.exit(f"ERROR: {self._phase_dir} not found")
        self._index_file = self._phase_dir / "index.json"
        if not self._index_file.exists():
            sys.exit(f"ERROR: {self._index_file} not found")

        idx = self._read_json(self._index_file)
        self._project = idx.get("project", "QuantBridge")
        self._phase_name = idx.get("phase", phase_dir_name)
        self._steps = idx["steps"]
        self._total = len(self._steps)

        # ★AC 없는 step 은 시작 전에 거부한다 — AC 부재 = 판정 불가 = 자기채점으로의 회귀.
        missing_ac = [s["step"] for s in self._steps if not s.get("ac")]
        if missing_ac:
            sys.exit(f"ERROR: step {missing_ac} 에 ac 배열이 없다 — 러너는 AC 없이 판정하지 않는다")

    # ── I/O ──────────────────────────────────────────────────────────────

    @staticmethod
    def _read_json(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(p: Path, data: dict):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _stamp(self) -> str:
        return datetime.now(self.TZ).strftime("%Y-%m-%dT%H:%M:%S%z")

    # ── git ──────────────────────────────────────────────────────────────

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self._root, capture_output=True, text=True)

    def _checkout_branch(self):
        # `feat/` 접두 = pre-push ref 가드 화이트리스트. 원본의 `feat-<name>` 은 임의
        # branch 로 분류돼 push 가 막힌다.
        branch = f"feat/harness-{self._phase_name}"
        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if r.returncode != 0:
            sys.exit(f"ERROR: git 사용 불가 — {r.stderr.strip()}")
        if r.stdout.strip() == branch:
            return
        exists = self._run_git("rev-parse", "--verify", branch).returncode == 0
        r = self._run_git("checkout", branch) if exists else self._run_git("checkout", "-b", branch)
        if r.returncode != 0:
            sys.exit(f"ERROR: 브랜치 '{branch}' checkout 실패 — {r.stderr.strip()}\n"
                     f"  Hint: 변경사항을 commit 하거나 치운 뒤 다시 시도해라.")
        print(f"  Branch: {branch}")

    def _commit(self, message: str) -> bool:
        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode == 0:
            return False
        r = self._run_git("commit", "-m", message)
        if r.returncode != 0:
            print(f"  WARN: 커밋 실패 — {r.stderr.strip()[:300]}")
            return False
        print(f"  Commit: {message}")
        return True

    # ── 컨텍스트 ─────────────────────────────────────────────────────────

    def _load_guardrails(self) -> str:
        sections = []
        for rel in GUARDRAIL_FILES:
            p = ROOT / rel
            if not p.exists():
                sys.exit(f"ERROR: 가드레일 {rel} 이 없다 — 4축 없이는 시작하지 않는다")
            sections.append(f"## 프로젝트 규칙 ({rel})\n\n{p.read_text(encoding='utf-8')}")
        return "\n\n---\n\n".join(sections)

    def _step_context(self, index: dict) -> str:
        lines = [
            f"- Step {s['step']} ({s['name']}): {s['summary']}"
            for s in index["steps"]
            if s["status"] == "completed" and s.get("summary")
        ]
        return ("## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n") if lines else ""

    def _preamble(self, guardrails: str, step_context: str, prev_error: str | None) -> str:
        retry = (
            f"\n## ⚠ 이전 시도 실패 — 아래를 반드시 반영해 수정하라\n\n{prev_error}\n\n---\n\n"
            if prev_error else ""
        )
        return (
            f"당신은 {self._project} 프로젝트의 개발자입니다. 아래 step 을 수행하세요.\n\n"
            f"{guardrails}\n\n---\n\n{step_context}{retry}"
            f"## 작업 규칙\n\n"
            f"1. 이전 step 의 코드를 읽고 일관성을 유지하라.\n"
            f"2. 이 step 에 명시된 작업만 수행하라. 추가 기능·파일을 만들지 마라.\n"
            f"3. 기존 테스트를 깨뜨리지 마라.\n"
            f"4. step 의 AC 커맨드를 직접 실행해 green 을 확인하라 — 단 **최종 판정은 러너가\n"
            f"   AC 를 재실행해 내린다.** status 를 completed 로 바꾸지 마라(러너 소관이다).\n"
            f"5. phases/{self._phase_dir_name}/index.json 의 해당 step 에는 다음 두 가지만 써라:\n"
            f"   - \"summary\": 산출물 한 줄 요약 (다음 step 프롬프트에 전달된다)\n"
            f"   - 사용자 개입이 필요하면(API 키·인증·수동 설정) \"status\": \"blocked\" 와\n"
            f"     \"blocked_reason\" 을 쓰고 즉시 중단하라.\n"
            f"6. 커밋하지 마라 — 커밋은 러너가 AC 통과 후에 한다.\n\n---\n\n"
        )

    # ── 실행 ─────────────────────────────────────────────────────────────

    def _save_run(self, step_num: int, attempt: int, payload: dict):
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._runs_dir / f"step{step_num}-attempt{attempt}.json", payload)

    def _invoke_codex(self, step: dict, preamble: str, attempt: int) -> tuple[bool, str]:
        """codex 호출. (성공여부, 실패사유) — TimeoutExpired 를 잡는다(수리 ②)."""
        step_file = self._phase_dir / f"step{step['step']}.md"
        if not step_file.exists():
            sys.exit(f"ERROR: {step_file} not found")
        prompt = preamble + step_file.read_text(encoding="utf-8")
        try:
            r = subprocess.run(
                [*CODEX_CMD, prompt],
                cwd=self._root, capture_output=True, text=True, timeout=CODEX_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            self._save_run(step["step"], attempt, {"error": f"codex timeout {CODEX_TIMEOUT}s"})
            return False, f"codex 가 {CODEX_TIMEOUT}s 안에 끝나지 않았다 (TimeoutExpired)"
        except FileNotFoundError:
            sys.exit("ERROR: codex CLI 가 PATH 에 없다")
        self._save_run(step["step"], attempt, {
            "exitCode": r.returncode, "stdout": r.stdout, "stderr": r.stderr,
        })
        if r.returncode != 0:
            return False, f"codex 비정상 종료 rc={r.returncode}\n{r.stderr[:500]}"
        return True, ""

    def _run_ac(self, step: dict, attempt: int) -> tuple[bool, str]:
        """★판정의 전부 — AC 커맨드를 러너가 직접 돌려 exit code 로 가른다(수리 ①)."""
        for i, cmd in enumerate(step["ac"]):
            print(f"    AC {i + 1}/{len(step['ac'])}: {cmd}")
            try:
                r = subprocess.run(
                    ["bash", "-c", cmd],
                    cwd=self._root, capture_output=True, text=True, timeout=AC_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                return False, f"AC timeout {AC_TIMEOUT}s: {cmd}"
            if r.returncode != 0:
                tail = ((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()[-40:]
                self._save_run(step["step"], attempt, {
                    "acFailed": cmd, "rc": r.returncode, "tail": tail,
                })
                return False, f"AC 실패 (rc={r.returncode}): {cmd}\n" + "\n".join(tail)
        return True, ""

    def _update_step(self, step_num: int, **fields):
        index = self._read_json(self._index_file)
        for s in index["steps"]:
            if s["step"] == step_num:
                s.update(fields)
        self._write_json(self._index_file, index)

    def _update_top_index(self, status: str):
        if not self._top_index_file.exists():
            return
        top = self._read_json(self._top_index_file)
        for phase in top.get("phases", []):
            if phase.get("dir") == self._phase_dir_name:
                phase["status"] = status
                key = {"completed": "completed_at", "error": "failed_at", "blocked": "blocked_at"}.get(status)
                if key:
                    phase[key] = self._stamp()
        self._write_json(self._top_index_file, top)

    def _execute_step(self, step: dict, guardrails: str):
        step_num, step_name = step["step"], step["name"]
        prev_error = None
        self._update_step(step_num, started_at=self._stamp())

        for attempt in range(1, self.MAX_RETRIES + 1):
            index = self._read_json(self._index_file)
            preamble = self._preamble(guardrails, self._step_context(index), prev_error)
            tag = f"Step {step_num}/{self._total - 1}: {step_name}"
            if attempt > 1:
                tag += f" [retry {attempt}/{self.MAX_RETRIES}]"

            with progress_indicator(tag) as pi:
                ok, why = self._invoke_codex(step, preamble, attempt)
            elapsed = int(pi.elapsed)

            # codex 가 blocked 를 선언했으면 존중한다 — 사람 개입 요청은 세션의 정당한 출구다.
            cur = next(s for s in self._read_json(self._index_file)["steps"] if s["step"] == step_num)
            if cur.get("status") == "blocked":
                self._update_step(step_num, blocked_at=self._stamp())
                self._update_top_index("blocked")
                self._commit(f"chore({self._phase_name}): step {step_num} blocked")
                print(f"  ⏸ Step {step_num}: blocked [{elapsed}s]\n    Reason: {cur.get('blocked_reason', '?')}")
                sys.exit(2)

            if ok:
                ok, why = self._run_ac(cur, attempt)

            if ok:
                summary = cur.get("summary") or f"step {step_num} 완료 (AC {len(step['ac'])}종 통과)"
                self._update_step(step_num, status="completed", summary=summary,
                                  completed_at=self._stamp())
                self._commit(f"feat({self._phase_name}): step {step_num} — {step_name}")
                print(f"  ✓ Step {step_num}: {step_name} [{elapsed}s]")
                return

            prev_error = why
            if attempt < self.MAX_RETRIES:
                print(f"  ↻ Step {step_num}: retry {attempt}/{self.MAX_RETRIES} — {why.splitlines()[0]}")
            else:
                self._update_step(step_num, status="error", failed_at=self._stamp(),
                                  error_message=f"[{self.MAX_RETRIES}회 시도 후 실패] {why[:1000]}")
                self._update_top_index("error")
                # ★코드 변경은 커밋하지 않는다 — AC 미통과 코드가 「진행」으로 읽히면 안 된다.
                #   index.json 만 남겨 상태를 보존한다(작업 트리는 사람이 검시).
                self._run_git("add", "--", str(self._index_file.relative_to(self._root)),
                              str(self._top_index_file.relative_to(self._root)))
                self._run_git("commit", "-m", f"chore({self._phase_name}): step {step_num} error")
                print(f"  ✗ Step {step_num}: {self.MAX_RETRIES}회 실패 [{elapsed}s]\n    {why.splitlines()[0]}")
                print("    → 원인 해결 후 status 를 pending 으로 되돌리고 재실행해라. 작업 트리는 그대로 뒀다.")
                sys.exit(1)

    def run(self):
        print(f"\n{'=' * 60}\n  QuantBridge Harness Runner (v2 — 러너가 AC 를 판정한다)")
        print(f"  Phase: {self._phase_name} | Steps: {self._total}"
              + (" | auto-push" if self._auto_push else ""))
        print("=" * 60)

        for s in self._steps:
            if s["status"] in ("error", "blocked"):
                sys.exit(f"\n  ✗ Step {s['step']} 가 {s['status']} 상태다 — 해결 후 pending 으로 되돌려라.")

        guardrails = self._load_guardrails()
        self._checkout_branch()

        index = self._read_json(self._index_file)
        if "created_at" not in index:
            index["created_at"] = self._stamp()
            self._write_json(self._index_file, index)

        while True:
            index = self._read_json(self._index_file)
            pending = next((s for s in index["steps"] if s["status"] == "pending"), None)
            if pending is None:
                break
            self._execute_step(pending, guardrails)

        index = self._read_json(self._index_file)
        index["completed_at"] = self._stamp()
        self._write_json(self._index_file, index)
        self._update_top_index("completed")
        self._commit(f"chore({self._phase_name}): mark phase completed")

        if self._auto_push:
            branch = f"feat/harness-{self._phase_name}"
            r = self._run_git("push", "-u", "origin", branch)
            if r.returncode != 0:
                sys.exit(f"\n  ERROR: git push 실패 — {r.stderr.strip()[:300]}")
            print(f"  ✓ Pushed: origin/{branch}")

        print(f"\n{'=' * 60}\n  Phase '{self._phase_name}' completed!\n{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="QuantBridge Harness Step Runner (v2)")
    parser.add_argument("phase_dir", help="phases/ 아래 phase 디렉터리명")
    parser.add_argument("--push", action="store_true", help="완주 후 branch push")
    args = parser.parse_args()
    StepExecutor(args.phase_dir, auto_push=args.push).run()


if __name__ == "__main__":
    main()
