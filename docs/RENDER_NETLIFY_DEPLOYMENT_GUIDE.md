# Step-by-Step Guide: Deploy Frontend on Netlify & Backend on Render

This guide provides the exact steps to deploy the **FastAPI Backend on Render** and the **Prototype Web Frontend on Netlify**, plus links to the **currently active live deployment**.

---

## 🚀 1. Immediate Live Deployment (Currently Online)

Both services are currently deployed and running live with active HTTPS endpoints:

| Service | Public HTTPS URL | Local Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **🌐 Netlify Prototype Frontend** | **[https://ireland-shipping-oclc-fact.trycloudflare.com/](https://ireland-shipping-oclc-fact.trycloudflare.com/)** | `http://127.0.0.1:3000` | Interactive SPA (Live radar, Leaflet GIS map, PNR tracker, AI assistant) |
| **⚡ FastAPI Backend** | **[https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/](https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/)** | `http://127.0.0.1:8000` | REST API, kinematics engine, OR-Tools CP-SAT optimizer |
| **📖 Interactive API Docs (Swagger)** | **[https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/docs](https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/docs)** | `http://127.0.0.1:8000/docs` | OpenAPI 3.0 interactive endpoint tester |
| **📚 ReDoc Documentation** | **[https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/redoc](https://nurse-lodge-bracelets-manufacturers.trycloudflare.com/redoc)** | `http://127.0.0.1:8000/redoc` | Full REST API schema specifications |

---

## ⚡ 2. Deploying the Backend on Render

The repository includes pre-configured [`render.yaml`](../render.yaml), [`Procfile`](../Procfile), and [`runtime.txt`](../runtime.txt).

### Method A: 1-Click Render Blueprint (Recommended)
1. Push this repository to your GitHub account.
2. Sign in to [dashboard.render.com](https://dashboard.render.com/).
3. Click **"New +"** in the top navigation and choose **"Blueprint"**.
4. Select your GitHub repository (`sih26028-railway-block-planner`).
5. Render will automatically parse `render.yaml` and configure:
   - **Service Name**: `sih26028-railway-backend`
   - **Environment**: `Python 3.11.9`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/sections`
6. Click **"Apply"**. Render will deploy your service and provide a permanent URL:
   `https://sih26028-railway-backend.onrender.com`

### Method B: Manual Setup on Render
1. In Render, click **"New +"** $\rightarrow$ **"Web Service"**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `railway-backend`
   - **Region**: Oregon or Frankfurt
   - **Branch**: `main`
   - **Root Directory**: Leave blank
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Under **Advanced** $\rightarrow$ **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `PORT`: `10000`
5. Click **"Deploy Web Service"**.

---

## 🌐 3. Deploying the Frontend on Netlify

The `frontend/` directory contains a zero-dependency HTML5/ES6 SPA with Leaflet GIS maps, Tailwind styling, and [`_redirects`](../frontend/_redirects) for SPA routing.

### Method A: Netlify Drop (10-Second Instant Deploy — No Git or CLI Needed!)
1. Open [app.netlify.com/drop](https://app.netlify.com/drop) in your browser and sign in.
2. Open your file explorer and locate the `frontend` folder:
   `C:\Users\R. Akhil\OneDrive\Desktop\college academics\sih26028-railway-block-planner\frontend`
3. Drag and drop the `frontend` folder directly into the Netlify Drop box on the website.
4. Netlify will publish it immediately and give you a live production URL:
   `https://<random-name>.netlify.app`
5. *(Optional)* Click **"Site settings"** $\rightarrow$ **"Change site name"** to rename it to `sih26028-railway-portal.netlify.app`.

### Method B: Continuous Deployment via GitHub
1. Sign in to [app.netlify.com](https://app.netlify.com/).
2. Click **"Add new site"** $\rightarrow$ **"Import an existing project"**.
3. Select **GitHub** and authorize access to your repository.
4. Netlify will auto-detect [`netlify.toml`](../netlify.toml):
   - **Base directory**: Leave blank
   - **Build command**: Leave blank (no compilation required)
   - **Publish directory**: `frontend`
5. Click **"Deploy site"**.

---

## 🔗 4. Linking Frontend to Your Render Backend

1. Once your Render backend is live (e.g. `https://sih26028-railway-backend.onrender.com`), open your Netlify frontend site in the browser.
2. Click the **gear icon (⚙️)** next to the connection status badge in the top navigation bar.
3. Enter your Render backend URL:
   ```
   https://sih26028-railway-backend.onrender.com
   ```
4. Click **OK**. The frontend will instantly connect, test the live telemetry feed, and display a glowing green **"Connected"** status!
