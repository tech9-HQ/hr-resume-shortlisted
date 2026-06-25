# Pre Screening Assistant

An AI-powered HR pre-screening tool built by Tech9Labs. HR uploads a candidate's resume, and the system generates personalised phone-screening questions (behavioral, compensation, logistics, background). After the call the HR rates each answer with stars and adds notes — the AI generates a scored interview report.

---

## Architecture

```
hr-ui/        React + Vite frontend (nginx in production)
api/          FastAPI backend (Uvicorn)
core/         AI logic — question generation, answer scoring, resume parsing
ingestion/    Optional OneDrive auto-ingestion of resumes
```

**Key technologies:**
- **Backend**: Python 3.11, FastAPI, DuckDB, OpenAI GPT-4.1-mini
- **Frontend**: React 19, Vite (rolldown), plain CSS
- **AI**: OpenAI `gpt-4o-mini` for personalised pre-screening questions and answer scoring
- **Database**: DuckDB (embedded, file-based — mount a persistent volume in production)

---

## Environment Variables

### Backend (`.env` / Code Engine secrets)

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `DB_PATH` | No | Path to DuckDB file. Default: `./resumes.duckdb`. In containers, point to a mounted volume: `/app/data/resumes.duckdb` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins. Default: `*`. Set to your frontend URL in production. |
| `ONEDRIVE_DRIVE_ID` | No | OneDrive Drive ID (leave blank to disable background ingestion) |
| `ONEDRIVE_FOLDER_ID` | No | OneDrive Folder ID |
| `AZURE_TENANT_ID` | No | Azure AD tenant (for OneDrive auth) |
| `AZURE_CLIENT_ID` | No | Azure AD client ID |
| `AZURE_CLIENT_SECRET` | No | Azure AD client secret |

### Frontend (build-time)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_BASE_URL` | Yes | Full URL of the backend API, e.g. `https://hr-api.example.com` |

Copy `.env.example` to `.env` and fill in the values.

---

## Local Development

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.prod.txt

# Create .env from the example
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY

uvicorn api.server:app --reload --port 8000
```

API available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd hr-ui
cp .env.local.example .env.local   # or create manually
# .env.local contents:
#   VITE_API_BASE_URL=http://localhost:8000

npm install
npm run dev
```

UI available at `http://localhost:5173`.

---

## Docker (local full-stack)

```bash
# Copy and fill in environment variables
cp .env.example .env

# Build and run both services
docker compose up --build

# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

Data is persisted in a named Docker volume (`hr_data`) mounted at `/app/data`.

---

## IBM Cloud Code Engine Deployment

### One-time setup

1. **Install IBM Cloud CLI**
   ```bash
   curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
   ibmcloud plugin install container-registry
   ibmcloud plugin install code-engine
   ```

2. **Log in and create resources**
   ```bash
   ibmcloud login --apikey <YOUR_API_KEY> -r us-south -g Default
   ibmcloud cr namespace-add hr-prescreening
   ibmcloud ce project create --name hr-prescreening
   ```

3. **Create a persistent volume for DuckDB** (Code Engine → Volumes)
   - Type: IBM Cloud File Storage
   - Mount path: `/app/data`
   - Attach to `hr-api` application

4. **Build and push images**
   ```bash
   ibmcloud cr login

   # Backend
   docker build -f Dockerfile.backend \
     -t icr.io/hr-prescreening/hr-api:latest .
   docker push icr.io/hr-prescreening/hr-api:latest

   # Frontend (replace URL with your Code Engine backend URL)
   docker build -f hr-ui/Dockerfile \
     --build-arg VITE_API_BASE_URL=https://hr-api.<region>.codeengine.appdomain.cloud \
     -t icr.io/hr-prescreening/hr-ui:latest ./hr-ui
   docker push icr.io/hr-prescreening/hr-ui:latest
   ```

5. **Deploy applications**
   ```bash
   ibmcloud ce project select --name hr-prescreening

   # Backend
   ibmcloud ce app create \
     --name hr-api \
     --image icr.io/hr-prescreening/hr-api:latest \
     --env OPENAI_API_KEY=<your-key> \
     --env DB_PATH=/app/data/resumes.duckdb \
     --env CORS_ORIGINS=https://hr-ui.<region>.codeengine.appdomain.cloud \
     --min-scale 1 --port 8000 --cpu 0.5 --memory 1G

   # Frontend
   ibmcloud ce app create \
     --name hr-ui \
     --image icr.io/hr-prescreening/hr-ui:latest \
     --min-scale 1 --port 80 --cpu 0.25 --memory 0.5G
   ```

### GitHub Actions (CI/CD)

Add these secrets to your GitHub repository (`Settings → Secrets → Actions`):

| Secret | Value |
|---|---|
| `IBM_API_KEY` | Your IBM Cloud API key |
| `IBM_ICR_NAMESPACE` | Container Registry namespace (e.g. `hr-prescreening`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `VITE_API_BASE_URL` | Backend Code Engine URL |

The workflow at `.github/workflows/ibm-cloud-deploy.yml` builds and deploys both containers on every push to `main`.

---

## Running Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

Tests use an in-memory DuckDB instance and mock all OpenAI calls.

---

## Project Structure

```
.
├── api/
│   └── server.py            FastAPI routes
├── core/
│   ├── interview.py         AI question generation & answer scoring
│   ├── memory.py            DuckDB persistence layer
│   ├── parsing.py           Resume text extraction (PDF/DOCX/TXT)
│   ├── categorization.py    Resume category detection
│   └── scoring.py           Resume fit scoring
├── ingestion/
│   ├── onedrive_watcher.py  OneDrive polling (optional)
│   └── auth.py              Azure AD token
├── hr-ui/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InterviewPortal.jsx   Phone-screening interview form
│   │   │   ├── ReportCard.jsx        Scored report view + print
│   │   │   ├── SessionHistory.jsx    All sessions with search & stats
│   │   │   ├── NewInterview.jsx      Start interview (upload resume)
│   │   │   └── Header.jsx
│   │   └── api/client.js             API calls
│   ├── Dockerfile
│   └── nginx.conf
├── tests/
├── Dockerfile.backend
├── docker-compose.yml
├── requirements.prod.txt    Minimal production requirements
└── .env.example
```

---

## Notes

- **DuckDB persistence**: DuckDB stores data in a single file. In containerised environments, always mount a persistent volume at the path set by `DB_PATH`. Without a volume, data is lost on container restart.
- **OpenAI fallback**: If the AI returns question types outside the allowed set (`Introduction`, `Background`, `Behavioral`, `Compensation`, `Logistics`), the system falls back to a fixed pre-screening template automatically.
- **Print to PDF**: The report card has a print-optimised layout. Use `Print / Save PDF` in the browser.

---

Made with care by [Tech9Labs](https://tech9labs.com)
