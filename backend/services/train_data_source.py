from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class TrainDataSource(ABC):

    @abstractmethod
    def get_live_position(
        self, train_number: str
    ) -> Optional[Dict[str, Any]]:
        """Return normalized live train data."""
        pass


class SimulatorDataSource(TrainDataSource):

    def get_live_position(self, train_number: str):
        from backend.services.train_service import (
            LIVE_TRAINS_DB,
            SIMULATOR_STARTED_AT,
        )
        from backend.schemas.api_models import TrainDirectionEnum
        from datetime import datetime, timezone

        train = LIVE_TRAINS_DB.get(train_number)

        if not train:
            return None

        now = datetime.now(timezone.utc)

        elapsed_seconds = max(
            0,
            int((now - SIMULATOR_STARTED_AT).total_seconds())
        )

        direction = train["direction"]

        distance = (
            train["speed_kmph"] * elapsed_seconds / 3600.0
        )

        # Dynamic section boundary resolution
        sec_id = train.get("section_id", "KNP-PRYJ-SEC-B")
        try:
            from backend.services.section_service import SECTION_DATABASE
            sec_meta = SECTION_DATABASE.get(sec_id, {})
            start_bound = float(sec_meta.get("start_km", 400.0))
            end_bound = float(sec_meta.get("end_km", 442.5))
        except Exception:
            start_bound, end_bound = 400.0, 442.5

        if direction == TrainDirectionEnum.UP:
            position = train["position_km"] + distance
        else:
            position = train["position_km"] - distance

        position = max(start_bound, min(end_bound, position))

        return {
            "train_number": train_number,
            "gps_lat": train.get("gps_lat"),
            "gps_lon": train.get("gps_lon"),
            "speed_kmph": train.get("speed_kmph", 0),
            "direction": direction,
            "position_km": position,
            "section_id": sec_id,
            "telemetry_timestamp": now.isoformat(),
            "data_source": "SIMULATED",
        }


class GovtRailwayDataSource(TrainDataSource):
    """
    Data source that integrates real running status from Government of India
    (CRIS / NTES / data.gov.in) if credentials or telemetry are provided,
    with automatic seamless fallback to calibrated simulation.
    """

    def __init__(self):
        self._simulator = SimulatorDataSource()

    def get_live_position(self, train_number: str) -> Optional[Dict[str, Any]]:
        from backend.services import govt_railway_service

        # 1. Attempt to fetch real running data from Government of India feed
        live_govt_data = govt_railway_service.fetch_live_train_status(train_number)
        if live_govt_data:
            live_govt_data["data_source"] = live_govt_data.get("data_source") or "GOVT_OF_INDIA_CRIS"
            return live_govt_data

        # 2. Fall back to calibrated kinematic simulation
        sim_data = self._simulator.get_live_position(train_number)
        if sim_data:
            sim_data["data_source"] = "SIMULATED"
        return sim_data


# Aliases for provider architecture specification
TrainDataProvider = TrainDataSource
SimulationProvider = SimulatorDataSource
RealTelemetryProvider = GovtRailwayDataSource


def get_train_data_source() -> TrainDataSource:
    """Factory returning configured railway telemetry provider."""
    import os
    mode = os.getenv("RAILWAY_DATA_MODE", "AUTO").upper()
    if mode == "SIMULATION":
        return SimulatorDataSource()
    return GovtRailwayDataSource()
