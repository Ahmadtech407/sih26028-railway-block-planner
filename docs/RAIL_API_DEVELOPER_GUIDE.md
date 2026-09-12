# Indian Railways Live Data & API Developer Guide

This guide details how to configure external Railway Data feeds, obtain API credentials from supported providers (RapidAPI IRCTC, data.gov.in, CRIS/NTES), and leverage the integrated pre-cleaned Kaggle Indian Railways dataset for zero-downtime fallback.

---

## 1. Architecture Overview

```
                      +------------------------------------------+
                      |   Passenger UI (Streamlit App)           |
                      |   - Zero API prompts or modal popups     |
                      |   - Passive live/offline status indicator|
                      +--------------------+---------------------+
                                           |
                                           v
                      +--------------------+---------------------+
                      |   FastAPI Backend / Internal Services    |
                      |   (backend/services/govt_railway_service)|
                      +--------------------+---------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
         (If RAIL_API_KEY set)                       (If No API Key set)
                    v                                             v
     +------------------------------+             +-------------------------------+
     |  Live External Rail APIs     |             |  Pre-Cleaned Kaggle Rail Data |
     |  - RapidAPI IRCTC Live Feed  |             |  - 200+ Indian Junctions      |
     |  - Open Government Data      |             |  - 18 Railway Zones           |
     |  - CRIS / NTES TMS API       |             |  - Trunk Corridor Chainages   |
     |  - Server-side error logging |             |  - Calibrated Empirical Delays|
     +------------------------------+             +-------------------------------+
```

### Key Highlights
1. **Zero User-Facing Prompts**: End users are never prompted to enter API keys, secrets, or setup configurations on the dashboard.
2. **Secure Server-Side Credentials**: All API credentials are read strictly from backend environment variables (`.env`).
3. **Resilient Dual-Mode Operation**: If API keys are missing or quota-exhausted, the system logs a structured warning on the server and transparently falls back to the pre-cleaned Kaggle rail dataset, ensuring uninterrupted UI telemetry.

---

## 2. Environment Configuration (`.env`)

Create or update a `.env` file in the project root directory:

```env
# =====================================================================
# Indian Railways Live Data Feed Credentials
# =====================================================================

# Primary Rail API Key (used for live train status and platform data)
RAIL_API_KEY=your_rapidapi_or_rail_api_key_here

# Rail API Provider: RAPIDAPI_IRCTC (default), CRIS_NTES, or DATA_GOV_IN
RAIL_API_PROVIDER=RAPIDAPI_IRCTC

# RapidAPI IRCTC Host (if using RapidAPI)
RAPIDAPI_HOST=irctc1.p.rapidapi.com

# Alternative provider-specific keys (optional overrides)
RAPIDAPI_KEY=your_rapidapi_key_here
CRIS_API_KEY=your_cris_ntes_key_here
DATA_GOV_IN_API_KEY=your_data_gov_in_api_key_here
```

### Environment Variable Reference

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `RAIL_API_KEY` | Recommended | `""` | Primary API authentication key used by backend services. |
| `RAIL_API_PROVIDER` | No | `RAPIDAPI_IRCTC` | Data feed adapter: `RAPIDAPI_IRCTC`, `CRIS_NTES`, or `DATA_GOV_IN`. |
| `RAPIDAPI_HOST` | No | `irctc1.p.rapidapi.com`| Host header for the RapidAPI IRCTC endpoint. |
| `RAPIDAPI_KEY` | No | Same as `RAIL_API_KEY`| Secondary alias for RapidAPI key. |
| `CRIS_API_KEY` | No | `""` | Official Centre for Railway Information Systems credential. |
| `DATA_GOV_IN_API_KEY` | No | `""` | Open Government Data (data.gov.in / NDAP) API token. |

---

## 3. Step-by-Step Provider Setup Guides

### Option A: RapidAPI (IRCTC / Indian Railway Live Status) — Recommended

RapidAPI hosts popular, high-uptime community and commercial endpoints for live Indian Railways data with free monthly quotas.

1. **Create an Account**:
   - Go to [RapidAPI](https://rapidapi.com/auth/sign-up) and register a free developer account.
2. **Find an Indian Railway API**:
   - Search for **"IRCTC"** or **"Indian Railway"** on RapidAPI Hub.
   - Popular endpoints include:
     - `IRCTC API` (e.g. `irctc1.p.rapidapi.com`)
     - `Indian Railway Live Status`
3. **Subscribe to Free Tier**:
   - Select the **Pricing** tab and subscribe to the Basic/Free tier (typically 50–500 requests/month free).
4. **Obtain API Keys**:
   - On the API endpoint testing page, locate the **Header Parameters** section in the right pane:
     - `X-RapidAPI-Key`: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
     - `X-RapidAPI-Host`: `irctc1.p.rapidapi.com`
5. **Configure `.env`**:
   ```env
   RAIL_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   RAIL_API_PROVIDER=RAPIDAPI_IRCTC
   RAPIDAPI_HOST=irctc1.p.rapidapi.com
   ```
6. **Restart Backend**:
   - Restart the uvicorn backend (`python -m uvicorn backend.main:app`). The backend will automatically pick up the credentials from `.env`.

---

### Option B: Open Government Data (data.gov.in / NDAP)

1. **Register**:
   - Visit [data.gov.in](https://data.gov.in/) or [NDAP NITI Aayog](https://ndap.niti.gov.in/).
   - Sign in using DigiLocker or your government portal login.
2. **Access Ministry of Railways Datasets**:
   - Search for Indian Railways timetable, train schedule, and station catalog datasets.
3. **Generate API Token**:
   - In your user profile, go to **My API Token / Keys** and click **Generate New Key**.
4. **Configure `.env`**:
   ```env
   RAIL_API_KEY=your_datagov_token_here
   RAIL_API_PROVIDER=DATA_GOV_IN
   ```

---

### Option C: CRIS / NTES (National Train Enquiry System)

*Note: Direct CRIS/NTES enterprise gateway access is primarily available to Indian Railways divisions, zonal control rooms, and academic/research partners.*

1. **Request Gateway Access**:
   - Contact your CRIS nodal officer or zonal division IT cell for NTES TMS feed credentials.
2. **Configure `.env`**:
   ```env
   RAIL_API_KEY=your_cris_partner_token
   RAIL_API_PROVIDER=CRIS_NTES
   ```

---

## 4. Pre-Cleaned Kaggle Rail Dataset Fallback

When `RAIL_API_KEY` is not provided or the network is offline, the backend seamlessly activates the pre-cleaned Kaggle Indian Railways dataset located at:
`backend/data/kaggle_rail_dataset.py`

### What is included:
- **200+ Major Junction Stations**: Spanning all 18 Indian Railway zones (NR, NCR, ER, ECR, CR, WR, WCR, SR, SCR, SWR, SECR, SER, ECoR, NFR, NWR, SCoR, KR, Metro).
- **Exact Coordinates**: Standard WGS84 latitudes and longitudes for accurate mapping.
- **Station Aliases**: Handles common variations (e.g. `NDLS` / `New Delhi`, `PRYJ` / `Prayagraj Junction` / `Allahabad`).
- **Trunk Corridor Chainages**: Distance tables for High-Density Networks (HDN) including Delhi-Howrah, Delhi-Mumbai, Delhi-Jammu, and Chennai-Bangalore.
- **Calibrated Empirical Delays**: Historical delay profiles by zone, section type, and peak hours derived from Kaggle train delay logs.

### Server Behavior without API Key:
- **Zero Frontend Disruption**: No error popups, no red banners, no disabled widgets.
- **Server-Side Log**:
  ```log
  WARNING:govt_railway_service:No RAIL_API_KEY / RAPIDAPI_KEY configured. Operating on Kaggle Indian Railways pre-cleaned dataset with calibrated kinematics.
  ```

---

## 5. Verification & Testing

Verify that your environment and data feeds are working properly by executing the test suite:

```bash
# Run Kaggle Dataset Verification
.venv\Scripts\python.exe -m pytest tests/test_kaggle_rail_data.py -v

# Run Rail Service & RapidAPI Integration Tests
.venv\Scripts\python.exe -m pytest tests/test_govt_railway_service.py -v

# Run Passenger View Presentation Tests
.venv\Scripts\python.exe -m pytest tests/test_passenger_view.py -v

# Run All Tests
.venv\Scripts\python.exe -m pytest -v
```
