from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List


class Settings:
    """Runtime settings loaded from environment variables.

    Defaults are intentionally local-development friendly. Production deployments
    should override paths, CORS origins, secrets and upload limits.
    """

    def __init__(self) -> None:
        self.backend_dir = Path(__file__).resolve().parents[1]
        self.project_root = Path(__file__).resolve().parents[2]
        self.app_name = "AI-Based Smart Vehicle Claim Assessment"
        self.environment = os.getenv("SVC_ENV", "development")
        self.demo_mode_enabled = os.getenv("SVC_DEMO_MODE", "true").lower() == "true"
        self.database_path = Path(os.getenv("SVC_DB_PATH", str(self.project_root / "outputs" / "app.sqlite3")))
        self.storage_dir = Path(os.getenv("SVC_STORAGE_DIR", str(self.project_root / "outputs")))
        self.upload_dir = self.storage_dir / "uploads"
        self.overlay_dir = self.storage_dir / "overlays"
        self.report_dir = self.storage_dir / "reports"
        self.model_dir = Path(os.getenv("SVC_MODEL_DIR", str(self.project_root / "models")))
        self.data_dir = Path(os.getenv("SVC_DATA_DIR", str(self.project_root / "data")))
        self.config_dir = Path(os.getenv("SVC_CONFIG_DIR", str(self.project_root / "configs")))
        self.max_image_mb = int(os.getenv("SVC_MAX_IMAGE_MB", "10"))
        self.max_document_mb = int(os.getenv("SVC_MAX_DOCUMENT_MB", "15"))
        self.cors_origins = self._split_origins(os.getenv("SVC_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
        self.yolo_weights_path = os.getenv("SVC_YOLO_WEIGHTS", "")
        self.ocr_engine = os.getenv("SVC_OCR_ENGINE", "auto")
        self.log_level = os.getenv("SVC_LOG_LEVEL", "INFO")

    @staticmethod
    def _split_origins(raw: str) -> List[str]:
        return [x.strip() for x in raw.split(",") if x.strip()]

    def ensure_dirs(self) -> None:
        for path in [self.storage_dir, self.upload_dir, self.overlay_dir, self.report_dir, self.database_path.parent]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
