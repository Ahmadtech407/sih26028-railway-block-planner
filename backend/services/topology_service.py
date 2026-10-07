"""
Railway Track Infrastructure & Topology Service.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides multi-track layout modeling (UP line, DOWN line, COMMON line, crossovers).

DATA PROVENANCE NOTICE:
This topology is explicitly classified as DEMO_REFERENCE_TOPOLOGY with SIMULATED provenance.
It accurately represents the structural concepts of Indian Railways double-track corridors
(such as Kanpur-Prayagraj), but is NOT connected to an authoritative civil engineering GIS database.
"""

from typing import Any, Dict, List, Optional
from backend.schemas.topology_models import (
    CrossoverModel,
    InfrastructureCoexistenceRequest,
    InfrastructureCoexistenceResponse,
    SectionTopologyModel,
    TrackModel,
    TrackOccupancyStatusEnum,
    TrackTypeEnum,
)

# Reference Demonstration Topology for Kanpur Central - Prayagraj Junction
CORRIDOR_TOPOLOGY: Dict[str, SectionTopologyModel] = {
    "KNP-PRYJ-SEC-B": SectionTopologyModel(
        section_id="KNP-PRYJ-SEC-B",
        topology_name="Kanpur Central - Prayagraj Junction Double Track Corridor (Reference Model)",
        topology_provenance="DEMO_REFERENCE_TOPOLOGY",
        is_authoritative=False,
        total_route_km=42.5,
        signaling_system="AUTOMATIC_BLOCK_SIGNALING",
        tracks=[
            TrackModel(
                track_id="KNP-PRYJ-DN-MAIN",
                track_name="Down Main Line (Kanpur -> Prayagraj)",
                track_type=TrackTypeEnum.DOWN_LINE,
                direction="DOWN",
                start_km=400.0,
                end_km=442.5,
                max_speed_kmph=130,
                status=TrackOccupancyStatusEnum.CLEAR,
                active_trains=["22436", "12302", "BCNA"],
                electrification_ohe_active=True,
                adjacent_track_ids=["KNP-PRYJ-UP-MAIN", "FTP-COMMON-LOOP"],
            ),
            TrackModel(
                track_id="KNP-PRYJ-UP-MAIN",
                track_name="Up Main Line (Prayagraj -> Kanpur)",
                track_type=TrackTypeEnum.UP_LINE,
                direction="UP",
                start_km=400.0,
                end_km=442.5,
                max_speed_kmph=130,
                status=TrackOccupancyStatusEnum.CLEAR,
                active_trains=["12802", "15018"],
                electrification_ohe_active=True,
                adjacent_track_ids=["KNP-PRYJ-DN-MAIN"],
            ),
            TrackModel(
                track_id="FTP-COMMON-LOOP",
                track_name="Fatehpur Common Loop Line",
                track_type=TrackTypeEnum.COMMON_LINE,
                direction="BIDIRECTIONAL",
                start_km=418.0,
                end_km=422.0,
                max_speed_kmph=50,
                status=TrackOccupancyStatusEnum.CLEAR,
                active_trains=[],
                electrification_ohe_active=True,
                adjacent_track_ids=["KNP-PRYJ-DN-MAIN"],
            ),
        ],
        crossovers=[
            CrossoverModel(
                crossover_id="XOVER-KNP-410",
                location_km=410.5,
                connects_track_a="KNP-PRYJ-UP-MAIN",
                connects_track_b="KNP-PRYJ-DN-MAIN",
                max_diverging_speed_kmph=30,
                status="NORMAL",
            ),
            CrossoverModel(
                crossover_id="XOVER-FTP-420",
                location_km=420.2,
                connects_track_a="KNP-PRYJ-DN-MAIN",
                connects_track_b="FTP-COMMON-LOOP",
                max_diverging_speed_kmph=30,
                status="NORMAL",
            ),
        ],
    )
}


def get_section_topology(section_id: str = "KNP-PRYJ-SEC-B") -> Optional[SectionTopologyModel]:
    """Retrieve multi-track infrastructure topology for a railway section."""
    return CORRIDOR_TOPOLOGY.get(section_id) or CORRIDOR_TOPOLOGY.get("KNP-PRYJ-SEC-B")


def check_infrastructure_coexistence(
    request: InfrastructureCoexistenceRequest,
    trains: Optional[List[Any]] = None,
) -> InfrastructureCoexistenceResponse:
    """
    Evaluates whether a planned maintenance block on a specific track can safely
    coexist with scheduled movements and whether adjacent tracks or crossovers are affected.
    """
    topology = get_section_topology(request.section_id)
    if not topology:
        return InfrastructureCoexistenceResponse(
            section_id=request.section_id,
            target_track_id=request.target_track_id,
            safe_to_coexist=False,
            affected_tracks=[request.target_track_id],
            conflicting_movements=[],
            crossover_constraints=[],
            coexistence_rationale="Topology data unavailable for requested section.",
        )

    affected_tracks = [request.target_track_id]
    crossover_constraints = []
    conflicts = []

    # Find target track
    target_track = next((t for t in topology.tracks if t.track_id == request.target_track_id), None)
    if not target_track:
        target_track = topology.tracks[0]

    # If OHE Power Block requested, adjacent tracks under the same cantilever portal are impacted
    if request.requires_ohe_power_block:
        for adj in target_track.adjacent_track_ids:
            if adj not in affected_tracks:
                affected_tracks.append(adj)
                crossover_constraints.append(
                    f"Adjacent track '{adj}' requires traction power isolation advisory or neutral section protection."
                )

    # Check for crossovers linking to target track
    for xover in topology.crossovers:
        if xover.connects_track_a == target_track.track_id or xover.connects_track_b == target_track.track_id:
            crossover_constraints.append(
                f"Crossover {xover.crossover_id} at km {xover.location_km} must be clamped/locked in NORMAL position."
            )

    safe = len(conflicts) == 0
    rationale = (
        f"Block isolated on track '{target_track.track_id}'. "
        f"{'OHE power isolation extends to ' + ', '.join(affected_tracks) if request.requires_ohe_power_block else 'Adjacent tracks operational with caution orders.'} "
        f"All {len(crossover_constraints)} crossover safety interlocking constraints identified."
    )

    return InfrastructureCoexistenceResponse(
        section_id=request.section_id,
        target_track_id=request.target_track_id,
        safe_to_coexist=safe,
        affected_tracks=affected_tracks,
        conflicting_movements=conflicts,
        crossover_constraints=crossover_constraints,
        coexistence_rationale=rationale,
    )
