"""어댑터 AC — **우리가 덮은 것만** 잰다.

상류 헬퍼 51건은 `tools/vendor/harness/test_execute.py` 가 pristine 그대로 덮는다(= 벤더 무결성).
여기 있는 것은 [ADR-033] §꼬임 표의 각 행이 실제로 막혔는지다.

★이 파일이 없으면 어댑터를 통째로 no-op 으로 바꿔도 상류 51건은 초록이다
  ([ADR-030] §발견⑤ — 「51 passed 가 실행기를 검증하지 않는다」).
"""

import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_SPEC = importlib.util.spec_from_file_location("qb", Path(__file__).parent / "qb_harness.py")
assert _SPEC and _SPEC.loader
qb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qb)


@pytest.fixture
def phase(tmp_path, monkeypatch):
    """tmp 트리에 phase 하나. ROOT·경로 상수를 전부 tmp 로 돌린다."""
    root = tmp_path
    (root / ".harness" / "docs").mkdir(parents=True)
    (root / ".harness" / "docs" / "01-domain.md").write_text("핵심 도메인 6종\n본문")
    (root / ".harness" / "docs" / "02-structure.md").write_text("Golden Rules (Immutable)\n본문")
    d = root / ".harness" / "phases" / "t"
    d.mkdir(parents=True)
    (d / "index.json").write_text(json.dumps({
        "project": "QB", "phase": "t",
        "steps": [{"step": 0, "name": "s0", "status": "pending"}],
    }, ensure_ascii=False))
    (d / "step0.md").write_text("# Step 0\n작업 내용")

    monkeypatch.setattr(qb, "ROOT", root)
    monkeypatch.setattr(qb, "PHASES_DIR", root / ".harness" / "phases")
    monkeypatch.setattr(qb, "GUARDRAIL_DIR", root / ".harness" / "docs")
    monkeypatch.setattr(qb.ex, "ROOT", root)
    return root


@pytest.fixture
def inst(phase):
    return qb.QBExecutor("t")


# ── 꼬임 1 — ROOT 깊이 ─────────────────────────────────────────────────────
class TestRootDepth:
    def test_module_root_is_repo_root_not_tools(self):
        """상류는 `scripts/` 루트 직하라 parent.parent. 우리는 `tools/scripts/` 라 한 단 깊다.

        틀리면 _load_guardrails() 가 **예외 없이 0자**를 낸다 — 음성 대조만으로는 못 잡는다.
        """
        assert qb.ROOT.name != "tools"
        assert (qb.ROOT / "AGENTS.md").is_file()
        assert (qb.ROOT / "apps").is_dir()

    def test_vendor_pristine_is_reachable(self):
        assert qb.VENDOR.is_file(), "상류 pristine 이 없으면 어댑터가 로드조차 안 된다"


# ── 꼬임 2 — 가드레일 축 ───────────────────────────────────────────────────
class TestGuardrails:
    def test_uses_harness_docs_not_repo_docs(self, inst):
        g = inst._load_guardrails()
        assert "핵심 도메인 6종" in g and "Golden Rules (Immutable)" in g

    def test_empty_guardrail_aborts_not_greenlights(self, phase, inst, monkeypatch):
        """★빈 입력을 조용히 통과시키면 안 된다 (LESSON-101 / §8.6).

        상류는 sections 가 비면 `""` 를 조용히 반환한다. 우리는 죽는다.
        """
        empty = phase / ".harness" / "empty"
        empty.mkdir()
        monkeypatch.setattr(qb, "GUARDRAIL_DIR", empty)
        with pytest.raises(SystemExit):
            inst._load_guardrails()

    def test_real_repo_guardrail_is_four_axes(self):
        """실제 레포에서 4축이 전부 실리는가 — 양성 대조.

        음성 대조(원장 4파일이 안 들어왔나)만 두면 **주입 0자가 4/4 통과**한다. 실제로 그랬다.
        """
        real = qb.QBExecutor.__new__(qb.QBExecutor)
        g = qb.QBExecutor._load_guardrails(real)
        assert len(g) > 40_000, f"{len(g)}자 — 4축이 안 실렸다"
        for axis in ("핵심 도메인 6종", "Golden Rules (Immutable)", "FastAPI 3-Layer", "React Hooks"):
            assert axis in g
        assert len(g) < 100_000, f"{len(g)}자 — docs/ 최상위(777,895자)가 새 들어왔다"


# ── 꼬임 3 — 원장 경로 파생 ────────────────────────────────────────────────
class TestLedgerPaths:
    def test_preamble_points_at_harness_phases(self, inst):
        """codex 적대 리뷰 F1(P1). 상류 단언은 부분문자열이라 옛·새 경로가 양쪽 다 통과했다."""
        pre = inst._build_preamble("G", "")
        assert ".harness/phases/t/index.json" in pre
        assert "/phases/t/index.json" not in pre.replace(".harness/phases/t/index.json", "")

    def test_commit_reset_paths_match_phases_dir(self, inst):
        calls = []

        def fake_git(*args):
            calls.append(args)
            return MagicMock(returncode=1 if args[:2] == ("diff", "--cached") else 0, stdout="", stderr="")

        inst._run_git = fake_git
        inst._commit_step(0, "s0")
        resets = [c[3] for c in calls if c[0] == "reset"]
        assert resets == [".harness/phases/t/step0-output.json", ".harness/phases/t/index.json"]
        assert not any(p.startswith("phases/") for p in resets)


# ── 꼬임 4 — 브랜치 ───────────────────────────────────────────────────────
class TestBranchPolicy:
    def test_does_not_switch_branch(self, inst):
        """상류는 `feat-{task}` 로 전환한다. 스모크에서 실제로 `feat-smoke` 로 이탈했다."""
        calls = []

        def fake_git(*args):
            calls.append(args)
            return MagicMock(returncode=0, stdout="worktree-x\n", stderr="")

        inst._run_git = fake_git
        inst._checkout_branch()
        assert not any(c[0] == "checkout" for c in calls), "어댑터는 브랜치를 전환하면 안 된다"


# ── ① 실행기 ──────────────────────────────────────────────────────────────
class TestExecutor:
    def test_invokes_codex_not_claude(self, inst):
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as m:
            inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        cmd = m.call_args[0][0]
        assert cmd[:3] == ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox"]
        assert cmd[cmd.index("-C") + 1] == inst._root
        assert m.call_args.kwargs["stdin"] is subprocess.DEVNULL
        # ★음성 대조 — 없으면 argv 를 상류로 되돌려도 초록이 난다
        assert "claude" not in cmd
        assert "-p" not in cmd, "codex 에서 -p 는 --profile 이다"

    def test_push_is_permanently_off(self, inst):
        assert inst._auto_push is False


# ── D5 — TimeoutExpired ───────────────────────────────────────────────────
class TestTimeout:
    def test_timeout_downgrades_step_to_error(self, inst):
        """★상류는 이걸 안 잡아 phase 가 traceback 으로 죽고 자기신고가 검증 없이 남는다.

        최악 갈래는 재실행 — `completed` 가 파일에 남아 다음 run 이 그 step 을 건너뛴다.
        """
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="codex", timeout=1800)):
            out = inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        assert out["timedOut"] is True
        assert inst._step_status(0) == "error"
        assert "상한을 넘겨" in json.loads(inst._index_file.read_text())["steps"][0]["error_message"]

    def test_timeout_skips_step_checks(self, inst):
        """타임아웃이면 고정 검사를 돌리지 않는다 — 이미 error 다."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="codex", timeout=1800)):
            out = inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        assert out["checks"] == []


# ── D4 — 저자 ③층(Stop 훅) 대체 ────────────────────────────────────────────
class TestStepChecks:
    def _mark_completed(self, inst):
        idx = json.loads(inst._index_file.read_text())
        idx["steps"][0]["status"] = "completed"
        inst._index_file.write_text(json.dumps(idx, ensure_ascii=False))

    def test_checks_run_only_when_session_says_completed(self, inst, monkeypatch):
        monkeypatch.setattr(qb, "STEP_CHECKS", [("probe", ["true"], qb.ROOT)])
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")):
            out = inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        assert out["checks"] == [], "세션이 pending 인데 검사가 돌면 안 된다"

    def test_failing_check_overturns_self_report(self, inst, monkeypatch):
        """★★자기신고를 러너가 **뒤집는** 유일한 지점. 저자 설계에서는 Stop 훅이 하던 일이다."""
        monkeypatch.setattr(qb, "STEP_CHECKS", [("probe", ["probe"], qb.ROOT)])
        real_run = subprocess.run

        def fake(cmd, *a, **kw):
            if cmd and cmd[0] == "probe":
                return MagicMock(returncode=1, stdout="boom", stderr="")
            self._mark_completed(inst)          # 세션이 completed 라고 신고
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake):
            out = inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        assert out["checks"] == [{"check": "probe", "rc": 1}]
        assert inst._step_status(0) == "error", "고정 검사가 실패했는데 completed 로 남았다"
        assert "고정 검사 실패" in json.loads(inst._index_file.read_text())["steps"][0]["error_message"]
        assert real_run is subprocess.run  # 패치 복구 확인

    def test_passing_check_leaves_completed(self, inst, monkeypatch):
        monkeypatch.setattr(qb, "STEP_CHECKS", [("probe", ["probe"], qb.ROOT)])

        def fake(cmd, *a, **kw):
            if cmd and cmd[0] == "probe":
                return MagicMock(returncode=0, stdout="", stderr="")
            self._mark_completed(inst)
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake):
            inst._invoke_claude({"step": 0, "name": "s0"}, "P")
        assert inst._step_status(0) == "completed"

    def test_real_step_checks_are_cheap_and_deterministic(self):
        """실제 STEP_CHECKS 가 워크트리에서 안전한 것만인지 — docker·DB·celery 금지."""
        for label, cmd, cwd in qb.STEP_CHECKS:
            joined = " ".join(cmd)
            for banned in ("docker", "make up", "celery", "pytest", "playwright"):
                assert banned not in joined, f"{label} 이 {banned} 를 부른다"
