#!/usr/bin/env python3
# 밤샘 무인 오케스트레이터 — 러너(execute.py) N벌을 워크트리에서 큐로 돌리고,
# 완주한 lane 을 **stage 브랜치로** PR·머지한 뒤, 마지막에 stage→main PR 하나를 남긴다.
#
# 왜 러너 밖인가: `execute.py` 는 phase **하나**만 처리한다(설계). 병렬은 러너 안이 아니라
# 밖에서 만든다 — `.claude/commands/harness.md` §5.
#
# 사람이 판단하는 자리는 **하나뿐이다**: 마지막 stage→main PR. 그 앞은 무인이다.
#   lane PR 은 base 가 `stage/**` 라 CI 가 발화한다(`ci.yml` 의 `pull_request.branches`).
#   CI 가 green 인 것만 머지한다 — red·충돌은 그 lane 만 남기고 나머지를 계속 간다.
#
# ★기본은 dry-run 이다. 실제 집행은 `--confirm`.
#
# 사용:
#   python3 tools/harness/night_run.py --stage stage/night6 --jobs 4 [lane...]   # 계획만 출력
#   python3 tools/harness/night_run.py --stage stage/night6 --jobs 4 --confirm   # 집행
#   python3 tools/harness/night_run.py --status                                  # 진행 상황만

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PHASES = ROOT / "phases"
WT_BASE = ROOT / ".claude" / "worktrees"
KST = timezone(timedelta(hours=9))

# CI 폴링 — GitHub API 를 두드리는 간격과 한도.
CI_POLL_SEC = 60
CI_TIMEOUT_SEC = 45 * 60


def log(msg: str) -> None:
    print(f"[{datetime.now(KST):%H:%M:%S}] {msg}", flush=True)


def run(*args: str, cwd: Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args), cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout
    )


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return run("git", *args, cwd=cwd)


# ── 전제 검사 ────────────────────────────────────────────────────────────────


def pending_lanes() -> list[str]:
    idx = json.loads((PHASES / "index.json").read_text(encoding="utf-8"))
    return [p["dir"] for p in idx["phases"] if p["status"] == "pending"]


def preflight(lanes: list[str], stage: str) -> list[str]:
    """막을 수 있는 실패를 착수 전에 전부 낸다. 반환값은 문제 목록(비면 통과)."""
    problems: list[str] = []

    for tool in ("git", "gh", "codex", "python3"):
        if shutil.which(tool) is None:
            problems.append(f"`{tool}` 이 PATH 에 없다")

    if git("diff", "--quiet").returncode != 0 or git("diff", "--cached", "--quiet").returncode != 0:
        problems.append("메인 워킹트리가 dirty 하다 — 커밋하거나 치운 뒤 시작해라")

    r = git("rev-parse", "--abbrev-ref", "HEAD")
    if r.stdout.strip() != "main":
        problems.append(f"메인 체크아웃이 main 이 아니다(현재 {r.stdout.strip()})")

    if run("gh", "auth", "status").returncode != 0:
        problems.append("`gh` 인증이 없다 — `gh auth login`")

    if not lanes:
        problems.append("pending lane 이 없다")

    for lane in lanes:
        d = PHASES / lane
        if not (d / "index.json").is_file():
            problems.append(f"{lane}: index.json 이 없다")
            continue
        steps = json.loads((d / "index.json").read_text(encoding="utf-8"))["steps"]
        for s in steps:
            if not s.get("ac"):
                problems.append(f"{lane} step{s['step']}: ac 가 없다 — 러너가 시작을 거부한다")
            if s["status"] != "pending":
                problems.append(f"{lane} step{s['step']}: status 가 {s['status']} 다")
            if not (d / f"step{s['step']}.md").is_file():
                problems.append(f"{lane}: step{s['step']}.md 가 없다")

    if not stage.startswith("stage/"):
        problems.append(
            f"stage 브랜치 이름이 `stage/` 로 시작하지 않는다({stage}) — "
            "CI 가 base=stage/** 인 PR 에만 발화한다(ci.yml)"
        )
    return problems


# ── 워크트리 ─────────────────────────────────────────────────────────────────


def worktree_path(slot: int) -> Path:
    return WT_BASE / f"night6-w{slot}"


def ensure_worktree(slot: int, stage: str, *, confirm: bool) -> Path:
    wt = worktree_path(slot)
    if wt.exists():
        log(f"  · 워크트리 재사용: {wt.name}")
        return wt
    log(f"  · 워크트리 생성: {wt.name} (base={stage})")
    if not confirm:
        return wt
    r = git("worktree", "add", "--detach", str(wt), stage)
    if r.returncode != 0:
        sys.exit(f"✗ worktree add 실패: {r.stderr.strip()[:300]}")
    r = run(
        "bash",
        str(ROOT / "tools" / "scripts" / "worktree-bootstrap.sh"),
        "--slot",
        str(slot),
        "--adopt-env",
        cwd=wt,
        timeout=1800,
    )
    if r.returncode != 0:
        sys.exit(f"✗ worktree-bootstrap 실패({wt.name}): {(r.stdout + r.stderr)[-800:]}")
    return wt


def reset_worktree(wt: Path, stage: str, lane: str) -> None:
    """다음 lane 을 위해 워크트리를 stage 최신으로 되돌리고 lane 브랜치를 새로 판다."""
    branch = f"feat/harness-{lane}"
    git("fetch", "origin", stage, cwd=wt)
    git("checkout", "--detach", f"origin/{stage}", cwd=wt)
    git("branch", "-D", branch, cwd=wt)  # 남아 있으면 지운다(실패해도 무방)
    r = git("checkout", "-b", branch, cwd=wt)
    if r.returncode != 0:
        raise RuntimeError(f"{lane}: 브랜치 생성 실패 — {r.stderr.strip()[:200]}")


# ── lane 실행 ────────────────────────────────────────────────────────────────


class Result:
    def __init__(self, lane: str) -> None:
        self.lane = lane
        self.state = "pending"  # completed | error | blocked | crashed
        self.pr: str | None = None
        self.merged = False
        self.detail = ""


def run_lane(lane: str, wt: Path, stage: str, res: Result) -> None:
    reset_worktree(wt, stage, lane)
    log(f"▶ {lane} 시작 ({wt.name})")
    r = subprocess.run(
        ["python3", str(wt / "tools" / "harness" / "execute.py"), lane, "--push"],
        cwd=wt,
        capture_output=True,
        text=True,
        timeout=4 * 3600,
    )
    idx_path = wt / "phases" / lane / "index.json"
    try:
        steps = json.loads(idx_path.read_text(encoding="utf-8"))["steps"]
    except Exception as exc:  # noqa: BLE001 — 파일이 없거나 깨진 경우도 결과다
        res.state = "crashed"
        res.detail = f"index.json 을 못 읽는다: {exc}"
        return

    bad = [s for s in steps if s["status"] in ("error", "blocked")]
    if bad:
        s = bad[0]
        res.state = s["status"]
        res.detail = (s.get("error_message") or s.get("blocked_reason") or "")[:400]
    elif all(s["status"] == "completed" for s in steps):
        res.state = "completed"
    else:
        res.state = "crashed"
        res.detail = (r.stdout + r.stderr)[-400:]
    log(f"■ {lane} → {res.state}")


def open_pr(lane: str, stage: str, res: Result) -> None:
    branch = f"feat/harness-{lane}"
    body = (
        f"밤샘 루프 6차 lane `{lane}` — 하네스 러너 무인 실행 결과.\n\n"
        f"- base: `{stage}` (CI 는 base=stage/** 인 PR 에 발화한다)\n"
        f"- step 4단계 전부 `completed` · AC 는 러너가 재실행해 판정했다\n"
        f"- ★**AC 초록은 AC 가 옳다는 뜻이 아니다** — diff 는 사람이 읽는다\n\n"
        f"상세: `phases/{lane}/index.json` 의 step 별 `summary`\n"
    )
    r = run(
        "gh",
        "pr",
        "create",
        "--base",
        stage,
        "--head",
        branch,
        "--title",
        f"test({lane}): 밤샘 루프 6차 — {lane}",
        "--body",
        body,
    )
    if r.returncode != 0:
        res.detail += f" | PR 생성 실패: {r.stderr.strip()[:200]}"
        return
    res.pr = r.stdout.strip().splitlines()[-1]
    log(f"  ↑ PR: {res.pr}")


def wait_ci_and_merge(res: Result) -> None:
    if not res.pr:
        return
    deadline = time.time() + CI_TIMEOUT_SEC
    while time.time() < deadline:
        r = run("gh", "pr", "view", res.pr, "--json", "statusCheckRollup,mergeable,state")
        if r.returncode != 0:
            time.sleep(CI_POLL_SEC)
            continue
        data = json.loads(r.stdout)
        checks = data.get("statusCheckRollup") or []
        concl = [c.get("conclusion") for c in checks if c.get("conclusion") is not None]
        pending = [c for c in checks if c.get("status") not in ("COMPLETED",)]
        if checks and not pending:
            if all(c in ("SUCCESS", "NEUTRAL", "SKIPPED") for c in concl):
                m = run("gh", "pr", "merge", res.pr, "--squash", "--delete-branch")
                res.merged = m.returncode == 0
                if not res.merged:
                    res.detail += f" | 머지 실패: {m.stderr.strip()[:200]}"
                log(f"  {'✓ 머지' if res.merged else '✗ 머지 실패'}: {res.pr}")
            else:
                res.detail += f" | CI red: {concl}"
                log(f"  ✗ CI red — 머지하지 않는다: {res.pr}")
            return
        time.sleep(CI_POLL_SEC)
    res.detail += " | CI 대기 시간 초과"


# ── 메인 ────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(description="밤샘 무인 오케스트레이터 (기본 dry-run)")
    p.add_argument("lanes", nargs="*", help="생략하면 pending 전량")
    p.add_argument("--stage", default="stage/night6", help="lane PR 의 base 브랜치")
    p.add_argument("--jobs", type=int, default=4, help="동시 실행 상한 = 워크트리 수")
    p.add_argument("--confirm", action="store_true", help="실제로 집행한다")
    p.add_argument("--status", action="store_true", help="진행 상황만 출력하고 끝낸다")
    args = p.parse_args()

    if args.status:
        idx = json.loads((PHASES / "index.json").read_text(encoding="utf-8"))
        for ph in idx["phases"]:
            if ph["dir"].startswith(("fe6-", "be6-")):
                print(f"  {ph['status']:10} {ph['dir']}")
        return 0

    lanes = args.lanes or pending_lanes()
    problems = preflight(lanes, args.stage)

    print("=" * 72)
    print(f"  밤샘 루프 오케스트레이터 — lane {len(lanes)} · 동시 {args.jobs} · base {args.stage}")
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

    # 1) stage 브랜치
    if git("rev-parse", "--verify", args.stage).returncode != 0:
        log(f"stage 브랜치 생성: {args.stage}")
        git("branch", args.stage, "main")
    r = git("push", "-u", "origin", args.stage)
    if r.returncode != 0 and "up to date" not in (r.stderr + r.stdout):
        sys.exit(f"✗ stage push 실패: {r.stderr.strip()[:300]}")

    # 2) 워크트리 — jobs 개만 만들어 재사용한다(12벌은 디스크·테스트 DB 낭비다)
    wts = [ensure_worktree(i + 1, args.stage, confirm=True) for i in range(args.jobs)]

    # 3) 큐 실행
    results = {lane: Result(lane) for lane in lanes}
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
                run_lane(lane, wt, args.stage, res)
            except Exception as exc:  # noqa: BLE001 — 한 lane 의 사고가 밤을 끝내면 안 된다
                res.state = "crashed"
                res.detail = str(exc)[:400]
                log(f"■ {lane} → crashed: {exc}")
            if res.state == "completed":
                open_pr(lane, args.stage, res)
                wait_ci_and_merge(res)

    threads = [threading.Thread(target=worker, args=(wt,), daemon=False) for wt in wts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 4) 요약 + stage→main PR
    print("\n" + "=" * 72)
    done = [r for r in results.values() if r.state == "completed"]
    merged = [r for r in done if r.merged]
    for r in results.values():
        mark = "✓" if r.merged else ("·" if r.state == "completed" else "✗")
        print(f"  {mark} {r.lane:24} {r.state:10} {r.pr or '':40} {r.detail[:60]}")
    print(f"\n  완주 {len(done)}/{len(lanes)} · 머지 {len(merged)}")

    if merged:
        body = (
            "밤샘 루프 6차 통합 PR — lane PR 들이 이 브랜치로 머지된 결과다.\n\n"
            f"- 완주 {len(done)}/{len(lanes)} · 머지 {len(merged)}\n"
            + "\n".join(f"- `{r.lane}` — {r.pr}" for r in merged)
            + "\n\n★**여기서부터는 사람이 판단한다.** lane 별 diff 를 읽고 머지해라 —\n"
            "AC 초록은 AC 가 옳다는 뜻이 아니다.\n"
        )
        r = run(
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            args.stage,
            "--title",
            "test(night6): 밤샘 루프 6차 통합 — 커버리지 + 린트 부채",
            "--body",
            body,
        )
        print("\n  통합 PR:", r.stdout.strip().splitlines()[-1] if r.returncode == 0 else f"생성 실패 — {r.stderr.strip()[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
