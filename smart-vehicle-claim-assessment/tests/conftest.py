import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

TEST_OUTPUTS = PROJECT_ROOT / "outputs" / "test"
if TEST_OUTPUTS.exists():
    shutil.rmtree(TEST_OUTPUTS)
TEST_OUTPUTS.mkdir(parents=True, exist_ok=True)
os.environ["SVC_DB_PATH"] = str(TEST_OUTPUTS / "test_app.sqlite3")
os.environ["SVC_STORAGE_DIR"] = str(TEST_OUTPUTS)
os.environ["SVC_DATA_DIR"] = str(PROJECT_ROOT / "data")
os.environ["SVC_CONFIG_DIR"] = str(PROJECT_ROOT / "configs")
os.environ["SVC_DEMO_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import db  # noqa: E402


db.init_db()
client = TestClient(app)
