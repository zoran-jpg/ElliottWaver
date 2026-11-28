"""Deterministic pivot-confirmation based swing preparation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from elliottwaver.application import CandleToSwingPreparationPort, TimeframeAnalysisRequest
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import (
    ConfirmationTimestampStatus,
    Pivot,
    PivotType,
    Price,
    Swing,
)

if TYPE_CHECKING:
    from elliottwaver.application.temporal_market_data import TemporalCandleRecord
    from elliottwaver.domain.market import Candle


_MIN_PIVOTS_FOR_SWING = 2


@dataclass(frozen=True, slots=True)
class _PivotSelectionEvent:
    pivot: Pivot
    selection_available_at: datetime


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

    def prepare_swings_causal(
        self,
        records: tuple[TemporalCandleRecord, ...],
        request: TimeframeAnalysisRequest,
        *,
        as_of: datetime,
    ) -> tuple[Swing, ...]:
        _validate_utc_datetime(as_of=as_of)

        if not records:
            return ()

        _validate_causal_records(records, request=request)

        confirmed_prefix = _confirmed_prefix(records, as_of=as_of)
        minimum_required = self.left_confirmation_candles + self.right_confirmation_candles + 1
        if len(confirmed_prefix) < minimum_required:
            return ()

        events = _confirmed_pivot_events(
            confirmed_prefix,
            request=request,
            left=self.left_confirmation_candles,
            right=self.right_confirmation_candles,
        )
        normalized, swing_confirmed_at = _normalize_pivot_events(events)
        return _build_swings_causal(normalized, swing_confirmed_at)


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


def _validate_utc_datetime(*, as_of: datetime) -> None:
    if as_of.tzinfo is None or as_of.tzinfo != UTC:
        message = "as_of must use the UTC timezone"
        raise DomainError(message)


def _validate_causal_records(
    records: tuple[TemporalCandleRecord, ...],
    *,
    request: TimeframeAnalysisRequest,
) -> None:
    previous_opened_at: datetime | None = None

    for record in records:
        candle = record.candle
        if candle.symbol != request.symbol:
            message = "records symbol must match request symbol"
            raise DomainError(message)

        if candle.timeframe != request.timeframe:
            message = "records timeframe must match request timeframe"
            raise DomainError(message)

        opened_at = candle.opened_at
        if previous_opened_at is not None and opened_at <= previous_opened_at:
            message = "records must be strictly chronological and unique by opened_at"
            raise DomainError(message)

        previous_opened_at = opened_at


def _confirmed_prefix(
    records: tuple[TemporalCandleRecord, ...],
    *,
    as_of: datetime,
) -> tuple[TemporalCandleRecord, ...]:
    prefix: list[TemporalCandleRecord] = []

    for record in records:
        status = record.temporal_semantics.confirmation_status(as_of=as_of)
        if status is not ConfirmationTimestampStatus.CONFIRMED:
            break
        prefix.append(record)

    return tuple(prefix)


def _confirmed_pivot_events(
    records: tuple[TemporalCandleRecord, ...],
    *,
    request: TimeframeAnalysisRequest,
    left: int,
    right: int,
) -> tuple[_PivotSelectionEvent, ...]:
    events: list[_PivotSelectionEvent] = []
    candles = tuple(record.candle for record in records)

    cumulative_available_at: list[datetime] = []
    running_max_available_at: datetime | None = None
    for record in records:
        available_at = record.temporal_semantics.available_at
        if available_at is None:
            message = "confirmed prefix records must have available_at"
            raise DomainError(message)

        if running_max_available_at is None or available_at > running_max_available_at:
            running_max_available_at = available_at
        cumulative_available_at.append(running_max_available_at)

    last_index = len(candles) - right
    for index in range(left, last_index):
        current = candles[index]
        window_start = index - left
        window_end = index + right + 1

        window_candles = candles[window_start:window_end]
        window_records = records[window_start:window_end]

        high_values = tuple(candle.high.value for candle in window_candles)
        low_values = tuple(candle.low.value for candle in window_candles)

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

        if is_high and is_low:
            continue

        window_available_candidates: list[datetime] = []
        for record in window_records:
            available_at = record.temporal_semantics.available_at
            if available_at is None:
                message = "window availability must be known for confirmed pivots"
                raise DomainError(message)
            window_available_candidates.append(available_at)
        window_available_at = max(window_available_candidates)

        selection_available_at = cumulative_available_at[window_end - 1]

        if is_high:
            events.append(
                _PivotSelectionEvent(
                    pivot=Pivot(
                        id=_pivot_id(current, PivotType.HIGH),
                        symbol=request.symbol,
                        timeframe=request.timeframe,
                        timestamp=current.opened_at,
                        price=Price.parse(current.high.value),
                        pivot_type=PivotType.HIGH,
                        confirmed_at=window_available_at,
                    ),
                    selection_available_at=selection_available_at,
                )
            )

        if is_low:
            events.append(
                _PivotSelectionEvent(
                    pivot=Pivot(
                        id=_pivot_id(current, PivotType.LOW),
                        symbol=request.symbol,
                        timeframe=request.timeframe,
                        timestamp=current.opened_at,
                        price=Price.parse(current.low.value),
                        pivot_type=PivotType.LOW,
                        confirmed_at=window_available_at,
                    ),
                    selection_available_at=selection_available_at,
                )
            )

    return tuple(events)


def _normalize_pivot_events(
    events: tuple[_PivotSelectionEvent, ...],
) -> tuple[tuple[_PivotSelectionEvent, ...], dict[tuple[EntityId, EntityId], datetime]]:
    if not events:
        return (), {}

    normalized: list[_PivotSelectionEvent] = [events[0]]
    swing_confirmed_at: dict[tuple[EntityId, EntityId], datetime] = {}

    for event in events[1:]:
        previous = normalized[-1]

        if event.pivot.timestamp <= previous.pivot.timestamp:
            continue

        if event.pivot.pivot_type is previous.pivot.pivot_type:
            selected = _pick_more_extreme(previous.pivot, event.pivot)
            if selected is previous.pivot:
                continue

            normalized[-1] = event
            if len(normalized) >= _MIN_PIVOTS_FOR_SWING:
                predecessor = normalized[-2]
                old_key = (predecessor.pivot.id, previous.pivot.id)
                swing_confirmed_at.pop(old_key, None)

                new_key = (predecessor.pivot.id, event.pivot.id)
                swing_confirmed_at[new_key] = _resolve_swing_confirmed_at(
                    predecessor,
                    event,
                )
            continue

        if not _forms_valid_swing_pair(previous.pivot, event.pivot):
            continue

        normalized.append(event)
        edge_key = (previous.pivot.id, event.pivot.id)
        if edge_key not in swing_confirmed_at:
            swing_confirmed_at[edge_key] = _resolve_swing_confirmed_at(previous, event)

    return tuple(normalized), swing_confirmed_at


def _resolve_swing_confirmed_at(
    start: _PivotSelectionEvent,
    end: _PivotSelectionEvent,
) -> datetime:
    start_confirmed_at = start.pivot.confirmed_at
    end_confirmed_at = end.pivot.confirmed_at
    if start_confirmed_at is None or end_confirmed_at is None:
        message = "causal swing requires confirmed start and end pivots"
        raise DomainError(message)

    return max(end.selection_available_at, start_confirmed_at, end_confirmed_at)


def _build_swings_causal(
    events: tuple[_PivotSelectionEvent, ...],
    swing_confirmed_at: dict[tuple[EntityId, EntityId], datetime],
) -> tuple[Swing, ...]:
    if len(events) < _MIN_PIVOTS_FOR_SWING:
        return ()

    swings: list[Swing] = []
    for start, end in pairwise(events):
        key = (start.pivot.id, end.pivot.id)
        confirmed_at = swing_confirmed_at.get(key)
        if confirmed_at is None:
            confirmed_at = _resolve_swing_confirmed_at(start, end)

        swings.append(
            Swing(
                id=_swing_id(start.pivot, end.pivot),
                start_pivot=start.pivot,
                end_pivot=end.pivot,
                confirmed_at=confirmed_at,
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
