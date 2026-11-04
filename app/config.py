import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-expense-tracker-secret-key-2026")
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DATA_DIR / 'expense_tracker.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
    ALLOWED_IMPORT_EXTENSIONS = {"csv", "xlsx", "xls"}
    
    # Machine Learning / Heuristic Thresholds
    ANOMALY_IQR_MULTIPLIER = 2.0
    ANOMALY_ZSCORE_THRESHOLD = 2.5
    CATEGORIZATION_CONFIDENCE_THRESHOLD = 0.55


    # Authentication / Access Control
    REQUIRE_LOGIN = True

class TestConfig(Config):
    TESTING = True
    REQUIRE_LOGIN = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

