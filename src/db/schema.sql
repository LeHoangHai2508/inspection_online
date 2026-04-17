CREATE TABLE IF NOT EXISTS templates (
    template_id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    product_code TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    review_notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS template_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    version TEXT NOT NULL,
    side TEXT NOT NULL,
    raw_text TEXT,
    source_file_path TEXT,
    approved_by TEXT,
    approved_at TEXT,
    UNIQUE(template_id, version, side),
    FOREIGN KEY(template_id) REFERENCES templates(template_id)
);

CREATE TABLE IF NOT EXISTS template_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    version TEXT NOT NULL,
    side TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_type TEXT NOT NULL,
    required INTEGER NOT NULL DEFAULT 1,
    compare_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    expected_value TEXT,
    bbox_json TEXT,
    FOREIGN KEY(template_id) REFERENCES templates(template_id)
);

CREATE TABLE IF NOT EXISTS template_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    version TEXT NOT NULL,
    side TEXT NOT NULL,
    line_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    confidence REAL,
    bbox_json TEXT,
    FOREIGN KEY(template_id) REFERENCES templates(template_id)
);

CREATE TABLE IF NOT EXISTS scan_jobs (
    scan_job_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    line_id TEXT,
    station_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(template_id) REFERENCES templates(template_id)
);

CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_job_id TEXT NOT NULL,
    side TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    quality_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);

CREATE TABLE IF NOT EXISTS ocr_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_job_id TEXT NOT NULL,
    side TEXT NOT NULL,
    camera_id TEXT,
    raw_text TEXT,
    blocks_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);

CREATE TABLE IF NOT EXISTS compare_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_job_id TEXT NOT NULL,
    side TEXT NOT NULL,
    field_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    expected_value TEXT,
    actual_value TEXT,
    confidence REAL,
    bbox_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);

CREATE TABLE IF NOT EXISTS side_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_job_id TEXT NOT NULL,
    side TEXT NOT NULL,
    status TEXT NOT NULL,
    raw_text TEXT,
    processing_time_ms INTEGER,
    annotated_assets_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);

CREATE TABLE IF NOT EXISTS overall_results (
    scan_job_id TEXT PRIMARY KEY,
    side1_status TEXT,
    side2_status TEXT,
    overall_status TEXT,
    operator_action_required TEXT,
    highest_severity TEXT,
    publish_to_iot INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);

CREATE TABLE IF NOT EXISTS iot_publish_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_job_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    publish_status TEXT NOT NULL,
    payload_path TEXT,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(scan_job_id) REFERENCES scan_jobs(scan_job_id)
);
