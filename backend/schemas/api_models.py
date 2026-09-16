"""
Pydantic Schemas for Indian Railways AI Section Controller REST API.
Includes Weather-Aware Optimization and Platform Management Models.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum, IntEnum


class TrainPriorityEnum(IntEnum):
    EMERGENCY = 1
    PREMIUM_EXPRESS = 2
    EXPRESS = 3
    MAINTENANCE = 4
    FREIGHT = 5


class TrainStatusEnum(str, Enum):
    ON_TIME = "ON TIME"
    DELAYED = "DELAYED"
    REGULATED = "REGULATED"
    RUNNING = "RUNNING"


class TrainDirectionEnum(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class WeatherRiskEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ============================================================
# SECTION & WEATHER SCHEMAS
# ============================================================

class SectionInfo(BaseModel):
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    section_name: str = Field(..., example="Kanpur Central - Prayagraj Junction (Down Line)")
    status: str = Field("CLEAR", example="CLEAR")
    length_km: float = Field(..., example=42.5)
    start_km: float = Field(400.0, example=400.0)
    end_km: float = Field(442.5, example=442.5)
    max_capacity_tph: int = Field(12, example=12)
    signals: str = Field("AUTOMATIC_BLOCK_SIGNALING", example="AUTOMATIC_BLOCK_SIGNALING")
    speed_limit_kmph: int = Field(130, example=130)
    active_trains: List[str] = Field(default_factory=list)


class SectionWeather(BaseModel):
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    temperature_c: float = Field(..., example=28.5)
    rain_probability_pct: int = Field(..., example=20)
    rainfall_intensity_mmh: float = Field(..., example=0.0)
    wind_speed_kmph: float = Field(..., example=14.0)
    visibility_km: float = Field(..., example=8.5)
    weather_condition: str = Field("Clear", example="Clear")
    weather_risk: WeatherRiskEnum = Field(WeatherRiskEnum.LOW, example="LOW")
    weather_score: int = Field(15, description="0-100 hazard rating", example=15)
    weather_reason: str = Field("Favorable weather conditions for all track operations.", example="Favorable conditions.")
    weather_source: str = Field("CALIBRATED_CLIMATE_MODEL", example="CALIBRATED_CLIMATE_MODEL")
    air_quality_index: Optional[int] = Field(68, description="Air Quality Index (US AQI)")
    air_quality_label: Optional[str] = Field("Moderate", description="Air quality condition summary")
    observed_at: str = Field(..., example="2026-08-27T15:00:00")
    forecast: List[Dict[str, Any]] = Field(default_factory=list)
    humidity_pct: Optional[float] = Field(None, description="Relative humidity percentage (%)")
    weather_icon: Optional[str] = Field("🌤️", description="WMO weather condition icon")
    station_name: Optional[str] = Field("Kanpur Central - Prayagraj", description="Station or region name")


# ============================================================
# TRAIN & PLATFORM SCHEMAS
# ============================================================

class TrainDetails(BaseModel):
    train_number: str = Field(..., example="22436")
    name: str = Field(..., example="Vande Bharat Express")
    priority: int = Field(2, example=2)
    entry_min: int = Field(..., description="Minutes past midnight (0-1440)", example=630)
    exit_min: int = Field(..., description="Minutes past midnight (0-1440)", example=660)
    entry_time: str = Field(..., example="10:30")
    exit_time: str = Field(..., example="11:00")
    position_km: float = Field(..., example=414.2)
    speed_kmph: float = Field(..., example=112.0)
    direction: TrainDirectionEnum = Field(TrainDirectionEnum.UP, example="UP")
    status: TrainStatusEnum = Field(TrainStatusEnum.ON_TIME, example="ON TIME")
    section_id: Optional[str] = Field("KNP-PRYJ-SEC-B", example="KNP-PRYJ-SEC-B")
    # Platform management fields
    platform_number: Optional[int] = Field(3, example=3)
    platform_status: Optional[str] = Field("ASSIGNED", example="ASSIGNED")
    platform_capacity: Optional[int] = Field(24, example=24)
    platform_available_from: Optional[str] = Field(None, example="10:00")
    platform_available_until: Optional[str] = Field(None, example="11:30")
    # Platform change tracking
    previous_platform_number: Optional[int] = Field(None, description="Previous platform before reassignment")
    # GPS & telemetry
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    telemetry_timestamp: Optional[str] = None
    data_source: str = Field("SIMULATED", example="SIMULATED")
    data_age_seconds: int = Field(0, ge=0)
    stale: bool = False
    current_station: Optional[str] = None
    next_station: Optional[str] = None
    eta_next_station: Optional[str] = None
    eta_minutes: Optional[int] = None
    # ML Prediction fields
    congestion_level: Optional[str] = Field(None, description="Predicted crowding: LOW / MEDIUM / HIGH")
    predicted_delay_minutes: Optional[int] = Field(None, description="ML-predicted delay in minutes")
    delay_minutes: Optional[int] = Field(0, description="Current reported delay in minutes")
    delay_reason: Optional[str] = Field(None, description="Human-readable delay cause")



class PlatformConflictItem(BaseModel):
    platform_number: int
    train_a: str
    train_b: str
    window_a: str
    window_b: str
    overlap_minutes: int
    severity: str = "MODERATE"  # "CRITICAL", "MODERATE", "LOW"
    recommended_alternate_platform: Optional[int] = None
    reason: str


class PlatformConflictRequest(BaseModel):
    section_id: str = Field("KNP-PRYJ-SEC-B", example="KNP-PRYJ-SEC-B")
    train_number: Optional[str] = None


class PlatformConflictResponse(BaseModel):
    section_id: str
    has_conflict: bool
    conflict_count: int
    conflicts: List[PlatformConflictItem] = Field(default_factory=list)
    available_platforms: List[int] = Field(default_factory=list)
    status: str


class PlatformStatusResponse(BaseModel):
    section_id: str
    source: str
    platforms: List[TrainDetails] = Field(default_factory=list)
    conflicts: List[PlatformConflictItem] = Field(default_factory=list)
    available_platforms: List[int] = Field(default_factory=list)


class TrainPredictionRequest(BaseModel):
    train_number: str = Field(..., example="22436")
    seconds_since_update: int = Field(0, description="Elapsed seconds without telemetry", example=120)


class TrainTelemetryIngestRequest(BaseModel):
    train_number: str
    section_id: str = "KNP-PRYJ-SEC-B"
    gps_lat: float
    gps_lon: float
    timestamp: str
    speed_kmph: float = Field(..., ge=0, le=300)
    direction: TrainDirectionEnum
    current_station: Optional[str] = None
    next_station: Optional[str] = None
    position_km: Optional[float] = Field(None, ge=0)


class TrainTelemetryIngestResponse(BaseModel):
    status: str
    train_number: str
    data_source: str
    telemetry_timestamp: str
    eta_next_station: Optional[str] = None
    eta_minutes: Optional[int] = None


class TrainPredictionResponse(BaseModel):
    train_number: str
    original_position_km: float
    predicted_position_km: float
    speed_kmph: float
    direction: str
    confidence_pct: float
    source: str


class TrainETAPredictionRequest(BaseModel):
    train_id: str = Field(..., example="22436")
    current_station: Optional[str] = None
    next_station: Optional[str] = None
    destination: Optional[str] = None
    position_km: Optional[float] = None
    destination_km: Optional[float] = None
    speed_kmph: Optional[float] = None
    delay_minutes: Optional[int] = 0
    weather_risk: Optional[str] = "LOW"
    congestion_level: Optional[str] = "LOW"
    priority: Optional[int] = 3
    model_name: Optional[str] = Field("best_model", description="Model to use: best_model, ensemble, xgboost, random_forest, svr, gradient_boosting, decision_tree")


class TrainETAPredictionResponse(BaseModel):
    train_id: str
    current_station: Optional[str] = None
    next_station: Optional[str] = None
    destination: Optional[str] = None
    predicted_remaining_travel_time: int = Field(..., description="Predicted remaining travel time in minutes")
    predicted_arrival_time: str = Field(..., description="Expected arrival time HH:MM")
    delay_estimate: int = Field(..., description="Estimated delay in minutes")
    confidence: float = Field(..., description="Prediction confidence score")
    prediction_status: str = Field(..., description="NOMINAL, DELAYED, ARRIVED, STOPPED, or FALLBACK")
    model_used: str = Field("XGBoost", description="Model used for ETA inference")
    model_predictions: Optional[Dict[str, float]] = Field(None, description="Predictions from all available models")
    prediction_method: Optional[str] = Field(None, description="ML_MULTI_MODEL or PHYSICS_FALLBACK")


class ModelPerformanceResponse(BaseModel):
    best_individual_model: Optional[str] = None
    selected_production_model: Optional[str] = None
    ensemble_weights: Optional[Dict[str, float]] = None
    models: Optional[Dict[str, Any]] = None
    ensemble_improved_over_best: Optional[bool] = None
    training_timestamp: Optional[str] = None


class DataProvenanceEnum(str, Enum):
    SIMULATED = "SIMULATED"
    LIVE_GPS = "LIVE_GPS"
    CALIBRATED_FALLBACK = "CALIBRATED_FALLBACK"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    GOVT_OPEN_FEED = "GOVT_OPEN_FEED"


class OperationalModeEnum(str, Enum):
    ADVISORY_DECISION_SUPPORT = "ADVISORY_DECISION_SUPPORT"
    SIMULATED_TESTBED = "SIMULATED_TESTBED"
    OFFLINE_BENCHMARK = "OFFLINE_BENCHMARK"


class NormalizedTrainState(BaseModel):
    train_number: str = Field(..., example="22436")
    timestamp: str = Field(..., description="ISO 8601 timestamp of observation")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_speed_kmph: float = Field(..., ge=0, le=300)
    direction: TrainDirectionEnum = TrainDirectionEnum.UP
    current_station: Optional[str] = None
    next_station: Optional[str] = None
    remaining_distance_km: float = Field(0.0, ge=0)
    current_delay_minutes: int = Field(0, ge=0)
    track_section: str = Field("KNP-PRYJ-SEC-B")
    congestion_status: str = Field("LOW", description="LOW, MEDIUM, or HIGH")
    data_source: DataProvenanceEnum = DataProvenanceEnum.SIMULATED
    data_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Sensor & telemetry confidence score")
    stale_status: bool = False
    train_mass_tonnes: float = Field(1400.0, ge=100.0, le=10000.0, description="Estimated train and rake trailing mass")
    track_gradient_pct: float = Field(0.0, ge=-5.0, le=5.0, description="Rising (+) or falling (-) track gradient")


class OperationalReadinessReport(BaseModel):
    system_name: str = "RailTrack AI Section Controller & Block Planner"
    system_version: str = "3.0.0"
    operational_mode: OperationalModeEnum = OperationalModeEnum.ADVISORY_DECISION_SUPPORT
    safety_classification: str = "NON_VITAL_ADVISORY_DSS"
    sil_certification_status: str = "NOT_SIL_CERTIFIED_REQUIRES_HUMAN_IN_THE_LOOP"
    primary_ml_model: str = "XGBoost Regressor (IR-XGB-DelayPredictor-v3.0)"
    supported_sections: List[str] = Field(default_factory=lambda: ["KNP-PRYJ-SEC-B", "NDLS-JAT-CORRIDOR"])
    telemetry_sources_active: List[str] = Field(default_factory=list)
    human_in_the_loop_mandatory: bool = True
    disclaimer: str = (
        "RailTrack is an advisory decision support system designed to assist section controllers. "
        "It does not operate as an autonomous fail-safe interlocking controller (CENELEC SIL-4) "
        "and does not directly interface with safety-critical signaling apparatus without human verification."
    )


# ============================================================
# CONFLICT & OPTIMIZER SCHEMAS
# ============================================================

class ConflictCheckRequest(BaseModel):
    section_id: str = Field("KNP-PRYJ-SEC-B", example="KNP-PRYJ-SEC-B")
    proposed_start_min: int = Field(..., ge=0, le=1440, example=600)
    proposed_end_min: int = Field(..., ge=0, le=1440, example=900)


class ConflictItem(BaseModel):
    train: str
    priority: int
    overlap_minutes: int
    train_window: str


class ConflictCheckResponse(BaseModel):
    section_id: str
    proposed_window: str
    has_conflict: bool
    conflict_count: int
    conflicting_trains: List[ConflictItem]
    status: str


class BlockOptimizationRequest(BaseModel):
    block_id: str = Field("MNT-KNP-04", example="MNT-KNP-04")
    section_id: str = Field("KNP-PRYJ-SEC-B", example="KNP-PRYJ-SEC-B")
    duration_minutes: int = Field(120, ge=15, le=360, example=120)
    earliest_start_min: int = Field(600, ge=0, le=1440, description="10:00 AM (600 mins)", example=600)
    latest_end_min: int = Field(900, ge=0, le=1440, description="03:00 PM (900 mins)", example=900)
    work_type: Optional[str] = Field("Rail Replacement", example="Rail Replacement")
    override_weather_risk: Optional[str] = Field(None, description="Optional override for testing weather impact (LOW/MEDIUM/HIGH/EXTREME)")
    override_platform_conflict: Optional[bool] = Field(None, description="Optional override for testing platform conflict scenarios")


class AffectedTrainInfo(BaseModel):
    train_number: str
    name: str
    priority: int
    scheduled_window: str
    delay_minutes: int
    action: str = "REGULATE_HOLD_AT_PRECEDING_STATION"
    platform_number: Optional[int] = None
    platform_reassigned_to: Optional[int] = None


class AlternativeSlot(BaseModel):
    start_min: int
    end_min: int
    formatted_window: str
    affected_trains: List[AffectedTrainInfo] = Field(default_factory=list)
    total_delay_min: int
    weighted_cost: float
    risk_level: str = "LOW"  # "LOW", "MEDIUM", "HIGH"
    recommendation_confidence_pct: float
    weather_risk: str = "LOW"
    weather_score: int = 15
    platform_conflicts: int = 0
    platform_reassignments: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


class BlockOptimizationResponse(BaseModel):
    block_id: str
    section_id: str
    status: str  # "OPTIMAL_SCHEDULED" or "NO_FEASIBLE_SLOT"
    allocated_start_min: Optional[int] = None
    allocated_end_min: Optional[int] = None
    formatted_window: Optional[str] = None
    duration_minutes: int
    safety_buffer_minutes: int = 5
    affected_trains: List[AffectedTrainInfo] = Field(default_factory=list)
    total_delay_min: int = 0
    weighted_cost: Optional[float] = None
    risk_level: Optional[str] = None
    recommendation_confidence_pct: Optional[float] = None
    asset_availability_gain: Optional[str] = None
    # Weather-Aware Optimization Metadata
    weather_risk: Optional[str] = "LOW"
    weather_score: Optional[int] = 15
    weather_reason: Optional[str] = None
    weather_source: Optional[str] = "CALIBRATED_CLIMATE_MODEL"
    weather_observed_at: Optional[str] = None
    # Platform-Aware Optimization Metadata
    platform_conflicts: int = 0
    platform_reassignments: List[str] = Field(default_factory=list)
    optimization_reason: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    alternatives: List[AlternativeSlot] = Field(default_factory=list)
    message: Optional[str] = None


class CommitBlockRequest(BaseModel):
    block_id: str = Field(..., example="MNT-KNP-04")
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    start_min: int = Field(..., example=755)
    end_min: int = Field(..., example=875)
    work_type: Optional[str] = Field("Rail Replacement", example="Rail Replacement")


class CommitBlockResponse(BaseModel):
    status: str = "SUCCESS"
    transaction_id: str
    block_id: str
    section_id: str
    start_time: str
    end_time: str
    committed_at: str
    caution_board_notice: str


class AIChatRequest(BaseModel):
    message: str = Field(..., example="Check Kanpur-Prayagraj section for any block conflicts between 10:00 and 15:00.")
    conversation_history: Optional[List[Dict[str, str]]] = None


class AIChatResponse(BaseModel):
    reply: str
    suggested_actions: List[str] = Field(default_factory=list)
