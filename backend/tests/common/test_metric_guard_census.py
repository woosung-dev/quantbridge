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
    (
        "backend/src/tasks/conditional_entry_janitor.py",
        "qb_live_conditional_reconcile_errors_total",
    ): 5,
    # ★2026-08-04 direction-channel-decomposition 연장 — `_reconcile_conditional_entries`
    # **12곳 전건 수리**(`qb_live_conditional_guard_total` 4곳은 여기서 **0** 이 됐다).
    # 판정 — ★**「전부 같은 형태」가 아니다.** 감싸는 핸들러가 갈린다:
    #   (a) **안쪽 `except` 에 잡히는 자리** → 예외가 그 핸들러의 라벨로 **오기록**되고
    #       루프는 계속된다. 실증: `unrepresentable_key` 는 발주 `try` 안이라 발주를
    #       시도한 적도 없는데 `stage="conditional_place"`(= 발주 실패)가 올랐다
    #       (`test_pre_execute_metric_failure_no_longer_masquerades_as_a_place_failure`).
    #   (b) **바깥 fail-open `except` 까지 가는 자리** → `stage="reconcile"` 로 계상하고
    #       **정상과 똑같이 `None` 을 반환**한다. 호출자(평가 tick)는 곧바로
    #       `outcome="success"` 를 계상하므로 **리컨사일이 조용히 사라지는데 성공으로
    #       기록된다.** 지속 실패 시 resting 조건부 주문 수렴이 멈춘다.
    # ★H8(거절이 집행으로 뒤집힘)은 **아니다** — 어느 갈래든 예외는 `continue` 와
    #   `execute` 를 함께 건너뛰므로 잘못된 주문이 나가지 않는다.
    # ★내가 처음 12곳을 전부 (b)로 적었고 **테스트가 그 일반화를 반증했다.** 직전 회차의
    #   「8곳 중 1곳만 fail-open `try` 안」과 같은 함정이다.
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_reconcile_errors_total"): 3,
    ("backend/src/tasks/live_signal.py", "qb_live_conditional_sweep_filled_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_gap_ledger_seed_total"): 1,
    # ★2026-08-03 metric-guard-residual-sweep — 12곳 중 8곳 수리. 잔여 4곳은 **판정 보류**
    #   (프로덕션 도달 경로를 한 줄로 못 적어 주입 하네스를 만들지 않았다. 만들면 프로덕션이
    #   못 만드는 상태를 손조립해 「실측 유해」로 적게 된다 — [BL-582] 함정의 거울상):
    #     `:3095` strategy_missing — FK `strategies.id ON DELETE RESTRICT`(`models.py:502`)가
    #        세션 존재 중 삭제를 막고, owner 는 등재 시 일치 후 이전 경로가 없다.
    #     `:3104` invalid_settings — `update_settings(settings: StrategySettings)` 가 같은
    #        클래스를 `model_dump()` 하므로 round-trip 이 항상 유효하다.
    #     `:3111` settings_unset — 등록 게이트(`live_session_service.py:84`)가 유일 방벽이고
    #        통과 뒤 settings 가 비는 경로가 없다.
    #     `:3278` idempotency_conflict — ★**도달 불가**. 유일 raise 지점
    #        (`order_service.py:369`)이 `if body_hash is not None` 안인데 `:3246` 은
    #        `body_hash=None` 을 넘긴다. 그 `except` 는 이 호출자에게 사문(死文)이다.
    ("backend/src/tasks/live_signal.py", "qb_live_signal_dispatch_total"): 4,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_divergence_total"): 4,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_entry_skipped_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_eval_duration_seconds"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_evaluated_total"): 6,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_liquidation_total"): 1,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_outbox_pending_gauge"): 2,
    ("backend/src/tasks/live_signal.py", "qb_live_signal_skipped_total"): 10,
    # ★`tasks/trading.py` · `trading/router.py` 의 `qb_active_orders` 는 2026-08-03
    #   metric-guard-residual 이 전건 감쌌다. Counter 는 0 인 키를 만들지 않으므로 항목
    #   자체를 지운다 — `: 0` 으로 남기면 `actual == _FROZEN_CENSUS` 가 영구 red 다.
    #   ★2026-08-03 metric-guard-residual-close 가 같은 이유로 두 항목을 더 지웠다:
    #   `tasks/trading.py`+`qb_closed_pnl_backfill_total`(15) ·
    #   `services/order_service.py`+`qb_order_rejected_total`(10).
    ("backend/src/tasks/trading.py", "qb_exchange_exit_attribution_total"): 1,
    ("backend/src/tasks/trading.py", "qb_exchange_exit_link_unverified_total"): 1,
    ("backend/src/tasks/trading.py", "qb_exchange_exit_rows_total"): 1,
    ("backend/src/tasks/trading.py", "qb_order_snapshot_fallback_total"): 2,
    ("backend/src/tasks/trading.py", "qb_trailing_placement_total"): 9,
    ("backend/src/tasks/websocket_task.py", "qb_ws_auth_circuit_total"): 1,
    ("backend/src/tasks/websocket_task.py", "qb_ws_duplicate_enqueue_total"): 2,
    ("backend/src/trading/kill_switch.py", "qb_kill_switch_triggered_total"): 1,
    ("backend/src/trading/providers.py", "qb_closed_pnl_backfill_total"): 1,
    ("backend/src/trading/realtime_publisher.py", "qb_rt_publish_failed_total"): 1,
    ("backend/src/trading/realtime_publisher.py", "qb_rt_publish_invalid_total"): 1,
    ("backend/src/trading/webhook.py", "qb_order_rejected_total"): 1,
    ("backend/src/trading/webhook.py", "qb_webhook_symbol_rejected_total"): 1,
    ("backend/src/trading/websocket/bybit_private_stream.py", "qb_ws_reconcile_skipped_total"): 1,
    ("backend/src/trading/websocket/bybit_private_stream.py", "qb_ws_reconnect_total"): 1,
    ("backend/src/trading/websocket/position_fanout.py", "qb_ws_subscribe_rejected_total"): 1,
    ("backend/src/trading/websocket/reconciliation.py", "qb_ws_reconcile_unknown_total"): 1,
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
        "159 − 2026-08-02 수리 18 = 141 − 2026-08-03 수리 12 = 129 "
        "− 2026-08-03 수리 25 = 104 − 2026-08-03 수리 8 = 96 − 2026-08-04 수리 12 = 84",
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
    assert len(_FROZEN_CENSUS) == 40
    assert sum(_FROZEN_CENSUS.values()) == 84

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


# ---------------------------------------------------------------------------
# 보호 목록 (L2) — CONTROL 이 손으로 동결한다. ★추론하지 않는다.
#
# 왜 추론을 안 쓰나: 「머니-패스」 zone 을 AST 로 추론하려 세 번 시도했고 정의를 조금씩
# 바꿀 때마다 6 / 13 / 14 곳으로 흔들렸다(2026-08-02). 그중 「6곳」은 프로토타입에 박아둔
# 임의의 40줄 창이 만든 값이었다. ⇒ 머니-패스 여부는 구문에서 추론할 수 없다.
# 신규 유입 차단은 위 census 천장이 담당하고, 이 목록은 **무엇을 왜 지키는지**를 고정한다.
# ---------------------------------------------------------------------------

_PROTECTED_SITES: tuple[tuple[str, str, str, str], ...] = (
    # (파일, 함수, metric, 이유)
    # Tier 1 — 주문 접수·실행 enqueue 성공 직후. 던지면 성공이 실패로 기록된다.
    (
        "backend/src/tasks/live_signal.py",
        "_reconcile_conditional_entries_inner",
        "qb_live_conditional_placed_total",
        "성공 접수를 stage=conditional_place 실패로 계상",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_reconcile_conditional_entries_inner",
        "qb_live_conditional_guard_total",
        "위와 같음 + _GuardOutcomeCounter 는 ValueError 도 던진다",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_reconcile_conditional_entries_inner",
        "qb_live_conditional_reconcile_errors_total",
        "지연 return 을 건너뛰어 낡은 스냅샷 위 과잉 등재 (실측: execute await 2회)",
    ),
    (
        "backend/src/tasks/trading.py",
        "_do_place_trailing_stop",
        "qb_trailing_placement_total",
        "중복 set_trading_stop + 거짓 trailing_unprotected critical alert",
    ),
    # Tier 2 — 내구 쓰기와 체결 후처리 훅 사이의 gauge. 던지면 후처리가 통째로 유실된다.
    (
        "backend/src/trading/websocket/state_handler.py",
        "handle_order_event",
        "qb_active_orders",
        "WS fill 주 경로. 23줄 아래 가드와 그 전용 회귀 테스트를 도달 불가로 만든다",
    ),
    (
        "backend/src/tasks/trading.py",
        "_execute_with_session",
        "qb_active_orders",
        "REST 동기 fill. max_retries=0 이라 회수 경로가 없다",
    ),
    (
        "backend/src/tasks/trading.py",
        "_fetch_order_status_with_session",
        "qb_active_orders",
        "watchdog fill",
    ),
    (
        "backend/src/trading/websocket/reconciliation.py",
        "run",
        "qb_active_orders",
        "reconciler fill",
    ),
    (
        "backend/src/tasks/conditional_entry_janitor.py",
        "_async_conditional_entry_janitor",
        "qb_active_orders",
        "janitor fill",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_write_back_confirmed_terminal",
        "qb_active_orders",
        "BL-567 이 '트레일링 영구 유실' 로 등재한 격리 블록의 한 줄 위",
    ),
    # ★2026-08-02 codex G6 Spec MAJOR 로 추가된 7곳 — 같은 결함 형태가 **내가 이미 고친
    #   파일 안에** 남아 있었다. 4곳은 `commit()` **앞**이라 더 나쁘다(계측 예외가 terminal
    #   DB 전이를 rollback 시킨다).
    (
        "backend/src/tasks/live_signal.py",
        "_reconcile_conditional_entries_inner",
        "qb_live_conditional_cancelled_total",
        "거래소 취소 성공 뒤. except 가 stage=cancel 실패로 계상하고 이후 reconcile 중단",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_async_sweep_conditional_entries",
        "qb_active_orders",
        "★commit 앞 + except 가 rollback — 계측 예외가 terminal DB 전이를 되돌린다",
    ),
    (
        "backend/src/tasks/conditional_entry_janitor.py",
        "_async_conditional_entry_janitor",
        "qb_active_orders",
        "★commit 앞 + rollback (2곳)",
    ),
    (
        "backend/src/tasks/trading.py",
        "_execute_with_session",
        "qb_active_orders",
        "reject 경로 commit 뒤 (2곳). 같은 문자열이 3곳이라 하나만 남기면 잘못된 패턴이 복제된다",
    ),
    (
        "backend/src/tasks/trading.py",
        "_fetch_order_status_with_session",
        "qb_active_orders",
        "같은 형태 — 일관성 유지",
    ),
    # ★2026-08-03 metric-guard-residual — 고장 주입으로 귀결을 **실측**하고 감싼 12곳.
    #   근거는 산문이 아니라 테스트다: `tests/trading/test_router_cancel_metric_failure.py` ·
    #   `tests/trading/test_trading_task_metric_failure.py` ·
    #   `tests/tasks/test_live_signal_metric_failure.py`.
    #   ★`_FROZEN_CENSUS` 는 `(파일, metric)` **합계**뿐이라 위치를 잃는다 — 같은 파일·metric 에
    #   새 raw 가 생기고 여기 자리가 raw 로 되돌아가면 **상쇄돼 통과**한다(2026-08-02 codex G1
    #   MAJOR#7). 그래서 자리마다 여기에 남긴다.
    (
        "backend/src/trading/router.py",
        "cancel_order",
        "qb_active_orders",
        "commit 뒤 — 던지면 확정된 취소가 HTTP 500 으로 보고된다 (H1, 주입 확인)",
    ),
    (
        "backend/src/tasks/trading.py",
        "_cancel_order_with_session",
        "qb_active_orders",
        "commit 뒤 + 바로 아래 로그가 거래소 취소를 남기는 유일한 라인 (H1)",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_reconcile_conditional_entries_inner",
        "qb_live_conditional_reconcile_errors_total",
        "★stand-down 직전 — 던지면 잘못된 전제 위 조건부 진입이 거래소에 남는다 (H4)",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_evaluate_session_inner",
        "qb_live_signal_divergence_total",
        "★세션 자동 비활성화 commit 뒤 · 무신호 차단 고지 앞 — 세션이 조용히 죽는다 (H2)",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "_evaluate_session_inner",
        "qb_live_signal_evaluated_total",
        "위와 같은 블록 — 둘 다 감싸야 고지에 도달한다",
    ),
    # ★2026-08-03 metric-guard-residual-close — 고장 주입 25곳(전건 「수리함」).
    #   BL-580 이 산문으로 뺐던 두 근거가 **둘 다 반증**됐다:
    #   ① 「order_service.py 10곳은 blast radius 0」 → 10/10 이 도메인 예외 대신 OSError 를
    #      탈출시킨다(4xx → 500, 그중 6종은 호출자 타입 분기까지 건너뛴다).
    #   ② 「closed_pnl 은 already_synced 로 수렴」 → 수렴 논거가 닿는 자리는 7곳 중 1곳뿐.
    #   정본: `tests/trading/test_order_rejected_metric.py` ·
    #   `tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
    #   `tests/tasks/test_closed_pnl_sweep_metric_failure.py` ·
    #   `tests/tasks/test_refresh_closed_pnl.py`.
    (
        "backend/src/trading/services/order_service.py",
        "_execute_inner",
        "qb_order_rejected_total",
        "★거절 8곳 — 도메인 예외가 삼켜지면 4xx 가 500 이 되고 호출자 기록 분기가 빠진다 (H5·H4)",
    ),
    (
        "backend/src/trading/services/order_service.py",
        "_validate_position_size",
        "qb_order_rejected_total",
        "risk 사이징 거절 — 구체 타입 catch 는 없지만 4xx 가 500 이 된다 (H5)",
    ),
    (
        "backend/src/tasks/trading.py",
        "_refresh_closed_pnl_with_session",
        "qb_closed_pnl_backfill_total",
        "★종결 skip 5곳 + applied/already_synced — 정상 종결이 재시도로 오분류된다 (H6·H1)",
    ),
    (
        "backend/src/tasks/trading.py",
        "refresh_closed_pnl_task",
        "qb_closed_pnl_backfill_total",
        "★포기 알림 바로 앞 — 던지면 알림이 1건 더가 아니라 0건이 된다 (H2)",
    ),
    (
        "backend/src/tasks/trading.py",
        "_sweep_closed_pnl_with_session",
        "qb_closed_pnl_backfill_total",
        "★계정 격리 handler 의 첫 줄 + 신규 청산 알림 앞 + 원장 적재 앞 (H4·H2·H7)",
    ),
    # ★2026-08-03 metric-guard-residual-sweep — 라이브 발주 outbox 경로 8곳(전건 「수리함」).
    #   전부 `mark_failed`/`mark_dispatched` + `commit()` **뒤**이고, 호출자
    #   `dispatch_live_signal_event_task:2793` 이 **예외 타입으로** 재시도를 가른다 ⇒ 계측이
    #   던지면 종결이 재시도로 오분류된다(H6). 정본 = `tests/tasks/test_live_signal_metric_failure.py`.
    #   ★★★**사전등록이 한 자리에서 반증됐다** — `:3133`(close_position_flat)만 fail-open
    #      `try` 안이라, 계측 예외를 `except` 가 「포지션 조회 실패」로 오인해 삼키고 **그대로
    #      발주한다**. 오기록이 아니라 **거절이 집행으로 뒤집히는** 자리다(신규 라벨 H8).
    #   ★이 함수는 metric 이 하나뿐이라 아래 `(파일, 함수, metric)` 삼중항은 **과선택**한다 —
    #    「이 함수에 가드된 dispatch_total 이 1개 이상」만 집행한다. **자리별 집행은 census
    #    천장**(`test_unguarded_mutation_count...`)이 한다. 잔여 4곳이 raw 로 남아 있으므로
    #    수리한 자리가 raw 로 되돌아가면 그 `(파일, metric)` 개수가 4를 넘어 red 가 된다.
    (
        "backend/src/tasks/live_signal.py",
        "_async_dispatch_event",
        "qb_live_signal_dispatch_total",
        "★발주 outbox 종결 7곳 — flat 청산 거부가 집행으로 뒤집히고(H8), "
        "kill-switch·도메인 거절의 타입이 소실돼 무재시도 분기를 건너뛴다 (H6·H5)",
    ),
    (
        "backend/src/tasks/live_signal.py",
        "dispatch_live_signal_event_task",
        "qb_live_signal_dispatch_total",
        "★재시도 소진 포기 기록 — 던지면 포기 반환이 사라지고 사유가 어디에도 안 남는다 (H6·H2)",
    ),
)

# ★공허화 방지 (codex G6 Standards MAJOR) — 목록이 비면 아래 두 테스트가 **반복할 항목이
#   없어 통과**한다. 그건 검증이 아니라 침묵이다.
assert _PROTECTED_SITES, "보호 목록이 비었다 — 이 테스트 파일은 아무것도 집행하지 않는다"


def _references_metric(node: ast.AST, metric: str) -> bool:
    """가드 인자 서브트리의 한 노드가 그 metric 을 가리키는가.

    세 형태를 덮는다:
    (a) ``record_metric_safely(qb_x.dec)`` — bound method 를 인자로 넘김
    (b) ``_count_safely(qb_x, ...)`` — counter 자체를 인자로 넘김
    (c) ``record_metric_safely(lambda: qb_x.labels(...).inc())`` — lambda 안 체인
    """
    if (
        isinstance(node, ast.Attribute)
        and node.attr in _MUTATION_METHODS
        and isinstance(node.value, ast.Name)
        and node.value.id == metric
    ):
        return True
    if isinstance(node, ast.Name) and node.id == metric:
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _metric_name(node.func.value) == metric
    )


def _guarded_metric_mentions(tree: ast.Module, function_name: str, metric: str) -> int:
    """해당 함수 안에서 그 metric 이 **가드의 인자로 구조적으로** 들어간 횟수.

    ★1차 구현은 `metric in ast.unparse(call)` 이라는 **문자열 포함**이었다 (2026-08-02 codex G6
    Standards MAJOR). 그러면 같은 이름이 주석·다른 인자에 스치기만 해도 통과하고, 같은 함수의
    **다른** mutation 을 감싸 놓고 목표 자리를 raw 로 되돌려도 통과한다. ⇒ AST 로 본다:
    가드 호출의 인자 서브트리 안에서 그 metric 을 뿌리로 하는 mutation/labels 노드를 찾는다.
    """
    found = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            name = (
                inner.func.id
                if isinstance(inner.func, ast.Name)
                else getattr(inner.func, "attr", None)
            )
            if name not in _GUARD_FUNCTIONS:
                continue
            for argument in list(inner.args) + [kw.value for kw in inner.keywords]:
                found += sum(1 for sub in ast.walk(argument) if _references_metric(sub, metric))
    return found


def test_every_protected_site_is_actually_guarded() -> None:
    """동결한 보호 자리 각각에 **가드된** mutation 이 실재하는지 확인한다.

    ★★이 테스트가 집행하는 것과 하지 않는 것을 정확히 적는다 (2026-08-02, 내가 한 번 틀렸다).

    **하지 않는 것:** 「이 함수 안에 그 metric 의 가드 밖 mutation 이 0개」를 요구하지 **않는다.**
    처음엔 그렇게 썼다가 red 가 났다 — `_reconcile_conditional_entries` 안의
    `qb_live_conditional_guard_total` 은 **9곳**이고 이번 회차가 감싼 것은 그중 발주 직후 1곳뿐이다.
    `(파일, 함수, metric)` 삼중항은 **과선택한다.** zone 추론이 6/13/14 로 흔들린 것과 같은 병이다.

    **집행은 위 census 천장이 한다.** 보호 site 를 raw 로 되돌리면 그 `(파일, metric)` 개수가
    올라가 `test_unguarded_mutation_count_per_file_matches_record` 가 red 가 된다. 실측 확인됨.

    **이 테스트의 몫:** 가드가 통째로 사라지는 것(리팩터링·되돌림)을 잡고, **무엇을 왜 지키는지**를
    코드 안에 남긴다.
    """
    missing = [
        f"{path}::{function} 에 {metric} 의 가드된 mutation 이 없다 — {reason}"
        for path, function, metric, reason in _PROTECTED_SITES
        if _guarded_metric_mentions(
            {p.relative_to(_REPOSITORY_ROOT).as_posix(): t for p, t in _source_trees()}[path],
            function,
            metric,
        )
        == 0
    ]
    assert not missing, "\n".join(missing)


def test_protected_site_list_is_not_vacuous() -> None:
    """공허화 방지 — 함수가 사라지거나 가드가 통째로 빠지면 '0건이라 통과' 가 아니라 red."""
    trees = {path.relative_to(_REPOSITORY_ROOT).as_posix(): tree for path, tree in _source_trees()}
    problems: list[str] = []
    for path, function, metric, _reason in _PROTECTED_SITES:
        tree = trees.get(path)
        if tree is None:
            problems.append(f"{path} 가 없다 — 보호 목록을 갱신해라")
            continue
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if function not in names:
            problems.append(f"{path}::{function} 가 없다 (rename?) — 보호 목록을 갱신해라")
            continue
        if _guarded_metric_mentions(tree, function, metric) == 0:
            problems.append(
                f"{path}::{function} 에 {metric} 의 **가드된** mutation 이 0개다 — "
                "자리가 비었으면 통과가 아니라 갱신 대상이다"
            )
    assert not problems, "\n".join(problems)
