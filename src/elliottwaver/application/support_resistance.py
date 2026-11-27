"""Deterministic support/resistance zone derivation from confirmed swings."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

    from elliottwaver.domain.market import Candle, Swing


ZoneType = Literal["support", "resistance"]
DEFAULT_MAX_ZONE_WIDTH_RATIO = Decimal("0.03")
_MIN_ZONE_WIDTH = Decimal("0.5")


@dataclass(frozen=True, slots=True)
class SupportResistanceZone:
    """Immutable support/resistance zone aggregated from confirmed swing pivots."""

    zone_type: ZoneType
    lower_price: Decimal
    upper_price: Decimal
    touch_count: int
    first_timestamp: datetime
    last_timestamp: datetime
    pivot_ids: tuple[str, ...]


def derive_support_resistance_zones(
    *,
    candles: tuple[Candle, ...],
    swings: tuple[Swing, ...],
    max_zone_width_ratio: Decimal = DEFAULT_MAX_ZONE_WIDTH_RATIO,
) -> tuple[SupportResistanceZone, ...]:
    """Create deterministic support/resistance zones from confirmed swing pivots."""

    if not candles or not swings:
        return ()

    candle_by_timestamp = {candle.opened_at: candle for candle in candles}
    raw_zones: list[SupportResistanceZone] = []
    seen_pivot_ids: set[str] = set()

    for swing in sorted(
        swings, key=lambda item: (item.start_timestamp, item.end_timestamp, str(item.id))
    ):
        for pivot in (swing.start_pivot, swing.end_pivot):
            pivot_id = str(pivot.id)
            if pivot_id in seen_pivot_ids:
                continue
            seen_pivot_ids.add(pivot_id)

            candle = candle_by_timestamp.get(pivot.timestamp)
            if candle is None:
                continue

            open_price = candle.open.value
            close_price = candle.close.value
            high_price = candle.high.value
            low_price = candle.low.value

            if pivot.pivot_type.value == "high":
                lower_price = max(open_price, close_price)
                upper_price = high_price
                zone_type: ZoneType = "resistance"
            elif pivot.pivot_type.value == "low":
                lower_price = low_price
                upper_price = min(open_price, close_price)
                zone_type = "support"
            else:
                continue

            if upper_price < lower_price:
                lower_price, upper_price = upper_price, lower_price

            raw_zones.append(
                SupportResistanceZone(
                    zone_type=zone_type,
                    lower_price=lower_price,
                    upper_price=upper_price,
                    touch_count=1,
                    first_timestamp=pivot.timestamp,
                    last_timestamp=pivot.timestamp,
                    pivot_ids=(pivot_id,),
                )
            )

    support_zones = _merge_overlapping_zones(
        tuple(zone for zone in raw_zones if zone.zone_type == "support"),
        max_zone_width_ratio=max_zone_width_ratio,
    )
    resistance_zones = _merge_overlapping_zones(
        tuple(zone for zone in raw_zones if zone.zone_type == "resistance"),
        max_zone_width_ratio=max_zone_width_ratio,
    )
    return support_zones + resistance_zones


def _merge_overlapping_zones(
    zones: tuple[SupportResistanceZone, ...],
    *,
    max_zone_width_ratio: Decimal,
) -> tuple[SupportResistanceZone, ...]:
    if not zones:
        return ()

    ordered = tuple(
        sorted(
            zones,
            key=lambda zone: (
                zone.lower_price,
                zone.upper_price,
                zone.first_timestamp,
                zone.pivot_ids[0],
            ),
        )
    )

    merged: list[SupportResistanceZone] = []
    for zone in ordered:
        if not merged:
            merged.append(zone)
            continue

        current = merged[-1]
        if zone.lower_price > current.upper_price:
            merged.append(zone)
            continue

        merged_lower = min(current.lower_price, zone.lower_price)
        merged_upper = max(current.upper_price, zone.upper_price)
        merged_width = merged_upper - merged_lower
        if merged_width > _max_zone_width(
            lower_price=merged_lower,
            upper_price=merged_upper,
            max_zone_width_ratio=max_zone_width_ratio,
        ):
            merged.append(zone)
            continue

        pivot_ids = tuple(sorted({*current.pivot_ids, *zone.pivot_ids}))
        merged[-1] = SupportResistanceZone(
            zone_type=current.zone_type,
            lower_price=merged_lower,
            upper_price=merged_upper,
            touch_count=len(pivot_ids),
            first_timestamp=min(current.first_timestamp, zone.first_timestamp),
            last_timestamp=max(current.last_timestamp, zone.last_timestamp),
            pivot_ids=pivot_ids,
        )

    return tuple(merged)


def _max_zone_width(
    *,
    lower_price: Decimal,
    upper_price: Decimal,
    max_zone_width_ratio: Decimal,
) -> Decimal:
    midpoint = (lower_price + upper_price) / Decimal("2")
    reference = abs(midpoint)
    ratio_width = reference * max_zone_width_ratio
    return max(_MIN_ZONE_WIDTH, ratio_width)
