# ResumeAI – Flask + MySQL + scikit-learn Resume Analyzer

## Tech Stack
- **Backend**: Python + Flask
- **Database**: MySQL (via PyMySQL + Flask-SQLAlchemy) · SQLite fallback for dev (`USE_SQLITE=1`)
- **Frontend**: HTML, CSS, JavaScript (Bootstrap 5.3, Bootstrap Icons, Chart.js, Inter font)
- **NLP/Analysis**: scikit-learn (TF-IDF + cosine similarity) for job matching and keyword extraction
- **File parsing**: PyMuPDF (`fitz`) for PDF, `python-docx` for DOCX
- **Auth**: Flask-Login + Werkzeug password hashing
- **Forms**: Flask-WTF / WTForms

## Project Structure
```
app.py               # Main Flask application & routes
config.py            # Configuration (MySQL / SQLite)
models.py            # SQLAlchemy models
forms.py             # WTForms form classes
services/
  extract.py         # PDF/DOCX text extraction
  rules.py           # ATS rule-based checks
  nlp.py             # TF-IDF + cosine similarity analysis
templates/           # Jinja2 templates (same design as Django version)
static/
  css/style.css      # Styles (copied from Django project)
  js/app.js          # Frontend JS (Flask-adapted)
media/               # Uploaded resume files
requirements.txt
.env.example
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
# Copy example and edit as needed
copy .env.example .env
```

The default `.env` uses **SQLite** (`USE_SQLITE=1`) — no MySQL setup needed for development.

### 3. Run the app
```bash
python app.py
```

Visit http://127.0.0.1:5000

## MySQL Setup (Production)

1. Create database:
```sql
CREATE DATABASE resume_analyzer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Update `.env`:
```
USE_SQLITE=0
DB_NAME=resume_analyzer
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

3. Tables are created automatically on first run via `db.create_all()`.

## Features
| Feature | Method |
|---------|--------|
| Resume Score | Rule-based section detection + TF-IDF keyword analysis |
| ATS Checker | Rule-based formatting checks (60%) + TF-IDF keyword density (40%) |
| Job Matching | TF-IDF cosine similarity between resume and job description |
| Improvement Suggestions | Keyword gap analysis + action verb recommendations |
| File Upload | PDF (PyMuPDF) + DOCX (python-docx) with magic-byte validation |
| Auth | Flask-Login + Werkzeug `pbkdf2:sha256` password hashing |
| CSRF Protection | Flask-WTF on all forms |

## Migration from Django
Key changes from the original Django version:
- Django ORM → SQLAlchemy (Flask-SQLAlchemy)
- Django auth → Flask-Login + Werkzeug
- Django forms → Flask-WTF / WTForms
- `{% url %}` → `{{ url_for() }}`
- `{% static %}` → `{{ url_for('static', filename=...) }}`
- `{% csrf_token %}` → `{{ form.hidden_tag() }}` or manual `<input name="csrf_token">`
- Gemini AI → scikit-learn TF-IDF + cosine similarity
