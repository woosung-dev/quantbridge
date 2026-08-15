#!/usr/bin/env python3
"""QuantBridge harness 어댑터 — 상류 러너를 **한 줄도 안 고치고** 우리 차이를 여기서만 덮는다.

상류: https://github.com/jha0313/harness_framework @ da676bc6
      `tools/vendor/harness/execute.py` (pristine · sha256 은 harness-test.sh 가 고정)

★왜 어댑터인가 — 상류는 **clone 해서 시작하는 스타터 템플릿**이지 라이브러리가 아니다.
  그래서 우리 레이아웃·역할 계약과 어긋나는 자리가 9곳 나온다([ADR-033] §꼬임).
  인라인 포크는 그 9곳을 상류 소스에 박아 「누구 것인가」를 지워 버린다. 어댑터는 상류를
  pristine 으로 두고 **차이 전량을 이 파일 하나에** 모은다.

★상류 설계는 4층인데 우리는 ①만 가져왔었다 —
  ① 엔진(execute.py) ② 저작 규약(.claude/commands/harness.md) ③ 검증 강제(.claude/settings.json
  Stop 훅 = lint+build+test) ④ 리뷰(commands/review.md).
  ③은 codex 가 `.claude/settings.json` 을 **안 읽어** 실행기 교체와 함께 사라졌다.
  이 파일의 `STEP_CHECKS` 가 그 층의 대체물이다(D4).

Usage:
    python3 tools/scripts/qb_harness.py <task-name>      # phases 는 .harness/phases/ 아래
    ★--push 는 없다 — Golden Rule(사용자 승인 없는 push 금지)이라 어댑터가 아예 안 받는다.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# ── 설정 — 상류와 다른 것은 전부 여기서 시작한다 ────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent  # tools/scripts/ → 레포 루트
VENDOR = ROOT / "tools" / "vendor" / "harness" / "execute.py"
PHASES_DIR = ROOT / ".harness" / "phases"
GUARDRAIL_DIR = ROOT / ".harness" / "docs"  # 4축 심링크

EXECUTOR = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"]
TIMEOUT_SEC = 1800

# ★D4 — 저자의 Stop 훅(`npm run lint && build && test`) 직역.
#   싸고 결정적인 것만. step 종료 후 세션이 "completed" 라고 했을 때만 돈다.
#   실패하면 index.json 을 error 로 뒤집어 **상류의 재시도 로직이 그대로 받는다**.
#   ★이것이 세션 자기신고를 러너가 처음으로 뒤집을 수 있게 하는 지점이다.
STEP_CHECKS = [
    ("FE typecheck", ["pnpm", "exec", "tsc", "--noEmit"], ROOT / "apps" / "web"),
    ("BE ruff", [str(ROOT / "apps" / "api" / ".venv" / "bin" / "ruff"), "check", "."], ROOT / "apps" / "api"),
]

# ── 상류를 pristine 으로 로드 ───────────────────────────────────────────────
if not VENDOR.is_file():
    print(f"ERROR: 상류 pristine 이 없다 — {VENDOR}")
    sys.exit(1)
_spec = importlib.util.spec_from_file_location("harness_upstream", VENDOR)
if _spec is None or _spec.loader is None:
    print(f"ERROR: {VENDOR} 를 로드할 수 없다")
    sys.exit(1)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)
# 상류가 ROOT 를 **모듈 상수**로 4곳에서 직접 참조하므로 인스턴스화 전에 갈아 끼운다.
# (상류는 `scripts/` 가 루트 직하라 parent.parent 가 맞지만 우리는 [ADR-029] 로 한 단 깊다 — 꼬임 1)
setattr(ex, "ROOT", ROOT)


class QBExecutor(ex.StepExecutor):  # type: ignore[misc,name-defined]
    """우리 차이 전량. 상류 `StepExecutor` 의 어느 메서드를 왜 덮는지가 곧 [ADR-033] §꼬임 표다."""

    def __init__(self, phase_dir_name: str):
        # 상류 __init__ 은 ROOT/"phases" 를 박아 두므로 전량 대체한다 (꼬임 3).
        self._root = str(ROOT)
        self._phases_dir = PHASES_DIR
        self._phase_dir = PHASES_DIR / phase_dir_name
        self._phase_dir_name = phase_dir_name
        self._top_index_file = PHASES_DIR / "index.json"
        self._auto_push = False  # ★영구 False — Golden Rule

        if not self._phase_dir.is_dir():
            print(f"ERROR: {self._phase_dir} not found")
            sys.exit(1)
        self._index_file = self._phase_dir / "index.json"
        if not self._index_file.exists():
            print(f"ERROR: {self._index_file} not found")
            sys.exit(1)

        idx = self._read_json(self._index_file)
        self._project = idx.get("project", "QuantBridge")
        self._phase_name = idx.get("phase", phase_dir_name)
        self._total = len(idx["steps"])

    # ── 꼬임 4 — 워크트리가 이미 브랜치를 가진다 ──────────────────────────
    def _checkout_branch(self):
        """상류는 `feat-{task}` 를 만들어 전환한다. 우리는 워크트리 브랜치를 그대로 쓴다.

        2026-08-15 스모크에서 상류 동작이 실제로 `feat-smoke` 로 이탈했다.
        """
        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if r.returncode != 0:
            print("  ERROR: git repo 가 아니다.")
            sys.exit(1)
        print(f"  Branch: {r.stdout.strip()} (어댑터 — 전환하지 않는다)")

    # ── 꼬임 2 — docs/ 최상위는 살아 있는 원장이다 ────────────────────────
    def _load_guardrails(self) -> str:
        """상류는 `CLAUDE.md` + `docs/*.md` 전량을 넣는다.

        우리 `docs/` 최상위는 README·status·backlog·roadmap·lessons **5파일 777,895자**이고
        정본인 `docs/reference/`·`docs/decisions/` 는 하위라 **0건** 잡힌다. 크기가 아니라
        **선택**의 문제다 ([ADR-030] §발견①). 4축 심링크 = 45,750자 (−94.1%).
        """
        sections = []
        for doc in sorted(GUARDRAIL_DIR.glob("*.md")):
            sections.append(f"## {doc.stem}\n\n{doc.read_text()}")
        if not sections:
            # ★빈 입력을 조용히 통과시키지 않는다 (LESSON-101 / §8.6).
            print(f"  ERROR: 가드레일 4축이 비었다 — {GUARDRAIL_DIR}")
            sys.exit(1)
        return "\n\n---\n\n".join(sections)

    # ── 꼬임 3 파생 — 프리앰블이 세션에게 알려 주는 원장 경로 ──────────────
    def _build_preamble(self, guardrails: str, step_context: str, prev_error=None) -> str:
        """상류는 `/phases/…` 를 박는다. 선행 슬래시라 절대 경로로도 읽힌다.

        2026-08-15 codex 적대 리뷰 F1(P1). 스모크가 통과한 것은 step 파일이 올바른 경로를
        따로 적어 **우연히 가렸기** 때문이다.
        """
        out = super()._build_preamble(guardrails, step_context, prev_error)
        return out.replace(
            f"/phases/{self._phase_dir_name}/index.json",
            f".harness/phases/{self._phase_dir_name}/index.json",
        )

    # ── 꼬임 3 파생 — 2단 커밋의 reset 경로 ───────────────────────────────
    def _commit_step(self, step_num: int, step_name: str):
        """상류 동작(세션 feat + 러너 chore)을 그대로 두되 경로만 우리 것으로.

        ★상류의 러너 feat 은 **세션이 커밋 안 했을 때의 폴백**이다(모순이 아니다).
        step 당 커밋은 무인 실행의 **롤백 지점**이라 없애지 않는다.
        """
        output_rel = f".harness/phases/{self._phase_dir_name}/step{step_num}-output.json"
        index_rel = f".harness/phases/{self._phase_dir_name}/index.json"

        self._run_git("add", "-A")
        self._run_git("reset", "HEAD", "--", output_rel)
        self._run_git("reset", "HEAD", "--", index_rel)

        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.FEAT_MSG.format(phase=self._phase_name, num=step_num, name=step_name)
            r = self._run_git("commit", "-m", msg)
            print(f"  Commit: {msg}" if r.returncode == 0 else f"  WARN: 코드 커밋 실패: {r.stderr.strip()}")

        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.CHORE_MSG.format(phase=self._phase_name, num=step_num)
            r = self._run_git("commit", "-m", msg)
            if r.returncode != 0:
                print(f"  WARN: housekeeping 커밋 실패: {r.stderr.strip()}")

    # ── 상태 원장에 실패를 써 넣는다 (상류 재시도 로직이 이걸 읽는다) ──────
    def _fail_step(self, step_num: int, message: str):
        index = self._read_json(self._index_file)
        for s in index["steps"]:
            if s["step"] == step_num:
                s["status"] = "error"
                s["error_message"] = message
        self._write_json(self._index_file, index)

    def _step_status(self, step_num: int) -> str:
        index = self._read_json(self._index_file)
        return next((s.get("status", "pending") for s in index["steps"] if s["step"] == step_num), "pending")

    # ── 꼬임 1·5·8 + D4·D5 가 전부 여기 모인다 ────────────────────────────
    def _invoke_claude(self, step: dict, preamble: str) -> dict:
        step_num, step_name = step["step"], step["name"]
        step_file = self._phase_dir / f"step{step_num}.md"
        if not step_file.exists():
            print(f"  ERROR: {step_file} not found")
            sys.exit(1)

        prompt = preamble + step_file.read_text()
        timed_out = False
        try:
            # ★① 실행기 codex. `-p` 를 옮기면 안 된다 — codex 에서 `-p` 는 `--profile` 이다.
            # ★stdin=DEVNULL 필수 — 열려 있으면 codex 가 무한 대기한다
            #   (generator-evaluator-pipeline.md §7.1, 워커 2기 52분·38분 소실).
            result = subprocess.run(
                [*EXECUTOR, "-C", self._root, prompt],
                cwd=self._root, capture_output=True, text=True,
                timeout=TIMEOUT_SEC, stdin=subprocess.DEVNULL,
            )
            rc, out, err = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            # ★D5 — 상류는 이걸 안 잡아 phase 전체가 traceback 으로 죽고, 그 step 의
            #   자기신고가 **검증되지 않은 채 커밋된 상태로 남는다**([ADR-030] 위험 7 —
            #   파일럿 B회차를 죽인 그것). 최악 갈래는 재실행이다: `completed` 가 파일에
            #   남아 다음 run 이 그 step 을 **건너뛴다**. 여기서 잡아 error 로 내린다.
            timed_out = True
            rc, out, err = -1, (e.stdout or b"").decode(errors="replace"), f"TimeoutExpired after {TIMEOUT_SEC}s"
            self._fail_step(step_num, f"[어댑터] 실행기가 {TIMEOUT_SEC}s 상한을 넘겨 중단됐다 — 자기신고는 신뢰하지 마라")
            print(f"\n  ✗ 실행기 타임아웃 {TIMEOUT_SEC}s — index.json 을 error 로 내렸다")

        if rc != 0 and not timed_out:
            print(f"\n  WARN: 실행기 비정상 종료 (code {rc})")
            if err:
                print(f"  stderr: {err[:500]}")

        checks = []
        if not timed_out and self._step_status(step_num) == "completed":
            checks = self._run_step_checks(step_num)

        output = {
            "step": step_num, "name": step_name, "exitCode": rc,
            "timedOut": timed_out, "checks": checks,
            "stdout": out, "stderr": err,
        }
        (self._phase_dir / f"step{step_num}-output.json").write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return output

    def _run_step_checks(self, step_num: int) -> list:
        """★D4 — 저자의 ③층(Stop 훅) 대체. 세션이 completed 라고 했을 때만 돈다.

        실패하면 index.json 을 error 로 뒤집는다 ⇒ 상류 재시도 로직이 에러 원문을 다음
        프롬프트에 넣어 다시 돌린다. **자기신고를 러너가 뒤집을 수 있는 유일한 지점이다.**
        """
        results, failed = [], []
        for label, cmd, cwd in STEP_CHECKS:
            if not Path(cwd).is_dir():
                results.append({"check": label, "skipped": "cwd 없음"})
                continue
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                               timeout=600, stdin=subprocess.DEVNULL)
            results.append({"check": label, "rc": r.returncode})
            mark = "✓" if r.returncode == 0 else "✗"
            print(f"    {mark} {label}")
            if r.returncode != 0:
                failed.append(f"{label}: rc={r.returncode}\n{(r.stdout + r.stderr)[-1500:]}")

        if failed:
            self._fail_step(step_num, "[어댑터 고정 검사 실패] " + "\n---\n".join(failed))
            print("    ★세션은 completed 라 했지만 고정 검사가 뒤집었다 — error 로 내렸다")
        return results


def main():
    p = argparse.ArgumentParser(description="QuantBridge harness 어댑터")
    p.add_argument("phase_dir", help="task 디렉터리명 (.harness/phases/ 아래)")
    QBExecutor(p.parse_args().phase_dir).run()


if __name__ == "__main__":
    main()
