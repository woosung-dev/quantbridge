"""새 source 실행 없이 사전등록·VM 관측·동등성·권한 경계를 검증한다."""

import base64
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "process_ab_tool", ROOT / "tools/scripts/editor-picks-process-ab.py"
)
AB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AB)


def registration():
    return {
        "workflow_budget_seconds": 2100,
        "probe_budget_seconds": 1800,
        "existing_transport_timeout_seconds": 900,
        "order": [{"label": "serial", "workers": 1}, {"label": "parallel", "workers": 2}],
        "job_repetitions_per_mode": 1,
        "selected": [{"id": "first"}, {"id": "second"}],
        "jobs": [
            {"id": name, "arm": arm, "timeframe": "1h", "months": 24, "scenario": "baseline"}
            for name in ("first", "second")
            for arm in ("pine", "terra")
        ],
        "success": {
            "all_eight_statuses_completed": True,
            "action_ledger_metrics_and_raw_result_hashes_exact": True,
            "speedup_min": 1.2,
            "minimum_mem_available_bytes": 2 * 1024**3,
            "oom_kill_delta": 0,
            "missing_measurements_fail": True,
            "automatic_adoption": False,
        },
    }


def measurement(wall):
    return {
        "wall_seconds": wall,
        "vm_cpu_percent": 75,
        "vm_min_mem_available_bytes": 4 * 1024**3,
        "vm_oom_kill_delta": 0,
        "sample_count": 4,
    }


def rows():
    return [
        {
            "job": job,
            "status": "completed",
            **dict.fromkeys(
                ("action_sha256", "ledger_sha256", "metrics_sha256", "result_sha256"), "a" * 64
            ),
        }
        for job in registration()["jobs"]
    ]


class ProcessABControls(unittest.TestCase):
    def test_registration_has_fixed_order_jobs_budget_and_no_automatic_adoption(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registration.json"
            expected = registration()
            path.write_text(json.dumps(expected))
            self.assertEqual(AB.registration(path), expected)

    def test_registration_cannot_reselect_change_budget_order_or_success(self):
        changes = [
            "source",
            "months",
            "cost",
            "budget",
            "timeout",
            "order",
            "boolean_workers",
            "threshold",
            "auto_adopt",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registration.json"
            for change in changes:
                with self.subTest(change=change):
                    value = registration()
                    if change in {"source", "months", "cost"}:
                        key, replacement = {
                            "source": ("id", "other"),
                            "months": ("months", 6),
                            "cost": ("scenario", "fees_x2"),
                        }[change]
                        value["jobs"][0][key] = replacement
                    elif change == "budget":
                        value["probe_budget_seconds"] = 3600
                    elif change == "timeout":
                        value["existing_transport_timeout_seconds"] = 1800
                    elif change == "order":
                        value["order"].reverse()
                    elif change == "boolean_workers":
                        value["order"][0]["workers"] = True
                    elif change == "threshold":
                        value["success"]["speedup_min"] = 1.0
                    else:
                        value["success"]["automatic_adoption"] = True
                    path.write_text(json.dumps(value))
                    with self.assertRaises(ValueError):
                        AB.registration(path)

    def test_vm_snapshot_and_cpu_include_global_proc_counters(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc = Path(temporary)
            (proc / "meminfo").write_text("MemTotal: 16777216 kB\nMemAvailable: 12582912 kB\n")
            (proc / "stat").write_text("cpu 100 0 100 800 0 0 0 0 0 0\n")
            (proc / "vmstat").write_text("pgfault 123\noom_kill 0\n")
            before = AB.snapshot(proc)
            after = {**before, "cpu_total": 1100, "cpu_idle": 825, "mem_available": 10 * 1024**3}
            measured = AB.observation([before, after], 2)
            self.assertEqual(measured["vm_cpu_percent"], 75)
            self.assertEqual(measured["vm_peak_used_memory_bytes"], 6 * 1024**3)
            self.assertEqual(measured["vm_min_mem_available_bytes"], 10 * 1024**3)
            self.assertIsNone(measured["rss_bytes"])
            (proc / "vmstat").write_text("pgfault 123\n")
            with self.assertRaises(ValueError):
                AB.snapshot(proc)

    def test_missing_counter_or_zero_cpu_delta_is_unknown_not_success(self):
        base = {
            "mem_total": 10,
            "mem_available": 5,
            "cpu_total": 100,
            "cpu_idle": 50,
            "oom_kill": 0,
        }
        with self.assertRaises(ValueError):
            AB.observation([base], 1)
        with self.assertRaises(ValueError):
            AB.observation([base, base], 1)

    def test_equal_completed_four_cells_speedup_and_memory_can_be_eligible_not_auto_adopted(self):
        result = AB.compare(rows(), rows(), [measurement(20), measurement(10)], registration())
        self.assertTrue(result["adoption_eligible"])
        self.assertEqual(result["speedup"], 2)
        self.assertFalse(result["automatic_adoption"])

    def test_any_hash_status_memory_oom_or_speed_failure_prevents_adoption(self):
        for change in [
            "action_sha256",
            "ledger_sha256",
            "metrics_sha256",
            "result_sha256",
            "failed",
            "memory",
            "oom",
            "slow",
            "missing_cell",
        ]:
            with self.subTest(change=change):
                right = rows()
                observed = [measurement(20), measurement(10)]
                if change.endswith("sha256"):
                    right[0][change] = "b" * 64
                elif change == "failed":
                    right[0]["status"] = "failed"
                elif change == "memory":
                    observed[1]["vm_min_mem_available_bytes"] = 1024
                elif change == "oom":
                    observed[1]["vm_oom_kill_delta"] = 1
                elif change == "slow":
                    observed[1]["wall_seconds"] = 21
                else:
                    right.pop()
                self.assertFalse(
                    AB.compare(rows(), right, observed, registration())["adoption_eligible"]
                )

    def test_missing_or_nonfinite_cpu_measurement_is_fail_closed(self):
        for change in ["missing", "nonfinite"]:
            observed = [measurement(20), measurement(10)]
            if change == "missing":
                del observed[1]["vm_cpu_percent"]
            else:
                observed[1]["vm_cpu_percent"] = float("nan")
            with self.assertRaises(ValueError):
                AB.compare(rows(), rows(), observed, registration())

    def test_original_source_never_runs_on_local_host(self):
        with self.assertRaises(ValueError):
            AB.runner(
                {}, type("Args", (), {"head": "a" * 40, "run_id": "1", "attempt": "1"})(), True
            )

    def test_credential_in_parent_environment_is_rejected_before_source_calls(self):
        args = type("Args", (), {"head": "a" * 40, "run_id": "1", "attempt": "1"})()
        reg = {
            "runner": {"memory_min_bytes": 14 * 1024**3},
            "binding_before_dispatch": {"control_head": "a" * 40},
        }
        with (
            patch.object(AB, "ROOT", Path("/home/runner/work/repo/repo")),
            patch.object(AB.platform, "system", return_value="Linux"),
            patch.object(AB.platform, "machine", return_value="aarch64"),
            patch.object(AB.os, "cpu_count", return_value=4),
            patch.object(AB, "snapshot", return_value={"mem_total": 16 * 1024**3}),
            patch.object(AB.subprocess, "check_output", return_value="a" * 40),
            patch.dict(
                AB.os.environ, {"GH_TOKEN": "trusted-synthetic-not-a-real-token"}, clear=True
            ),
            self.assertRaises(ValueError),
        ):
            AB.runner(reg, args, True)

    def test_workflow_keeps_owner_and_exact_head_gate_and_no_credentials_in_execution(self):
        text = (ROOT / ".github/workflows/editor-picks-process-ab.yml").read_text()
        self.assertIn("github.actor == github.repository_owner", text)
        self.assertIn("head.sha == vars.EDITOR_PICKS_AB_HEAD", text)
        self.assertIn("timeout-minutes: 35", text)
        worker = text.split("- name: Compare fixed four jobs without credentials", 1)[1].split(
            "- name: Preserve encrypted probe evidence only", 1
        )[0]
        self.assertIn("env -i", worker)
        self.assertIn("PINE_AST_CACHE_DIR=''", worker)
        self.assertNotIn("GH_TOKEN", worker)
        self.assertNotIn("EDITOR_PICKS_RESEARCH_KEY", worker)
        self.assertNotIn("secrets.", worker)

    def test_urlsafe_dummy_key_is_accepted_but_malformed_key_is_rejected(self):
        args = type("Args", (), {"head": "a" * 40, "run_id": "1", "attempt": "1"})()
        reg = {
            "runner": {"memory_min_bytes": 14 * 1024**3},
            "binding_before_dispatch": {"control_head": "a" * 40},
        }
        env = {
            "PATH": "/usr/bin",
            "HOME": "/home/runner",
            "LANG": "C.UTF-8",
            "PINE_AST_CACHE_DIR": "",
            "TRADING_ENCRYPTION_KEYS": base64.urlsafe_b64encode(bytes([255]) * 32).decode(),
        }
        self.assertIn("_", env["TRADING_ENCRYPTION_KEYS"])
        with (
            patch.object(AB, "ROOT", Path("/home/runner/work/repo/repo")),
            patch.object(AB.platform, "system", return_value="Linux"),
            patch.object(AB.platform, "machine", return_value="aarch64"),
            patch.object(AB.os, "cpu_count", return_value=4),
            patch.object(AB, "snapshot", return_value={"mem_total": 16 * 1024**3}),
            patch.object(AB.subprocess, "check_output", return_value="a" * 40),
            patch.dict(AB.os.environ, env, clear=True),
        ):
            AB.runner(reg, args, True)
            AB.os.environ["TRADING_ENCRYPTION_KEYS"] = "invalid!"
            with self.assertRaises(ValueError):
                AB.runner(reg, args, True)

    def test_already_expired_budget_starts_no_process(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(AB.subprocess, "Popen") as spawn,
        ):
            with self.assertRaises(ValueError):
                AB.monitored([], Path(temporary), 0, [])
            spawn.assert_not_called()

    def test_exited_parent_still_terminates_group_and_only_owned_containers(self):
        process = MagicMock(pid=987654321, returncode=0)
        process.poll.return_value = 0
        before = {
            "mem_total": 16 * 1024**3,
            "mem_available": 12 * 1024**3,
            "cpu_total": 100,
            "cpu_idle": 50,
            "oom_kill": 0,
        }
        after = {**before, "cpu_total": 200, "cpu_idle": 75}
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(AB, "containers", return_value=(set(), {})),
            patch.object(AB, "remaining_containers", return_value={"owned-id": {}}),
            patch.object(AB, "snapshot", side_effect=[before, after]),
            patch.object(AB.subprocess, "Popen", return_value=process),
            patch.object(AB.os, "killpg") as kill,
            patch.object(AB.subprocess, "run") as remove,
            patch.object(AB, "stopped_writers"),
        ):
            AB.monitored([], Path(temporary), time.monotonic() + 10, ["image"])
            self.assertEqual(
                [call.args[1] for call in kill.call_args_list],
                [AB.signal.SIGTERM, AB.signal.SIGKILL],
            )
            self.assertEqual(remove.call_args.args[0], ["docker", "rm", "--force", "owned-id"])

    def test_container_identity_image_and_created_time_must_match_before_cleanup(self):
        state = {
            "baseline_container_ids": [],
            "allowed_image_ids": ["image"],
            "started_at_epoch": 1,
        }
        metadata = {
            "id": "owned",
            "image": "image",
            "name": "/qb-python-" + "a" * 32,
            "created": "1970-01-01T00:00:02+00:00",
        }
        for change in ("baseline", "image", "created", "name"):
            with self.subTest(change=change):
                changed = dict(metadata)
                selected = dict(state)
                if change == "baseline":
                    selected["baseline_container_ids"] = ["owned"]
                elif change == "image":
                    changed["image"] = "foreign-image"
                elif change == "created":
                    changed["created"] = "1970-01-01T00:00:00+00:00"
                else:
                    changed["name"] = "foreign-name"
                with (
                    patch.object(AB, "containers", return_value=({"owned"}, {"owned": changed})),
                    self.assertRaises(ValueError),
                ):
                    AB.remaining_containers(selected)

    def test_live_group_writer_prevents_pack_even_without_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "mode"
            folder.mkdir()
            (folder / "process-state.json").write_text(json.dumps({"pgid": 321}))
            proc = root / "proc"
            (proc / "123").mkdir(parents=True)
            (proc / "123/stat").write_text("123 (spawn child) S 1 321 321 0 0")
            with (
                patch.object(AB, "remaining_containers", return_value={}),
                self.assertRaises(ValueError),
            ):
                AB.stopped_writers(folder, proc)
            (proc / "123/stat").write_text("123 (spawn child) Z 1 321 321 0 0")
            with patch.object(AB, "remaining_containers", return_value={}):
                AB.stopped_writers(folder, proc)
            with (
                patch.object(AB, "remaining_containers", return_value={"owned": {}}),
                self.assertRaises(ValueError),
            ):
                AB.stopped_writers(folder, proc)

    def test_workflow_deadline_precedes_checkout_and_registration_is_not_in_worker_env(self):
        text = (ROOT / ".github/workflows/editor-picks-process-ab.yml").read_text()
        self.assertLess(
            text.index("Freeze the execution deadline"), text.index("actions/checkout@v4")
        )
        self.assertIn("time.monotonic()+1800", text)
        worker = text.split("- name: Compare fixed four jobs without credentials", 1)[1].split(
            "- name: Preserve encrypted probe evidence only", 1
        )[0]
        self.assertIn("--budget-file", worker)
        self.assertNotIn("REGISTRATION_JSON:", worker)

    def test_timeout_kills_group_and_cannot_report_a_successful_measurement(self):
        process = MagicMock(pid=987654321, returncode=-15)
        process.poll.return_value = None
        measured = {
            "mem_total": 16 * 1024**3,
            "mem_available": 12 * 1024**3,
            "cpu_total": 100,
            "cpu_idle": 50,
            "oom_kill": 0,
        }
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(AB, "containers", return_value=(set(), {})),
            patch.object(AB, "remaining_containers", return_value={}),
            patch.object(AB, "snapshot", return_value=measured),
            patch.object(AB.subprocess, "Popen", return_value=process),
            patch.object(AB.os, "killpg") as kill,
            patch.object(AB, "stopped_writers"),
            patch.object(AB.time, "monotonic", side_effect=[0, 0, 0, 11]),
            self.assertRaises(ValueError),
        ):
            try:
                AB.monitored([], Path(temporary), 10, ["image"])
            finally:
                self.assertEqual(
                    [call.args[1] for call in kill.call_args_list],
                    [AB.signal.SIGTERM, AB.signal.SIGKILL],
                )


if __name__ == "__main__":
    unittest.main()
