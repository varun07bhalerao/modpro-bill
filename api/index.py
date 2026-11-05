import sys
import os
import shutil
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure writable storage in /tmp when running serverless
tmp_storage = Path("/tmp/storage")
tmp_storage.mkdir(parents=True, exist_ok=True)
(tmp_storage / "original-documents").mkdir(parents=True, exist_ok=True)
(tmp_storage / "tagged-documents").mkdir(parents=True, exist_ok=True)

# Copy seed SQLite database if not present in /tmp
tmp_db = tmp_storage / "billnexa.db"
src_db = ROOT_DIR / "storage" / "billnexa.db"
if not tmp_db.exists() and src_db.exists():
    try:
        shutil.copy2(str(src_db), str(tmp_db))
    except Exception:
        pass

# Copy storage sample documents if available
src_docs = ROOT_DIR / "storage" / "original-documents"
if src_docs.exists():
    for f in src_docs.glob("*.pdf"):
        target_f = tmp_storage / "original-documents" / f.name
        if not target_f.exists():
            try:
                shutil.copy2(str(f), str(target_f))
            except Exception:
                pass

src_tagged = ROOT_DIR / "storage" / "tagged-documents"
if src_tagged.exists():
    for f in src_tagged.glob("*.pdf"):
        target_f = tmp_storage / "tagged-documents" / f.name
        if not target_f.exists():
            try:
                shutil.copy2(str(f), str(target_f))
            except Exception:
                pass

from backend.app.main import app
