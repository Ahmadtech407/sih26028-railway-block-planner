# RailTrack System Integration & Architecture Status

**Project**: RailTrack — SIH26028 Railway Block Planner & Passenger Intelligence  
**Status**: Production Hardened  
**Date**: October 2026  

---

## 1. Subsystem Integration Matrix

| Subsystem | Tech Stack | Status | Integration Notes |
| :--- | :--- | :--- | :--- |
| **FastAPI REST Backend** | Python 3.14, FastAPI, Uvicorn | `OPERATIONAL` | Root health, clearance, blocks, optimizer, PNR, auth, and trains endpoints fully active. |
| **CP-SAT Optimizer** | Google OR-Tools 9.x | `OPERATIONAL` | Multi-resource discrete intervals, valid reified exclusion, status fidelity, independent validator. |
| **Safety Clearance Engine** | SQLite3, Pydantic V2 | `OPERATIONAL` | Multi-department review chain, separation of duties, 25 kV AC OHE permit gate. |
| **Physical TSR Engine** | Kinematic Run-Time Model | `OPERATIONAL` | Geometric boundary partitioning, minimum speed resolution, no double counting. |
| **Signaling Boundary** | Adapter Layer | `OPERATIONAL` | Declares `NOT_CONNECTED`, advisory mode only, blocks interlocking clear commands. |
| **Machine Learning Inference** | XGBoost, RF, HistGBM, Joblib | `OPERATIONAL` | Dynamic ETA inference with physical kinematic guardrails and zero data leakage. |
| **Database Persistence** | SQLite (with Supabase sync) | `OPERATIONAL` | Online atomic backup with SHA-256 fingerprinting, verified restore, and durable writes. |
| **Passenger Journey Assistant** | FastAPI `/api/journey/assist` | `OPERATIONAL` | Dynamic route timetable search, deadline filtering, transparent probability scoring. |
| **Streamlit Interface** | Streamlit 1.40+ | `OPERATIONAL` | Interactive controller dashboards and passenger assistance visualizers. |

---

## 2. API Endpoint Catalog

- `GET /health`: Deep system healthcheck, database status, and ML model loaded count.
- `POST /api/optimizer/solve`: Solves track maintenance possession with OR-Tools CP-SAT.
- `POST /api/conflicts/check`: Checks train conflict windows across a proposed maintenance slot.
- `GET /api/clearance/signaling/status`: Declares non-vital signaling integration status (`NOT_CONNECTED`).
- `POST /api/clearance`: Submits a new clearance proposal (`DRAFT` / `AI_RECOMMENDED`).
- `POST /api/clearance/{block_id}/advance`: Multi-departmental review gate with separation of duties.
- `POST /api/blocks/commit`: Hard safety gated commit to TMS (requires `APPROVED` + `ohe_isolation_confirmed`).
- `GET /api/blocks`: Retrieves persistent committed maintenance block history.
- `GET /api/trains/data-source`: Real-time data provenance disclosure.
- `POST /api/journey/assist`: Passenger multi-criteria journey recommendation engine.
