# Deployment Guide — Indian Railways AI Section Controller & Block Planner

This guide provides both the **immediate live public URLs** and options for **permanent cloud hosting**.

---

## 1. 🚀 Immediate Live Access (Currently Active)

Both services are currently deployed and routed through secure Cloudflare edge tunnels with an active keepalive daemon:

| Service | Public HTTPS URL | Local Address | Description |
| :--- | :--- | :--- | :--- |
| **🚆 Passenger Frontend Dashboard** | **[https://cet-restaurant-diy-bugs.trycloudflare.com/](https://cet-restaurant-diy-bugs.trycloudflare.com/)** | `http://127.0.0.1:8501` | Interactive Streamlit tracking & journey prediction interface |
| **⚡ FastAPI Backend API** | **[https://competent-directories-promise-found.trycloudflare.com/](https://competent-directories-promise-found.trycloudflare.com/)** | `http://127.0.0.1:8000` | REST API, optimization engine, AI Section Controller |
| **📖 Interactive API Docs (Swagger)** | **[https://competent-directories-promise-found.trycloudflare.com/docs](https://competent-directories-promise-found.trycloudflare.com/docs)** | `http://127.0.0.1:8000/docs` | OpenAPI 3.0 interactive endpoint tester |
| **📚 ReDoc Documentation** | **[https://competent-directories-promise-found.trycloudflare.com/redoc](https://competent-directories-promise-found.trycloudflare.com/redoc)** | `http://127.0.0.1:8000/redoc` | Clean API documentation view |

---

## 2. 🐳 Docker & Docker Compose (Any VPS / Cloud Server)

Ready-to-use Dockerfiles and Compose configurations are provided in the project root:
- [`Dockerfile.backend`](../Dockerfile.backend)
- [`Dockerfile.frontend`](../Dockerfile.frontend)
- [`docker-compose.yml`](../docker-compose.yml)

### Run with Docker Compose:
```bash
docker-compose up --build -d
```
- Backend will be available at: `http://localhost:8000`
- Frontend will be available at: `http://localhost:8501`

---

## 3. ☁️ Permanent Cloud Deployment Options

### Option A: Streamlit Community Cloud (Frontend — 100% Free)
1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Click **"New app"**:
   - **Repository**: Your GitHub repo
   - **Branch**: `main`
   - **Main file path**: `passenger_app.py`
4. In Advanced Settings, add the environment variable:
   ```
   BACKEND_API_URL = https://your-backend-url.onrender.com
   ```
5. Click **Deploy**.

---

### Option B: Render.com (Backend — Free Tier Available)
1. Go to [render.com](https://render.com/) and link your GitHub repository.
2. Click **"New +"** $\rightarrow$ **"Web Service"**.
3. Select your repository and configure:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in the Render dashboard:
   - `RAIL_API_KEY`: (Optional for live IRCTC feed)
   - `RAIL_API_PROVIDER`: `RAPIDAPI_IRCTC`
   - `RAPIDAPI_HOST`: `irctc1.p.rapidapi.com`
5. Click **Deploy Web Service**. Render gives you a permanent `https://<service-name>.onrender.com` URL.

---

### Option C: Railway.app (Backend + Frontend)
1. In Railway, click **"New Project"** $\rightarrow$ **"Deploy from GitHub repo"**.
2. Railway will auto-detect the Python project or Dockerfiles.
3. Set the start commands:
   - Service 1 (Backend): `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Service 2 (Frontend): `streamlit run passenger_app.py --server.port $PORT --server.address 0.0.0.0`
