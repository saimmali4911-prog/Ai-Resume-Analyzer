import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-change-me')
    DEBUG = os.getenv('DEBUG', '1') == '1'
    MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '5'))
    MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
    WTF_CSRF_ENABLED = True

    USE_SQLITE = os.getenv('USE_SQLITE', '0') == '1'
    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'db.sqlite3')
    else:
        DB_NAME = os.getenv('DB_NAME', 'resume_analyzer')
        DB_USER = os.getenv('DB_USER', 'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
        DB_PORT = os.getenv('DB_PORT', '3306')
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
