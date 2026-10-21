"""체결 위상으로 판정하는 보유 경계. 봉 내부 체결 순서는 추측하지 않는다."""

from dataclasses import dataclass

from src.strategy.pine_v2.strategy_state import FillPhase


@dataclass(frozen=True)
class HoldingPeriod:
    entry_bar: int
    exit_bar: int | None
    entry_phase: FillPhase
    exit_phase: FillPhase

    def full_bars(self, last_bar: int) -> range:
        """확실히 전부 보유한 봉만 반환한다. 부분 봉은 체결가로 별도 계산한다."""
        start = self.entry_bar + (self.entry_phase != "bar_open")
        stop = (
            last_bar + 1
            if self.exit_bar is None
            else self.exit_bar + (self.exit_phase == "bar_close")
        )
        return range(start, max(start, stop))

    def holds_at(self, bar: int) -> bool | None:
        """봉 시가부터 종가 직전 정산의 보유 여부. 내부 체결 경계는 미상이다.

        시가 진입은 포함하고 시가 청산은 제외한다. 종가 체결은 해당 봉의
        정산 뒤에 발생한다. 봉 내부의 정확한 시각을 모르면 None을 반환한다.
        """
        if bar < self.entry_bar or (self.exit_bar is not None and bar > self.exit_bar):
            return False
        if bar == self.entry_bar:
            if self.entry_phase == "bar_close":
                return False
            if self.entry_phase == "intrabar_unknown":
                return None
        if bar == self.exit_bar:
            if self.exit_phase == "bar_open":
                return False
            if self.exit_phase == "intrabar_unknown":
                return None
        return True
