# RailTrack Production Readiness & Real-World Feasibility Audit

**System Name**: RailTrack AI Section Controller & Block Planner (SIH26028)  
**Classification**: Non-Vital Advisory Decision Support System (ADSS)  
**Safety Integrity Level**: Not SIL-Certified (CENELEC EN 50126 / 50128 / 50129 Uncertified)  
**Audit Date**: October 2026  
**Auditor Role**: Principal Railway Systems Engineer, Safety Architect & DevOps Specialist  

---

## 1. Executive Summary & Brutal Truth

RailTrack is an advanced algorithmic planning prototype and passenger journey intelligence system developed for Indian Railways section controllers and travelling passengers. It successfully models:
- Google OR-Tools CP-SAT multi-resource constraint programming for track maintenance possession scheduling.
- Physically meaningful Temporary Speed Restriction (TSR) run-time dilation ($\Delta t = d/v_{\text{tsr}} - d/v_{\text{normal}}$) partitioned along corridor geometry.
- Staged clearance and review state machines with strict separation of duties and traction power isolation prerequisites.
- Multi-model dynamic ETA delay prediction using ensemble learning on open railway datasets.

**CRITICAL REALITY CHECK**:
RailTrack is **NOT** a Vital Railway Safety System. It is an **Advisory Decision Support System (ADSS)** intended exclusively for human-in-the-loop decision recommendation. It has **NOT** undergone CENELEC SIL-4 validation by the Research Designs and Standards Organisation (RDSO) or the Commissioner of Railway Safety (CRS). Under no circumstances may software outputs independently clear signals, throw point machines, or authorize track possession without verified human intervention.

---

## 2. Subsystem Feasibility & Operational Realities

### 2.1 Signaling & Interlocking Boundary
- **Field Reality**: Indian Railways operational dispatching is governed by Electronic Interlocking (EI), Route Relay Interlocking (RRI), and Panel Interlocking (PI) systems adhering to SIL-4 fail-safe standards.
- **RailTrack Status**: Non-vital stub adapter (`signaling_adapter.py`). Returns `STATUS: NOT_CONNECTED`.
- **Field Feasibility**: To deploy in real-world Indian Railways control offices (e.g. at Divisional Railway Manager offices in Prayagraj or Kanpur), RailTrack must interface via read-only optical data diodes with the Control Office Application (COA) and Section Interlocking Data Loggers. Direct command dispatch into Electronic Interlocking is strictly prohibited by IR General Rules (G&SR).

### 2.2 Traction Power (25 kV AC OHE) Isolation
- **Field Reality**: Track maintenance involving rail cranes, ballast tampers, or track renewal trains requires physical de-energization and discharge-rod earthing of the 25 kV AC overhead catenary line. Physical safety depends on visual confirmation of earth discharge rods placed on OHE masts by the Traction Power Controller (TPC) and engineering field supervisors.
- **RailTrack Status**: Implements a rigorous transactional Permit-to-Work state machine:
  `NOT_REQUESTED -> REQUESTED -> ISOLATION_PENDING -> ISOLATION_CONFIRMED -> EARTHING_CONFIRMED -> PERMIT_ACTIVE -> WORK_COMPLETE -> RESTORATION_PENDING -> RESTORED`.
- **Field Feasibility**: The software state machine provides operational decision support and audit trail traceability. However, software flags can **never** substitute for physical earthing and lock-out/tag-out (LOTO) key exchanges on the ground.

### 2.3 Mathematical Optimization Engine (OR-Tools CP-SAT)
- **Field Reality**: Section Controllers juggle dynamic priority trains, unplanned crossings, freight rakes, and emergency cautions. Universal assumptions (such as fixed 5-minute headways or absolute zero-delay premium trains) do not reflect real railway diversity.
- **RailTrack Status**: Fully corrected CP-SAT solver with:
  - Infrastructure-specific validated headway, sectional running times, and exclusive physical resources (`SectionInfrastructureConfig`).
  - Strict absence of implicit defaults (fails with `PLANNING_ERROR_MISSING_INFRASTRUCTURE_CONFIG` on unvalidated corridors).
  - Valid boolean reified inequalities and `AddBoolOr` for distinct alternative window generation.
  - Independent post-solve constraint validator (`validate_schedule_independently`) completely decoupled from the optimizer's conflict detection.
  - Transparent solver status fidelity (`OPTIMAL_SCHEDULED` vs `FEASIBLE_SUBOPTIMAL_SCHEDULED` vs `NO_FEASIBLE_SLOT`).

### 2.4 Machine Learning & Data Provenance
- **Field Reality**: Official Indian Railways real-time train movement APIs are managed by the Centre for Railway Information Systems (CRIS) through National Train Enquiry System (NTES) and Control Office Application (COA). Direct external access requires government accreditation.
- **RailTrack Status**: Real-time train telemetry defaults to calibrated simulated reference timetables or RapidAPI IRCTC feeds when configured. When external feeds are absent, system explicitly declares `DATA_SOURCE: SIMULATED` or `REFERENCE_SAMPLE_DATASET` without fabricating live CRIS connectivity.
- **Leakage Prevention**: All training matrices are audited via `LeakageAuditor` to guarantee zero target leakage in predictive models.

---

## 3. Disaster Recovery & Database Durability

- **Local SQLite Storage**:
  - Employs zero-downtime atomic online backups via `sqlite3.Connection.backup()`.
  - Backups are cryptographically fingerprinted using SHA-256 and structurally verified via `PRAGMA integrity_check`.
  - Restoration runbook tested and verified on disk (`data/backups/`).
- **PostgreSQL / Supabase Storage**:
  - REST API client captures application-level JSON table snapshots.
  - Production point-in-time recovery (PITR) and physical write-ahead log (WAL) backups require PostgreSQL `pg_dump` or Supabase CLI (`supabase db dump`) with direct connection credentials.

---

## 4. Verification & Audit Sign-Off

| Dimension | Real-World Feasibility | Prototype Audit Status |
| :--- | :--- | :--- |
| **SIL-4 Certification** | Not SIL-4 Certified | Clearly declared as non-vital ADSS |
| **Interlocking Control** | Read-only advisory only | Blocks signal clearing, declares NOT_CONNECTED |
| **OHE Isolation** | Physical earthing mandatory | Software workflow gates TMS commit on active permit |
| **CP-SAT Solver** | Production ready | Validated multi-resource discrete CP-SAT formulation |
| **TSR Physics** | Multi-segment geometric partitioning | Partitions geometry, eliminates double counting |
| **Data Integrity** | Zero data falsification | Explicit provenance labels on all data responses |
