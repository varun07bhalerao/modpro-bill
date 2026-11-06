import os
import shutil
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

def is_serverless_env() -> bool:
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"):
        return True
    storage_dir = BASE_DIR / "storage"
    if storage_dir.exists() and not os.access(str(storage_dir), os.W_OK):
        return True
    if not storage_dir.exists() and not os.access(str(BASE_DIR), os.W_OK):
        return True
    return False

is_serverless = is_serverless_env()

if is_serverless:
    default_storage = Path("/tmp/storage")
    default_storage.mkdir(parents=True, exist_ok=True)
    (default_storage / "original-documents").mkdir(parents=True, exist_ok=True)
    (default_storage / "tagged-documents").mkdir(parents=True, exist_ok=True)

    # Pre-populate DB if present
    src_db = BASE_DIR / "storage" / "billnexa.db"
    dest_db = default_storage / "billnexa.db"
    if not dest_db.exists() and src_db.exists():
        try:
            shutil.copy2(str(src_db), str(dest_db))
        except Exception:
            pass

    # Ensure SQLite points to writable /tmp
    configured_db = os.getenv("DATABASE_URL")
    if not configured_db or "sqlite" in configured_db:
        final_db = f"sqlite:////tmp/storage/billnexa.db"
    else:
        final_db = configured_db
else:
    default_storage = BASE_DIR / "storage"
    configured_db = os.getenv("DATABASE_URL")
    final_db = configured_db or f"sqlite:///{BASE_DIR / 'storage' / 'billnexa.db'}"

class Settings(BaseModel):
    APP_NAME: str = "Bill Nexa"
    APP_VERSION: str = "1.0.0"
    ENV: str = os.getenv("ENV", "development")
    
    # Storage
    STORAGE_DIR: Path = default_storage
    ORIGINAL_DOCS_DIR: Path = default_storage / "original-documents"
    TAGGED_DOCS_DIR: Path = default_storage / "tagged-documents"
    
    # Database
    DATABASE_URL: str = final_db
    
    # Supabase (Optional for direct connection)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # AI Engine
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "demo") # demo | gemini | openai
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "gemini-1.5-pro")

    # JWT Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "bill-nexa-enterprise-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

settings = Settings()

# Ensure directories exist
try:
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.ORIGINAL_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    settings.TAGGED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
