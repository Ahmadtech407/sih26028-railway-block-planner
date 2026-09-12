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

        if direction == TrainDirectionEnum.UP:
            position = train["position_km"] + distance
        else:
            position = train["position_km"] - distance

        position = max(400.0, min(442.5, position))

        return {
            "train_number": train_number,
            "gps_lat": train.get("gps_lat"),
            "gps_lon": train.get("gps_lon"),
            "speed_kmph": train.get("speed_kmph", 0),
            "direction": direction,
            "position_km": position,
            "section_id": train.get("section_id"),
            "telemetry_timestamp": now.isoformat(),
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
            return live_govt_data

        # 2. Fall back to calibrated kinematic simulation
        return self._simulator.get_live_position(train_number)