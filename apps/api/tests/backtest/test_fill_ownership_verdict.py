"""`scripts/fill_ownership_verdict.py` 계약 시험 (Evaluator 소유 — 구현을 보지 않고 씀).

계약(CONTROL 동결)만 보고 쓴 시험이다. 픽스처는 **손으로 만든 prometheus 텍스트**이고
서버 실측값을 박지 않는다 — 창이 바뀌어도 red 가 나면 안 된다.

★stdout(사람용 표)은 **한 줄도 단언하지 않는다.** 표의 소수점 자리수가 4→6 으로 바뀌어도
이 시험은 green 이어야 한다(음성 대조 N). 판정은 오직 `--out` JSON 으로 한다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPT = BACKEND_DIR / "scripts" / "fill_ownership_verdict.py"

METRIC = "qb_live_conditional_fill_ownership_total"

NUMERATOR_LABELS = {"agree"}
DENOMINATOR_LABELS = {"agree", "engine_only_suppressed", "ledger_only_adopted"}
EXCLUDED_LABELS = {
    "ledger_only_orphan",
    "ledger_fill_out_of_window",
    "ledger_unreadable_fallback",
}

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(),
    reason=(
        "scripts/fill_ownership_verdict.py 미구현 — 파일이 생기면 자동으로 켜진다. "
        "ImportError 로 red 를 만드는 것은 판별력 0이라 skip 으로 처리한다."
    ),
)


def _prom_text(counts: dict[str, Any], *, extra_lines: tuple[str, ...] = ()) -> str:
    """`generate_latest()` 원문을 흉내 낸 텍스트.

    - 주석(`#`) 줄을 포함한다.
    - 같은 `outcome` 라벨을 쓰는 **무관한 family** 를 하나 섞어, 파서가 family 이름으로
      거르는지 본다(라벨만 보고 긁으면 값이 오염된다).
    """
    lines = [
        "# HELP qb_unrelated_counter_total 무관한 family — 같은 라벨 키를 쓴다",
        "# TYPE qb_unrelated_counter_total counter",
        'qb_unrelated_counter_total{outcome="agree"} 9999.0',
        f"# HELP {METRIC} conditional fill ownership outcome",
        f"# TYPE {METRIC} counter",
    ]
    for label, value in counts.items():
        lines.append(f'{METRIC}{{outcome="{label}"}} {value}')
    lines.extend(extra_lines)
    return "\n".join(lines) + "\n"


def _run(
    tmp_path: Path,
    t0_counts: dict[str, Any],
    t1_counts: dict[str, Any],
    *,
    t0_at: str = "2026-08-07T00:00:00Z",
    t1_at: str = "2026-08-07T12:00:00Z",
    t0_extra: tuple[str, ...] = (),
    t1_extra: tuple[str, ...] = (),
    t0_raw: str | None = None,
    t1_raw: str | None = None,
    t0_path_override: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    t0 = tmp_path / "t0.prom"
    t1 = tmp_path / "t1.prom"
    out = tmp_path / "verdict.json"
    t0.write_text(t0_raw if t0_raw is not None else _prom_text(t0_counts, extra_lines=t0_extra))
    t1.write_text(t1_raw if t1_raw is not None else _prom_text(t1_counts, extra_lines=t1_extra))
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--t0",
            str(t0_path_override if t0_path_override is not None else t0),
            "--t0-at",
            t0_at,
            "--t1",
            str(t1),
            "--t1-at",
            t1_at,
            "--out",
            str(out),
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    return proc, out


def _verdict(
    tmp_path: Path, t0_counts: dict[str, Any], t1_counts: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    """정상 처리 경로 — exit 0 을 요구하고 `--out` JSON 을 돌려준다."""
    proc, out = _run(tmp_path, t0_counts, t1_counts, **kwargs)
    assert proc.returncode == 0, (
        f"정상 입력인데 exit={proc.returncode} (계약: 정상 처리는 항상 0).\nstderr:\n{proc.stderr}"
    )
    assert out.exists(), f"--out 파일이 없다: {out}\nstderr:\n{proc.stderr}"
    return json.loads(out.read_text())


def _zero_all() -> dict[str, float]:
    return dict.fromkeys(sorted(DENOMINATOR_LABELS | EXCLUDED_LABELS | {"other"}), 0.0)


def test_denominator_excludes_orphan_out_of_window_and_unreadable(tmp_path: Path) -> None:
    """분모는 3라벨뿐이고, 제외 3라벨은 `excluded` 에 **이유 문자열과 함께** 남는다."""
    t0 = _zero_all()
    t1 = {
        "agree": 40.0,
        "engine_only_suppressed": 6.0,
        "ledger_only_adopted": 4.0,
        # 아래 3종이 분모에 섞이면 D 가 50 이 아니라 650 이 된다.
        "ledger_only_orphan": 100.0,
        "ledger_fill_out_of_window": 200.0,
        "ledger_unreadable_fallback": 300.0,
        "other": 0.0,
    }
    doc = _verdict(tmp_path, t0, t1)

    assert doc["denominator"]["value"] == pytest.approx(50.0), (
        f"D 가 {doc['denominator']['value']} — 제외 3라벨(orphan/out_of_window/unreadable)이 "
        f"분모에 섞였다. 기대 50.0 = 40+6+4"
    )
    assert set(doc["denominator"]["labels"]) == DENOMINATOR_LABELS, (
        f"denominator.labels 가 {sorted(doc['denominator']['labels'])} — "
        f"기대 {sorted(DENOMINATOR_LABELS)}"
    )

    excluded = doc["excluded"]
    assert set(excluded) == EXCLUDED_LABELS, (
        f"excluded 키가 {sorted(excluded)} — 기대 {sorted(EXCLUDED_LABELS)}"
    )
    for label, expected_delta in (
        ("ledger_only_orphan", 100.0),
        ("ledger_fill_out_of_window", 200.0),
        ("ledger_unreadable_fallback", 300.0),
    ):
        assert excluded[label]["delta"] == pytest.approx(expected_delta), (
            f"excluded[{label}].delta 가 {excluded[label]['delta']} — 기대 {expected_delta}"
        )
        reason = excluded[label].get("reason")
        assert isinstance(reason, str) and reason.strip(), (
            f"excluded[{label}].reason 이 비었다 — 제외 라벨은 **왜 제외했는지**를 "
            f"문자열로 남겨야 한다 (got {reason!r})"
        )


def test_numerator_is_agree_only(tmp_path: Path) -> None:
    """분자는 Δagree 뿐이다 — 분모 라벨을 하나라도 더하면 값이 달라진다."""
    t0 = _zero_all()
    t1 = {**_zero_all(), "agree": 33.0, "engine_only_suppressed": 7.0, "ledger_only_adopted": 5.0}
    doc = _verdict(tmp_path, t0, t1)

    assert doc["numerator"]["value"] == pytest.approx(33.0), (
        f"N 이 {doc['numerator']['value']} — 기대 33.0(Δagree). "
        f"engine_only_suppressed/ledger_only_adopted 를 분자에 더했을 가능성"
    )
    assert set(doc["numerator"]["labels"]) == NUMERATOR_LABELS, (
        f"numerator.labels 가 {sorted(doc['numerator']['labels'])} — 기대 ['agree']"
    )


def test_uses_t1_minus_t0_diff_not_absolute(tmp_path: Path) -> None:
    """★T0 가 0 이 **아닌** 픽스처. 절대값(=T1 그대로) 구현이면 반드시 깨진다."""
    t0 = {
        **_zero_all(),
        "agree": 100.0,
        "engine_only_suppressed": 10.0,
        "ledger_only_adopted": 20.0,
    }
    t1 = {
        **_zero_all(),
        "agree": 140.0,
        "engine_only_suppressed": 15.0,
        "ledger_only_adopted": 25.0,
    }
    doc = _verdict(tmp_path, t0, t1)

    # 차분: N=40, D=50, A=0.8 / 절대값 구현: N=140, D=180, A≈0.7778
    assert doc["delta"]["agree"] == pytest.approx(40.0), (
        f"delta[agree] 가 {doc['delta']['agree']} — 기대 40.0 (=140-100). "
        f"140.0 이면 T1 절대값을 그대로 쓴 것이다"
    )
    assert doc["numerator"]["value"] == pytest.approx(40.0), (
        f"N 이 {doc['numerator']['value']} — 기대 40.0. 140.0 이면 절대값 구현"
    )
    assert doc["denominator"]["value"] == pytest.approx(50.0), (
        f"D 가 {doc['denominator']['value']} — 기대 50.0. 180.0 이면 절대값 구현"
    )
    assert doc["verdict"] == "measured", f"verdict={doc['verdict']} reason={doc['verdict_reason']}"
    assert doc["agreement_rate"] == pytest.approx(0.8), (
        f"A 가 {doc['agreement_rate']} — 기대 0.8. 0.7778 이면 절대값 구현"
    )

    # raw 는 두 시점을 **그대로** 반향해야 한다 (차분만 남기고 버리면 재검산이 불가능).
    assert doc["raw"]["t0"]["agree"] == pytest.approx(100.0), (
        f"raw.t0 반향 실패: {doc['raw']['t0']}"
    )
    assert doc["raw"]["t1"]["agree"] == pytest.approx(140.0), (
        f"raw.t1 반향 실패: {doc['raw']['t1']}"
    )


def test_negative_delta_yields_held_counter_reset(tmp_path: Path) -> None:
    """게이트 1 — 어떤 라벨이든 Δ<0 이면 `held` / counter_reset."""
    t0 = {
        **_zero_all(),
        "agree": 100.0,
        "engine_only_suppressed": 40.0,
        "ledger_only_adopted": 40.0,
    }
    # agree 만 줄었다(프로세스 재기동). 나머지는 늘어서 D 는 문턱을 넘는다.
    t1 = {**_zero_all(), "agree": 90.0, "engine_only_suppressed": 80.0, "ledger_only_adopted": 80.0}
    doc = _verdict(tmp_path, t0, t1)

    assert doc["verdict"] == "held", (
        f"Δagree = -10 인데 verdict={doc['verdict']} — counter reset 을 못 잡았다. "
        f"reason={doc['verdict_reason']!r}"
    )
    assert "counter_reset" in doc["verdict_reason"], (
        f"verdict_reason={doc['verdict_reason']!r} — 'counter_reset' 키워드가 없다"
    )
    assert doc["agreement_rate"] is None, (
        f"verdict != measured 인데 agreement_rate={doc['agreement_rate']} — null 이어야 한다"
    )
    for key, value in doc["breakdown"].items():
        assert value is None, (
            f"verdict != measured 인데 breakdown[{key}]={value} — null 이어야 한다"
        )


def test_unknown_label_yields_held(tmp_path: Path) -> None:
    """게이트 2 — `other` 증가 **와** 7종 밖 라벨, **둘 다** held 여야 한다."""
    base_t0 = _zero_all()
    base_t1 = {
        **_zero_all(),
        "agree": 60.0,
        "engine_only_suppressed": 20.0,
        "ledger_only_adopted": 20.0,
    }

    # (a) other 가 늘었다 — D=100 이라 게이트 3 과 헷갈릴 여지가 없다.
    doc_other = _verdict(tmp_path / "a", {**base_t0}, {**base_t1, "other": 3.0})
    assert doc_other["verdict"] == "held", (
        f"Δother=3 인데 verdict={doc_other['verdict']} — 게이트 2 미발화. "
        f"reason={doc_other['verdict_reason']!r}"
    )
    assert "unknown_label" in doc_other["verdict_reason"], (
        f"verdict_reason={doc_other['verdict_reason']!r} — 'unknown_label' 키워드가 없다"
    )
    assert doc_other["agreement_rate"] is None, "held 인데 agreement_rate 가 null 이 아니다"

    # (b) 알려진 7종 밖 라벨이 원문에 있다 (값이 안 변해도 held).
    rogue = f'{METRIC}{{outcome="ledger_only_shrugged"}} 1.0'
    doc_rogue = _verdict(tmp_path / "b", {**base_t0}, {**base_t1}, t1_extra=(rogue,))
    assert doc_rogue["verdict"] == "held", (
        f"7종 밖 라벨 'ledger_only_shrugged' 가 원문에 있는데 verdict={doc_rogue['verdict']} — "
        f"모르는 라벨을 조용히 무시했다. reason={doc_rogue['verdict_reason']!r}"
    )
    assert "unknown_label" in doc_rogue["verdict_reason"], (
        f"verdict_reason={doc_rogue['verdict_reason']!r} — 'unknown_label' 키워드가 없다"
    )


def test_denominator_below_30_yields_undecidable(tmp_path: Path) -> None:
    """게이트 3 — 경계 2건. D=29 는 undecidable, D=30 은 measured."""
    t0 = _zero_all()

    doc_29 = _verdict(
        tmp_path / "d29",
        {**t0},
        {**_zero_all(), "agree": 20.0, "engine_only_suppressed": 5.0, "ledger_only_adopted": 4.0},
    )
    assert doc_29["denominator"]["value"] == pytest.approx(29.0), (
        f"픽스처 D 가 {doc_29['denominator']['value']} — 29.0 이어야 경계를 잰다"
    )
    assert doc_29["verdict"] == "undecidable", (
        f"D=29 인데 verdict={doc_29['verdict']} — 문턱 미만은 undecidable 이어야 한다. "
        f"reason={doc_29['verdict_reason']!r}"
    )
    assert "sample_below_threshold" in doc_29["verdict_reason"], (
        f"verdict_reason={doc_29['verdict_reason']!r} — 'sample_below_threshold' 키워드가 없다"
    )
    assert doc_29["agreement_rate"] is None, "undecidable 인데 agreement_rate 가 null 이 아니다"

    doc_30 = _verdict(
        tmp_path / "d30",
        {**t0},
        {**_zero_all(), "agree": 21.0, "engine_only_suppressed": 5.0, "ledger_only_adopted": 4.0},
    )
    assert doc_30["denominator"]["value"] == pytest.approx(30.0), (
        f"픽스처 D 가 {doc_30['denominator']['value']} — 30.0 이어야 경계를 잰다"
    )
    assert doc_30["verdict"] == "measured", (
        f"D=30 인데 verdict={doc_30['verdict']} — 문턱은 '30 미만'이지 '30 이하'가 아니다. "
        f"reason={doc_30['verdict_reason']!r}"
    )
    assert doc_30["agreement_rate"] is not None, "measured 인데 agreement_rate 가 null 이다"

    assert doc_30["thresholds"]["min_denominator"] == 30, (
        f"thresholds.min_denominator={doc_30['thresholds']['min_denominator']} — 계약값 30"
    )


def test_measured_reports_rate_and_type_a_b_breakdown(tmp_path: Path) -> None:
    """게이트 4 — A · 형A · 형B 를 전부 보고한다."""
    t0 = _zero_all()
    t1 = {**_zero_all(), "agree": 60.0, "engine_only_suppressed": 30.0, "ledger_only_adopted": 10.0}
    doc = _verdict(tmp_path, t0, t1)

    assert doc["verdict"] == "measured", (
        f"verdict={doc['verdict']} reason={doc['verdict_reason']!r} — D=100 이라 measured 여야 한다"
    )
    assert doc["verdict_reason"] == "ok" or "ok" in doc["verdict_reason"], (
        f"measured 의 reason 이 {doc['verdict_reason']!r} — 계약 키워드 'ok'"
    )
    assert doc["agreement_rate"] == pytest.approx(0.6), (
        f"A={doc['agreement_rate']} — 기대 0.6 (=60/100)"
    )
    assert doc["breakdown"]["type_a_engine_ahead"] == pytest.approx(0.3), (
        f"형A={doc['breakdown']['type_a_engine_ahead']} — 기대 0.3 "
        f"(=Δengine_only_suppressed/D=30/100)"
    )
    assert doc["breakdown"]["type_b_ledger_ahead"] == pytest.approx(0.1), (
        f"형B={doc['breakdown']['type_b_ledger_ahead']} — 기대 0.1 (=Δledger_only_adopted/D=10/100)"
    )


def test_missing_input_file_exits_2_and_verdict_never_changes_exit_code(tmp_path: Path) -> None:
    """exit code 계약 — 오류만 2, 판정 결과는 exit code 를 **절대** 바꾸지 않는다."""
    t1_ok = {
        **_zero_all(),
        "agree": 60.0,
        "engine_only_suppressed": 30.0,
        "ledger_only_adopted": 10.0,
    }

    # (1) 입력 파일 부재 → 2, 그리고 --out 을 만들지 않는다.
    proc_missing, out_missing = _run(
        tmp_path / "missing",
        _zero_all(),
        t1_ok,
        t0_path_override=tmp_path / "missing" / "nope.prom",
    )
    assert proc_missing.returncode == 2, (
        f"입력 파일 부재인데 exit={proc_missing.returncode} — 계약 2.\nstderr:\n{proc_missing.stderr}"
    )
    assert not out_missing.exists(), (
        "입력이 없는데 --out 을 썼다 — 실패 시 판정 파일을 남기면 낡은 판정이 통과로 읽힌다"
    )

    # (2) counter family 부재 → 2
    proc_no_family, _ = _run(
        tmp_path / "nofamily",
        _zero_all(),
        t1_ok,
        t0_raw="# TYPE qb_other_total counter\nqb_other_total 1.0\n",
    )
    assert proc_no_family.returncode == 2, (
        f"counter family 부재인데 exit={proc_no_family.returncode} — 계약 2.\n"
        f"stderr:\n{proc_no_family.stderr}"
    )

    # (3) 파싱 실패 → 2
    proc_garbage, _ = _run(
        tmp_path / "garbage",
        _zero_all(),
        t1_ok,
        t0_raw="이건 prometheus 텍스트가 아니다 <<<>>>\n{{{\n",
    )
    assert proc_garbage.returncode == 2, (
        f"파싱 실패인데 exit={proc_garbage.returncode} — 계약 2.\nstderr:\n{proc_garbage.stderr}"
    )

    # (4) ★판정 3종 전부 exit 0 — verdict 가 exit code 를 바꾸면 안 된다.
    cases: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        (
            "measured",
            _zero_all(),
            {
                **_zero_all(),
                "agree": 60.0,
                "engine_only_suppressed": 30.0,
                "ledger_only_adopted": 10.0,
            },
        ),
        (
            "undecidable",
            _zero_all(),
            {
                **_zero_all(),
                "agree": 1.0,
                "engine_only_suppressed": 1.0,
                "ledger_only_adopted": 1.0,
            },
        ),
        (
            "held",
            {**_zero_all(), "agree": 100.0},
            {
                **_zero_all(),
                "agree": 90.0,
                "engine_only_suppressed": 80.0,
                "ledger_only_adopted": 80.0,
            },
        ),
    ]
    seen: set[str] = set()
    for name, t0_counts, t1_counts in cases:
        proc, out = _run(tmp_path / f"exit_{name}", t0_counts, t1_counts)
        assert proc.returncode == 0, (
            f"verdict={name} 인데 exit={proc.returncode} — 판정 결과는 exit code 를 바꾸지 않는다.\n"
            f"stderr:\n{proc.stderr}"
        )
        seen.add(json.loads(out.read_text())["verdict"])
    assert seen == {"measured", "undecidable", "held"}, (
        f"판정 3종을 다 밟지 못했다: {sorted(seen)} — 이 시험은 3종 전부가 exit 0 임을 재야 한다"
    )


def test_window_timestamps_echoed_iso8601(tmp_path: Path) -> None:
    """`window.t0_at`/`t1_at` 은 입력 문자열 **그대로** 반향한다."""
    t0_at = "2026-08-07T01:15:00Z"
    t1_at = "2026-08-07T13:45:00Z"
    doc = _verdict(
        tmp_path,
        _zero_all(),
        {**_zero_all(), "agree": 60.0, "engine_only_suppressed": 30.0, "ledger_only_adopted": 10.0},
        t0_at=t0_at,
        t1_at=t1_at,
    )
    assert doc["window"]["t0_at"] == t0_at, (
        f"window.t0_at={doc['window']['t0_at']!r} — 입력 {t0_at!r} 을 그대로 반향해야 한다 "
        f"(재포맷하면 원본 창을 잃는다)"
    )
    assert doc["window"]["t1_at"] == t1_at, (
        f"window.t1_at={doc['window']['t1_at']!r} — 입력 {t1_at!r} 을 그대로 반향해야 한다"
    )
    # elapsed_hours 의 계산식은 계약에 없다. 이름이 곧 정의라고 읽어 두 시각의 차로만 본다.
    assert doc["window"]["elapsed_hours"] == pytest.approx(12.5, abs=0.01), (
        f"elapsed_hours={doc['window']['elapsed_hours']} — 기대 12.5 (01:15 → 13:45)"
    )


def test_gate_precedence_negative_delta_beats_unknown_label(tmp_path: Path) -> None:
    """★게이트 **순서** — 1(counter reset)과 2(unknown label)가 동시에 참이면 1이 이긴다."""
    t0 = {
        **_zero_all(),
        "agree": 100.0,
        "engine_only_suppressed": 40.0,
        "ledger_only_adopted": 40.0,
    }
    t1 = {
        **_zero_all(),
        "agree": 90.0,  # Δ<0 → 게이트 1
        "engine_only_suppressed": 80.0,
        "ledger_only_adopted": 80.0,
        "other": 5.0,  # Δother>0 → 게이트 2
    }
    doc = _verdict(tmp_path, t0, t1, t1_extra=(f'{METRIC}{{outcome="ledger_only_shrugged"}} 2.0',))

    assert doc["verdict"] == "held", f"verdict={doc['verdict']} — 두 게이트 다 held 여야 한다"
    assert "counter_reset" in doc["verdict_reason"], (
        f"verdict_reason={doc['verdict_reason']!r} — 게이트 1(counter_reset)이 게이트 2보다 "
        f"먼저 평가돼야 한다. 'unknown_label' 만 나왔다면 순서가 뒤집힌 것이다"
    )
