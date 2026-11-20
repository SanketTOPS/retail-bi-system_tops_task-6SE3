# 📈 AI-Powered Retail Business Intelligence System

An enterprise-grade, multi-agent business intelligence and decision-support platform designed for omnichannel retail commerce. Built with **FastAPI**, **CrewAI**, **PostgreSQL (Neon)**, **Pandas**, and **React 18 (Vite + Recharts)**.

---

## 🌟 Key Architecture Pillars

| Pillar | Engineering Guarantee |
|---|---|
| **Zero Numerical Hallucination** | **100% of calculations** (KPIs, margins, trends, RFM scores, anomalies) are computed using pure **Pandas & NumPy** deterministic code. The LLMs **never calculate numbers** and are strictly restricted to narrative synthesis, qualitative insights, and strategic evaluation. |
| **Dual-Layer Verification Engine** | Every quantitative claim made by the Strategy Agent is audited by a **Python Numerical Verifier** ($\le 1\%$ tolerance against PostgreSQL) and a dedicated **Verification Agent**. If inconsistencies or phantom numbers are detected, an automated **self-correction reflection loop** re-runs the agents (max 2 retries). |
| **Human-in-the-Loop (HITL) Governance** | Consequential recommendations (inventory reorders, marketing budget shifts, discount policy changes) are locked until reviewed by a **Manager** or **Admin**. No operational change executes without explicit, recorded consent in an immutable audit ledger. |
| **Role-Based Access Control (RBAC)** | Three hierarchical roles: **Analyst** (data upload, run analyses), **Manager** (review & approve recommendations), and **Admin** (user governance, role delegation, system health). First registered account automatically becomes `admin`. |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer["🖥️ Frontend Client Layer (React 18 + Vite)"]
        UI_DASH["Executive Dashboard\n(Recharts KPI Scorecards)"]
        UI_PIPE["Multi-Agent Pipeline\n(Live Status & Trace Drawer)"]
        UI_APPR["Manager Approvals\n(HITL Action Queue)"]
        UI_CHAT["AI Business Advisor\n(Grounded Chat Interface)"]
        UI_DATA["Dataset Ingestion\n(Drag & Drop + Cleaning Report)"]
    end

    subgraph Gateway["🌐 API Gateway & Security Layer"]
        AUTH_INT["Axios JWT Interceptor\n(Auto-Attach Bearer & 401 Logout)"]
        CORS_MW["FastAPI CORS Middleware\n(Strict Origin Whitelist)"]
        RBAC_DEP["FastAPI Dependencies\n(require_roles: admin, manager, analyst)"]
    end

    subgraph ServiceLayer["⚙️ FastAPI Backend Services (Python 3.11)"]
        ROUTERS["REST API Routers\n(/auth, /profile, /datasets, /analytics,\n/analysis, /approvals, /chat, /reports, /admin)"]
        PANDAS_SVC["Analytics Service\n(Pure Pandas & NumPy Calculators)"]
        RUNNER_SVC["Analysis Background Runner\n(Concurrency Lock & Task Dispatch)"]
        REPORT_SVC["ReportLab PDF Service\n(Headless Agg Matplotlib + 2-Pass Canvas)"]
    end

    subgraph AgentLayer["🤖 CrewAI Multi-Agent Intelligence Engine"]
        A1["1. Data Analyst Agent"]
        A2["2. Marketing Strategist"]
        A3["3. Financial Analyst"]
        A4["4. Operations Officer"]
        A5["5. Principal Strategist"]
        A6["6. Verification Engine"]
        REFL["Self-Correction Loop\n(Max 2 Reflection Retries)"]
    end

    subgraph StorageLayer["🗄️ Persistence & Cloud Storage"]
        POSTGRES[("PostgreSQL Database\n(Neon Cloud Serverless)\n6 Retail Tables + 10 System Tables")]
        DISK_CACHE[("Local Disk / Shared Mount\nRaw Excel Files & Generated PDFs")]
    end

    ClientLayer --> AUTH_INT --> CORS_MW --> RBAC_DEP --> ROUTERS
    ROUTERS --> PANDAS_SVC --> POSTGRES
    ROUTERS --> RUNNER_SVC --> AgentLayer
    ROUTERS --> REPORT_SVC --> DISK_CACHE
    
    A1 --> A2 --> A3 --> A4 --> A5 --> A6
    A6 -.->|Diff > 1% or Phantom Claims| REFL -.-> A5
    A6 -->|Approved| POSTGRES
```

---

## 🤖 Multi-Agent Sequential Workflow

The intelligence pipeline executes **6 sequential agents** using CrewAI with strict tool-binding (`build_tools(dataset_id)` binds the dataset server-side so the LLM cannot pick or query unauthorized datasets).

```mermaid
sequenceDiagram
    autonumber
    participant D as Analyst / Trigger
    participant T1 as 1. Data Analyst
    participant T2 as 2. Marketing
    participant T3 as 3. Finance
    participant T4 as 4. Operations
    participant T5 as 5. Strategy
    participant T6 as 6. Verification
    participant DB as PostgreSQL / Pandas Tools

    D->>T1: Launch Analysis (Dataset ID bound server-side)
    T1->>DB: Query KPIs, monthly trends, variance anomalies
    DB-->>T1: Return exact numbers
    T1->>T2: Hand off numerical findings [Context: T1]
    T2->>DB: Query sales channels & discounting performance
    DB-->>T2: Return channel metrics
    T2->>T3: Hand off customer & channel findings [Context: T1]
    T3->>DB: Query operating expenses & category gross margins
    DB-->>T3: Return financial breakdown
    T3->>T4: Hand off cost structures [Context: T1]
    T4->>DB: Query warehouse movement & stockout incidents
    DB-->>T4: Return logistics data
    T4->>T5: Synthesize complete business context [Context: T1, T2, T3, T4]
    T5->>T5: Generate StrategyReport (Insights, Risks, Recommendations, Claims)
    T5->>T6: Submit Report for Numerical Audit [Context: T1..T5]
    T6->>DB: Recompute every quantitative claim via recompute_metric_tool
    
    alt Inconsistency Detected (Diff > 1% or Unsupported Numbers)
        T6-->>T5: Rejection Notice with Feedback (Self-Correction Loop 1/2)
        T5->>T5: Re-evaluate and regenerate corrected claims
        T5->>T6: Resubmit corrected report
    end

    T6-->>D: Approved! Status: VERIFIED (or VERIFIED_WITH_WARNINGS)
```

---

## 💻 Technology Stack

| Layer | Technologies | Version |
|---|---|---|
| **Backend Framework** | FastAPI, Uvicorn, Python 3.11 | `0.111.0` |
| **ORM & Database** | SQLAlchemy 2.0, PostgreSQL (Neon Cloud), Alembic | `2.0.30` |
| **Analytics Engine** | Pandas, NumPy, OpenPyXL (Pure deterministic Python) | `2.2.2` |
| **Multi-Agent Orchestration** | CrewAI, LiteLLM (Google Gemini 1.5 Pro / Flash) | `0.70.1` |
| **PDF Dossier Generation** | ReportLab (2-pass `NumberedCanvas`), Matplotlib (`Agg` backend) | `4.2.0` |
| **Frontend Framework** | React 18, Vite, React Router v6 | `18.3.1` |
| **Data Visualizations** | Recharts (Responsive Composed, Area, Pie, Bar charts) | `2.12.4` |
| **HTTP Transport & Auth** | Axios (Singleton with Request & Response Interceptors) | `1.6.8` |
| **Notifications** | React Hot Toast | `2.4.1` |

---

## 🚀 Step-by-Step Local Setup

### 1. Prerequisites
- **Python**: Version `3.11` or higher installed.
- **Node.js**: Version `18` or `20` LTS with `npm`.
- **PostgreSQL**: Local PostgreSQL 15+ or a free cloud database on [Neon.tech](https://neon.tech).

---

### 2. Backend Setup

```bash
# Navigate to backend directory
cd retail-bi-system/backend

# Create and activate a Python virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install all backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
```

Edit `backend/.env` with your credentials:
```env
APP_ENV=development
SECRET_KEY=generate_a_random_32_byte_hex_string_here
DATABASE_URL=postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/retail_bi?sslmode=require
LLM_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini/gemini-1.5-pro
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Run the backend server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI backend will run at **http://localhost:8000**.  
Swagger documentation is available at **http://localhost:8000/docs**.

---

### 3. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd retail-bi-system/frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```
The React frontend will be live at **http://localhost:5173**.

---

### 4. First-Time User Registration
1. Navigate to **http://localhost:5173/register**.
2. Create your account. **The first registered account automatically receives the `admin` role**.
3. Subsequent registrations default to `analyst`. You can promote them to `manager` or `admin` via the Admin Panel.

---

## 🌐 Cloud Deployment Guide

### A. Neon PostgreSQL (Cloud Database)
1. Sign up at [neon.tech](https://neon.tech) and create a new project (e.g. `retail-bi`).
2. Copy the connection string with pooling or direct access (ensure `?sslmode=require` is appended):
   ```
   postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/retail_bi?sslmode=require
   ```
3. Tables and relationships are automatically generated on first startup via `Base.metadata.create_all()` in the FastAPI lifespan handler.

---

### B. Backend Deployment (Render or Railway)

#### Option 1: Render Cloud (`render.yaml`)
1. Fork or push this repository to GitHub.
2. In Render, select **Blueprints** and connect your repository.
3. Render automatically picks up `render.yaml` and provisions:
   - `retail-bi-backend` (Web Service)
   - `retail-bi-frontend` (Static Site)
4. Add the secret environment variables (`DATABASE_URL`, `LLM_API_KEY`, `SECRET_KEY`) in the Render Dashboard.

#### Option 2: Docker / Railway
A production multi-stage [`Dockerfile`](file:///c:/Users/Admin/Desktop/AI_Task/retail-bi-system/backend/Dockerfile) and [`railway.json`](file:///c:/Users/Admin/Desktop/AI_Task/retail-bi-system/railway.json) are included.
- **Root Directory**: `backend`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

### C. Frontend Deployment (Vercel)
1. Connect your GitHub repository to Vercel.
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Vite`.
4. Configure Environment Variable:
   - `VITE_API_URL`: `https://your-backend.onrender.com/api/v1`
5. The included [`frontend/vercel.json`](file:///c:/Users/Admin/Desktop/AI_Task/retail-bi-system/frontend/vercel.json) handles SPA route rewrites:
   ```json
   {
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```

---

## 🔒 Environment Variable & CORS Checklist

| Variable Name | Location | Required | Example / Description |
|---|---|:---:|---|
| `DATABASE_URL` | Backend `.env` | Yes | `postgresql://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | Backend `.env` | Yes | 32+ character random string for JWT HS256 encryption |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend `.env` | No | Default: `1440` (24 hours) |
| `LLM_API_KEY` | Backend `.env` | Yes | Google Gemini API Key |
| `LLM_MODEL` | Backend `.env` | No | Default: `gemini/gemini-1.5-pro` (or `gemini/gemini-1.5-flash`) |
| `ALLOWED_ORIGINS` | Backend `.env` | Yes | Comma-separated client URLs (e.g. `https://retail-bi.vercel.app`) |
| `UPLOAD_DIR` | Backend `.env` | No | Directory for dataset storage (Default: `/tmp/uploads`) |
| `VITE_API_URL` | Frontend `.env` | Yes | Public API Base URL: `https://api.yourdomain.com/api/v1` |
| `VITE_APP_NAME` | Frontend `.env` | No | Display name: `Retail BI System` |

---

## 📋 Complete API Reference Summary

| Method | Endpoint | Auth Required | Accessible Roles | Description |
|---|---|:---:|:---:|---|
| **POST** | `/api/v1/auth/register` | No | Public | Register new user account (first user becomes `admin`) |
| **POST** | `/api/v1/auth/login` | No | Public | OAuth2 form login returning JWT access token |
| **GET** | `/api/v1/auth/me` | Yes | All | Fetch authenticated user profile & role |
| **POST** | `/api/v1/auth/change-password` | Yes | All | Update user credentials |
| **GET** | `/api/v1/profile` | Yes | All | Fetch business profile |
| **POST** | `/api/v1/profile` | Yes | All | Create business profile & strategic goals |
| **PUT** | `/api/v1/profile` | Yes | All | Update business profile attributes |
| **GET** | `/api/v1/profile/all` | Yes | `admin` | List all profiles across platform |
| **POST** | `/api/v1/datasets/upload` | Yes | All | Multipart upload of `.xlsx` with Pandas cleaning & period filter |
| **GET** | `/api/v1/datasets` | Yes | All | List accessible datasets with pagination |
| **GET** | `/api/v1/datasets/{id}` | Yes | All | Get dataset metadata & data cleaning report |
| **GET** | `/api/v1/datasets/{id}/preview` | Yes | All | Preview first 5 sample rows across all 6 retail tables |
| **DELETE**| `/api/v1/datasets/{id}` | Yes | All | Cascading delete of dataset & child records |
| **GET** | `/api/v1/analytics/{id}/kpis` | Yes | All | Executive KPI scorecard (Revenue, Expenses, Margin, AOV, etc.) |
| **GET** | `/api/v1/analytics/{id}/trends` | Yes | All | Monthly progressions and MoM growth % |
| **GET** | `/api/v1/analytics/{id}/anomalies` | Yes | All | Statistical anomalies ($> 1.5$ std dev or $> 20\%$ shift) |
| **GET** | `/api/v1/analytics/{id}/segments` | Yes | All | Customer RFM behavioral segmentation |
| **GET** | `/api/v1/analytics/{id}/finance` | Yes | All | Cost breakdown and category gross margins |
| **GET** | `/api/v1/analytics/{id}/operations`| Yes | All | Warehouse throughput & stockout counts |
| **GET** | `/api/v1/analytics/{id}/marketing` | Yes | All | Channel-level velocity and discounting rates |
| **POST** | `/api/v1/analysis/run` | Yes | All | Trigger 6-agent background analysis with concurrency lock |
| **GET** | `/api/v1/analysis/{id}/status` | Yes | All | Poll live progress %, active agent, and step statuses |
| **GET** | `/api/v1/analysis/{id}/logs` | Yes | All | Detailed execution traces and agent reasoning logs |
| **GET** | `/api/v1/analysis/{id}/report` | Yes | All | Completed verified intelligence report |
| **GET** | `/api/v1/analysis/history` | Yes | All | Historical analysis run ledger |
| **GET** | `/api/v1/reports` | Yes | All | List verified intelligence reports |
| **GET** | `/api/v1/reports/{id}/pdf` | Yes | All | Download ReportLab compiled PDF dossier (Axios blob) |
| **GET** | `/api/v1/approvals/pending` | Yes | `manager`, `admin` | Consequential initiatives awaiting approval |
| **POST** | `/api/v1/approvals/{id}/decision`| Yes | `manager`, `admin` | Record managerial approval / rejection decision |
| **GET** | `/api/v1/approvals/history` | Yes | `manager`, `admin` | Chronological audit trail of all managerial decisions |
| **POST** | `/api/v1/chat` | Yes | All | Grounded Q&A conversation with AI business advisor |
| **GET** | `/api/v1/chat/history` | Yes | All | Fetch conversation history |
| **DELETE**| `/api/v1/chat/history` | Yes | All | Clear chat conversation history |
| **GET** | `/api/v1/admin/stats` | Yes | `admin` | Platform health metrics, success rates, duration |
| **GET** | `/api/v1/admin/users` | Yes | `admin` | User directory with search and role/status filtering |
| **PATCH** | `/api/v1/admin/users/{id}/role` | Yes | `admin` | Change user role (self-demotion protected) |
| **PATCH** | `/api/v1/admin/users/{id}/status`| Yes | `admin` | Activate / deactivate user account (self-lockout protected) |

---

## 📸 Interface Walkthrough & Screenshots

### 1. Executive Analytics Dashboard
> Real-time Recharts visualizations powered by pure Pandas computations. Features 12 KPI cards, monthly revenue vs expense composed chart, category margins, and customer RFM clusters.
*(Screenshot Placeholder: `docs/screenshots/dashboard.png`)*

### 2. Multi-Agent Analysis Pipeline
> Visual 6-step timeline tracking the sequential progression from Data Analyst through Verification Engine, with live status badges, execution times, and expandable trace drawers.
*(Screenshot Placeholder: `docs/screenshots/analysis_pipeline.png`)*

### 3. Managerial HITL Approval Queue
> Consequential strategic recommendations gated by managerial sign-off, featuring priority tags, expected impact, and an interactive decision modal with audit comments.
*(Screenshot Placeholder: `docs/screenshots/approvals_queue.png`)*

### 4. Grounded Business AI Advisor (Chat)
> ChatGPT-style interface grounded strictly in Pandas analytics tools with zero hallucination, suggested prompts, and analysis context binding.
*(Screenshot Placeholder: `docs/screenshots/ai_chat.png`)*

---

## 📄 License
This project is proprietary software developed for enterprise retail intelligence and operational decision support.
