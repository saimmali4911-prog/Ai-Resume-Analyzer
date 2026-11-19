import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'resume-analyzer-secret-key-2026')
    DEBUG = os.getenv('DEBUG', '1') == '1'
    MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '5'))
    MEDIA_ROOT = os.getenv('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    SUPABASE_URL = os.getenv('SUPABASE_URL', os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')).strip()
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', os.getenv('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY', '')).strip()

    raw_db_url = os.getenv('DATABASE_URL', '').strip()
    if raw_db_url:
        # Supabase / Heroku often supply postgres:// which SQLAlchemy 2.0 requires as postgresql://
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
        # Select best available PostgreSQL driver (psycopg 3, psycopg2, or pure-python pg8000)
        if raw_db_url.startswith('postgresql://') and not raw_db_url.startswith('postgresql+'):
            try:
                import psycopg
            except ImportError:
                try:
                    import psycopg2
                    raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
                except ImportError:
                    try:
                        import pg8000
                        raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
                    except ImportError:
                        pass
        SQLALCHEMY_DATABASE_URI = raw_db_url
    elif os.getenv('USE_SQLITE', '1') == '1':
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
    else:
        DB_NAME = os.getenv('DB_NAME', 'resume_analyzer')
        DB_USER = os.getenv('DB_USER', 'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
        DB_PORT = os.getenv('DB_PORT', '3306')
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SAMESITE = 'None' if os.getenv('COOKIE_SECURE', '0') == '1' else 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('COOKIE_SECURE', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
