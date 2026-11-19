# ResumeXpert AI – Decoupled Full-Stack Resume Analyzer

Decoupled architecture featuring a Flask REST API backend and a standalone, static frontend deployable to Vercel or Netlify.

---

## Architecture Overview

```
resume_analyzer_flask/
├── backend/                  # Flask REST API
│   ├── app.py                # Main Flask REST API & CORS configuration
│   ├── config.py             # Config (MySQL + SQLite fallback)
│   ├── models.py             # SQLAlchemy models with .to_dict() serialization
│   ├── services/             # Core NLP & Extraction services
│   │   ├── extract.py        # PDF (PyMuPDF) and DOCX (python-docx) extraction
│   │   ├── rules.py          # Rule-based ATS formatting & structure checks
│   │   └── nlp.py            # scikit-learn TF-IDF + cosine similarity
│   ├── media/                # Storage for user-uploaded resumes
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Environment variables
│   └── .env.example          # Example environment configuration
│
├── frontend/                 # Decoupled Static Frontend (Vercel/Netlify ready)
│   ├── index.html            # Landing page
│   ├── login.html            # User login page
│   ├── register.html         # User registration page
│   ├── dashboard.html        # Interactive dashboard with Chart.js
│   ├── upload.html           # Drag & drop upload, text extraction & management
│   ├── tool.html             # Multi-tool runner (Analysis, ATS, Match, Improve)
│   ├── history.html          # Full analysis history table
│   ├── profile.html          # User profile settings
│   ├── css/
│   │   └── style.css         # Custom Bootstrap 5 theme & styling
│   ├── js/
│   │   ├── api.js            # Centralized API client (fetch with credentials/tokens)
│   │   └── app.js            # Frontend logic, Chart.js graphs, UI state
│   └── vercel.json           # Vercel deployment configuration
│
├── .gitignore
└── README.md
```

---

## 1. Backend Setup & Run

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Environment Configuration
The `.env` file comes preconfigured with SQLite fallback (`USE_SQLITE=1`):
```ini
SECRET_KEY=dev-secret-key-resume-analyzer-2026
DEBUG=1
USE_SQLITE=1
MAX_UPLOAD_MB=5
PORT=5000
```

To switch to MySQL in production, set:
```ini
USE_SQLITE=0
DB_NAME=resume_analyzer
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### Start the Backend
```bash
cd backend
python app.py
```
Backend API will be running on `http://127.0.0.1:5000`.

---

## 2. Frontend Setup & Run

The `frontend/` directory is 100% static (HTML, CSS, JS) and connects to `http://127.0.0.1:5000` by default.

### Run Locally
Serve the `frontend/` directory with any static server:
```bash
# Option A: Python simple HTTP server
cd frontend
python -m http.server 3000

# Option B: Node http-server / npx serve
npx serve frontend

# Option C: VS Code Live Server
# Right click frontend/index.html -> "Open with Live Server"
```
Then visit `http://localhost:3000`.

---

## 3. Deploying Frontend to Vercel / Netlify

### Vercel
1. Set the Root Directory to `frontend`.
2. Vercel automatically detects the static HTML files and applies `vercel.json` with clean URLs.
3. If your backend is hosted separately (e.g. Railway, Render, Fly.io), specify `window.API_BASE_URL` or store it in `localStorage.setItem('API_BASE_URL', 'https://your-api.domain.com')`.

### Netlify
1. Publish directory: `frontend`.
2. Connect backend URL as needed.

---

## 4. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `POST` | `/api/auth/register` | Register new user, returns token & user profile |
| `POST` | `/api/auth/login` | Login user, returns token & user profile |
| `POST` | `/api/auth/logout` | Invalidate user session |
| `GET` | `/api/auth/me` | Current user profile & resume statistics |
| `PUT` | `/api/auth/profile` | Update user names, email, phone, role, bio |
| `GET` | `/api/resumes` | List current user's uploaded resumes |
| `POST` | `/api/resumes/upload` | Multipart upload (PDF/DOCX), validates & extracts text |
| `GET` | `/api/resumes/<id>/text` | Get extracted text for a resume |
| `GET` | `/api/resumes/<id>/file` | Download original uploaded file |
| `DELETE` | `/api/resumes/<id>` | Delete resume & associated analyses |
| `POST` | `/api/analysis/run/<kind>` | Run `analysis`, `ats`, `match`, or `improve` |
| `GET` | `/api/analysis/history` | List all past analyses sorted by date |
| `GET` | `/api/analysis/<kind>/<id>` | Get specific analysis result |
| `GET` | `/api/dashboard` | Dashboard stats, recent matches & chart datasets |
