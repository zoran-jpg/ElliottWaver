"""Analysis use-case contracts and application orchestration services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.confluence import (
    ConfluenceSeverity,
    MultiTimeframeConfluenceAnalyzer,
    MultiTimeframeConfluenceResult,
)
from elliottwaver.domain.detection import DetectionResult, WaveDetector
from elliottwaver.domain.multi_timeframe import (
    MultiTimeframeAnalysis,
    MultiTimeframeAnalyzer,
)
from elliottwaver.domain.multi_timeframe import (
    Timeframe as HierarchyTimeframe,
)
from elliottwaver.domain.scoring import ScoringResult, WaveScorer
from elliottwaver.domain.selection import SelectionResult, WaveSelector
from elliottwaver.domain.trend_hierarchy import TrendHierarchy, TrendHierarchyBuilder

if TYPE_CHECKING:
    from elliottwaver.core.shared.identifiers import EntityId
    from elliottwaver.domain.market import Candle, Swing


_ZERO = 0
_UTC_OFFSET = UTC.utcoffset(None)

_MARKET_TIMEFRAME_ORDER: tuple[MarketTimeframe, ...] = (
    MarketTimeframe.ONE_WEEK,
    MarketTimeframe.ONE_DAY,
    MarketTimeframe.FOUR_HOURS,
    MarketTimeframe.ONE_HOUR,
    MarketTimeframe.THIRTY_MINUTES,
    MarketTimeframe.FIFTEEN_MINUTES,
    MarketTimeframe.FIVE_MINUTES,
    MarketTimeframe.ONE_MINUTE,
)

_MARKET_TO_HIERARCHY_TIMEFRAME: dict[MarketTimeframe, HierarchyTimeframe] = {
    MarketTimeframe.ONE_WEEK: HierarchyTimeframe.parse("W1"),
    MarketTimeframe.ONE_DAY: HierarchyTimeframe.parse("D1"),
    MarketTimeframe.FOUR_HOURS: HierarchyTimeframe.parse("H4"),
    MarketTimeframe.ONE_HOUR: HierarchyTimeframe.parse("H1"),
    MarketTimeframe.THIRTY_MINUTES: HierarchyTimeframe.parse("M30"),
    MarketTimeframe.FIFTEEN_MINUTES: HierarchyTimeframe.parse("M15"),
    MarketTimeframe.FIVE_MINUTES: HierarchyTimeframe.parse("M5"),
    MarketTimeframe.ONE_MINUTE: HierarchyTimeframe.parse("M1"),
}

_HIERARCHY_TO_MARKET_TIMEFRAME: dict[str, MarketTimeframe] = {
    hierarchy_timeframe.value: market_timeframe
    for market_timeframe, hierarchy_timeframe in _MARKET_TO_HIERARCHY_TIMEFRAME.items()
}

ISSUE_NO_MARKET_DATA = "no_market_data"
ISSUE_INSUFFICIENT_MARKET_DATA = "insufficient_market_data"
ISSUE_NO_WAVE_CANDIDATES = "no_wave_candidates"
ISSUE_NO_SELECTED_CANDIDATES = "no_selected_candidates"
ISSUE_INVALID_HIERARCHY = "invalid_hierarchy"
ISSUE_CONFLUENCE_CONFLICTS = "confluence_conflicts"


class AnalysisStage(StrEnum):
    """Stable stages for the analysis pipeline."""

    MARKET_DATA = "market_data"
    DETECTION = "detection"
    VALIDATION = "validation"
    SCORING = "scoring"
    SELECTION = "selection"
    MULTI_TIMEFRAME = "multi_timeframe"
    HIERARCHY = "hierarchy"
    CONFLUENCE = "confluence"
    COMPLETED = "completed"


class AnalysisIssueSeverity(StrEnum):
    """Severity levels for analysis issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_ANALYSIS_STAGE_ORDER: tuple[AnalysisStage, ...] = (
    AnalysisStage.MARKET_DATA,
    AnalysisStage.DETECTION,
    AnalysisStage.VALIDATION,
    AnalysisStage.SCORING,
    AnalysisStage.SELECTION,
    AnalysisStage.MULTI_TIMEFRAME,
    AnalysisStage.HIERARCHY,
    AnalysisStage.CONFLUENCE,
    AnalysisStage.COMPLETED,
)

_ISSUE_SEVERITY_ORDER: tuple[AnalysisIssueSeverity, ...] = (
    AnalysisIssueSeverity.INFO,
    AnalysisIssueSeverity.WARNING,
    AnalysisIssueSeverity.ERROR,
    AnalysisIssueSeverity.CRITICAL,
)


@dataclass(frozen=True, slots=True)
class TimeframeAnalysisRequest:
    """Request to analyze one symbol and one timeframe."""

    symbol: Symbol
    timeframe: MarketTimeframe
    start_time: datetime
    end_time: datetime
    maximum_candles: int | None = None

    def __post_init__(self) -> None:
        _validate_utc_range(self.start_time, self.end_time, "start_time", "end_time")
        _validate_optional_positive_int(self.maximum_candles, "maximum_candles")


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Request to analyze multiple timeframes for one symbol."""

    symbol: Symbol
    timeframe_requests: tuple[TimeframeAnalysisRequest, ...]
    start_time: datetime
    end_time: datetime
    maximum_candles: int | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        _validate_utc_range(self.start_time, self.end_time, "start_time", "end_time")
        _validate_optional_positive_int(self.maximum_candles, "maximum_candles")

        if not self.timeframe_requests:
            message = "timeframe_requests must not be empty"
            raise DomainError(message)

        normalized_correlation_id = self.correlation_id
        if normalized_correlation_id is not None:
            normalized_correlation_id = normalized_correlation_id.strip()
            if not normalized_correlation_id:
                message = "correlation_id must not be empty"
                raise DomainError(message)
            object.__setattr__(self, "correlation_id", normalized_correlation_id)

        normalized_requests = tuple(
            sorted(
                self.timeframe_requests,
                key=lambda request: _market_timeframe_rank(request.timeframe),
            )
        )
        seen: set[MarketTimeframe] = set()

        for request in normalized_requests:
            if request.symbol != self.symbol:
                message = "timeframe_requests must use the same symbol as AnalysisRequest"
                raise DomainError(message)
            if request.start_time != self.start_time or request.end_time != self.end_time:
                message = "timeframe_requests must use the same time range as AnalysisRequest"
                raise DomainError(message)
            if request.timeframe in seen:
                message = "timeframe_requests must not contain duplicate timeframes"
                raise DomainError(message)
            seen.add(request.timeframe)

        object.__setattr__(self, "timeframe_requests", normalized_requests)

    @property
    def timeframes(self) -> tuple[MarketTimeframe, ...]:
        """Return normalized requested timeframes."""

        return tuple(request.timeframe for request in self.timeframe_requests)

    def maximum_candles_for(self, timeframe: MarketTimeframe) -> int | None:
        """Return the timeframe-specific maximum candles or the global default."""

        for request in self.timeframe_requests:
            if request.timeframe == timeframe and request.maximum_candles is not None:
                return request.maximum_candles
        return self.maximum_candles


@dataclass(frozen=True, slots=True)
class AnalysisIssue:
    """Structured issue reported during analysis."""

    stage: AnalysisStage
    issue_code: str
    message: str
    severity: AnalysisIssueSeverity
    timeframe: MarketTimeframe | None = None
    details: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not self.issue_code.strip():
            message = "issue_code must not be empty"
            raise DomainError(message)

        if not self.message.strip():
            message = "message must not be empty"
            raise DomainError(message)

        seen: set[str] = set()
        normalized_details: list[tuple[str, object]] = []
        for key, value in self.details:
            normalized_key = key.strip()
            if not normalized_key:
                message = "detail keys must not be empty"
                raise DomainError(message)
            if normalized_key in seen:
                message = "detail keys must be unique"
                raise DomainError(message)
            seen.add(normalized_key)
            normalized_details.append((normalized_key, value))

        object.__setattr__(
            self, "details", tuple(sorted(normalized_details, key=lambda item: item[0]))
        )

    @property
    def sort_key(self) -> tuple[int, int, str, int]:
        """Return a deterministic key for stable issue ordering."""

        timeframe_rank = (
            _market_timeframe_rank(self.timeframe)
            if self.timeframe is not None
            else len(_MARKET_TIMEFRAME_ORDER)
        )
        return (
            _analysis_stage_rank(self.stage),
            timeframe_rank,
            self.issue_code,
            _analysis_issue_severity_rank(self.severity),
        )


@dataclass(frozen=True, slots=True)
class AnalysisMetadata:
    """Metadata shared by analysis results and responses."""

    analysis_id: EntityId
    correlation_id: str | None
    requested_at: datetime
    completed_at: datetime
    symbol: Symbol
    requested_timeframes: tuple[MarketTimeframe, ...]
    processed_timeframes: tuple[MarketTimeframe, ...]

    def __post_init__(self) -> None:
        _validate_utc_datetime(self.requested_at, "requested_at")
        _validate_utc_datetime(self.completed_at, "completed_at")

        if self.completed_at < self.requested_at:
            message = "completed_at must not be before requested_at"
            raise DomainError(message)

        normalized_requested_timeframes = _normalize_market_timeframes(self.requested_timeframes)
        normalized_processed_timeframes = _normalize_market_timeframes(self.processed_timeframes)

        if not set(normalized_processed_timeframes).issubset(set(normalized_requested_timeframes)):
            message = "processed_timeframes must be a subset of requested_timeframes"
            raise DomainError(message)

        normalized_correlation_id = self.correlation_id
        if normalized_correlation_id is not None:
            normalized_correlation_id = normalized_correlation_id.strip()
            if not normalized_correlation_id:
                message = "correlation_id must not be empty"
                raise DomainError(message)
            object.__setattr__(self, "correlation_id", normalized_correlation_id)

        object.__setattr__(self, "requested_timeframes", normalized_requested_timeframes)
        object.__setattr__(self, "processed_timeframes", normalized_processed_timeframes)


@dataclass(frozen=True, slots=True)
class TimeframeAnalysisResult:
    """Per-timeframe pipeline result."""

    request: TimeframeAnalysisRequest
    metadata: AnalysisMetadata
    candles: tuple[Candle, ...]
    prepared_swings: tuple[Swing, ...]
    detection_result: DetectionResult
    scoring_result: ScoringResult
    selection_result: SelectionResult
    issues: tuple[AnalysisIssue, ...] = ()
    stage: AnalysisStage = AnalysisStage.MARKET_DATA

    def __post_init__(self) -> None:
        if self.metadata.symbol != self.request.symbol:
            message = "metadata symbol must match request symbol"
            raise DomainError(message)

        if self.metadata.requested_timeframes != (self.request.timeframe,):
            message = "metadata requested_timeframes must contain the request timeframe"
            raise DomainError(message)

        processed_timeframes = self.metadata.processed_timeframes
        if processed_timeframes not in ((), (self.request.timeframe,)):
            message = "metadata processed_timeframes must be empty or contain the request timeframe"
            raise DomainError(message)

        object.__setattr__(
            self, "issues", tuple(sorted(self.issues, key=lambda issue: issue.sort_key))
        )

    @property
    def timeframe(self) -> MarketTimeframe:
        """Return the analyzed timeframe."""

        return self.request.timeframe

    @property
    def has_issues(self) -> bool:
        """Return True when issues were reported."""

        return bool(self.issues)

    @property
    def is_processed(self) -> bool:
        """Return True when market data was sufficient to proceed."""

        return bool(self.metadata.processed_timeframes)


@dataclass(frozen=True, slots=True)
class AnalysisResponse:
    """Aggregated analysis response returned by the multi-timeframe service."""

    metadata: AnalysisMetadata
    stage: AnalysisStage
    timeframe_results: tuple[TimeframeAnalysisResult, ...] = ()
    multi_timeframe_analysis: MultiTimeframeAnalysis | None = None
    trend_hierarchy: TrendHierarchy | None = None
    confluence_result: MultiTimeframeConfluenceResult | None = None
    issues: tuple[AnalysisIssue, ...] = ()

    def __post_init__(self) -> None:
        sorted_results = tuple(
            sorted(
                self.timeframe_results,
                key=lambda result: _market_timeframe_rank(result.timeframe),
            )
        )
        object.__setattr__(self, "timeframe_results", sorted_results)
        object.__setattr__(
            self, "issues", tuple(sorted(self.issues, key=lambda issue: issue.sort_key))
        )

        requested_timeframes = tuple(result.timeframe for result in sorted_results)
        if self.metadata.requested_timeframes != requested_timeframes:
            message = "metadata requested_timeframes must match the timeframe results"
            raise DomainError(message)

        processed_timeframes = tuple(
            result.timeframe for result in sorted_results if result.is_processed
        )
        if self.metadata.processed_timeframes != processed_timeframes:
            message = "metadata processed_timeframes must match processed timeframe results"
            raise DomainError(message)

    @property
    def is_success(self) -> bool:
        """Return True when all requested timeframes were processed without issues."""

        return (
            self.completed
            and not self.has_issues
            and self.processed_timeframe_count == len(self.metadata.requested_timeframes)
        )

    @property
    def is_partial(self) -> bool:
        """Return True when at least one, but not all, requested timeframes were processed."""

        return 0 < self.processed_timeframe_count < len(self.metadata.requested_timeframes)

    @property
    def has_issues(self) -> bool:
        """Return True when one or more issues were reported."""

        return bool(self.issues)

    @property
    def completed(self) -> bool:
        """Return True when the analysis reached the completed stage."""

        return self.stage is AnalysisStage.COMPLETED

    @property
    def processed_timeframe_count(self) -> int:
        """Return the number of processed timeframes."""

        return len(self.metadata.processed_timeframes)


@runtime_checkable
class MarketDataProvider(Protocol):
    """Load immutable candle data for a time range."""

    def load_candles(
        self,
        symbol: Symbol,
        timeframe: MarketTimeframe,
        start_time: datetime,
        end_time: datetime,
        maximum_candles: int | None = None,
    ) -> tuple[Candle, ...]:
        """Return candles in immutable order for the requested market slice."""


@runtime_checkable
class AnalysisClock(Protocol):
    """Controlled analysis clock used for deterministic timestamps."""

    def now(self) -> datetime:
        """Return a UTC-aware datetime."""


@runtime_checkable
class AnalysisIdProvider(Protocol):
    """Generate stable analysis identifiers."""

    def next_analysis_id(self) -> EntityId:
        """Return the next analysis identifier."""


@runtime_checkable
class CandleToSwingPreparationPort(Protocol):
    """Prepare swing inputs from loaded candles without introducing strategy logic."""

    def prepare_swings(
        self,
        candles: tuple[Candle, ...],
        request: TimeframeAnalysisRequest,
    ) -> tuple[Swing, ...]:
        """Return prepared swings for downstream detection."""


@runtime_checkable
class AnalyzeTimeframeUseCase(Protocol):
    """Use-case contract for a single timeframe analysis."""

    def analyze(self, request: TimeframeAnalysisRequest) -> TimeframeAnalysisResult:
        """Analyze one timeframe and return a structured result."""


@runtime_checkable
class AnalyzeMultiTimeframeUseCase(Protocol):
    """Use-case contract for a multi-timeframe analysis."""

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Analyze multiple timeframes and return a structured response."""


@dataclass(frozen=True, slots=True)
class AnalyzeTimeframeService:
    """Orchestrate market data, detection, scoring, and selection for one timeframe."""

    market_data_provider: MarketDataProvider
    swing_preparation_port: CandleToSwingPreparationPort
    analysis_clock: AnalysisClock
    analysis_id_provider: AnalysisIdProvider
    detector: WaveDetector = field(default_factory=WaveDetector)
    scorer: WaveScorer = field(default_factory=WaveScorer)
    selector: WaveSelector = field(default_factory=WaveSelector)

    def analyze(self, request: TimeframeAnalysisRequest) -> TimeframeAnalysisResult:
        """Analyze one timeframe without mutating the request or recomputing domain logic."""

        requested_at = self.analysis_clock.now()
        analysis_id = self.analysis_id_provider.next_analysis_id()
        maximum_candles = request.maximum_candles

        candles = self.market_data_provider.load_candles(
            request.symbol,
            request.timeframe,
            request.start_time,
            request.end_time,
            maximum_candles=maximum_candles,
        )

        issues: list[AnalysisIssue] = []
        if not candles:
            issues.append(
                AnalysisIssue(
                    stage=AnalysisStage.MARKET_DATA,
                    issue_code=ISSUE_NO_MARKET_DATA,
                    message="No candles were returned for the requested timeframe",
                    severity=AnalysisIssueSeverity.ERROR,
                    timeframe=request.timeframe,
                    details=(
                        ("symbol", request.symbol.value),
                        ("start_time", request.start_time),
                        ("end_time", request.end_time),
                    ),
                )
            )

        prepared_swings = (
            self.swing_preparation_port.prepare_swings(candles, request) if candles else ()
        )
        if candles and not prepared_swings:
            issues.append(
                AnalysisIssue(
                    stage=AnalysisStage.VALIDATION,
                    issue_code=ISSUE_INSUFFICIENT_MARKET_DATA,
                    message="Candles were loaded but no swing input could be prepared",
                    severity=AnalysisIssueSeverity.WARNING,
                    timeframe=request.timeframe,
                    details=(("candle_count", len(candles)),),
                )
            )

        detection_result = self.detector.detect(prepared_swings)
        if prepared_swings and not detection_result.candidates:
            issues.append(
                AnalysisIssue(
                    stage=AnalysisStage.DETECTION,
                    issue_code=ISSUE_NO_WAVE_CANDIDATES,
                    message="No wave candidates were detected",
                    severity=AnalysisIssueSeverity.WARNING,
                    timeframe=request.timeframe,
                    details=(("swing_count", len(prepared_swings)),),
                )
            )

        scoring_result = self.scorer.score(detection_result.candidates)
        selection_result = self.selector.select(scoring_result)
        if detection_result.candidates and not selection_result.selected_candidates:
            issues.append(
                AnalysisIssue(
                    stage=AnalysisStage.SELECTION,
                    issue_code=ISSUE_NO_SELECTED_CANDIDATES,
                    message="Detected candidates were not selected",
                    severity=AnalysisIssueSeverity.WARNING,
                    timeframe=request.timeframe,
                    details=(
                        ("candidate_count", len(detection_result.candidates)),
                        ("scored_candidate_count", len(scoring_result.scored_candidates)),
                    ),
                )
            )

        completed_at = self.analysis_clock.now()
        metadata = AnalysisMetadata(
            analysis_id=analysis_id,
            correlation_id=None,
            requested_at=requested_at,
            completed_at=completed_at,
            symbol=request.symbol,
            requested_timeframes=(request.timeframe,),
            processed_timeframes=(request.timeframe,) if prepared_swings else (),
        )
        stage = _resolve_timeframe_stage(
            candles=candles,
            prepared_swings=prepared_swings,
            detection_result=detection_result,
            scoring_result=scoring_result,
            selection_result=selection_result,
        )
        return TimeframeAnalysisResult(
            request=request,
            metadata=metadata,
            candles=candles,
            prepared_swings=prepared_swings,
            detection_result=detection_result,
            scoring_result=scoring_result,
            selection_result=selection_result,
            issues=tuple(issues),
            stage=stage,
        )


@dataclass(frozen=True, slots=True)
class AnalyzeMultiTimeframeService:
    """Orchestrate the full analysis pipeline across requested timeframes."""

    timeframe_use_case: AnalyzeTimeframeUseCase
    analysis_clock: AnalysisClock
    analysis_id_provider: AnalysisIdProvider
    multi_timeframe_analyzer: MultiTimeframeAnalyzer = field(default_factory=MultiTimeframeAnalyzer)
    trend_hierarchy_builder: TrendHierarchyBuilder = field(default_factory=TrendHierarchyBuilder)
    confluence_analyzer: MultiTimeframeConfluenceAnalyzer = field(
        default_factory=MultiTimeframeConfluenceAnalyzer
    )

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Analyze all requested timeframes and aggregate the deterministic outputs."""

        requested_at = self.analysis_clock.now()
        analysis_id = self.analysis_id_provider.next_analysis_id()

        timeframe_results = tuple(
            self.timeframe_use_case.analyze(_resolved_timeframe_request(request, timeframe_request))
            for timeframe_request in request.timeframe_requests
        )

        processed_timeframe_results = tuple(
            result for result in timeframe_results if result.is_processed
        )
        completed_at = self.analysis_clock.now()

        if processed_timeframe_results:
            selections_by_timeframe = tuple(
                (
                    _to_hierarchy_timeframe(result.timeframe),
                    result.selection_result,
                )
                for result in processed_timeframe_results
            )
            multi_timeframe_analysis = self.multi_timeframe_analyzer.analyze(
                selections_by_timeframe,
                symbol=request.symbol,
                analysed_at=completed_at,
            )
            trend_hierarchy = self.trend_hierarchy_builder.build(multi_timeframe_analysis)
            confluence_result = self.confluence_analyzer.analyze(trend_hierarchy)
        else:
            multi_timeframe_analysis = None
            trend_hierarchy = None
            confluence_result = None

        issues = _collect_multi_timeframe_issues(
            timeframe_results=timeframe_results,
            trend_hierarchy=trend_hierarchy,
            confluence_result=confluence_result,
        )

        metadata = AnalysisMetadata(
            analysis_id=analysis_id,
            correlation_id=request.correlation_id,
            requested_at=requested_at,
            completed_at=completed_at,
            symbol=request.symbol,
            requested_timeframes=request.timeframes,
            processed_timeframes=tuple(result.timeframe for result in processed_timeframe_results),
        )
        stage = _resolve_response_stage(
            timeframe_results=timeframe_results,
            multi_timeframe_analysis=multi_timeframe_analysis,
            trend_hierarchy=trend_hierarchy,
            confluence_result=confluence_result,
        )
        return AnalysisResponse(
            metadata=metadata,
            stage=stage,
            timeframe_results=timeframe_results,
            multi_timeframe_analysis=multi_timeframe_analysis,
            trend_hierarchy=trend_hierarchy,
            confluence_result=confluence_result,
            issues=tuple(issues),
        )


def _resolved_timeframe_request(
    request: AnalysisRequest,
    timeframe_request: TimeframeAnalysisRequest,
) -> TimeframeAnalysisRequest:
    maximum_candles = timeframe_request.maximum_candles
    if maximum_candles is None:
        maximum_candles = request.maximum_candles

    return TimeframeAnalysisRequest(
        symbol=request.symbol,
        timeframe=timeframe_request.timeframe,
        start_time=request.start_time,
        end_time=request.end_time,
        maximum_candles=maximum_candles,
    )


def _collect_multi_timeframe_issues(
    *,
    timeframe_results: tuple[TimeframeAnalysisResult, ...],
    trend_hierarchy: TrendHierarchy | None,
    confluence_result: MultiTimeframeConfluenceResult | None,
) -> tuple[AnalysisIssue, ...]:
    issues: list[AnalysisIssue] = [issue for result in timeframe_results for issue in result.issues]

    if trend_hierarchy is not None and not trend_hierarchy.is_valid:
        issues.append(
            AnalysisIssue(
                stage=AnalysisStage.HIERARCHY,
                issue_code=ISSUE_INVALID_HIERARCHY,
                message="Trend hierarchy failed structural validation",
                severity=AnalysisIssueSeverity.ERROR,
                details=(("issue_count", len(trend_hierarchy.validation.issues)),),
            )
        )

    if confluence_result is not None and confluence_result.has_conflicts:
        highest_severity = AnalysisIssueSeverity.WARNING
        if any(
            conflict.severity is ConfluenceSeverity.CRITICAL
            for conflict in confluence_result.conflicts
        ):
            highest_severity = AnalysisIssueSeverity.CRITICAL
        issues.append(
            AnalysisIssue(
                stage=AnalysisStage.CONFLUENCE,
                issue_code=ISSUE_CONFLUENCE_CONFLICTS,
                message="Confluence analysis reported conflicts",
                severity=highest_severity,
                details=(
                    ("conflict_count", len(confluence_result.conflicts)),
                    ("evidence_count", len(confluence_result.evidences)),
                ),
            )
        )

    return tuple(issues)


def _resolve_timeframe_stage(
    *,
    candles: tuple[Candle, ...],
    prepared_swings: tuple[Swing, ...],
    detection_result: DetectionResult,
    scoring_result: ScoringResult,
    selection_result: SelectionResult,
) -> AnalysisStage:
    if not candles:
        return AnalysisStage.MARKET_DATA

    if not prepared_swings:
        return AnalysisStage.VALIDATION

    if not detection_result.candidates:
        return AnalysisStage.DETECTION

    if not scoring_result.scored_candidates:
        return AnalysisStage.SCORING

    if not selection_result.selected_candidates:
        return AnalysisStage.SELECTION

    return AnalysisStage.COMPLETED


def _resolve_response_stage(
    *,
    timeframe_results: tuple[TimeframeAnalysisResult, ...],
    multi_timeframe_analysis: MultiTimeframeAnalysis | None,
    trend_hierarchy: TrendHierarchy | None,
    confluence_result: MultiTimeframeConfluenceResult | None,
) -> AnalysisStage:
    if confluence_result is not None:
        if not any(result.has_issues for result in timeframe_results):
            return AnalysisStage.COMPLETED
        return AnalysisStage.CONFLUENCE

    if trend_hierarchy is not None:
        return AnalysisStage.HIERARCHY

    if multi_timeframe_analysis is not None:
        return AnalysisStage.MULTI_TIMEFRAME

    if not timeframe_results:
        return AnalysisStage.MARKET_DATA

    return max((result.stage for result in timeframe_results), key=_analysis_stage_rank)


def _analysis_stage_rank(stage: AnalysisStage) -> int:
    return _ANALYSIS_STAGE_ORDER.index(stage)


def _analysis_issue_severity_rank(severity: AnalysisIssueSeverity) -> int:
    return _ISSUE_SEVERITY_ORDER.index(severity)


def _market_timeframe_rank(timeframe: MarketTimeframe) -> int:
    return _MARKET_TIMEFRAME_ORDER.index(timeframe)


def _normalize_market_timeframes(
    timeframes: tuple[MarketTimeframe, ...],
) -> tuple[MarketTimeframe, ...]:
    normalized = tuple(sorted(timeframes, key=_market_timeframe_rank))
    if len(set(normalized)) != len(normalized):
        message = "timeframes must not contain duplicates"
        raise DomainError(message)
    return normalized


def _validate_optional_positive_int(value: int | None, field_name: str) -> None:
    if value is None:
        return
    if value <= _ZERO:
        message = f"{field_name} must be greater than zero"
        raise DomainError(message)


def _validate_utc_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != _UTC_OFFSET:
        message = f"{field_name} must be timezone-aware UTC"
        raise DomainError(message)


def _validate_utc_range(
    start_time: datetime, end_time: datetime, start_name: str, end_name: str
) -> None:
    _validate_utc_datetime(start_time, start_name)
    _validate_utc_datetime(end_time, end_name)

    if start_time >= end_time:
        message = f"{start_name} must be before {end_name}"
        raise DomainError(message)


def _to_hierarchy_timeframe(timeframe: MarketTimeframe) -> HierarchyTimeframe:
    return _MARKET_TO_HIERARCHY_TIMEFRAME[timeframe]


def _to_market_timeframe(timeframe: HierarchyTimeframe) -> MarketTimeframe:
    return _HIERARCHY_TO_MARKET_TIMEFRAME[timeframe.value]


__all__ = [
    "ISSUE_CONFLUENCE_CONFLICTS",
    "ISSUE_INSUFFICIENT_MARKET_DATA",
    "ISSUE_INVALID_HIERARCHY",
    "ISSUE_NO_MARKET_DATA",
    "ISSUE_NO_SELECTED_CANDIDATES",
    "ISSUE_NO_WAVE_CANDIDATES",
    "AnalysisClock",
    "AnalysisIdProvider",
    "AnalysisIssue",
    "AnalysisIssueSeverity",
    "AnalysisMetadata",
    "AnalysisRequest",
    "AnalysisResponse",
    "AnalysisStage",
    "AnalyzeMultiTimeframeService",
    "AnalyzeMultiTimeframeUseCase",
    "AnalyzeTimeframeService",
    "AnalyzeTimeframeUseCase",
    "CandleToSwingPreparationPort",
    "MarketDataProvider",
    "TimeframeAnalysisRequest",
    "TimeframeAnalysisResult",
]
