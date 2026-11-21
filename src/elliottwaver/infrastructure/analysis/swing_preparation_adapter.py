"""Deterministic pivot-confirmation based swing preparation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from elliottwaver.application import CandleToSwingPreparationPort, TimeframeAnalysisRequest
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Pivot, PivotType, Price, Swing

if TYPE_CHECKING:
    from elliottwaver.domain.market import Candle


_MIN_PIVOTS_FOR_SWING = 2


@dataclass(frozen=True, slots=True)
class PivotSwingPreparationAdapter(CandleToSwingPreparationPort):
    """Prepare swings from confirmed pivots using deterministic tie-break rules.

    Confirmation:
    - A pivot is confirmed only when both left and right confirmation candles exist.
    - Window winners use deterministic tie-breaks for equal highs/lows: the leftmost candle wins.

    Normalization:
    - Pivots are reduced to an alternating sequence.
    - Consecutive highs keep the highest pivot (equal prices keep earlier timestamp).
    - Consecutive lows keep the lowest pivot (equal prices keep earlier timestamp).
    """

    left_confirmation_candles: int = 1
    right_confirmation_candles: int = 1

    def __post_init__(self) -> None:
        if self.left_confirmation_candles < 1:
            message = "left_confirmation_candles must be >= 1"
            raise ValueError(message)
        if self.right_confirmation_candles < 1:
            message = "right_confirmation_candles must be >= 1"
            raise ValueError(message)

    def prepare_swings(
        self,
        candles: tuple[Candle, ...],
        request: TimeframeAnalysisRequest,
    ) -> tuple[Swing, ...]:
        if len(candles) < self.left_confirmation_candles + self.right_confirmation_candles + 1:
            return ()

        confirmed = _confirmed_pivots(
            candles,
            request=request,
            left=self.left_confirmation_candles,
            right=self.right_confirmation_candles,
        )
        normalized = _normalize_pivots(confirmed)
        return _build_swings(normalized)


def _confirmed_pivots(
    candles: tuple[Candle, ...],
    *,
    request: TimeframeAnalysisRequest,
    left: int,
    right: int,
) -> tuple[Pivot, ...]:
    pivots: list[Pivot] = []
    last_index = len(candles) - right

    for index in range(left, last_index):
        current = candles[index]
        window_start = index - left
        window_end = index + right + 1
        window = candles[window_start:window_end]

        high_values = tuple(candle.high.value for candle in window)
        low_values = tuple(candle.low.value for candle in window)

        max_high = max(high_values)
        min_low = min(low_values)

        leftmost_high_offset = next(
            offset for offset, value in enumerate(high_values) if value == max_high
        )
        leftmost_low_offset = next(
            offset for offset, value in enumerate(low_values) if value == min_low
        )

        is_high = current.high.value == max_high and leftmost_high_offset == left
        is_low = current.low.value == min_low and leftmost_low_offset == left

        # Ambiguous flat candles that satisfy both directions are ignored.
        if is_high and is_low:
            continue

        if is_high:
            pivots.append(
                Pivot(
                    id=_pivot_id(current, PivotType.HIGH),
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    timestamp=current.opened_at,
                    price=Price.parse(current.high.value),
                    pivot_type=PivotType.HIGH,
                )
            )

        if is_low:
            pivots.append(
                Pivot(
                    id=_pivot_id(current, PivotType.LOW),
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    timestamp=current.opened_at,
                    price=Price.parse(current.low.value),
                    pivot_type=PivotType.LOW,
                )
            )

    return tuple(sorted(pivots, key=lambda pivot: pivot.timestamp))


def _normalize_pivots(pivots: tuple[Pivot, ...]) -> tuple[Pivot, ...]:
    if not pivots:
        return ()

    normalized: list[Pivot] = [pivots[0]]

    for pivot in pivots[1:]:
        previous = normalized[-1]

        if pivot.timestamp <= previous.timestamp:
            continue

        if pivot.pivot_type is previous.pivot_type:
            normalized[-1] = _pick_more_extreme(previous, pivot)
            continue

        if not _forms_valid_swing_pair(previous, pivot):
            continue

        normalized.append(pivot)

    return tuple(normalized)


def _pick_more_extreme(left: Pivot, right: Pivot) -> Pivot:
    if left.pivot_type is PivotType.HIGH:
        if right.price.value > left.price.value:
            return right
        return left

    if right.price.value < left.price.value:
        return right
    return left


def _forms_valid_swing_pair(start: Pivot, end: Pivot) -> bool:
    if start.pivot_type is PivotType.LOW and end.pivot_type is PivotType.HIGH:
        return end.price.value > start.price.value
    if start.pivot_type is PivotType.HIGH and end.pivot_type is PivotType.LOW:
        return end.price.value < start.price.value
    return False


def _build_swings(pivots: tuple[Pivot, ...]) -> tuple[Swing, ...]:
    if len(pivots) < _MIN_PIVOTS_FOR_SWING:
        return ()

    swings: list[Swing] = []
    for start, end in pairwise(pivots):
        swings.append(
            Swing(
                id=_swing_id(start, end),
                start_pivot=start,
                end_pivot=end,
            )
        )

    return tuple(swings)


def _pivot_id(candle: Candle, pivot_type: PivotType) -> EntityId:
    raw = (
        "pivot:"
        f"{candle.symbol.value}:"
        f"{candle.timeframe.value}:"
        f"{candle.opened_at.isoformat()}:"
        f"{pivot_type.value}"
    )
    return EntityId(value=uuid5(NAMESPACE_URL, raw))


def _swing_id(start_pivot: Pivot, end_pivot: Pivot) -> EntityId:
    raw = f"swing:{start_pivot.id}:{end_pivot.id}"
    return EntityId(value=uuid5(NAMESPACE_URL, raw))
