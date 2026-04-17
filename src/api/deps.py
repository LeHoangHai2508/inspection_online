from __future__ import annotations

from dataclasses import dataclass

from src.counter.service import CounterService
from src.db.repositories.counter_repo import SQLiteCounterRepository
from src.db.repositories.iot_event_repo import SQLiteIoTEventRepository
from src.db.repositories.scan_result_repo import SQLiteScanResultRepository
from src.db.repositories.template_repo import SQLiteTemplateRepository
from src.db.sqlite import initialize_database
from src.pipeline.orchestrator import InspectionOrchestrator
from src.template_service.service import TemplateService
from src.utils.config_loader import load_yaml_config
from src.utils.paths import PROJECT_ROOT, ensure_storage_tree


@dataclass
class ApplicationContainer:
    template_service: TemplateService
    inspection_orchestrator: InspectionOrchestrator
    counter_service: CounterService
    iot_event_repository: SQLiteIoTEventRepository


def _check_ocr_backend_on_startup() -> None:
    """Fail fast if prod mode requires a real OCR backend but none is available."""
    app_cfg = load_yaml_config("configs/app.yaml", default={"env": "local"})
    ocr_cfg = load_yaml_config(
        "configs/ocr.yaml",
        default={"strict_real_ocr": False},
    )
    env = str(app_cfg.get("env", "local"))
    strict = bool(ocr_cfg.get("strict_real_ocr", False)) or env == "prod"

    if not strict:
        return

    import importlib.util
    import shutil

    has_paddle = importlib.util.find_spec("paddleocr") is not None
    has_tesseract = (
        importlib.util.find_spec("pytesseract") is not None
        or shutil.which("tesseract") is not None
    )
    if not has_paddle and not has_tesseract:
        raise RuntimeError(
            f"[STARTUP] env={env}, strict_real_ocr=true — "
            "no real OCR backend found (paddleocr / tesseract). "
            "Install one or set strict_real_ocr: false in configs/ocr.yaml."
        )


def build_container() -> ApplicationContainer:
    _check_ocr_backend_on_startup()
    ensure_storage_tree()
    db_path = str(PROJECT_ROOT / "data" / "sqlite" / "inspection.db")
    initialize_database(
        db_path=db_path,
        schema_path=str(PROJECT_ROOT / "src" / "db" / "schema.sql"),
    )
    template_repo = SQLiteTemplateRepository(db_path=db_path)
    template_service = TemplateService(repository=template_repo)
    return ApplicationContainer(
        template_service=template_service,
        inspection_orchestrator=InspectionOrchestrator(
            template_service=template_service,
            scan_result_repository=SQLiteScanResultRepository(db_path=db_path),
        ),
        counter_service=CounterService(
            repository=SQLiteCounterRepository(db_path=db_path)
        ),
        iot_event_repository=SQLiteIoTEventRepository(db_path=db_path),
    )


_container = build_container()


def get_container() -> ApplicationContainer:
    return _container
