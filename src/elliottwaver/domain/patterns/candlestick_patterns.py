"""Deterministic candlestick pattern detection based on completed OHLC candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import CandleTemporalSemantics, ConfirmationTimestampStatus

if TYPE_CHECKING:
    from elliottwaver.domain.market import Candle

_ZERO = Decimal("0")
_ONE = Decimal("1")
_FOUR_CANDLE_PATTERN_OFFSET = 3
_UTC_OFFSET = UTC.utcoffset(None)


class CandlestickPatternType(StrEnum):
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    TWEEZER_BOTTOM = "tweezer_bottom"
    TWEEZER_TOP = "tweezer_top"
    BULLISH_THREE_LINE_STRIKE = "bullish_three_line_strike"
    BEARISH_THREE_LINE_STRIKE = "bearish_three_line_strike"


class CandlestickPatternDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class CandlestickPatternContext(StrEnum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CandlestickPatternConfig:
    min_engulfing_body_factor: Decimal = Decimal("1.20")
    max_unfavorable_engulfing_wick_share: Decimal = Decimal("0.30")
    max_rejection_body_share: Decimal = Decimal("0.40")
    min_rejection_body_share: Decimal = Decimal("0.10")
    min_dominant_wick_share: Decimal = Decimal("0.50")
    max_opposite_wick_share: Decimal = Decimal("0.10")
    max_doji_body_share: Decimal = Decimal("0.10")
    min_tweezer_wick_share: Decimal = Decimal("0.50")
    tweezer_extreme_tolerance_share: Decimal = Decimal("0.10")
    context_window_size: int = 5

    def __post_init__(self) -> None:
        _validate_ratio(self.min_engulfing_body_factor, "min_engulfing_body_factor", minimum=_ONE)
        _validate_ratio(
            self.max_unfavorable_engulfing_wick_share,
            "max_unfavorable_engulfing_wick_share",
        )
        _validate_ratio(self.max_rejection_body_share, "max_rejection_body_share")
        _validate_ratio(self.min_rejection_body_share, "min_rejection_body_share")
        if self.max_rejection_body_share < self.min_rejection_body_share:
            message = "max_rejection_body_share must be >= min_rejection_body_share"
            raise DomainError(message)
        _validate_ratio(self.min_dominant_wick_share, "min_dominant_wick_share")
        _validate_ratio(self.max_opposite_wick_share, "max_opposite_wick_share")
        _validate_ratio(self.max_doji_body_share, "max_doji_body_share")
        _validate_ratio(self.min_tweezer_wick_share, "min_tweezer_wick_share")
        _validate_ratio(self.tweezer_extreme_tolerance_share, "tweezer_extreme_tolerance_share")
        if self.context_window_size <= 0:
            message = "context_window_size must be > 0"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class CandleGeometry:
    high: Decimal
    low: Decimal
    span: Decimal
    body: Decimal
    body_top: Decimal
    body_bottom: Decimal
    upper_wick: Decimal
    lower_wick: Decimal
    body_share: Decimal
    upper_wick_share: Decimal
    lower_wick_share: Decimal
    direction: CandlestickPatternDirection
    zero_span: bool


@dataclass(frozen=True, slots=True)
class CandlestickPattern:
    pattern_id: str
    pattern_type: CandlestickPatternType
    direction: CandlestickPatternDirection
    started_at: datetime
    ended_at: datetime
    confirmed_at: datetime | None
    confirmation_status: ConfirmationTimestampStatus
    candle_timestamps: tuple[datetime, ...]
    price_anchor: Decimal
    context: CandlestickPatternContext
    reasons: tuple[str, ...]
    body_share: Decimal
    dominant_wick_share: Decimal
    opposite_wick_share: Decimal
    geometric_score: Decimal


class CandlestickPatternEngine:
    def __init__(self, config: CandlestickPatternConfig | None = None) -> None:
        self._config = config or CandlestickPatternConfig()

    @property
    def config(self) -> CandlestickPatternConfig:
        return self._config

    def detect(self, candles: tuple[Candle, ...]) -> tuple[CandlestickPattern, ...]:
        return self.detect_with_temporal_semantics(candles=candles)

    def detect_with_temporal_semantics(
        self,
        *,
        candles: tuple[Candle, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None = None,
        as_of: datetime | None = None,
    ) -> tuple[CandlestickPattern, ...]:
        if not candles:
            return ()

        if as_of is not None:
            _validate_utc_datetime(as_of, "as_of")

        ordered = tuple(sorted(candles, key=lambda candle: candle.opened_at))
        self._validate_candles(ordered)
        geometries = tuple(_compute_geometry(candle) for candle in ordered)

        patterns: list[CandlestickPattern] = []
        seen_ids: set[str] = set()
        for index in range(len(ordered)):
            patterns.extend(
                self._detect_single(
                    index,
                    ordered,
                    geometries,
                    temporal_semantics_by_opened_at,
                    as_of,
                )
            )
            patterns.extend(
                self._detect_double(
                    index,
                    ordered,
                    geometries,
                    temporal_semantics_by_opened_at,
                    as_of,
                )
            )
            patterns.extend(
                self._detect_four(
                    index,
                    ordered,
                    geometries,
                    temporal_semantics_by_opened_at,
                    as_of,
                )
            )

        unique: list[CandlestickPattern] = []
        for pattern in patterns:
            if pattern.pattern_id in seen_ids:
                continue
            seen_ids.add(pattern.pattern_id)
            unique.append(pattern)

        return tuple(
            sorted(
                unique,
                key=lambda pattern: (
                    pattern.ended_at,
                    pattern.started_at,
                    pattern.pattern_type.value,
                    pattern.pattern_id,
                ),
            )
        )

    def _validate_candles(self, candles: tuple[Candle, ...]) -> None:
        seen_timestamps: set[datetime] = set()
        previous_timestamp: datetime | None = None
        for candle in candles:
            if candle.opened_at in seen_timestamps:
                message = "candle timestamps must be unique"
                raise DomainError(message)
            seen_timestamps.add(candle.opened_at)
            if previous_timestamp is not None and candle.opened_at <= previous_timestamp:
                message = "candles must be in strictly ascending chronological order"
                raise DomainError(message)
            previous_timestamp = candle.opened_at

    def _detect_single(
        self,
        index: int,
        candles: tuple[Candle, ...],
        geometries: tuple[CandleGeometry, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None,
        as_of: datetime | None,
    ) -> tuple[CandlestickPattern, ...]:
        candle = candles[index]
        geometry = geometries[index]
        context = self._context_before(index, candles)
        results: list[CandlestickPattern] = []

        is_dragonfly = self._is_dragonfly_doji(geometry)
        is_gravestone = self._is_gravestone_doji(geometry)
        if is_dragonfly:
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.DRAGONFLY_DOJI,
                    direction=CandlestickPatternDirection.BULLISH,
                    candles=(candle,),
                    context=context,
                    price_anchor=candle.low.value,
                    body_share=geometry.body_share,
                    dominant_wick_share=geometry.lower_wick_share,
                    opposite_wick_share=geometry.upper_wick_share,
                    geometric_score=_doji_score(geometry),
                    reasons=(
                        "very_small_body",
                        "dominant_lower_wick",
                        "minimal_upper_wick",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )
        if is_gravestone:
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.GRAVESTONE_DOJI,
                    direction=CandlestickPatternDirection.BEARISH,
                    candles=(candle,),
                    context=context,
                    price_anchor=candle.high.value,
                    body_share=geometry.body_share,
                    dominant_wick_share=geometry.upper_wick_share,
                    opposite_wick_share=geometry.lower_wick_share,
                    geometric_score=_doji_score(geometry),
                    reasons=(
                        "very_small_body",
                        "dominant_upper_wick",
                        "minimal_lower_wick",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        # Doji has priority over hammer/shooting-star at exact threshold overlap.
        if is_dragonfly or is_gravestone:
            return tuple(results)

        if self._is_hammer(geometry):
            direction = (
                CandlestickPatternDirection.BULLISH
                if context is CandlestickPatternContext.DOWNTREND
                else CandlestickPatternDirection.NEUTRAL
            )
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.HAMMER,
                    direction=direction,
                    candles=(candle,),
                    context=context,
                    price_anchor=candle.low.value,
                    body_share=geometry.body_share,
                    dominant_wick_share=geometry.lower_wick_share,
                    opposite_wick_share=geometry.upper_wick_share,
                    geometric_score=_rejection_score(geometry),
                    reasons=(
                        "small_to_medium_body",
                        "dominant_lower_wick",
                        "small_upper_wick",
                        "body_near_upper_range",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        if self._is_shooting_star(geometry):
            direction = (
                CandlestickPatternDirection.BEARISH
                if context is CandlestickPatternContext.UPTREND
                else CandlestickPatternDirection.NEUTRAL
            )
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.SHOOTING_STAR,
                    direction=direction,
                    candles=(candle,),
                    context=context,
                    price_anchor=candle.high.value,
                    body_share=geometry.body_share,
                    dominant_wick_share=geometry.upper_wick_share,
                    opposite_wick_share=geometry.lower_wick_share,
                    geometric_score=_rejection_score(geometry),
                    reasons=(
                        "small_to_medium_body",
                        "dominant_upper_wick",
                        "small_lower_wick",
                        "body_near_lower_range",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        return tuple(results)

    def _detect_double(
        self,
        index: int,
        candles: tuple[Candle, ...],
        geometries: tuple[CandleGeometry, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None,
        as_of: datetime | None,
    ) -> tuple[CandlestickPattern, ...]:
        if index < 1:
            return ()

        previous = candles[index - 1]
        current = candles[index]
        previous_geometry = geometries[index - 1]
        current_geometry = geometries[index]
        context = self._context_before(index - 1, candles)
        results: list[CandlestickPattern] = []

        if self._is_bullish_engulfing(previous_geometry, current_geometry):
            geometric_score = _engulfing_score(
                engulfing_body=current_geometry.body,
                engulfed_body=previous_geometry.body,
                unfavorable_wick_share=current_geometry.upper_wick_share,
                max_unfavorable_share=self._config.max_unfavorable_engulfing_wick_share,
            )
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.BULLISH_ENGULFING,
                    direction=CandlestickPatternDirection.BULLISH,
                    candles=(previous, current),
                    context=context,
                    price_anchor=min(previous.low.value, current.low.value),
                    body_share=current_geometry.body_share,
                    dominant_wick_share=current_geometry.lower_wick_share,
                    opposite_wick_share=current_geometry.upper_wick_share,
                    geometric_score=geometric_score,
                    reasons=(
                        "first_bearish_second_bullish",
                        "second_body_engulfs_first_body",
                        "second_body_materially_larger",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        if self._is_bearish_engulfing(previous_geometry, current_geometry):
            geometric_score = _engulfing_score(
                engulfing_body=current_geometry.body,
                engulfed_body=previous_geometry.body,
                unfavorable_wick_share=current_geometry.lower_wick_share,
                max_unfavorable_share=self._config.max_unfavorable_engulfing_wick_share,
            )
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.BEARISH_ENGULFING,
                    direction=CandlestickPatternDirection.BEARISH,
                    candles=(previous, current),
                    context=context,
                    price_anchor=max(previous.high.value, current.high.value),
                    body_share=current_geometry.body_share,
                    dominant_wick_share=current_geometry.upper_wick_share,
                    opposite_wick_share=current_geometry.lower_wick_share,
                    geometric_score=geometric_score,
                    reasons=(
                        "first_bullish_second_bearish",
                        "second_body_engulfs_first_body",
                        "second_body_materially_larger",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        if self._is_tweezer_bottom(previous, current, previous_geometry, current_geometry):
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.TWEEZER_BOTTOM,
                    direction=CandlestickPatternDirection.BULLISH,
                    candles=(previous, current),
                    context=context,
                    price_anchor=min(previous.low.value, current.low.value),
                    body_share=current_geometry.body_share,
                    dominant_wick_share=min(
                        previous_geometry.lower_wick_share,
                        current_geometry.lower_wick_share,
                    ),
                    opposite_wick_share=max(
                        previous_geometry.upper_wick_share,
                        current_geometry.upper_wick_share,
                    ),
                    geometric_score=Decimal("0.70"),
                    reasons=(
                        "similar_lows_within_tolerance",
                        "both_show_lower_rejection",
                        "second_candle_rejects_lower_prices",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        if self._is_tweezer_top(previous, current, previous_geometry, current_geometry):
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.TWEEZER_TOP,
                    direction=CandlestickPatternDirection.BEARISH,
                    candles=(previous, current),
                    context=context,
                    price_anchor=max(previous.high.value, current.high.value),
                    body_share=current_geometry.body_share,
                    dominant_wick_share=min(
                        previous_geometry.upper_wick_share,
                        current_geometry.upper_wick_share,
                    ),
                    opposite_wick_share=max(
                        previous_geometry.lower_wick_share,
                        current_geometry.lower_wick_share,
                    ),
                    geometric_score=Decimal("0.70"),
                    reasons=(
                        "similar_highs_within_tolerance",
                        "both_show_upper_rejection",
                        "second_candle_rejects_higher_prices",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        return tuple(results)

    def _detect_four(
        self,
        index: int,
        candles: tuple[Candle, ...],
        geometries: tuple[CandleGeometry, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None,
        as_of: datetime | None,
    ) -> tuple[CandlestickPattern, ...]:
        if index < _FOUR_CANDLE_PATTERN_OFFSET:
            return ()

        c1, c2, c3, c4 = candles[index - 3], candles[index - 2], candles[index - 1], candles[index]
        g1, g2, g3, g4 = (
            geometries[index - 3],
            geometries[index - 2],
            geometries[index - 1],
            geometries[index],
        )
        context = self._context_before(index - 3, candles)

        combined_low = min(g1.body_bottom, g2.body_bottom, g3.body_bottom)
        combined_high = max(g1.body_top, g2.body_top, g3.body_top)

        results: list[CandlestickPattern] = []
        if (
            g1.direction is CandlestickPatternDirection.BEARISH
            and g2.direction is CandlestickPatternDirection.BEARISH
            and g3.direction is CandlestickPatternDirection.BEARISH
            and g4.direction is CandlestickPatternDirection.BULLISH
            and c2.close.value <= c1.close.value
            and c3.close.value <= c2.close.value
            and g4.body_bottom <= combined_low
            and g4.body_top >= combined_high
        ):
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.BULLISH_THREE_LINE_STRIKE,
                    direction=CandlestickPatternDirection.BULLISH,
                    candles=(c1, c2, c3, c4),
                    context=context,
                    price_anchor=min(c1.low.value, c2.low.value, c3.low.value, c4.low.value),
                    body_share=g4.body_share,
                    dominant_wick_share=g4.lower_wick_share,
                    opposite_wick_share=g4.upper_wick_share,
                    geometric_score=Decimal("0.75"),
                    reasons=(
                        "three_bearish_sequence",
                        "bullish_strike_engulfs_prior_body_range",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        if (
            g1.direction is CandlestickPatternDirection.BULLISH
            and g2.direction is CandlestickPatternDirection.BULLISH
            and g3.direction is CandlestickPatternDirection.BULLISH
            and g4.direction is CandlestickPatternDirection.BEARISH
            and c2.close.value >= c1.close.value
            and c3.close.value >= c2.close.value
            and g4.body_bottom <= combined_low
            and g4.body_top >= combined_high
        ):
            results.append(
                self._build_pattern(
                    pattern_type=CandlestickPatternType.BEARISH_THREE_LINE_STRIKE,
                    direction=CandlestickPatternDirection.BEARISH,
                    candles=(c1, c2, c3, c4),
                    context=context,
                    price_anchor=max(c1.high.value, c2.high.value, c3.high.value, c4.high.value),
                    body_share=g4.body_share,
                    dominant_wick_share=g4.upper_wick_share,
                    opposite_wick_share=g4.lower_wick_share,
                    geometric_score=Decimal("0.75"),
                    reasons=(
                        "three_bullish_sequence",
                        "bearish_strike_engulfs_prior_body_range",
                    ),
                    temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
                    as_of=as_of,
                )
            )

        return tuple(results)

    def _context_before(
        self,
        first_pattern_index: int,
        candles: tuple[Candle, ...],
    ) -> CandlestickPatternContext:
        start = first_pattern_index - self._config.context_window_size
        if start < 0:
            return CandlestickPatternContext.UNKNOWN

        window = candles[start:first_pattern_index]
        if len(window) < self._config.context_window_size:
            return CandlestickPatternContext.UNKNOWN

        net_change = window[-1].close.value - window[0].open.value
        if net_change > _ZERO:
            return CandlestickPatternContext.UPTREND
        if net_change < _ZERO:
            return CandlestickPatternContext.DOWNTREND
        return CandlestickPatternContext.NEUTRAL

    def _is_bullish_engulfing(
        self,
        first: CandleGeometry,
        second: CandleGeometry,
    ) -> bool:
        if first.direction is not CandlestickPatternDirection.BEARISH:
            return False
        if second.direction is not CandlestickPatternDirection.BULLISH:
            return False
        if first.body == _ZERO:
            return False

        if second.body < first.body * self._config.min_engulfing_body_factor:
            return False
        if second.upper_wick_share > self._config.max_unfavorable_engulfing_wick_share:
            return False

        first_low, first_high = first.body_bottom, first.body_top
        second_low, second_high = second.body_bottom, second.body_top
        return second_low <= first_low and second_high >= first_high

    def _is_bearish_engulfing(
        self,
        first: CandleGeometry,
        second: CandleGeometry,
    ) -> bool:
        if first.direction is not CandlestickPatternDirection.BULLISH:
            return False
        if second.direction is not CandlestickPatternDirection.BEARISH:
            return False
        if first.body == _ZERO:
            return False

        if second.body < first.body * self._config.min_engulfing_body_factor:
            return False
        if second.lower_wick_share > self._config.max_unfavorable_engulfing_wick_share:
            return False

        first_low, first_high = first.body_bottom, first.body_top
        second_low, second_high = second.body_bottom, second.body_top
        return second_low <= first_low and second_high >= first_high

    def _is_hammer(self, geometry: CandleGeometry) -> bool:
        if geometry.zero_span:
            return False

        body_near_top = geometry.body_bottom >= geometry.low + (geometry.span * Decimal("0.5"))
        return (
            self._config.min_rejection_body_share
            <= geometry.body_share
            <= self._config.max_rejection_body_share
            and geometry.lower_wick_share >= self._config.min_dominant_wick_share
            and geometry.upper_wick_share <= self._config.max_opposite_wick_share
            and body_near_top
        )

    def _is_shooting_star(self, geometry: CandleGeometry) -> bool:
        if geometry.zero_span:
            return False

        body_near_bottom = geometry.body_top <= geometry.low + (geometry.span * Decimal("0.5"))
        return (
            self._config.min_rejection_body_share
            <= geometry.body_share
            <= self._config.max_rejection_body_share
            and geometry.upper_wick_share >= self._config.min_dominant_wick_share
            and geometry.lower_wick_share <= self._config.max_opposite_wick_share
            and body_near_bottom
        )

    def _is_dragonfly_doji(self, geometry: CandleGeometry) -> bool:
        if geometry.zero_span:
            return False
        return (
            geometry.body_share <= self._config.max_doji_body_share
            and geometry.lower_wick_share >= self._config.min_dominant_wick_share
            and geometry.upper_wick_share <= self._config.max_opposite_wick_share
        )

    def _is_gravestone_doji(self, geometry: CandleGeometry) -> bool:
        if geometry.zero_span:
            return False
        return (
            geometry.body_share <= self._config.max_doji_body_share
            and geometry.upper_wick_share >= self._config.min_dominant_wick_share
            and geometry.lower_wick_share <= self._config.max_opposite_wick_share
        )

    def _is_tweezer_bottom(
        self,
        first_candle: Candle,
        second_candle: Candle,
        first_geometry: CandleGeometry,
        second_geometry: CandleGeometry,
    ) -> bool:
        tolerance = (
            max(first_geometry.span, second_geometry.span)
            * self._config.tweezer_extreme_tolerance_share
        )
        lows_close = abs(first_candle.low.value - second_candle.low.value) <= tolerance
        second_rejection = second_candle.close.value >= second_candle.open.value

        return (
            lows_close
            and first_geometry.lower_wick_share >= self._config.min_tweezer_wick_share
            and second_geometry.lower_wick_share >= self._config.min_tweezer_wick_share
            and second_rejection
        )

    def _is_tweezer_top(
        self,
        first_candle: Candle,
        second_candle: Candle,
        first_geometry: CandleGeometry,
        second_geometry: CandleGeometry,
    ) -> bool:
        tolerance = (
            max(first_geometry.span, second_geometry.span)
            * self._config.tweezer_extreme_tolerance_share
        )
        highs_close = abs(first_candle.high.value - second_candle.high.value) <= tolerance
        second_rejection = second_candle.close.value <= second_candle.open.value

        return (
            highs_close
            and first_geometry.upper_wick_share >= self._config.min_tweezer_wick_share
            and second_geometry.upper_wick_share >= self._config.min_tweezer_wick_share
            and second_rejection
        )

    def _build_pattern(
        self,
        *,
        pattern_type: CandlestickPatternType,
        direction: CandlestickPatternDirection,
        candles: tuple[Candle, ...],
        context: CandlestickPatternContext,
        price_anchor: Decimal,
        body_share: Decimal,
        dominant_wick_share: Decimal,
        opposite_wick_share: Decimal,
        geometric_score: Decimal,
        reasons: tuple[str, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None,
        as_of: datetime | None,
    ) -> CandlestickPattern:
        started_at = candles[0].opened_at
        ended_at = candles[-1].opened_at
        confirmed_at, confirmation_status = self._resolve_confirmation(
            candles=candles,
            temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
            as_of=as_of,
        )
        pattern_id = (
            f"{pattern_type.value}:{started_at.isoformat()}:{ended_at.isoformat()}:"
            f"{direction.value}"
        )
        return CandlestickPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            direction=direction,
            started_at=started_at,
            ended_at=ended_at,
            confirmed_at=confirmed_at,
            confirmation_status=confirmation_status,
            candle_timestamps=tuple(candle.opened_at for candle in candles),
            price_anchor=price_anchor,
            context=context,
            reasons=reasons,
            body_share=body_share,
            dominant_wick_share=dominant_wick_share,
            opposite_wick_share=opposite_wick_share,
            geometric_score=max(_ZERO, min(_ONE, geometric_score)),
        )

    def _resolve_confirmation(
        self,
        *,
        candles: tuple[Candle, ...],
        temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None,
        as_of: datetime | None,
    ) -> tuple[datetime | None, ConfirmationTimestampStatus]:
        confirmed_at: datetime | None = None

        if temporal_semantics_by_opened_at is None:
            return confirmed_at, ConfirmationTimestampStatus.UNKNOWN

        semantics = [temporal_semantics_by_opened_at.get(candle.opened_at) for candle in candles]
        if any(item is None for item in semantics):
            return confirmed_at, ConfirmationTimestampStatus.UNKNOWN

        typed_semantics = tuple(item for item in semantics if item is not None)
        statuses = tuple(item.confirmation_status(as_of=as_of) for item in typed_semantics)

        if any(status is ConfirmationTimestampStatus.PENDING for status in statuses):
            return confirmed_at, ConfirmationTimestampStatus.PENDING

        if any(status is ConfirmationTimestampStatus.UNKNOWN for status in statuses):
            return confirmed_at, ConfirmationTimestampStatus.UNKNOWN

        required_confirmation_time = max(
            item.available_at for item in typed_semantics if item.available_at is not None
        )
        return required_confirmation_time, ConfirmationTimestampStatus.CONFIRMED


def detect_candlestick_patterns(
    *,
    candles: tuple[Candle, ...],
    config: CandlestickPatternConfig | None = None,
    temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics] | None = None,
    as_of: datetime | None = None,
) -> tuple[CandlestickPattern, ...]:
    return CandlestickPatternEngine(config=config).detect_with_temporal_semantics(
        candles=candles,
        temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
        as_of=as_of,
    )


def detect_candlestick_patterns_with_temporal_confirmation(
    *,
    candles: tuple[Candle, ...],
    temporal_semantics_by_opened_at: dict[datetime, CandleTemporalSemantics],
    as_of: datetime,
    config: CandlestickPatternConfig | None = None,
) -> tuple[CandlestickPattern, ...]:
    return detect_candlestick_patterns(
        candles=candles,
        config=config,
        temporal_semantics_by_opened_at=temporal_semantics_by_opened_at,
        as_of=as_of,
    )


def _validate_utc_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != _UTC_OFFSET:
        message = f"{field_name} must be timezone-aware UTC"
        raise DomainError(message)


def _compute_geometry(candle: Candle) -> CandleGeometry:
    high = candle.high.value
    low = candle.low.value
    open_price = candle.open.value
    close_price = candle.close.value

    span = high - low
    body_top = max(open_price, close_price)
    body_bottom = min(open_price, close_price)
    body = body_top - body_bottom
    upper_wick = max(_ZERO, high - body_top)
    lower_wick = max(_ZERO, body_bottom - low)

    if close_price > open_price:
        direction = CandlestickPatternDirection.BULLISH
    elif close_price < open_price:
        direction = CandlestickPatternDirection.BEARISH
    else:
        direction = CandlestickPatternDirection.NEUTRAL

    if span == _ZERO:
        return CandleGeometry(
            high=high,
            low=low,
            span=span,
            body=body,
            body_top=body_top,
            body_bottom=body_bottom,
            upper_wick=upper_wick,
            lower_wick=lower_wick,
            body_share=_ZERO,
            upper_wick_share=_ZERO,
            lower_wick_share=_ZERO,
            direction=direction,
            zero_span=True,
        )

    return CandleGeometry(
        high=high,
        low=low,
        span=span,
        body=body,
        body_top=body_top,
        body_bottom=body_bottom,
        upper_wick=upper_wick,
        lower_wick=lower_wick,
        body_share=body / span,
        upper_wick_share=upper_wick / span,
        lower_wick_share=lower_wick / span,
        direction=direction,
        zero_span=False,
    )


__all__ = [
    "CandleTemporalSemantics",
    "CandlestickPattern",
    "CandlestickPatternConfig",
    "CandlestickPatternContext",
    "CandlestickPatternDirection",
    "CandlestickPatternEngine",
    "CandlestickPatternType",
    "ConfirmationTimestampStatus",
    "detect_candlestick_patterns",
    "detect_candlestick_patterns_with_temporal_confirmation",
]


def _doji_score(geometry: CandleGeometry) -> Decimal:
    return max(_ZERO, _ONE - geometry.body_share)


def _rejection_score(geometry: CandleGeometry) -> Decimal:
    return max(_ZERO, _ONE - geometry.body_share)


def _engulfing_score(
    *,
    engulfing_body: Decimal,
    engulfed_body: Decimal,
    unfavorable_wick_share: Decimal,
    max_unfavorable_share: Decimal,
) -> Decimal:
    body_component = _ONE if engulfed_body == _ZERO else min(_ONE, engulfing_body / engulfed_body)

    wick_penalty = max(_ZERO, unfavorable_wick_share - max_unfavorable_share)
    return max(_ZERO, min(_ONE, body_component - wick_penalty))


def _validate_ratio(
    value: Decimal,
    name: str,
    *,
    minimum: Decimal = _ZERO,
) -> None:
    if not value.is_finite() or value < minimum:
        message = f"{name} must be finite and >= {minimum}"
        raise DomainError(message)
