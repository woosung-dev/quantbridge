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

    def _state_files(self) -> list:
        """하네스 상태 파일 — 코드가 아니라 진행 기록이다."""
        return [str(self._index_file.relative_to(self._root)),
                str(self._top_index_file.relative_to(self._root))]

    def _commit(self, message: str) -> bool:
        """코드와 하네스 상태를 **다른 커밋**으로 나눈다.

        원본(finsight `scripts/execute.py::_commit_step`)의 2단 커밋 이식분이다.
        한 커밋에 섞으면 step diff 가 「무엇을 고쳤나」를 잃는다 — 실측 `36e8732a`
        (`feat(...): step 5` 에 `index.json` 6줄이 동승). 산출물 자체(`runs/`)는
        `.gitignore` 가 이미 막으므로 여기서 뺄 것은 상태 파일 2개뿐이다.
        """
        state = self._state_files()
        self._run_git("add", "-A")
        for rel in state:
            self._run_git("reset", "HEAD", "--", rel)

        code_committed = False
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            r = self._run_git("commit", "-m", message)
            if r.returncode == 0:
                code_committed = True
                print(f"  Commit: {message}")
            else:
                print(f"  WARN: 커밋 실패 — {r.stderr.strip()[:300]}")

        # 상태 파일은 뒤따라 별도 커밋. 코드 커밋이 없었으면 원래 메시지를 그대로 써
        # 「무엇을 기록한 커밋인가」를 잃지 않는다(blocked·completed 표시가 그 경우다).
        self._run_git("add", "--", *state)
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = f"chore({self._phase_name}): harness state" if code_committed else message
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  Commit: {msg}")
                return True
            print(f"  WARN: 상태 커밋 실패 — {r.stderr.strip()[:300]}")
        return code_committed

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


# ═══════════════════════════════════════════════════════════════════════════
# 병렬 오케스트레이션 (`--parallel`)
#
# ★위의 `StepExecutor` 는 그대로 **phase 하나만** 처리한다 — 그 설계는 안 바뀐다.
#   아래는 그 러너를 **워크트리에서 여러 벌 띄우는 바깥 루프**이고, 위 코드를 건드리지 않는다.
# ★사람이 판단하는 자리는 **마지막 stage→main PR 하나**다. 그 앞은 무인이다:
#   lane 완주 → push → base=stage/** 로 PR(그래야 `ci.yml` 이 발화한다) → CI green → 머지.
#   CI red·충돌 난 lane 은 그 lane 만 남기고 나머지를 계속 간다.
# ★기본은 dry-run 이다. 실제 집행은 `--confirm`.
# ═══════════════════════════════════════════════════════════════════════════

PHASES_DIR = ROOT / "phases"
WT_BASE = ROOT / ".claude" / "worktrees"
CI_POLL_SEC = 60
CI_TIMEOUT_SEC = 45 * 60


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone(timedelta(hours=9))):%H:%M:%S}] {msg}", flush=True)


def _sh(*args, cwd: Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args), cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout
    )


def _git(*args, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return _sh("git", *args, cwd=cwd)


def _slug(stage: str) -> str:
    """`stage/night6` → `night6`. 워크트리 이름을 특정 회차에 묶지 않기 위한 파생."""
    return stage.split("/", 1)[-1].replace("/", "-")


def _pending_lanes() -> list:
    idx = json.loads((PHASES_DIR / "index.json").read_text(encoding="utf-8"))
    return [p["dir"] for p in idx["phases"] if p["status"] == "pending"]


def _preflight(lanes: list, stage: str) -> list:
    """막을 수 있는 실패를 착수 전에 전부 낸다. 반환값이 비면 통과."""
    problems = []
    for tool in ("git", "gh", "codex"):
        if not _sh("which", tool).stdout.strip():
            problems.append(f"`{tool}` 이 PATH 에 없다")
    if _git("diff", "--quiet").returncode != 0 or _git("diff", "--cached", "--quiet").returncode != 0:
        problems.append("메인 워킹트리가 dirty 하다 — 커밋하거나 치운 뒤 시작해라")
    head = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if head != "main":
        problems.append(f"메인 체크아웃이 main 이 아니다(현재 {head})")
    if _sh("gh", "auth", "status").returncode != 0:
        problems.append("`gh` 인증이 없다 — `gh auth login`")
    if not lanes:
        problems.append("pending lane 이 없다")
    if not stage.startswith("stage/"):
        problems.append(
            f"stage 브랜치 이름이 `stage/` 로 시작하지 않는다({stage}) — "
            "CI 는 base=stage/** 인 PR 에만 발화한다(ci.yml)"
        )
    for lane in lanes:
        d = PHASES_DIR / lane
        if not (d / "index.json").is_file():
            problems.append(f"{lane}: index.json 이 없다")
            continue
        for s in json.loads((d / "index.json").read_text(encoding="utf-8"))["steps"]:
            if not s.get("ac"):
                problems.append(f"{lane} step{s['step']}: ac 가 없다 — 러너가 시작을 거부한다")
            if s["status"] != "pending":
                problems.append(f"{lane} step{s['step']}: status 가 {s['status']} 다")
            if not (d / f"step{s['step']}.md").is_file():
                problems.append(f"{lane}: step{s['step']}.md 가 없다")
    return problems


def _ensure_worktree(slot: int, stage: str) -> Path:
    """워크트리는 `--parallel N` 만큼만 만들어 **재사용**한다 — lane 수만큼 만들면
    디스크(node_modules·.venv)와 슬롯 테스트 DB 를 그만큼 쓴다."""
    wt = WT_BASE / f"{_slug(stage)}-w{slot}"
    if wt.exists():
        _log(f"  · 워크트리 재사용: {wt.name}")
        return wt
    _log(f"  · 워크트리 생성: {wt.name} (base={stage})")
    r = _git("worktree", "add", "--detach", str(wt), stage)
    if r.returncode != 0:
        sys.exit(f"ERROR: worktree add 실패 — {r.stderr.strip()[:300]}")
    r = _sh("bash", str(ROOT / "tools" / "scripts" / "worktree-bootstrap.sh"),
            "--slot", str(slot), "--adopt-env", cwd=wt, timeout=1800)
    if r.returncode != 0:
        sys.exit(f"ERROR: worktree-bootstrap 실패({wt.name}) — {(r.stdout + r.stderr)[-800:]}")
    return wt


def _reset_worktree(wt: Path, stage: str, lane: str) -> None:
    """다음 lane 을 위해 워크트리를 stage 최신으로 되돌리고 lane 브랜치를 새로 판다."""
    branch = f"feat/harness-{lane}"
    _git("fetch", "origin", stage, cwd=wt)
    _git("checkout", "--detach", f"origin/{stage}", cwd=wt)
    _git("branch", "-D", branch, cwd=wt)  # 남아 있으면 지운다(없으면 실패해도 무방)
    r = _git("checkout", "-b", branch, cwd=wt)
    if r.returncode != 0:
        raise RuntimeError(f"{lane}: 브랜치 생성 실패 — {r.stderr.strip()[:200]}")


class LaneResult:
    def __init__(self, lane: str):
        self.lane = lane
        self.state = "pending"  # completed | error | blocked | crashed
        self.pr = None
        self.merged = False
        self.detail = ""


def _run_lane(lane: str, wt: Path, stage: str, res: LaneResult) -> None:
    _reset_worktree(wt, stage, lane)
    _log(f"▶ {lane} 시작 ({wt.name})")
    r = subprocess.run([sys.executable, str(wt / "tools" / "harness" / "execute.py"), lane, "--push"],
                       cwd=wt, capture_output=True, text=True, timeout=4 * 3600)
    try:
        steps = json.loads((wt / "phases" / lane / "index.json").read_text(encoding="utf-8"))["steps"]
    except Exception as exc:  # noqa: BLE001 — 파일이 없거나 깨진 것도 결과다
        res.state, res.detail = "crashed", f"index.json 을 못 읽는다: {exc}"
        return
    bad = [s for s in steps if s["status"] in ("error", "blocked")]
    if bad:
        res.state = bad[0]["status"]
        res.detail = (bad[0].get("error_message") or bad[0].get("blocked_reason") or "")[:400]
    elif all(s["status"] == "completed" for s in steps):
        res.state = "completed"
    else:
        res.state, res.detail = "crashed", (r.stdout + r.stderr)[-400:]

    # ★2026-08-22 사고 — lane 이 step 4/4 completed 를 선언했는데 브랜치가 base 와 같은 SHA 였다.
    #   워크트리에서 pre-commit 이 죽어(`pnpm exec lint-staged` rc=254 — 루트 node_modules 부재)
    #   `_commit` 의 WARN 이 버려지는 stdout 에만 찍혔고, 빈 브랜치가 push 돼 `gh pr create` 가
    #   "no commits between" 으로 실패했다. 그 실패도 `res.detail` 에만 적혀 로그는 침묵했다.
    #   ⇒ 「완주」의 정의에 **커밋이 존재한다**를 넣는다. 판정은 러너가, 로그는 사람이 읽는다.
    if res.state == "completed":
        ahead = _git("rev-list", "--count", f"origin/{stage}..HEAD", cwd=wt)
        if ahead.returncode != 0 or ahead.stdout.strip() == "0":
            res.state = "crashed"
            res.detail = (f"step 은 전부 completed 인데 origin/{stage} 대비 커밋이 0건이다 — "
                          f"커밋이 막혔다(pre-commit 훅 · 작업 트리 = {wt.name})")
    _log(f"■ {lane} → {res.state}")


def _open_pr(lane: str, stage: str, res: LaneResult) -> None:
    body = (f"하네스 lane `{lane}` — 러너 무인 실행 결과.\n\n"
            f"- base: `{stage}` (CI 는 base=stage/** 인 PR 에 발화한다)\n"
            f"- step 전부 `completed` · AC 는 러너가 재실행해 판정했다\n"
            f"- ★**AC 초록은 AC 가 옳다는 뜻이 아니다** — diff 는 사람이 읽는다\n\n"
            f"상세 = `phases/{lane}/index.json` 의 step 별 `summary`\n")
    r = _sh("gh", "pr", "create", "--base", stage, "--head", f"feat/harness-{lane}",
            "--title", f"test({lane}): 하네스 무인 실행 — {lane}", "--body", body)
    if r.returncode != 0:
        res.detail += f" | PR 생성 실패: {r.stderr.strip()[:200]}"
        _log(f"  ✗ PR 생성 실패: {lane} — {r.stderr.strip()[:200]}")
        return
    res.pr = r.stdout.strip().splitlines()[-1]
    _log(f"  ↑ PR: {res.pr}")


def _wait_ci_and_merge(res: LaneResult) -> None:
    if not res.pr:
        return
    deadline = time.time() + CI_TIMEOUT_SEC
    while time.time() < deadline:
        r = _sh("gh", "pr", "view", res.pr, "--json", "statusCheckRollup,mergeable,state")
        if r.returncode != 0:
            time.sleep(CI_POLL_SEC)
            continue
        checks = json.loads(r.stdout).get("statusCheckRollup") or []
        if checks and all(c.get("status") == "COMPLETED" for c in checks):
            concl = [c.get("conclusion") for c in checks]
            if all(c in ("SUCCESS", "NEUTRAL", "SKIPPED") for c in concl):
                m = _sh("gh", "pr", "merge", res.pr, "--squash", "--delete-branch")
                res.merged = m.returncode == 0
                if not res.merged:
                    res.detail += f" | 머지 실패: {m.stderr.strip()[:200]}"
                _log(f"  {'✓ 머지' if res.merged else '✗ 머지 실패'}: {res.pr}")
            else:
                res.detail += f" | CI red: {concl}"
                _log(f"  ✗ CI red — 머지하지 않는다: {res.pr}")
            return
        time.sleep(CI_POLL_SEC)
    res.detail += " | CI 대기 시간 초과"


def run_parallel(args) -> int:
    lanes = args.lanes if args.lanes else _pending_lanes()
    problems = _preflight(lanes, args.stage)

    print("=" * 72)
    print(f"  하네스 병렬 오케스트레이션 — lane {len(lanes)} · 동시 {args.parallel} · base {args.stage}")
    print(f"  모드: {'집행(--confirm)' if args.confirm else 'DRY-RUN — 아무것도 바꾸지 않는다'}")
    print("=" * 72)
    for i, lane in enumerate(lanes):
        print(f"  {i + 1:2}. {lane}")
    if problems:
        print("\n✗ 전제 위반 — 고치기 전에는 시작하지 않는다:")
        for why in problems:
            print(f"  - {why}")
        return 1
    print("\n✓ 전제 통과")
    if not args.confirm:
        print("\n집행하려면 --confirm 을 붙여라.")
        return 0

    if _git("rev-parse", "--verify", args.stage).returncode != 0:
        _log(f"stage 브랜치 생성: {args.stage}")
        _git("branch", args.stage, "main")
    # ★이미 원격과 같으면 push 하지 않는다 — 2026-08-22 실측: 올릴 ref 가 없는 push 는
    #   pre-push 훅에 **stdin 을 주지 않고**, 훅은 그때 「현재 브랜치」로 폴백한다. 메인
    #   체크아웃은 `main` 이므로(전제 검사가 그렇게 요구한다) 가드가 정당하게 거부한다.
    #   즉 재시작 때마다 시작 자체가 막힌다. 비교로 push 를 건너뛰면 그 경로에 안 들어간다.
    local = _git("rev-parse", args.stage).stdout.strip()
    remote = _git("rev-parse", f"origin/{args.stage}").stdout.strip()
    if local != remote:
        r = _git("push", "-u", "origin", args.stage)
        if r.returncode != 0 and "up to date" not in (r.stderr + r.stdout):
            sys.exit(f"ERROR: stage push 실패 — {r.stderr.strip()[:300]}")

    wts = [_ensure_worktree(i + 1, args.stage) for i in range(args.parallel)]
    results = {lane: LaneResult(lane) for lane in lanes}
    queue = list(lanes)
    qlock = threading.Lock()

    def worker(wt: Path) -> None:
        while True:
            with qlock:
                if not queue:
                    return
                lane = queue.pop(0)
            res = results[lane]
            try:
                _run_lane(lane, wt, args.stage, res)
            except Exception as exc:  # noqa: BLE001 — 한 lane 의 사고가 밤을 끝내면 안 된다
                res.state, res.detail = "crashed", str(exc)[:400]
                _log(f"■ {lane} → crashed: {exc}")
            if res.state == "completed":
                _open_pr(lane, args.stage, res)
                _wait_ci_and_merge(res)

    threads = [threading.Thread(target=worker, args=(wt,)) for wt in wts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("\n" + "=" * 72)
    done = [r for r in results.values() if r.state == "completed"]
    merged = [r for r in done if r.merged]
    for r in results.values():
        mark = "✓" if r.merged else ("·" if r.state == "completed" else "✗")
        print(f"  {mark} {r.lane:24} {r.state:10} {r.pr or '':40} {r.detail[:60]}")
    print(f"\n  완주 {len(done)}/{len(lanes)} · 머지 {len(merged)}")

    if merged:
        body = (f"`{args.stage}` 통합 PR — lane PR 들이 이 브랜치로 머지된 결과다.\n\n"
                f"- 완주 {len(done)}/{len(lanes)} · 머지 {len(merged)}\n"
                + "\n".join(f"- `{r.lane}` — {r.pr}" for r in merged)
                + "\n\n★**여기서부터는 사람이 판단한다.** lane 별 diff 를 읽고 머지해라 —\n"
                  "AC 초록은 AC 가 옳다는 뜻이 아니다.\n")
        r = _sh("gh", "pr", "create", "--base", "main", "--head", args.stage,
                "--title", f"test({_slug(args.stage)}): 하네스 통합 — lane {len(merged)}건", "--body", body)
        print("\n  통합 PR:", r.stdout.strip().splitlines()[-1] if r.returncode == 0
              else f"생성 실패 — {r.stderr.strip()[:200]}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="QuantBridge Harness Step Runner (v2)")
    parser.add_argument("phase_dir", nargs="?", help="phases/ 아래 phase 디렉터리명")
    parser.add_argument("--push", action="store_true", help="완주 후 branch push")
    # ── 병렬 오케스트레이션 — 러너를 워크트리에서 N벌 띄우는 바깥 루프 ──────
    parser.add_argument("--parallel", type=int, metavar="N",
                        help="lane 을 워크트리 N벌에서 큐로 돌린다 (기본 dry-run)")
    parser.add_argument("--stage", help="lane PR 의 base 브랜치 (`stage/...`) — --parallel 에 필수")
    parser.add_argument("--lanes", nargs="*", default=None, help="생략하면 pending 전량")
    parser.add_argument("--confirm", action="store_true", help="--parallel 을 실제로 집행한다")
    parser.add_argument("--status", action="store_true", help="phase 진행 상황만 출력한다")
    args = parser.parse_args()

    if args.status:
        idx = json.loads((PHASES_DIR / "index.json").read_text(encoding="utf-8"))
        for ph in idx["phases"]:
            if ph["status"] != "completed":
                print(f"  {ph['status']:10} {ph['dir']}")
        return 0

    if args.parallel:
        if args.phase_dir:
            parser.error("--parallel 과 phase_dir 은 함께 쓸 수 없다 (lane 은 --lanes 로 준다)")
        if not args.stage:
            parser.error("--parallel 에는 --stage 가 필요하다 (예: --stage stage/night6)")
        return run_parallel(args)

    if not args.phase_dir:
        parser.error("phase_dir 이 필요하다 (또는 --parallel / --status)")
    StepExecutor(args.phase_dir, auto_push=args.push).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
