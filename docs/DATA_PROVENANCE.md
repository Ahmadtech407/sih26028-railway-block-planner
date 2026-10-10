# Data Provenance, Licensing & External Integration Truth

**System**: RailTrack — Indian Railways AI Section Controller & Block Planner (SIH26028)  
**Document**: Data Provenance & Telemetry Architecture  
**Status**: Authoritative Disclosure  

---

## 1. Ground Truth Statement on Railway Data Access

> [!IMPORTANT]
> **GOVERNMENT RAILWAY API ACCESS DISCLOSURE**  
> Indian Railways live operational train telemetry is managed by the **Centre for Railway Information Systems (CRIS)** through the **National Train Enquiry System (NTES)** and the **Control Office Application (COA)**.
> Direct access to CRIS production data streams is strictly restricted to authorized railway personnel and authenticated government integrations.
> 
> **RailTrack does NOT fabricate live government access.**
> All real-time telemetry, timetable feeds, and train positions in RailTrack are explicitly tagged with their true data provenance:
> - `DATA_SOURCE: SIMULATED` (High-fidelity kinematic simulator)
> - `DATA_SOURCE: REFERENCE_SAMPLE_DATASET` (Pre-configured IR corridor timetables)
> - `DATA_SOURCE: RAPIDAPI_IRCTC` (External commercial proxy when configured)
> - `DATA_SOURCE: GOVT_OPEN_FEED` (Ministry of Railways / data.gov.in public archives)

---

## 2. Catalog of Open Railway Datasets

All machine learning models are trained exclusively on verifiable open datasets cataloged in `backend/ml/data/metadata/dataset_catalog.json`:

| Dataset ID | Name & Description | Source & License | Records | Target Variable |
| :--- | :--- | :--- | :--- | :--- |
| `IR_TIMETABLE_2023_DATA_GOV` | Complete Indian Railways Timetable (Trains & Schedules) | data.gov.in (National Data Sharing & Accessibility Policy - NDSAP) | 8,300+ stations | `StationOrder`, `scheduled_runtime` |
| `IRCTC_HISTORICAL_RUNNING_DELAY` | Historical Train Running Status (Train 12423, 12424, 12346) | Public running status archives (ODbL / Public Domain) | 12,400+ observations | `target_delay_minutes` |
| `IMD_OPEN_WEATHER_ARCHIVE` | Historical meteorological observations for UP/Delhi railway nodes | IMD Open Portal & Open-Meteo Climate Reanalysis (CC-BY 4.0) | Multi-year hourly | `weather_risk_score`, `rainfall_intensity_mmh` |

---

## 3. Data Leakage Prevention Guarantee

All predictive models deployed in `data/models/` are audited using `LeakageAuditor` (`backend/ml/data/leakage_audit.py`).
1. **Forbidden Post-Trip Variables**:
   `actual_arrival`, `actual_travel_time`, `final_delay`, `post_trip_cause` are strictly prohibited from appearing in the feature matrix $X$.
2. **Permitted Pre-Trip / Real-Time Variables**:
   Only information known prior to or during train transit is permitted:
   `priority`, `StationOrder`, `halt_time_minutes`, `distance_travelled_km`, `distance_remaining_km`, `speed_kmph`, `hour_of_day`, `is_peak_hour`, `is_weekend`, `temperature_c`, `rainfall_intensity_mmh`, `visibility_km`, `weather_risk_score`, `trains_in_section`, `preceding_delay_minutes`.
3. **Temporal Split Invariant**:
   Train, validation, and test datasets are partitioned chronologically to prevent temporal data leakage.
