import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "aws-diary-secret-key-change-in-production")
    
    # Database Configuration (AWS RDS MySQL or SQLite fallback)
    DB_HOST = os.getenv("DB_HOST", "")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "admin")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "diarydb")
    USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true" or not DB_HOST

    # Storage Configuration (AWS S3 or Local fallback)
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true" or not S3_BUCKET_NAME
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
