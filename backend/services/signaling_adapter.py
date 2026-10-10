"""
Signaling and Interlocking Boundary Adapter.

Indian Railways AI Section Controller & Block Planner (SIH26028).

SAFETY BOUNDARY ARCHITECTURE:
1. This prototype is an Advisory Decision Support System (ADSS) and is strictly NON-VITAL.
2. It does NOT possess CENELEC EN 50128 / EN 50129 SIL-4 safety certification.
3. It CANNOT directly clear signals, lock/unlock routes, or grant track possession.
4. When no authorized physical Electronic Interlocking (EI) or Axle Counter adapter
   is connected, it declares STATUS: NOT_CONNECTED and blocks operational authorization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SignalingIntegrationMode(str, Enum):
    NOT_CONNECTED = "NOT_CONNECTED"
    SIMULATED_LAB = "SIMULATED_LAB"
    AUTHORIZED_EI_FEED = "AUTHORIZED_EI_FEED"


class InterlockingStatus(BaseModel):
    adapter_id: str = "EI-ADAPTER-NULL"
    mode: SignalingIntegrationMode = SignalingIntegrationMode.NOT_CONNECTED
    is_live_authorized: bool = False
    connected_hardware: Optional[str] = None
    sil_certified: bool = False
    certification_standard: str = "NON_VITAL_ADVISORY_ONLY (NOT SIL-4)"
    last_heartbeat: Optional[str] = None
    signal_aspect_control_enabled: bool = False
    route_locking_control_enabled: bool = False
    message: str = (
        "Signaling adapter NOT CONNECTED to live interlocking. "
        "RailTrack is an offline advisory planner and cannot verify track clear status independently."
    )


class RouteLockVerification(BaseModel):
    section_id: str
    track_id: str
    route_id: Optional[str] = None
    verified_isolated: bool = False
    interlocking_source: str = "NONE"
    rejection_reason: Optional[str] = None


class SignalingAdapter:
    """
    Interface boundary for future Electronic Interlocking (EI) and Axle Counter adapters.
    Defaults to safe, disconnected, non-vital state.
    """

    def __init__(self):
        self._mode = SignalingIntegrationMode.NOT_CONNECTED
        self._live_key = None
        self._connected = False

    def get_status(self) -> InterlockingStatus:
        """Returns the current operational status of the signaling boundary."""
        return InterlockingStatus(
            adapter_id="EI-ADAPTER-STUB-v2",
            mode=self._mode,
            is_live_authorized=self._connected and self._mode == SignalingIntegrationMode.AUTHORIZED_EI_FEED,
            connected_hardware=None,
            sil_certified=False,
            certification_standard="CENELEC EN 50126/50128 NOT SATISFIED - ADVISORY DSS ONLY",
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
            signal_aspect_control_enabled=False,
            route_locking_control_enabled=False,
            message=(
                "AUTHORITATIVE SIGNALING NOT CONNECTED. All route locking, track occupancy, "
                "and signal aspects shown in RailTrack are advisory or simulated. "
                "Operational track possession must not be authorized based on software state alone."
            ),
        )

    def get_signaling_status(self) -> Dict[str, Any]:
        """Dictionary representation of signaling boundary status for API and tests."""
        st = self.get_status()
        return {
            "status": st.mode.value,
            "mode": f"NON_VITAL_ADVISORY ({st.mode.value})",
            "vital_interlocking_authorized": st.is_live_authorized,
            "signal_control_permitted": st.signal_aspect_control_enabled,
            "sil_certified": st.sil_certified,
            "certification_standard": st.certification_standard,
            "message": st.message,
        }

    def verify_route_isolation(self, section_id: str, track_id: str) -> RouteLockVerification:
        """
        Safety check called before track block authorization.
        Fails closed: if no verified live interlocking feed exists, returns verified_isolated=False.
        """
        if self._mode != SignalingIntegrationMode.AUTHORIZED_EI_FEED or not self._connected:
            return RouteLockVerification(
                section_id=section_id,
                track_id=track_id,
                verified_isolated=False,
                interlocking_source="DISCONNECTED_STUB",
                rejection_reason=(
                    "External Electronic Interlocking (EI) not connected. "
                    "Physical route isolation cannot be independently confirmed by software."
                ),
            )

        return RouteLockVerification(
            section_id=section_id,
            track_id=track_id,
            verified_isolated=True,
            interlocking_source="AUTHORIZED_EI",
        )


signaling_adapter = SignalingAdapter()
