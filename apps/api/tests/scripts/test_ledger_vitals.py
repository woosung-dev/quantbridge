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
        ["bash", str(SCRIPT), "--status-file", str(status_file), "--backlog-file", str(backlog_file)],
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
    result = run(_status_with_zero_table("`다음 행동 =` 는 인용이다. 다음 행동 = 현재 것"), "", tmp_path)

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


def test_zero_table_allows_three_rows_and_rejects_two(tmp_path: Path) -> None:
    """⓪ 표의 데이터 세 행은 통과하고, 두 행은 ② 위반으로 실패한다."""
    allowed = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(3)}"), "", tmp_path)
    rejected = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(2)}"), "", tmp_path)

    assert allowed.returncode == 0
    assert "⓪ 행=3" in allowed.stdout
    assert rejected.returncode == 1
    assert "✗ ②" in rejected.stdout
    assert "2개" in rejected.stdout


def test_zero_table_header_and_separator_are_not_data_rows(tmp_path: Path) -> None:
    """머리행과 구분행은 데이터가 아니므로 데이터 두 행만 있으면 실패한다."""
    result = run(_status_with_next_action(f"### ⓪ 다음 후보\n{_pipe_table(2)}"), "", tmp_path)

    assert result.returncode == 1
    assert "✗ ②" in result.stdout
    assert "2개" in result.stdout


def test_table_outside_zero_heading_does_not_count(tmp_path: Path) -> None:
    """⓪가 아닌 헤딩 아래 표는 다음 후보 정족수에 포함되지 않는다."""
    result = run(_status_with_next_action(f"### 다른 표\n{_pipe_table(3)}"), "", tmp_path)

    assert result.returncode == 1
    assert "✗ ②" in result.stdout
    assert "0개" in result.stdout
