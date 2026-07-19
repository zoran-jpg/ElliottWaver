from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from elliottwaver.application import (
    ISSUE_CONFLUENCE_CONFLICTS,
    ISSUE_INVALID_HIERARCHY,
    ISSUE_NO_MARKET_DATA,
    ISSUE_NO_SELECTED_CANDIDATES,
    ISSUE_NO_WAVE_CANDIDATES,
    AnalysisClock,
    AnalysisIdProvider,
    AnalysisIssue,
    AnalysisIssueSeverity,
    AnalysisMetadata,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStage,
    AnalyzeMultiTimeframeService,
    AnalyzeMultiTimeframeUseCase,
    AnalyzeTimeframeService,
    AnalyzeTimeframeUseCase,
    CandleToSwingPreparationPort,
    MarketDataProvider,
    TimeframeAnalysisRequest,
    TimeframeAnalysisResult,
)
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.confluence import (
    MultiTimeframeConfluenceAnalyzer,
    MultiTimeframeConfluenceResult,
)
from elliottwaver.domain.detection import DetectionResult, WaveCandidate
from elliottwaver.domain.market import Candle, Pivot, PivotType, Price, Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.multi_timeframe import (
    MultiTimeframeAnalysis,
)
from elliottwaver.domain.multi_timeframe import (
    Timeframe as HierarchyTimeframe,
)
from elliottwaver.domain.rules.wave_rules import RuleResult
from elliottwaver.domain.scoring import (
    ScoreComponent,
    ScoredWaveCandidate,
    ScoringResult,
    WaveScore,
)
from elliottwaver.domain.selection import SelectedWaveCandidate, SelectionReason, SelectionResult
from elliottwaver.domain.trend_hierarchy import TrendHierarchy, TrendNode

ANALYSIS_ID = EntityId.parse("12345678-1234-5678-1234-567812345678")
CORRELATION_ID = "corr-001"
SYMBOL = Symbol("EURUSD")
REQUEST_START = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)
REQUEST_END = datetime(2026, 7, 19, 6, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 7, 19, 0, 5, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 7, 19, 0, 6, tzinfo=UTC)


def make_timeframe(hour: int = 0) -> datetime:
    return datetime(2026, 7, 19, hour, 0, tzinfo=UTC)


def make_candle() -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        opened_at=make_timeframe(),
        open=Price.parse("100"),
        high=Price.parse("110"),
        low=Price.parse("90"),
        close=Price.parse("105"),
        volume=Decimal("1"),
    )


def make_pivot(
    *,
    pivot_id: str,
    timestamp: datetime,
    price: str,
    pivot_type: PivotType,
) -> Pivot:
    return Pivot(
        id=EntityId.parse(pivot_id),
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        timestamp=timestamp,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def make_valid_swings() -> tuple[Swing, ...]:
    pivots = (
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345681",
            timestamp=make_timeframe(0),
            price="100",
            pivot_type=PivotType.LOW,
        ),
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345682",
            timestamp=make_timeframe(1),
            price="120",
            pivot_type=PivotType.HIGH,
        ),
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345683",
            timestamp=make_timeframe(2),
            price="108",
            pivot_type=PivotType.LOW,
        ),
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345684",
            timestamp=make_timeframe(3),
            price="132",
            pivot_type=PivotType.HIGH,
        ),
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345685",
            timestamp=make_timeframe(4),
            price="121",
            pivot_type=PivotType.LOW,
        ),
        make_pivot(
            pivot_id="12345678-1234-5678-1234-567812345686",
            timestamp=make_timeframe(5),
            price="140",
            pivot_type=PivotType.HIGH,
        ),
    )
    return (
        Swing(
            id=EntityId.parse("12345678-1234-5678-1234-567812345691"),
            start_pivot=pivots[0],
            end_pivot=pivots[1],
        ),
        Swing(
            id=EntityId.parse("12345678-1234-5678-1234-567812345692"),
            start_pivot=pivots[1],
            end_pivot=pivots[2],
        ),
        Swing(
            id=EntityId.parse("12345678-1234-5678-1234-567812345693"),
            start_pivot=pivots[2],
            end_pivot=pivots[3],
        ),
        Swing(
            id=EntityId.parse("12345678-1234-5678-1234-567812345694"),
            start_pivot=pivots[3],
            end_pivot=pivots[4],
        ),
        Swing(
            id=EntityId.parse("12345678-1234-5678-1234-567812345695"),
            start_pivot=pivots[4],
            end_pivot=pivots[5],
        ),
    )


def make_wave_candidate() -> WaveCandidate:
    wave = Wave(
        id=EntityId.parse("12345678-1234-5678-1234-567812345700"),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
        swings=make_valid_swings(),
    )
    return WaveCandidate(wave=wave, rule_result=RuleResult())


def make_scored_candidate(score_percent: str = "95") -> ScoredWaveCandidate:
    candidate = make_wave_candidate()
    score = WaveScore(
        total_score=Decimal("1"),
        components=(
            ScoreComponent(
                name="placeholder", weight=Decimal("1"), value=Decimal("1"), max_value=Decimal("1")
            ),
        ),
        percentage=Decimal(score_percent),
    )
    return ScoredWaveCandidate(candidate=candidate, score=score)


def make_selected_candidate(score_percent: str = "95") -> SelectedWaveCandidate:
    scored_candidate = make_scored_candidate(score_percent)
    reason = SelectionReason(
        policy_name="top_score",
        reason_code="highest_score",
        message="Selected highest scored candidate",
        metrics=(("score_percent", scored_candidate.score.percentage),),
    )
    return SelectedWaveCandidate(
        scored_candidate=scored_candidate,
        reasons=(reason,),
        rank=1,
    )


def make_timeframe_analysis_result(
    timeframe: MarketTimeframe,
    *,
    processed: bool,
    selected: bool,
) -> TimeframeAnalysisResult:
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=timeframe,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=50,
    )
    metadata = AnalysisMetadata(
        analysis_id=ANALYSIS_ID,
        correlation_id=CORRELATION_ID,
        requested_at=REQUESTED_AT,
        completed_at=COMPLETED_AT,
        symbol=SYMBOL,
        requested_timeframes=(timeframe,),
        processed_timeframes=(timeframe,) if processed else (),
    )
    if selected:
        candidate = make_wave_candidate()
        detection_result = DetectionResult(candidates=(candidate,))
        scored_candidate = make_scored_candidate()
        scoring_result = ScoringResult(scored_candidates=(scored_candidate,))
        selection_result = SelectionResult(
            selected_candidates=(make_selected_candidate(),),
            policy_name="top_score",
            considered_candidates=1,
        )
    else:
        detection_result = DetectionResult()
        scoring_result = ScoringResult()
        selection_result = SelectionResult(
            selected_candidates=(), policy_name="top_score", considered_candidates=0
        )

    return TimeframeAnalysisResult(
        request=request,
        metadata=metadata,
        candles=(make_candle(),) if processed else (),
        prepared_swings=make_valid_swings() if processed else (),
        detection_result=detection_result,
        scoring_result=scoring_result,
        selection_result=selection_result,
        issues=(),
        stage=AnalysisStage.COMPLETED if selected else AnalysisStage.SELECTION,
    )


def make_response(
    *,
    timeframe_results: tuple[TimeframeAnalysisResult, ...],
    processed_timeframes: tuple[MarketTimeframe, ...],
    stage: AnalysisStage,
    issues: tuple[AnalysisIssue, ...] = (),
    multi_timeframe_analysis: MultiTimeframeAnalysis | None = None,
    trend_hierarchy: TrendHierarchy | None = None,
    confluence_result: MultiTimeframeConfluenceResult | None = None,
) -> AnalysisResponse:
    metadata = AnalysisMetadata(
        analysis_id=ANALYSIS_ID,
        correlation_id=CORRELATION_ID,
        requested_at=REQUESTED_AT,
        completed_at=COMPLETED_AT,
        symbol=SYMBOL,
        requested_timeframes=tuple(result.timeframe for result in timeframe_results),
        processed_timeframes=processed_timeframes,
    )
    return AnalysisResponse(
        metadata=metadata,
        stage=stage,
        timeframe_results=timeframe_results,
        multi_timeframe_analysis=multi_timeframe_analysis,
        trend_hierarchy=trend_hierarchy,
        confluence_result=confluence_result,
        issues=issues,
    )


class StaticClock:
    def __init__(self, instant: datetime) -> None:
        self.instant = instant
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return self.instant


class StaticIdProvider:
    def __init__(self, analysis_id: EntityId) -> None:
        self.analysis_id = analysis_id
        self.calls = 0

    def next_analysis_id(self) -> EntityId:
        self.calls += 1
        return self.analysis_id


class RecordingMarketDataProvider:
    def __init__(self, candles: tuple[Candle, ...]) -> None:
        self.candles = candles
        self.calls: list[tuple[Symbol, MarketTimeframe, datetime, datetime, int | None]] = []

    def load_candles(
        self,
        symbol: Symbol,
        timeframe: MarketTimeframe,
        start_time: datetime,
        end_time: datetime,
        maximum_candles: int | None = None,
    ) -> tuple[Candle, ...]:
        self.calls.append((symbol, timeframe, start_time, end_time, maximum_candles))
        return self.candles


class RecordingSwingPreparationPort:
    def __init__(self, swings: tuple[Swing, ...]) -> None:
        self.swings = swings
        self.calls: list[tuple[tuple[Candle, ...], TimeframeAnalysisRequest]] = []

    def prepare_swings(
        self,
        candles: tuple[Candle, ...],
        request: TimeframeAnalysisRequest,
    ) -> tuple[Swing, ...]:
        self.calls.append((candles, request))
        return self.swings


class EmptyDetector:
    def detect(self, _swings: tuple[Swing, ...]) -> DetectionResult:
        return DetectionResult()


class CandidateDetector:
    def __init__(self, candidates: tuple[WaveCandidate, ...]) -> None:
        self.candidates = candidates

    def detect(self, _swings: tuple[Swing, ...]) -> DetectionResult:
        return DetectionResult(candidates=self.candidates)


class EmptyScorer:
    def score(self, _candidates: tuple[WaveCandidate, ...]) -> ScoringResult:
        return ScoringResult()


class CandidateScorer:
    def __init__(self, scored_candidates: tuple[ScoredWaveCandidate, ...]) -> None:
        self.scored_candidates = scored_candidates

    def score(self, _candidates: tuple[WaveCandidate, ...]) -> ScoringResult:
        return ScoringResult(scored_candidates=self.scored_candidates)


class EmptySelector:
    def select(self, scoring_result: ScoringResult) -> SelectionResult:
        return SelectionResult(
            selected_candidates=(),
            policy_name="top_score",
            considered_candidates=len(scoring_result.scored_candidates),
        )


class CandidateSelector:
    def __init__(self, selected_candidates: tuple[SelectedWaveCandidate, ...]) -> None:
        self.selected_candidates = selected_candidates

    def select(self, scoring_result: ScoringResult) -> SelectionResult:
        return SelectionResult(
            selected_candidates=self.selected_candidates,
            policy_name="top_score",
            considered_candidates=len(scoring_result.scored_candidates),
        )


class TimeframeUseCaseStub:
    def __init__(self, results: dict[MarketTimeframe, TimeframeAnalysisResult]) -> None:
        self.results = results
        self.calls: list[TimeframeAnalysisRequest] = []

    def analyze(self, request: TimeframeAnalysisRequest) -> TimeframeAnalysisResult:
        self.calls.append(request)
        return self.results[request.timeframe]


class InvalidHierarchyBuilder:
    def __init__(self, hierarchy: TrendHierarchy) -> None:
        self.hierarchy = hierarchy

    def build(self, _analysis: MultiTimeframeAnalysis) -> TrendHierarchy:
        return self.hierarchy


def test_timeframe_analysis_request_valid_invalid_and_immutable() -> None:
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=100,
    )

    assert request.maximum_candles == 100

    with pytest.raises(FrozenInstanceError):
        request.__setattr__("maximum_candles", 5)

    with pytest.raises(DomainError, match="timezone-aware UTC"):
        TimeframeAnalysisRequest(
            symbol=SYMBOL,
            timeframe=MarketTimeframe.ONE_DAY,
            start_time=datetime(2026, 7, 19, 0, 0),  # noqa: DTZ001
            end_time=REQUEST_END,
        )

    with pytest.raises(DomainError, match="must be before end_time"):
        TimeframeAnalysisRequest(
            symbol=SYMBOL,
            timeframe=MarketTimeframe.ONE_DAY,
            start_time=REQUEST_END,
            end_time=REQUEST_START,
        )

    with pytest.raises(DomainError, match="greater than zero"):
        TimeframeAnalysisRequest(
            symbol=SYMBOL,
            timeframe=MarketTimeframe.ONE_DAY,
            start_time=REQUEST_START,
            end_time=REQUEST_END,
            maximum_candles=0,
        )


def test_analysis_request_validates_and_normalizes_timeframes() -> None:
    h4 = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.FOUR_HOURS,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=40,
    )
    d1 = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )

    request = AnalysisRequest(
        symbol=SYMBOL,
        timeframe_requests=(h4, d1),
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=80,
        correlation_id="  corr-001  ",
    )

    assert request.timeframes == (MarketTimeframe.ONE_DAY, MarketTimeframe.FOUR_HOURS)
    assert request.maximum_candles_for(MarketTimeframe.FOUR_HOURS) == 40
    assert request.maximum_candles_for(MarketTimeframe.ONE_DAY) == 80
    assert request.correlation_id == CORRELATION_ID

    with pytest.raises(FrozenInstanceError):
        request.__setattr__("maximum_candles", 10)

    with pytest.raises(DomainError, match="must not be empty"):
        AnalysisRequest(
            symbol=SYMBOL,
            timeframe_requests=(),
            start_time=REQUEST_START,
            end_time=REQUEST_END,
        )

    with pytest.raises(DomainError, match="duplicate timeframes"):
        AnalysisRequest(
            symbol=SYMBOL,
            timeframe_requests=(d1, d1),
            start_time=REQUEST_START,
            end_time=REQUEST_END,
        )

    with pytest.raises(DomainError, match="timezone-aware UTC"):
        AnalysisRequest(
            symbol=SYMBOL,
            timeframe_requests=(d1,),
            start_time=datetime(2026, 7, 19, 0, 0),  # noqa: DTZ001
            end_time=REQUEST_END,
        )

    with pytest.raises(DomainError, match="must be before end_time"):
        AnalysisRequest(
            symbol=SYMBOL,
            timeframe_requests=(d1,),
            start_time=REQUEST_END,
            end_time=REQUEST_START,
        )


def test_analysis_issue_validates_severity_timeframe_and_immutability() -> None:
    issue = AnalysisIssue(
        stage=AnalysisStage.SCORING,
        issue_code=ISSUE_NO_SELECTED_CANDIDATES,
        message="No selected candidates",
        severity=AnalysisIssueSeverity.WARNING,
        timeframe=MarketTimeframe.ONE_DAY,
        details=(("score_percent", Decimal("42")),),
    )

    assert issue.stage is AnalysisStage.SCORING
    assert issue.severity is AnalysisIssueSeverity.WARNING
    assert issue.timeframe == MarketTimeframe.ONE_DAY

    with pytest.raises(FrozenInstanceError):
        issue.__setattr__("message", "changed")

    with pytest.raises(DomainError, match="issue_code must not be empty"):
        AnalysisIssue(
            stage=AnalysisStage.SCORING,
            issue_code="",
            message="No selected candidates",
            severity=AnalysisIssueSeverity.WARNING,
        )


def test_analysis_metadata_validates_ranges_and_immutability() -> None:
    metadata = AnalysisMetadata(
        analysis_id=ANALYSIS_ID,
        correlation_id=CORRELATION_ID,
        requested_at=REQUESTED_AT,
        completed_at=COMPLETED_AT,
        symbol=SYMBOL,
        requested_timeframes=(MarketTimeframe.FOUR_HOURS, MarketTimeframe.ONE_DAY),
        processed_timeframes=(MarketTimeframe.ONE_DAY,),
    )

    assert metadata.requested_timeframes == (
        MarketTimeframe.ONE_DAY,
        MarketTimeframe.FOUR_HOURS,
    )
    assert metadata.processed_timeframes == (MarketTimeframe.ONE_DAY,)

    with pytest.raises(FrozenInstanceError):
        metadata.__setattr__("correlation_id", "changed")

    with pytest.raises(DomainError, match="completed_at must not be before requested_at"):
        AnalysisMetadata(
            analysis_id=ANALYSIS_ID,
            correlation_id=CORRELATION_ID,
            requested_at=COMPLETED_AT,
            completed_at=REQUESTED_AT,
            symbol=SYMBOL,
            requested_timeframes=(MarketTimeframe.ONE_DAY,),
            processed_timeframes=(MarketTimeframe.ONE_DAY,),
        )


def test_analysis_response_full_partial_empty_issue_and_immutability() -> None:
    full_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_DAY, processed=True, selected=True
    )
    partial_result = make_timeframe_analysis_result(
        MarketTimeframe.FOUR_HOURS, processed=False, selected=False
    )

    full_response = make_response(
        timeframe_results=(full_result,),
        processed_timeframes=(MarketTimeframe.ONE_DAY,),
        stage=AnalysisStage.COMPLETED,
    )
    partial_response = make_response(
        timeframe_results=(full_result, partial_result),
        processed_timeframes=(MarketTimeframe.ONE_DAY,),
        stage=AnalysisStage.COMPLETED,
    )
    empty_response = make_response(
        timeframe_results=(partial_result,),
        processed_timeframes=(),
        stage=AnalysisStage.MARKET_DATA,
    )
    issue_response = make_response(
        timeframe_results=(full_result,),
        processed_timeframes=(MarketTimeframe.ONE_DAY,),
        stage=AnalysisStage.CONFLUENCE,
        issues=(
            AnalysisIssue(
                stage=AnalysisStage.CONFLUENCE,
                issue_code=ISSUE_CONFLUENCE_CONFLICTS,
                message="Confluence conflicts",
                severity=AnalysisIssueSeverity.CRITICAL,
            ),
        ),
    )

    assert full_response.is_success is True
    assert full_response.is_partial is False
    assert full_response.completed is True
    assert full_response.processed_timeframe_count == 1

    assert partial_response.is_success is False
    assert partial_response.is_partial is True
    assert partial_response.completed is True

    assert empty_response.is_success is False
    assert empty_response.is_partial is False
    assert empty_response.completed is False

    assert issue_response.has_issues is True
    assert issue_response.stage is AnalysisStage.CONFLUENCE

    with pytest.raises(FrozenInstanceError):
        full_response.__setattr__("stage", AnalysisStage.SCORING)


def test_analysis_protocols_accept_simple_fakes() -> None:
    class FakeMarketDataProvider:
        def load_candles(
            self,
            _symbol: Symbol,
            _timeframe: MarketTimeframe,
            _start_time: datetime,
            _end_time: datetime,
            _maximum_candles: int | None = None,
        ) -> tuple[Candle, ...]:
            return ()

    class FakeClock:
        def now(self) -> datetime:
            return REQUESTED_AT

    class FakeIdProvider:
        def next_analysis_id(self) -> EntityId:
            return ANALYSIS_ID

    class FakeSwingPort:
        def prepare_swings(
            self,
            _candles: tuple[Candle, ...],
            _request: TimeframeAnalysisRequest,
        ) -> tuple[Swing, ...]:
            return ()

    class FakeTimeframeUseCase:
        def analyze(self, request: TimeframeAnalysisRequest) -> TimeframeAnalysisResult:
            return make_timeframe_analysis_result(
                request.timeframe, processed=False, selected=False
            )

    class FakeMultiTimeframeUseCase:
        def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
            result = make_timeframe_analysis_result(
                request.timeframes[0], processed=False, selected=False
            )
            return make_response(
                timeframe_results=(result,),
                processed_timeframes=(),
                stage=AnalysisStage.MARKET_DATA,
            )

    assert isinstance(FakeMarketDataProvider(), MarketDataProvider)
    assert isinstance(FakeClock(), AnalysisClock)
    assert isinstance(FakeIdProvider(), AnalysisIdProvider)
    assert isinstance(FakeSwingPort(), CandleToSwingPreparationPort)
    assert isinstance(FakeTimeframeUseCase(), AnalyzeTimeframeUseCase)
    assert isinstance(FakeMultiTimeframeUseCase(), AnalyzeMultiTimeframeUseCase)


def test_analyze_timeframe_service_handles_empty_market_data_and_uses_ports() -> None:
    market_data_provider = RecordingMarketDataProvider(())
    swing_port = RecordingSwingPreparationPort(make_valid_swings())
    clock = StaticClock(REQUESTED_AT)
    id_provider = StaticIdProvider(ANALYSIS_ID)
    service = AnalyzeTimeframeService(
        market_data_provider=market_data_provider,
        swing_preparation_port=swing_port,
        analysis_clock=clock,
        analysis_id_provider=id_provider,
    )
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=25,
    )

    result = service.analyze(request)

    assert result.stage is AnalysisStage.MARKET_DATA
    assert result.has_issues is True
    assert result.issues[0].issue_code == ISSUE_NO_MARKET_DATA
    assert result.metadata.analysis_id == ANALYSIS_ID
    assert result.metadata.requested_at == REQUESTED_AT
    assert result.metadata.completed_at == REQUESTED_AT
    assert result.metadata.processed_timeframes == ()
    assert market_data_provider.calls[0][-1] == 25
    assert swing_port.calls == []
    assert clock.calls == 2
    assert id_provider.calls == 1


def test_analyze_timeframe_service_completes_with_prepared_swings() -> None:
    candles = (make_candle(),)
    market_data_provider = RecordingMarketDataProvider(candles)
    swing_port = RecordingSwingPreparationPort(make_valid_swings())
    clock = StaticClock(REQUESTED_AT)
    id_provider = StaticIdProvider(ANALYSIS_ID)
    service = AnalyzeTimeframeService(
        market_data_provider=market_data_provider,
        swing_preparation_port=swing_port,
        analysis_clock=clock,
        analysis_id_provider=id_provider,
    )
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )

    result = service.analyze(request)

    assert result.stage is AnalysisStage.COMPLETED
    assert result.has_issues is False
    assert result.detection_result.candidates
    assert result.scoring_result.scored_candidates
    assert result.selection_result.selected_candidates
    assert result.metadata.processed_timeframes == (MarketTimeframe.ONE_DAY,)


def test_analyze_timeframe_service_reports_no_candidates_and_no_selection() -> None:
    candles = (make_candle(),)
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )
    service_no_candidates = AnalyzeTimeframeService(
        market_data_provider=RecordingMarketDataProvider(candles),
        swing_preparation_port=RecordingSwingPreparationPort(make_valid_swings()),
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
        detector=cast("Any", EmptyDetector()),
        scorer=cast("Any", EmptyScorer()),
        selector=cast("Any", EmptySelector()),
    )

    no_candidates = service_no_candidates.analyze(request)
    assert no_candidates.stage is AnalysisStage.DETECTION
    assert no_candidates.issues[0].issue_code == ISSUE_NO_WAVE_CANDIDATES

    service_no_selection = AnalyzeTimeframeService(
        market_data_provider=RecordingMarketDataProvider(candles),
        swing_preparation_port=RecordingSwingPreparationPort(make_valid_swings()),
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
        detector=cast("Any", CandidateDetector((make_wave_candidate(),))),
        scorer=cast("Any", CandidateScorer((make_scored_candidate(),))),
        selector=cast("Any", EmptySelector()),
    )

    no_selection = service_no_selection.analyze(request)
    assert no_selection.stage is AnalysisStage.SELECTION
    assert no_selection.issues[0].issue_code == ISSUE_NO_SELECTED_CANDIDATES


def test_analyze_timeframe_service_is_deterministic_and_propagates_programming_errors() -> None:
    request = TimeframeAnalysisRequest(
        symbol=SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )

    deterministic_service = AnalyzeTimeframeService(
        market_data_provider=RecordingMarketDataProvider((make_candle(),)),
        swing_preparation_port=RecordingSwingPreparationPort(make_valid_swings()),
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
    )
    first = deterministic_service.analyze(request)
    second = deterministic_service.analyze(request)
    assert first == second

    class RaisingDetector:
        def detect(self, _swings: tuple[Swing, ...]) -> DetectionResult:
            error_message = "boom"
            raise RuntimeError(error_message)

    exploding_service = AnalyzeTimeframeService(
        market_data_provider=RecordingMarketDataProvider((make_candle(),)),
        swing_preparation_port=RecordingSwingPreparationPort(make_valid_swings()),
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
        detector=cast("Any", RaisingDetector()),
    )

    with pytest.raises(RuntimeError, match="boom"):
        exploding_service.analyze(request)


def test_analyze_multi_timeframe_service_handles_full_partial_empty_and_integration_paths() -> None:
    one_day_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_DAY, processed=True, selected=True
    )
    four_hour_result = make_timeframe_analysis_result(
        MarketTimeframe.FOUR_HOURS, processed=True, selected=True
    )
    one_hour_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_HOUR, processed=False, selected=False
    )

    request = AnalysisRequest(
        symbol=SYMBOL,
        timeframe_requests=(
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.ONE_HOUR,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.ONE_DAY,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
                maximum_candles=60,
            ),
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.FOUR_HOURS,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
        ),
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        maximum_candles=80,
        correlation_id=CORRELATION_ID,
    )

    timeframe_use_case = TimeframeUseCaseStub(
        {
            MarketTimeframe.ONE_HOUR: one_hour_result,
            MarketTimeframe.ONE_DAY: one_day_result,
            MarketTimeframe.FOUR_HOURS: four_hour_result,
        }
    )
    service = AnalyzeMultiTimeframeService(
        timeframe_use_case=timeframe_use_case,
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
    )

    response = service.analyze(request)

    assert [result.timeframe for result in response.timeframe_results] == [
        MarketTimeframe.ONE_DAY,
        MarketTimeframe.FOUR_HOURS,
        MarketTimeframe.ONE_HOUR,
    ]
    assert response.metadata.requested_timeframes == (
        MarketTimeframe.ONE_DAY,
        MarketTimeframe.FOUR_HOURS,
        MarketTimeframe.ONE_HOUR,
    )
    assert response.metadata.processed_timeframes == (
        MarketTimeframe.ONE_DAY,
        MarketTimeframe.FOUR_HOURS,
    )
    assert response.is_partial is True
    assert response.processed_timeframe_count == 2
    assert response.multi_timeframe_analysis is not None
    assert response.trend_hierarchy is not None
    assert response.confluence_result is not None
    assert response.stage in (AnalysisStage.CONFLUENCE, AnalysisStage.COMPLETED)

    assert len(timeframe_use_case.calls) == 3
    assert timeframe_use_case.calls[0].maximum_candles == 60
    assert timeframe_use_case.calls[1].maximum_candles == 80
    assert timeframe_use_case.calls[2].maximum_candles == 80

    identical_response = service.analyze(request)
    assert response == identical_response

    request = AnalysisRequest(
        symbol=SYMBOL,
        timeframe_requests=(
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.ONE_DAY,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
        ),
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )
    no_success_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_DAY,
        processed=False,
        selected=False,
    )
    no_success_use_case = TimeframeUseCaseStub({MarketTimeframe.ONE_DAY: no_success_result})
    no_success_response = AnalyzeMultiTimeframeService(
        timeframe_use_case=no_success_use_case,
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
    ).analyze(request)
    assert no_success_response.multi_timeframe_analysis is None
    assert no_success_response.trend_hierarchy is None
    assert no_success_response.confluence_result is None
    assert no_success_response.processed_timeframe_count == 0
    assert no_success_response.is_partial is False


def test_analyze_multi_timeframe_service_uses_hierarchy_and_confluence_and_reports_issues() -> None:
    one_day_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_DAY, processed=True, selected=True
    )
    four_hour_result = make_timeframe_analysis_result(
        MarketTimeframe.FOUR_HOURS, processed=True, selected=True
    )

    node_one = TrendNode(
        timeframe=HierarchyTimeframe.parse("D1"),
        selected_wave_candidate=one_day_result.selection_result.selected_candidates[0],
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=REQUESTED_AT,
    )
    node_two = TrendNode(
        timeframe=HierarchyTimeframe.parse("H4"),
        selected_wave_candidate=four_hour_result.selection_result.selected_candidates[0],
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=REQUESTED_AT,
    )
    invalid_hierarchy = TrendHierarchy(
        nodes=(node_two, node_one),
        relations=(),
    )

    timeframe_use_case = TimeframeUseCaseStub(
        {
            MarketTimeframe.ONE_DAY: one_day_result,
            MarketTimeframe.FOUR_HOURS: four_hour_result,
        }
    )
    service = AnalyzeMultiTimeframeService(
        timeframe_use_case=timeframe_use_case,
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
        trend_hierarchy_builder=cast("Any", InvalidHierarchyBuilder(invalid_hierarchy)),
        confluence_analyzer=MultiTimeframeConfluenceAnalyzer(),
    )
    request = AnalysisRequest(
        symbol=SYMBOL,
        timeframe_requests=(
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.ONE_DAY,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.FOUR_HOURS,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
        ),
        start_time=REQUEST_START,
        end_time=REQUEST_END,
    )

    response = service.analyze(request)

    assert response.trend_hierarchy is not None
    assert response.trend_hierarchy.is_valid is False
    assert response.confluence_result is not None
    assert response.confluence_result.has_conflicts is True
    assert any(issue.issue_code == ISSUE_INVALID_HIERARCHY for issue in response.issues)
    assert any(issue.issue_code == ISSUE_CONFLUENCE_CONFLICTS for issue in response.issues)


def test_analyze_multi_timeframe_service_is_deterministic_and_preserves_inputs() -> None:
    one_day_result = make_timeframe_analysis_result(
        MarketTimeframe.ONE_DAY, processed=True, selected=True
    )
    request = AnalysisRequest(
        symbol=SYMBOL,
        timeframe_requests=(
            TimeframeAnalysisRequest(
                symbol=SYMBOL,
                timeframe=MarketTimeframe.ONE_DAY,
                start_time=REQUEST_START,
                end_time=REQUEST_END,
            ),
        ),
        start_time=REQUEST_START,
        end_time=REQUEST_END,
        correlation_id=CORRELATION_ID,
    )
    use_case = TimeframeUseCaseStub({MarketTimeframe.ONE_DAY: one_day_result})
    service = AnalyzeMultiTimeframeService(
        timeframe_use_case=use_case,
        analysis_clock=StaticClock(REQUESTED_AT),
        analysis_id_provider=StaticIdProvider(ANALYSIS_ID),
    )

    first = service.analyze(request)
    second = service.analyze(request)

    assert first == second
    assert request.timeframe_requests[0].maximum_candles is None
    assert use_case.calls[0].maximum_candles is None
    assert use_case.calls[1].maximum_candles is None
