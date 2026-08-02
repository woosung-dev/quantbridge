"""R1 metric guard census.

대상 = ``backend/src/**/*.py``.

site는 다음 AST ``Call`` 이다.

(a) ``func.attr`` 이 ``inc``, ``dec``, ``observe``, ``set`` 중 하나이고,
    ``.labels(...)`` 체인의 뿌리가 ``^qb_`` 인 ``Name`` 이거나 그 ``Name`` 에 직접
    mutation 을 호출한 것.
(b) 뿌리가 ``^qb_`` 인 ``.labels(...)`` 호출 중 (a)의 수신자가 아닌 것, 즉 증가 없이
    라벨 조합을 실체화하는 호출.

guarded는 ``record_metric_safely`` / ``_count_safely`` / ``_touch_safely`` 호출이 덮는
범위다.

(i) 호출 인자 서브트리와 그 안의 ``lambda:`` 본문.
(ii) 이름으로 넘긴 중첩 ``def`` 본문. 예를 들어 ``def increment(): ...`` 뒤에
     ``record_metric_safely(increment)`` 를 호출하면 그 본문은 guarded다.

못 잡는 것: 별칭(``c = qb_x; c.inc()``), ``getattr`` 등 동적 접근, 모듈 alias 경유,
``qb_`` 아닌 이름, 그리고 가드 밖인지만 알 뿐 그 자리가 머니-패스인지는 모른다.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.common.metrics import _LIVE_CONDITIONAL_GUARD_OUTCOMES

_MUTATION_METHODS = frozenset({"inc", "dec", "observe", "set"})
_GUARD_FUNCTIONS = frozenset({"record_metric_safely", "_count_safely", "_touch_safely"})
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"

_CENSUS_RULE_FAILURE_MESSAGE = """
R1 metric guard census rule:
(a) ``inc``/``dec``/``observe``/``set`` Call whose ``qb_`` Name is the metric root.
(b) a root-``qb_`` ``.labels(...)`` Call that is not the receiver of (a).
(i) Guard coverage includes every argument subtree, including lambda bodies.
(ii) Guard coverage includes the body of a nested def passed to the guard by name.
못 잡는 것: aliases, dynamic getattr access, module aliases, non-qb_ names, and whether an
unguarded site belongs to a money path.
""".strip()


_FROZEN_CENSUS: dict[tuple[str, str], int] = {
    ("backend/src/common/alert.py", "qb_pending_alerts"): 2,
    ("backend/src/common/metrics.py", "qb_ccxt_request_duration_seconds"): 1,
    ("backend/src/common/metrics.py", "qb_ccxt_request_errors_total"): 1,
    ("backend/src/common/metrics_multiproc.py", "qb_metrics_mutation_failed_total"): 1,
    ("backend/src/common/rate_limit.py", "qb_rate_limit_throttled_total"): 1,
    ("backend/src/common/redis_client.py", "qb_redis_lock_pool_healthy"): 1,
    ("backend/src/common/redlock.py", "qb_redlock_acquire_total"): 3,
    ("backend/src/tasks/_ws_circuit_breaker.py", "qb_ws_auth_circuit_total"): 4,
    ("backend/src/tasks/backtest.py", "qb_backtest_duration_seconds"): 1,
    ("backend/src/tasks/conditional_entry_janitor.py", "qb_active_orders"): 3,
    (
        "backend/src/tasks/conditional_entry_janitor.py",
        "qb_live_conditional_reconcile_errors_total",
    ): 5,
    ("backend/src/tasks/live_signal.py", "qb_active_orders"): 3,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_cancelled_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_guard_total"): 9,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_placed_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_reconcile_errors_total"): 14,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_sweep_filled_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_gap_ledger_seed_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_dispatch_total"): 12,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_divergence_total"): 5,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_entry_skipped_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_eval_duration_seconds"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_evaluated_total"): 7,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_liquidation_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_outbox_pending_gauge"): 2,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_skipped_total"): 10,
    ("backend/src/tasks/trading.py", "qb_active_orders"): 8,
    ("backend/src/tasks/trading.py", "qb_closed_pnl_backfill_total"): 15,
    ("backend/src/tasks/trading.py", "qb_exchange_exit_attribution_total"): 1,
    ("backend/src/tasks/trading.py", "qb_exchange_exit_link_unverified_total"): 1,
    ("backend/src/tasks/trading.py", "qb_exchange_exit_rows_total"): 1,
    ("backend/src/tasks/trading.py", "qb_order_snapshot_fallback_total"): 2,
    ("backend/src/tasks/trading.py", "qb_trailing_placement_total"): 10,
    ("backend/src/tasks/websocket_task.py", "qb_ws_auth_circuit_total"): 1,
    ("backend/src/tasks/websocket_task.py", "qb_ws_duplicate_enqueue_total"): 2,
    ("backend/src/trading/kill_switch.py", "qb_kill_switch_triggered_total"): 1,
    ("backend/src/trading/providers.py", "qb_closed_pnl_backfill_total"): 1,
    ("backend/src/trading/realtime_publisher.py", "qb_rt_publish_failed_total"): 1,
    ("backend/src/trading/realtime_publisher.py", "qb_rt_publish_invalid_total"): 1,
    ("backend/src/trading/router.py", "qb_active_orders"): 1,
    ("backend/src/trading/services/order_service.py", "qb_order_rejected_total"): 10,
    ("backend/src/trading/webhook.py", "qb_order_rejected_total"): 1,
    ("backend/src/trading/webhook.py", "qb_webhook_symbol_rejected_total"): 1,
    ("backend/src/trading/websocket/bybit_private_stream.py", "qb_ws_reconcile_skipped_total"): 1,
    ("backend/src/trading/websocket/bybit_private_stream.py", "qb_ws_reconnect_total"): 1,
    ("backend/src/trading/websocket/position_fanout.py", "qb_ws_subscribe_rejected_total"): 1,
    ("backend/src/trading/websocket/reconciliation.py", "qb_active_orders"): 1,
    ("backend/src/trading/websocket/reconciliation.py", "qb_ws_reconcile_unknown_total"): 1,
    ("backend/src/trading/websocket/state_handler.py", "qb_active_orders"): 1,
    ("backend/src/trading/websocket/state_handler.py", "qb_ws_orphan_buffer_size"): 2,
    ("backend/src/trading/websocket/state_handler.py", "qb_ws_orphan_event_total"): 1,
}


@dataclass(frozen=True)
class _MetricSite:
    path: str
    lineno: int
    metric: str
    verb: str
    function_name: str


def _metric_name(expression: ast.expr) -> str | None:
    if isinstance(expression, ast.Name) and expression.id.startswith("qb_"):
        return expression.id
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "labels"
    ):
        return _metric_name(expression.func.value)
    return None


def _mutation_site(call: ast.Call) -> tuple[str, str] | None:
    if not isinstance(call.func, ast.Attribute) or call.func.attr not in _MUTATION_METHODS:
        return None
    metric = _metric_name(call.func.value)
    if metric is None:
        return None
    return metric, call.func.attr


def _labels_site(call: ast.Call, mutation_receivers: set[int]) -> tuple[str, str] | None:
    if (
        not isinstance(call.func, ast.Attribute)
        or call.func.attr != "labels"
        or id(call) in mutation_receivers
    ):
        return None
    metric = _metric_name(call.func.value)
    if metric is None:
        return None
    return metric, "labels"


def _is_guard_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id in _GUARD_FUNCTIONS


def _enclosing_function(node: ast.AST, parents: dict[int, ast.AST]) -> ast.AST | None:
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = parents.get(id(current))
    return None


def _guarded_node_ids(tree: ast.AST) -> set[int]:
    parents = {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    nested_defs: defaultdict[tuple[int | None, str], list[ast.AST]] = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parent_function = _enclosing_function(node, parents)
            nested_defs[
                (id(parent_function) if parent_function is not None else None, node.name)
            ].append(node)

    guarded: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_guard_call(node):
            continue
        arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
        for argument in arguments:
            guarded.update(id(descendant) for descendant in ast.walk(argument))
            if not isinstance(argument, ast.Name):
                continue
            parent_function = _enclosing_function(node, parents)
            candidates = nested_defs[
                (id(parent_function) if parent_function is not None else None, argument.id)
            ]
            for nested_def in candidates:
                if nested_def.lineno < node.lineno:
                    guarded.update(id(descendant) for descendant in ast.walk(nested_def))
    return guarded


class _SiteCollector(ast.NodeVisitor):
    def __init__(self, path: str, guarded_node_ids: set[int]) -> None:
        self._path = path
        self._guarded_node_ids = guarded_node_ids
        self._function_names: list[str] = []
        self._calls: list[ast.Call] = []
        self._call_function_names: dict[int, str] = {}
        self.sites: list[_MetricSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._function_names.append(node.name)
        self.generic_visit(node)
        self._function_names.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self._calls.append(node)
        self._call_function_names[id(node)] = (
            self._function_names[-1] if self._function_names else "<module>"
        )
        self.generic_visit(node)

    def collect(self) -> list[_MetricSite]:
        mutation_receivers = {
            id(call.func.value)
            for call in self._calls
            if _mutation_site(call) is not None and isinstance(call.func, ast.Attribute)
        }
        for call in self._calls:
            site = _mutation_site(call) or _labels_site(call, mutation_receivers)
            if site is None or id(call) in self._guarded_node_ids:
                continue
            metric, verb = site
            self.sites.append(
                _MetricSite(
                    path=self._path,
                    lineno=call.lineno,
                    metric=metric,
                    verb=verb,
                    function_name=self._call_function_names[id(call)],
                )
            )
        return self.sites


def _collect_unguarded_sites(tree: ast.AST, path: str) -> list[_MetricSite]:
    collector = _SiteCollector(path, _guarded_node_ids(tree))
    collector.visit(tree)
    return collector.collect()


def _source_trees() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(_SOURCE_ROOT.rglob("*.py"))
    ]


def _census_sites() -> list[_MetricSite]:
    sites: list[_MetricSite] = []
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        sites.extend(_collect_unguarded_sites(tree, relative_path))
    return sites


def _census_failure_message(actual: Counter[tuple[str, str]], sites: list[_MetricSite]) -> str:
    added_sites: list[_MetricSite] = []
    for key, actual_count in actual.items():
        frozen_count = _FROZEN_CENSUS.get(key, 0)
        if actual_count > frozen_count:
            key_sites = sorted(
                (site for site in sites if (site.path, site.metric) == key),
                key=lambda site: site.lineno,
            )
            added_sites.extend(key_sites[frozen_count:])

    reduced_entries = [
        (key, actual.get(key, 0))
        for key, frozen_count in _FROZEN_CENSUS.items()
        if actual.get(key, 0) < frozen_count
    ]
    lines = [
        "Metric guard census diverged from the frozen R1 baseline.",
        "159 − 사전등록 10 = 149",
        "새 site (file, lineno, metric, verb, 함수명):",
    ]
    lines.extend(
        f"  ({site.path}, {site.lineno}, {site.metric}, {site.verb}, {site.function_name})"
        for site in sorted(added_sites, key=lambda site: (site.path, site.lineno))
    )
    lines.append("줄어든 항목 (동결값의 이 항목을 N으로 낮춰라):")
    lines.extend(f"  {key}: 이 항목을 {count} 으로 낮춰라" for key, count in reduced_entries)
    return "\n".join(lines)


def _outcome_leaves(expression: ast.expr) -> list[ast.expr]:
    if isinstance(expression, ast.IfExp):
        return [*_outcome_leaves(expression.body), *_outcome_leaves(expression.orelse)]
    return [expression]


def _guard_outcome_expression(call: ast.Call) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == "outcome":
            return keyword.value
    return None


def _guard_outcome_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "labels"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "qb_live_conditional_guard_total"
        ):
            calls.append(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "_count_safely"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "qb_live_conditional_guard_total"
        ):
            calls.append(node)
    return calls


def test_census_rule_is_stated_in_the_failure_message() -> None:
    for required_text in ("(a)", "(b)", "(i)", "(ii)", "못 잡는 것"):
        assert required_text in _CENSUS_RULE_FAILURE_MESSAGE


def test_census_rule_classifies_the_synthetic_fixture() -> None:
    fixture = ast.parse(
        """
qb_a.inc()
record_metric_safely(lambda: qb_b.labels(x="y").inc())
record_metric_safely(qb_c.dec)

def bump():
    qb_d.inc()

record_metric_safely(bump)
qb_fixture.labels(x="y")
qb_multiline.labels(
    x="y",
).inc()
c = qb_e
c.inc()
"""
    )

    sites = _collect_unguarded_sites(fixture, "synthetic.py")
    actual = {(site.metric, site.verb) for site in sites}
    expected = {
        ("qb_a", "inc"),
        ("qb_fixture", "labels"),
        ("qb_multiline", "inc"),
    }

    assert actual == expected
    assert sum(site.metric == "qb_multiline" for site in sites) == 1
    assert all(site.metric != "qb_e" for site in sites), "별칭 c = qb_e; c.inc()는 잡지 못한다"
    assert all(site.metric not in {"qb_b", "qb_c", "qb_d"} for site in sites)


def test_unguarded_mutation_counts_match_the_frozen_census() -> None:
    assert len(_FROZEN_CENSUS) == 51
    assert sum(_FROZEN_CENSUS.values()) == 159

    sites = _census_sites()
    actual = Counter((site.path, site.metric) for site in sites)

    assert actual == _FROZEN_CENSUS, _census_failure_message(actual, sites)


def test_guard_outcome_literals_are_all_allowed() -> None:
    violations: list[str] = []
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        for call in _guard_outcome_calls(tree):
            expression = _guard_outcome_expression(call)
            if expression is None:
                violations.append(f"{relative_path}:{call.lineno}: outcome= is required")
                continue
            for leaf in _outcome_leaves(expression):
                if not isinstance(leaf, ast.Constant) or not isinstance(leaf.value, str):
                    violations.append(
                        f"{relative_path}:{leaf.lineno}: outcome leaf is not a static string literal: "
                        f"{ast.unparse(leaf)}"
                    )
                    continue
                if leaf.value not in _LIVE_CONDITIONAL_GUARD_OUTCOMES:
                    violations.append(
                        f"{relative_path}:{leaf.lineno}: unsupported outcome literal {leaf.value!r}"
                    )

    assert not violations, "\n".join(violations)
