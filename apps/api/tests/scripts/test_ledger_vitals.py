"""원장 활력 ①·② 축의 awk 판정을 임시 원장으로 고정한다.

★이 테스트는 DB 픽스처를 쓰지 않는다. 실제 docs 원장 대신 argv 테스트 오버라이드를 쓴다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "ledger-vitals.sh"


def run(status_text: str, backlog_text: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """임시 원장만 대상으로 스크립트를 실행한다."""
    status_file = tmp_path / "status.md"
    backlog_file = tmp_path / "backlog.md"
    status_file.write_text(status_text, encoding="utf-8")
    backlog_file.write_text(backlog_text, encoding="utf-8")
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--status-file",
            str(status_file),
            "--backlog-file",
            str(backlog_file),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _status_with_zero_table(next_actions: str = "다음 행동 = 하나", rows: int = 3) -> str:
    """축 ①을 재는 동안 ②를 통과시키는 최소 status 본문을 만든다."""
    data_rows = "\n".join(f"| 후보 {number} |" for number in range(1, rows + 1))
    return f"""{next_actions}

### ⓪ 다음 후보
| 후보 |
| --- |
{data_rows}
"""


def _status_with_next_action(zero_section: str) -> str:
    """축 ②를 재는 동안 ①을 통과시키는 최소 status 본문을 만든다."""
    return f"""다음 행동 = 하나

{zero_section}
"""


def _pipe_table(rows: int) -> str:
    """머리행과 구분행을 포함한 파이프 표를 만든다."""
    data_rows = "\n".join(f"| 후보 {number} |" for number in range(1, rows + 1))
    return f"""| 후보 |
| --- |
{data_rows}"""


def test_next_action_allows_one_and_rejects_two(tmp_path: Path) -> None:
    """살아 있는 다음 행동 하나는 통과하고, 둘은 ① 위반으로 실패한다."""
    allowed = run(_status_with_zero_table(), "", tmp_path)
    rejected = run(_status_with_zero_table("다음 행동 = 하나\n다음 행동 = 둘"), "", tmp_path)

    assert allowed.returncode == 0
    assert "다음 행동=1" in allowed.stdout
    assert rejected.returncode == 1
    assert "✗ ①" in rejected.stdout
    assert "2개" in rejected.stdout


def test_next_action_inside_strikethrough_is_ignored(tmp_path: Path) -> None:
    """같은 줄의 취소선 안쪽 지시는 세지 않고, 살아 있는 한 개만 센다."""
    result = run(
        _status_with_zero_table("~~다음 행동 = 옛것~~ → 새 사실. 다음 행동 = 현재 것"),
        "",
        tmp_path,
    )

    assert result.returncode == 0
    assert "다음 행동=1" in result.stdout


def test_next_action_inside_inline_code_is_ignored(tmp_path: Path) -> None:
    """인라인 코드의 다음 행동 표기는 인용이므로 세지 않는다."""
    result = run(
        _status_with_zero_table("`다음 행동 =` 는 인용이다. 다음 행동 = 현재 것"), "", tmp_path
    )

    assert result.returncode == 0
    assert "다음 행동=1" in result.stdout


def test_next_action_inside_indented_and_quoted_fences_is_ignored(tmp_path: Path) -> None:
    """들여쓰기와 인용부 뒤의 코드펜스 안쪽 지시는 모두 세지 않는다."""
    next_actions = """  ```
다음 행동 = 들여쓴 코드
  ```
> ~~~
다음 행동 = 인용 코드
> ~~~
다음 행동 = 현재 것"""
    result = run(_status_with_zero_table(next_actions), "", tmp_path)

    assert result.returncode == 0
    assert "다음 행동=1" in result.stdout


def test_zero_table_allows_one_row_and_rejects_zero(tmp_path: Path) -> None:
    """⓪ 표의 데이터 한 행은 통과하고, 빈 표는 ② 위반으로 실패한다 (하한 ≥1 — 2026-08-25 사용자 결정)."""
    allowed = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(1)}"), "", tmp_path)
    rejected = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(0)}"), "", tmp_path)

    assert allowed.returncode == 0
    assert "⓪ 행=1" in allowed.stdout
    assert rejected.returncode == 1
    assert "✗ ②" in rejected.stdout
    assert "0개" in rejected.stdout


def test_zero_table_header_and_separator_are_not_data_rows(tmp_path: Path) -> None:
    """머리행과 구분행은 데이터가 아니므로 그 둘만 있는 표는 빈 표로 실패한다."""
    result = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(0)}"), "", tmp_path)

    assert result.returncode == 1
    assert "✗ ②" in result.stdout
    assert "0개" in result.stdout


def test_table_outside_zero_heading_does_not_count(tmp_path: Path) -> None:
    """⓪가 아닌 헤딩 아래 표는 다음 후보 정족수에 포함되지 않는다."""
    result = run(_status_with_next_action(f"### 다른 표\n{_pipe_table(3)}"), "", tmp_path)

    assert result.returncode == 1
    assert "✗ ②" in result.stdout
    assert "0개" in result.stdout


def test_resolved_backlog_section_fails_third_axis_with_its_id(tmp_path: Path) -> None:
    """RESOLVED 한 건은 ③만 실패시키며 BL 번호를 stdout에 남긴다."""
    result = run(
        _status_with_zero_table(),
        """### BL-101 역류
**상태:** RESOLVED
""",
        tmp_path,
    )

    assert result.returncode == 1
    assert "✗ ③" in result.stdout
    assert "1건" in result.stdout
    assert "BL-101" in result.stdout
    assert "✗ ①" not in result.stdout
    assert "✗ ②" not in result.stdout


def test_backlog_without_resolved_section_passes_third_axis(tmp_path: Path) -> None:
    """RESOLVED 판정 섹션이 없으면 세 축 모두 통과한다."""
    result = run(
        _status_with_zero_table(),
        """### BL-102 진행 중
**상태:** ACTIVE
""",
        tmp_path,
    )

    assert result.returncode == 0
    assert "✓ ledger-vitals 3축 통과" in result.stdout
    assert "다음 행동=1" in result.stdout
    assert "⓪ 행=3" in result.stdout
    assert "역류=0" in result.stdout


def test_partial_resolved_and_deferred_take_precedence_over_resolved(tmp_path: Path) -> None:
    """우선순위상 부분 RESOLVED와 미도래 DEFERRED는 역류가 아니다."""
    partial = run(
        _status_with_zero_table(),
        """### BL-103 부분 처리
**상태:** 부분 RESOLVED
""",
        tmp_path,
    )
    deferred = run(
        _status_with_zero_table(),
        """### BL-104 대기
**상태:** ⏳ **대기 (트리거 미도래)** RESOLVED
""",
        tmp_path,
    )

    assert partial.returncode == 0
    assert deferred.returncode == 0
    assert "역류=0" in partial.stdout
    assert "역류=0" in deferred.stdout


def test_lowercase_resolved_backlog_section_fails_third_axis(tmp_path: Path) -> None:
    """RESOLVED 대소문자는 무관하므로 소문자도 역류다."""
    result = run(
        _status_with_zero_table(),
        """### BL-105 소문자
**Status:** resolved
""",
        tmp_path,
    )

    assert result.returncode == 1
    assert "✗ ③" in result.stdout
    assert "BL-105" in result.stdout


def test_struck_status_line_does_not_consume_section_verdict_slot(tmp_path: Path) -> None:
    """취소선 상태줄은 제외되어 다음 유효 상태줄이 해당 섹션을 판정한다."""
    active_after_struck_resolved = run(
        _status_with_zero_table(),
        """### BL-106 철회 후 진행
**상태:** ~~RESOLVED~~
**상태:** ACTIVE
""",
        tmp_path,
    )
    resolved_after_struck_active = run(
        _status_with_zero_table(),
        """### BL-107 철회 후 종료
**상태:** ~~ACTIVE~~
**상태:** RESOLVED
""",
        tmp_path,
    )

    assert active_after_struck_resolved.returncode == 0
    assert resolved_after_struck_active.returncode == 1
    assert "BL-107" in resolved_after_struck_active.stdout


def test_each_section_is_counted_once_and_lines_outside_sections_are_ignored(
    tmp_path: Path,
) -> None:
    """③은 한 BL 섹션을 한 번만 세고 BL 헤딩 밖 상태줄은 보지 않는다."""
    result = run(
        _status_with_zero_table(),
        """**상태:** RESOLVED

### BL-108 중복 상태줄
**상태:** RESOLVED
**Status:** RESOLVED
""",
        tmp_path,
    )

    assert result.returncode == 1
    assert "✗ ③" in result.stdout
    assert "1건" in result.stdout
    assert "BL-108" in result.stdout


def test_third_axis_does_not_exclude_code_fences(tmp_path: Path) -> None:
    """③은 ①·②와 달리 코드펜스 안 상태줄도 현재 구현대로 판정한다."""
    result = run(
        _status_with_zero_table(),
        """### BL-109 코드펜스
```
**상태:** RESOLVED
```
""",
        tmp_path,
    )

    assert result.returncode == 1
    assert "✗ ③" in result.stdout
    assert "BL-109" in result.stdout


def test_missing_status_or_backlog_file_returns_rc_three(tmp_path: Path) -> None:
    """측정 대상 원장 하나라도 없으면 통과 대신 정확히 rc=3으로 중단한다."""
    status_file = tmp_path / "status.md"
    backlog_file = tmp_path / "backlog.md"
    status_file.write_text(_status_with_zero_table(), encoding="utf-8")
    backlog_file.write_text("", encoding="utf-8")

    missing_status = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--status-file",
            str(tmp_path / "missing-status.md"),
            "--backlog-file",
            str(backlog_file),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    missing_backlog = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--status-file",
            str(status_file),
            "--backlog-file",
            str(tmp_path / "missing-backlog.md"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert missing_status.returncode == 3
    assert missing_backlog.returncode == 3


def test_invalid_arguments_return_rc_one(tmp_path: Path) -> None:
    """알 수 없는 인자와 값 없는 플래그는 정확히 rc=1로 거부한다."""
    unknown_argument = subprocess.run(
        ["bash", str(SCRIPT), "--unknown"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    missing_value = subprocess.run(
        ["bash", str(SCRIPT), "--status-file"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert unknown_argument.returncode == 1
    assert "알 수 없는 인자" in unknown_argument.stderr
    assert missing_value.returncode == 1
    assert "값이 필요하다" in missing_value.stderr


def test_file_overrides_announce_test_mode_to_stderr(tmp_path: Path) -> None:
    """argv 원장 오버라이드는 집행 로그와 구분되는 test-mode 표기를 남긴다."""
    result = run(_status_with_zero_table(), "", tmp_path)

    assert result.returncode == 0
    assert "test-mode" in result.stderr
