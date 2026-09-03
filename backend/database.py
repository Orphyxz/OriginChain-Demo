import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .domain import (
    DEFAULT_PRODUCT_SPECIFICATION_CODE,
    DEMO_QUALITY_STANDARDS,
    EVIDENCE_ISSUERS,
    PRODUCT_SPECIFICATION,
    PRODUCT_SPECIFICATION_REQUIREMENTS,
    QUALITY_PROFILE,
    QUALITY_SOURCES,
    STAGE_PREFIX,
)
from .metadata_hash import canonical_metadata, metadata_hash, product_metadata


DEFAULT_DB_PATH = Path(__file__).with_name("originchain_demo.sqlite3")


class ProductRepository:
    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self.db_path = Path(db_path or os.environ.get("ORIGINCHAIN_DB_PATH", DEFAULT_DB_PATH))

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    organization_name TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS products (
                    product_code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    batch_number TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    product_key TEXT NOT NULL,
                    metadata_hash TEXT NOT NULL,
                    registration_tx_hash TEXT NOT NULL,
                    registration_block_number INTEGER NOT NULL,
                    category TEXT NOT NULL DEFAULT 'SKINCARE',
                    subcategory TEXT NOT NULL DEFAULT 'FACIAL_SERUM',
                    product_type TEXT NOT NULL DEFAULT 'ANTI_AGING_SERUM',
                    manufactured_date TEXT,
                    expiry_date TEXT,
                    current_stage TEXT NOT NULL DEFAULT 'MANUFACTURER',
                    final_sale_status TEXT NOT NULL DEFAULT 'NOT_READY',
                    lineage_hash TEXT,
                    registered_by_user_id TEXT,
                    specification_code TEXT,
                    specification_version TEXT,
                    specification_snapshot_hash TEXT,
                    specification_assigned_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS ownership_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT NOT NULL,
                    from_role TEXT NOT NULL,
                    from_address TEXT NOT NULL,
                    to_role TEXT NOT NULL,
                    to_address TEXT NOT NULL,
                    transaction_hash TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    initiated_by_user_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_code) REFERENCES products(product_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS raw_material_batches (
                    id TEXT PRIMARY KEY,
                    internal_batch_id TEXT NOT NULL UNIQUE,
                    material_name TEXT NOT NULL,
                    material_category TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    supplier_identifier TEXT,
                    supplier_lot_number TEXT NOT NULL,
                    quantity REAL NOT NULL CHECK(quantity > 0),
                    unit TEXT NOT NULL,
                    manufacturing_date TEXT,
                    received_date TEXT NOT NULL,
                    expiry_retest_date TEXT,
                    country_source TEXT,
                    notes TEXT,
                    quality_status TEXT NOT NULL DEFAULT 'PENDING',
                    created_by_user_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS product_raw_materials (
                    product_code TEXT NOT NULL,
                    raw_material_batch_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(product_code, raw_material_batch_id),
                    FOREIGN KEY(product_code) REFERENCES products(product_code) ON DELETE CASCADE,
                    FOREIGN KEY(raw_material_batch_id) REFERENCES raw_material_batches(id)
                );

                CREATE TABLE IF NOT EXISTS quality_standards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    product_category TEXT NOT NULL,
                    product_subcategory TEXT NOT NULL,
                    supply_chain_stage TEXT NOT NULL,
                    category TEXT NOT NULL,
                    check_name TEXT NOT NULL,
                    requirement_description TEXT NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1,
                    evidence_required INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    reference_name TEXT,
                    reference_code TEXT,
                    notes TEXT,
                    classification TEXT NOT NULL DEFAULT 'ORIGINCHAIN_INTERNAL',
                    requirement_rationale TEXT NOT NULL DEFAULT '',
                    evidence_expectation TEXT NOT NULL DEFAULT '',
                    expected_document_type TEXT NOT NULL DEFAULT 'OTHER',
                    package_component TEXT,
                    expected_visual_characteristic TEXT,
                    defect_categories_json TEXT NOT NULL DEFAULT '[]',
                    trusted_issuer_required INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS quality_sources (
                    source_code TEXT PRIMARY KEY,
                    authority TEXT NOT NULL,
                    title TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    edition TEXT NOT NULL,
                    publication_year INTEGER,
                    status TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_verified_at TEXT NOT NULL,
                    revision_of_source_code TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    review_owner_user_id TEXT,
                    reviewed_by_user_id TEXT,
                    reviewed_at TEXT,
                    review_status TEXT NOT NULL DEFAULT 'CURRENT',
                    next_review_due TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(authority, title, edition)
                );

                CREATE TABLE IF NOT EXISTS quality_profiles (
                    profile_code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    product_category TEXT NOT NULL,
                    product_subcategory TEXT NOT NULL,
                    product_type TEXT NOT NULL,
                    disclaimer TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS quality_standard_sources (
                    standard_id INTEGER NOT NULL,
                    source_code TEXT NOT NULL,
                    mapping_precision TEXT NOT NULL DEFAULT 'STANDARD_LEVEL',
                    interpretation TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(standard_id, source_code),
                    FOREIGN KEY(standard_id) REFERENCES quality_standards(id) ON DELETE CASCADE,
                    FOREIGN KEY(source_code) REFERENCES quality_sources(source_code)
                );

                CREATE TABLE IF NOT EXISTS quality_profile_requirements (
                    profile_code TEXT NOT NULL,
                    standard_id INTEGER NOT NULL,
                    display_order INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(profile_code, standard_id),
                    FOREIGN KEY(profile_code) REFERENCES quality_profiles(profile_code) ON DELETE CASCADE,
                    FOREIGN KEY(standard_id) REFERENCES quality_standards(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS product_specifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    specification_code TEXT NOT NULL UNIQUE,
                    product_category TEXT NOT NULL,
                    product_subcategory TEXT NOT NULL,
                    product_type TEXT NOT NULL,
                    specification_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    effective_from TEXT,
                    effective_until TEXT,
                    created_by_user_id TEXT,
                    approved_at TEXT,
                    approved_by_user_id TEXT,
                    supersedes_specification_code TEXT,
                    change_summary TEXT NOT NULL,
                    disclaimer TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(product_type, version)
                );

                CREATE TABLE IF NOT EXISTS product_specification_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    specification_id INTEGER NOT NULL,
                    requirement_code TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requirement_type TEXT NOT NULL,
                    package_component TEXT,
                    expected_characteristic TEXT NOT NULL,
                    evidence_expectation TEXT NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1,
                    display_order INTEGER NOT NULL,
                    ml_eligible INTEGER NOT NULL DEFAULT 0,
                    visual_component TEXT,
                    defect_categories_json TEXT NOT NULL DEFAULT '[]',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(specification_id, requirement_code),
                    FOREIGN KEY(specification_id) REFERENCES product_specifications(id)
                );

                CREATE TABLE IF NOT EXISTS quality_standard_specification_requirements (
                    standard_id INTEGER NOT NULL,
                    specification_requirement_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(standard_id, specification_requirement_id),
                    FOREIGN KEY(standard_id) REFERENCES quality_standards(id) ON DELETE CASCADE,
                    FOREIGN KEY(specification_requirement_id) REFERENCES product_specification_requirements(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidence_issuers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issuer_code TEXT NOT NULL UNIQUE,
                    issuer_name TEXT NOT NULL,
                    issuer_type TEXT NOT NULL,
                    organization_name TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    trust_status TEXT NOT NULL,
                    verification_method TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS quality_change_records (
                    id TEXT PRIMARY KEY,
                    change_type TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_code TEXT NOT NULL,
                    previous_version TEXT,
                    new_version TEXT,
                    change_summary TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    requested_by_user_id TEXT,
                    approved_by_user_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_at TEXT
                );

                DROP TRIGGER IF EXISTS immutable_used_product_specification_update;
                CREATE TRIGGER immutable_used_product_specification_update
                BEFORE UPDATE ON product_specifications
                WHEN EXISTS (
                    SELECT 1 FROM products p
                    WHERE p.specification_code = OLD.specification_code
                )
                AND (
                    NEW.specification_code IS NOT OLD.specification_code OR
                    NEW.product_category IS NOT OLD.product_category OR
                    NEW.product_subcategory IS NOT OLD.product_subcategory OR
                    NEW.product_type IS NOT OLD.product_type OR
                    NEW.specification_name IS NOT OLD.specification_name OR
                    NEW.version IS NOT OLD.version OR
                    NEW.effective_from IS NOT OLD.effective_from OR
                    NEW.created_by_user_id IS NOT OLD.created_by_user_id OR
                    NEW.approved_at IS NOT OLD.approved_at OR
                    NEW.approved_by_user_id IS NOT OLD.approved_by_user_id OR
                    NEW.supersedes_specification_code IS NOT OLD.supersedes_specification_code OR
                    NEW.change_summary IS NOT OLD.change_summary OR
                    NEW.disclaimer IS NOT OLD.disclaimer
                )
                BEGIN
                    SELECT RAISE(ABORT, 'A product specification assigned to a batch is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_used_product_specification_delete
                BEFORE DELETE ON product_specifications
                WHEN EXISTS (
                    SELECT 1 FROM products p
                    WHERE p.specification_code = OLD.specification_code
                )
                BEGIN
                    SELECT RAISE(ABORT, 'A product specification assigned to a batch is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_used_product_requirement_update
                BEFORE UPDATE ON product_specification_requirements
                WHEN EXISTS (
                    SELECT 1 FROM products p
                    JOIN product_specifications s ON s.specification_code = p.specification_code
                    WHERE s.id = OLD.specification_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Requirements for an assigned product specification are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS immutable_used_product_requirement_delete
                BEFORE DELETE ON product_specification_requirements
                WHEN EXISTS (
                    SELECT 1 FROM products p
                    JOIN product_specifications s ON s.specification_code = p.specification_code
                    WHERE s.id = OLD.specification_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Requirements for an assigned product specification are immutable');
                END;

                CREATE TABLE IF NOT EXISTS quality_results (
                    id TEXT PRIMARY KEY,
                    context_type TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    standard_id INTEGER NOT NULL,
                    result TEXT NOT NULL,
                    notes TEXT,
                    inspector_stage TEXT NOT NULL,
                    submitted_by_user_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(context_type, context_id, standard_id),
                    FOREIGN KEY(standard_id) REFERENCES quality_standards(id)
                );

                CREATE TABLE IF NOT EXISTS quality_result_sources (
                    quality_result_id TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    title TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL DEFAULT 'UNKNOWN',
                    source_type TEXT NOT NULL DEFAULT 'STANDARD',
                    edition TEXT NOT NULL,
                    publication_year INTEGER,
                    status_at_submission TEXT NOT NULL,
                    mapping_precision TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_verified_at TEXT NOT NULL DEFAULT '',
                    snapshotted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(quality_result_id, source_code),
                    FOREIGN KEY(quality_result_id) REFERENCES quality_results(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidence_files (
                    id TEXT PRIMARY KEY,
                    quality_result_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL UNIQUE,
                    content_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    uploader_stage TEXT NOT NULL,
                    visibility TEXT NOT NULL DEFAULT 'INTERNAL',
                    blockchain_tx_hash TEXT,
                    blockchain_block_number INTEGER,
                    uploaded_by_user_id TEXT,
                    document_type TEXT NOT NULL DEFAULT 'OTHER',
                    laboratory_name TEXT,
                    report_reference TEXT,
                    test_date TEXT,
                    test_method_source_code TEXT,
                    result_summary TEXT,
                    accreditation_status_text TEXT,
                    document_notes TEXT,
                    issuer_id INTEGER,
                    issuer_code_snapshot TEXT,
                    issuer_name_snapshot TEXT,
                    issuer_type_snapshot TEXT,
                    issuer_trust_status_at_submission TEXT,
                    issuer_report_number TEXT,
                    issuer_document_date TEXT,
                    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                    verified_by_user_id TEXT,
                    verified_at TEXT,
                    verification_notes TEXT,
                    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(quality_result_id) REFERENCES quality_results(id) ON DELETE CASCADE,
                    FOREIGN KEY(issuer_id) REFERENCES evidence_issuers(id)
                );

                CREATE TABLE IF NOT EXISTS stage_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_type TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    commitment_hash TEXT NOT NULL,
                    blocking_reasons_json TEXT NOT NULL DEFAULT '[]',
                    blockchain_tx_hash TEXT,
                    blockchain_block_number INTEGER,
                    approved_at TEXT,
                    approved_by_user_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(context_type, context_id, stage)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_user_id TEXT,
                    actor_role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    result TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._upgrade_products(connection)
            self._upgrade_attribution(connection)
            self._upgrade_quality_traceability(connection)
            self._upgrade_governance(connection)
            self._seed_quality_sources(connection)
            self._seed_standards(connection)
            self._seed_profile(connection)
            self._seed_product_specification(connection)
            self._seed_evidence_issuers(connection)
            self._seed_change_records(connection)

    def _upgrade_products(self, connection: sqlite3.Connection) -> None:
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(products)")}
        additions = {
            "category": "TEXT NOT NULL DEFAULT 'SKINCARE'",
            "subcategory": "TEXT NOT NULL DEFAULT 'FACIAL_SERUM'",
            "product_type": "TEXT NOT NULL DEFAULT 'ANTI_AGING_SERUM'",
            "manufactured_date": "TEXT",
            "expiry_date": "TEXT",
            "current_stage": "TEXT NOT NULL DEFAULT 'MANUFACTURER'",
            "final_sale_status": "TEXT NOT NULL DEFAULT 'NOT_READY'",
            "lineage_hash": "TEXT",
            "specification_code": "TEXT",
            "specification_version": "TEXT",
            "specification_snapshot_hash": "TEXT",
            "specification_assigned_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")

    def _upgrade_attribution(self, connection: sqlite3.Connection) -> None:
        additions = {
            "products": {"registered_by_user_id": "TEXT"},
            "ownership_transfers": {"initiated_by_user_id": "TEXT"},
            "raw_material_batches": {"created_by_user_id": "TEXT"},
            "quality_results": {"submitted_by_user_id": "TEXT"},
            "evidence_files": {"uploaded_by_user_id": "TEXT"},
            "stage_approvals": {"approved_by_user_id": "TEXT"},
        }
        for table, columns in additions.items():
            existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _upgrade_quality_traceability(self, connection: sqlite3.Connection) -> None:
        additions = {
            "quality_standards": {
                "classification": "TEXT NOT NULL DEFAULT 'ORIGINCHAIN_INTERNAL'",
                "requirement_rationale": "TEXT NOT NULL DEFAULT ''",
                "evidence_expectation": "TEXT NOT NULL DEFAULT ''",
                "expected_document_type": "TEXT NOT NULL DEFAULT 'OTHER'",
                "package_component": "TEXT",
                "expected_visual_characteristic": "TEXT",
                "defect_categories_json": "TEXT NOT NULL DEFAULT '[]'",
                "trusted_issuer_required": "INTEGER NOT NULL DEFAULT 0",
            },
            "evidence_files": {
                "document_type": "TEXT NOT NULL DEFAULT 'OTHER'",
                "laboratory_name": "TEXT",
                "report_reference": "TEXT",
                "test_date": "TEXT",
                "test_method_source_code": "TEXT",
                "result_summary": "TEXT",
                "accreditation_status_text": "TEXT",
                "document_notes": "TEXT",
                "issuer_id": "INTEGER",
                "issuer_code_snapshot": "TEXT",
                "issuer_name_snapshot": "TEXT",
                "issuer_type_snapshot": "TEXT",
                "issuer_trust_status_at_submission": "TEXT",
                "issuer_report_number": "TEXT",
                "issuer_document_date": "TEXT",
                "verification_status": "TEXT NOT NULL DEFAULT 'UNVERIFIED'",
                "verified_by_user_id": "TEXT",
                "verified_at": "TEXT",
                "verification_notes": "TEXT",
            },
            "quality_result_sources": {
                "jurisdiction": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
                "source_type": "TEXT NOT NULL DEFAULT 'STANDARD'",
                "last_verified_at": "TEXT NOT NULL DEFAULT ''",
            },
        }
        for table, columns in additions.items():
            existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _upgrade_governance(self, connection: sqlite3.Connection) -> None:
        additions = {
            "quality_sources": {
                "review_owner_user_id": "TEXT",
                "reviewed_by_user_id": "TEXT",
                "reviewed_at": "TEXT",
                "review_status": "TEXT NOT NULL DEFAULT 'CURRENT'",
                "next_review_due": "TEXT",
            },
        }
        for table, columns in additions.items():
            existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _seed_quality_sources(self, connection: sqlite3.Connection) -> None:
        for source in QUALITY_SOURCES:
            connection.execute(
                """
                INSERT INTO quality_sources (
                    source_code, authority, title, jurisdiction, source_type, edition,
                    publication_year, status, source_url, last_verified_at,
                    revision_of_source_code, notes
                ) VALUES (
                    :source_code, :authority, :title, :jurisdiction, :source_type, :edition,
                    :publication_year, :status, :source_url, :last_verified_at,
                    :revision_of_source_code, :notes
                )
                ON CONFLICT(source_code) DO UPDATE SET
                    authority = excluded.authority, title = excluded.title,
                    jurisdiction = excluded.jurisdiction, source_type = excluded.source_type,
                    status = excluded.status, source_url = excluded.source_url,
                    last_verified_at = excluded.last_verified_at,
                    revision_of_source_code = excluded.revision_of_source_code,
                    notes = excluded.notes, updated_at = CURRENT_TIMESTAMP
                """,
                source,
            )
            connection.execute(
                """
                UPDATE quality_sources SET
                    review_owner_user_id = COALESCE(review_owner_user_id, 'user_admin'),
                    reviewed_by_user_id = COALESCE(reviewed_by_user_id, 'user_admin'),
                    reviewed_at = COALESCE(reviewed_at, '2026-08-30'),
                    review_status = COALESCE(review_status, 'CURRENT'),
                    next_review_due = COALESCE(next_review_due, '2027-02-28')
                WHERE source_code = ?
                """,
                (source["source_code"],),
            )

    def seed_user(self, user: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id, username, display_name, password_hash, role, organization_name, active
                ) VALUES (
                    :id, :username, :display_name, :password_hash, :role, :organization_name, :active
                )
                ON CONFLICT(username) DO UPDATE SET
                    display_name = excluded.display_name,
                    role = excluded.role,
                    organization_name = excluded.organization_name,
                    password_hash = CASE
                        WHEN users.password_hash = '' THEN excluded.password_hash
                        ELSE users.password_hash
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                user,
            )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),))

    def add_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        values = {
            **event,
            "metadata_json": json.dumps(event.get("metadata", {}), sort_keys=True, separators=(",", ":")),
        }
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (
                    actor_user_id, actor_role, action, entity_type, entity_id, result, metadata_json
                ) VALUES (
                    :actor_user_id, :actor_role, :action, :entity_type, :entity_id, :result, :metadata_json
                )
                """,
                values,
            )
            event_id = cursor.lastrowid
        return self._one("SELECT * FROM audit_events WHERE id = ?", (event_id,))

    def list_audit_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT a.*, u.username, u.display_name, u.organization_name
            FROM audit_events a LEFT JOIN users u ON u.id = a.actor_user_id
            ORDER BY a.id DESC LIMIT ?
            """,
            (limit,),
        )
        for row in rows:
            row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
        return rows

    def _seed_standards(self, connection: sqlite3.Connection) -> None:
        for item in DEMO_QUALITY_STANDARDS:
            code = item["code"]
            stage = next(stage for stage, prefix in STAGE_PREFIX.items() if code.startswith(prefix))
            connection.execute(
                """
                INSERT INTO quality_standards (
                    code, name, description, product_category, product_subcategory,
                    supply_chain_stage, category, check_name, requirement_description,
                    required, evidence_required, notes, classification, requirement_rationale,
                    evidence_expectation, expected_document_type, package_component,
                    expected_visual_characteristic, defect_categories_json, trusted_issuer_required
                ) VALUES (?, ?, ?, 'SKINCARE', 'FACIAL_SERUM', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    product_category = excluded.product_category,
                    product_subcategory = excluded.product_subcategory,
                    supply_chain_stage = excluded.supply_chain_stage,
                    category = excluded.category,
                    check_name = excluded.check_name,
                    requirement_description = excluded.requirement_description,
                    required = excluded.required,
                    evidence_required = excluded.evidence_required,
                    notes = excluded.notes,
                    classification = excluded.classification,
                    requirement_rationale = excluded.requirement_rationale,
                    evidence_expectation = excluded.evidence_expectation,
                    expected_document_type = excluded.expected_document_type,
                    package_component = excluded.package_component,
                    expected_visual_characteristic = excluded.expected_visual_characteristic,
                    defect_categories_json = excluded.defect_categories_json,
                    trusted_issuer_required = excluded.trusted_issuer_required
                """,
                (
                    code, "OriginChain Demo Quality Standard", item["check_name"], stage.value,
                    item["category"], item["check_name"], item["requirement_description"],
                    int(item["required"]), int(item["evidence_required"]),
                    "Educational source mapping; not a regulatory, laboratory, or certification claim.",
                    item["classification"], item["requirement_rationale"], item["evidence_expectation"],
                    item["expected_document_type"], item["package_component"],
                    item["expected_visual_characteristic"], json.dumps(item["defect_categories"]),
                    int(item["trusted_issuer_required"]),
                ),
            )
            standard_id = connection.execute(
                "SELECT id FROM quality_standards WHERE code = ?", (code,)
            ).fetchone()["id"]
            connection.execute("DELETE FROM quality_standard_sources WHERE standard_id = ?", (standard_id,))
            for source_code in item["sources"]:
                connection.execute(
                    """
                    INSERT INTO quality_standard_sources (
                        standard_id, source_code, mapping_precision, interpretation
                    ) VALUES (?, ?, 'STANDARD_LEVEL', ?)
                    """,
                    (standard_id, source_code, item["requirement_rationale"]),
                )

    def _seed_profile(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO quality_profiles (
                profile_code, name, description, jurisdiction, version, status,
                product_category, product_subcategory, product_type, disclaimer
            ) VALUES (
                :profile_code, :name, :description, :jurisdiction, :version, :status,
                :product_category, :product_subcategory, :product_type, :disclaimer
            )
            ON CONFLICT(profile_code) DO UPDATE SET
                name = excluded.name, description = excluded.description,
                jurisdiction = excluded.jurisdiction, version = excluded.version,
                status = excluded.status, product_category = excluded.product_category,
                product_subcategory = excluded.product_subcategory,
                product_type = excluded.product_type, disclaimer = excluded.disclaimer,
                updated_at = CURRENT_TIMESTAMP
            """,
            QUALITY_PROFILE,
        )
        for order, item in enumerate(DEMO_QUALITY_STANDARDS, start=1):
            standard_id = connection.execute(
                "SELECT id FROM quality_standards WHERE code = ?", (item["code"],)
            ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO quality_profile_requirements (profile_code, standard_id, display_order)
                VALUES (?, ?, ?)
                ON CONFLICT(profile_code, standard_id) DO UPDATE SET display_order = excluded.display_order
                """,
                (QUALITY_PROFILE["profile_code"], standard_id, order),
            )

    def _seed_product_specification(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO product_specifications (
                specification_code, product_category, product_subcategory, product_type,
                specification_name, version, status, effective_from, effective_until,
                created_by_user_id, approved_at, approved_by_user_id,
                supersedes_specification_code, change_summary, disclaimer
            ) VALUES (
                :specification_code, :product_category, :product_subcategory, :product_type,
                :specification_name, :version, :status, :effective_from, :effective_until,
                :created_by_user_id, :approved_at, :approved_by_user_id,
                :supersedes_specification_code, :change_summary, :disclaimer
            ) ON CONFLICT(specification_code) DO NOTHING
            """,
            PRODUCT_SPECIFICATION,
        )
        specification_id = connection.execute(
            "SELECT id FROM product_specifications WHERE specification_code = ?",
            (DEFAULT_PRODUCT_SPECIFICATION_CODE,),
        ).fetchone()["id"]
        for item in PRODUCT_SPECIFICATION_REQUIREMENTS:
            connection.execute(
                """
                INSERT INTO product_specification_requirements (
                    specification_id, requirement_code, category, description,
                    requirement_type, package_component, expected_characteristic,
                    evidence_expectation, required, display_order, ml_eligible,
                    visual_component, defect_categories_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(specification_id, requirement_code) DO NOTHING
                """,
                (
                    specification_id, item["requirement_code"], item["category"],
                    item["description"], item["requirement_type"], item["package_component"],
                    item["expected_characteristic"], item["evidence_expectation"],
                    int(item["required"]), item["display_order"], int(item["ml_eligible"]),
                    item["visual_component"], json.dumps(item["defect_categories"]),
                ),
            )
            requirement_id = connection.execute(
                """
                SELECT id FROM product_specification_requirements
                WHERE specification_id = ? AND requirement_code = ?
                """,
                (specification_id, item["requirement_code"]),
            ).fetchone()["id"]
            for check_code in item["quality_check_codes"]:
                standard = connection.execute(
                    "SELECT id FROM quality_standards WHERE code = ?", (check_code,)
                ).fetchone()
                if standard:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO quality_standard_specification_requirements (
                            standard_id, specification_requirement_id
                        ) VALUES (?, ?)
                        """,
                        (standard["id"], requirement_id),
                    )

        seeded_snapshot = {
            "specification_code": PRODUCT_SPECIFICATION["specification_code"],
            "version": PRODUCT_SPECIFICATION["version"],
            "product_type": PRODUCT_SPECIFICATION["product_type"],
            "requirements": [
                {
                    "requirement_code": item["requirement_code"],
                    "description": item["description"],
                    "expected_characteristic": item["expected_characteristic"],
                    "required": bool(item["required"]),
                    "visual_component": item.get("visual_component"),
                    "defect_categories": list(item.get("defect_categories", ())),
                }
                for item in PRODUCT_SPECIFICATION_REQUIREMENTS
            ],
        }
        connection.execute(
            """
            UPDATE products SET specification_code = ?, specification_version = ?,
                specification_snapshot_hash = ?, specification_assigned_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE specification_code IS NULL AND product_type = ?
            """,
            (
                PRODUCT_SPECIFICATION["specification_code"], PRODUCT_SPECIFICATION["version"],
                metadata_hash(seeded_snapshot), PRODUCT_SPECIFICATION["product_type"],
            ),
        )

    def _seed_evidence_issuers(self, connection: sqlite3.Connection) -> None:
        for issuer in EVIDENCE_ISSUERS:
            connection.execute(
                """
                INSERT INTO evidence_issuers (
                    issuer_code, issuer_name, issuer_type, organization_name,
                    jurisdiction, trust_status, verification_method, notes
                ) VALUES (
                    :issuer_code, :issuer_name, :issuer_type, :organization_name,
                    :jurisdiction, :trust_status, :verification_method, :notes
                ) ON CONFLICT(issuer_code) DO NOTHING
                """,
                issuer,
            )

    def _seed_change_records(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO quality_change_records (
                id, change_type, target_type, target_code, previous_version,
                new_version, change_summary, reason, requested_by_user_id,
                approved_by_user_id, status, created_at, approved_at
            ) VALUES (
                'chg_initial_aurelia_spec_v1', 'PRODUCT_SPEC_UPDATE',
                'PRODUCT_SPECIFICATION', ?, NULL, '1.0', ?, ?,
                'user_admin', 'user_admin', 'IMPLEMENTED',
                '2026-08-30T00:00:00Z', '2026-08-30T00:00:00Z'
            )
            """,
            (
                DEFAULT_PRODUCT_SPECIFICATION_CODE,
                PRODUCT_SPECIFICATION["change_summary"],
                "Initial fictional demo specification governance record.",
            ),
        )

    def create_raw_material(self, item: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO raw_material_batches (
                    id, internal_batch_id, material_name, material_category, supplier_name,
                    supplier_identifier, supplier_lot_number, quantity, unit,
                    manufacturing_date, received_date, expiry_retest_date,
                    country_source, notes, created_by_user_id
                ) VALUES (
                    :id, :internal_batch_id, :material_name, :material_category, :supplier_name,
                    :supplier_identifier, :supplier_lot_number, :quantity, :unit,
                    :manufacturing_date, :received_date, :expiry_retest_date,
                    :country_source, :notes, :created_by_user_id
                )
                """,
                item,
            )
        return self.get_raw_material(item["id"])

    def get_raw_material(self, material_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM raw_material_batches WHERE id = ?", (material_id,))

    def get_raw_material_by_batch(self, internal_batch_id: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM raw_material_batches WHERE internal_batch_id = ?",
            (internal_batch_id,),
        )

    def list_raw_materials(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM raw_material_batches ORDER BY created_at, material_name")

    def update_raw_material_status(self, material_id: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE raw_material_batches SET quality_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, material_id),
            )

    def product_specifications(self, approved_only: bool = False) -> list[dict[str, Any]]:
        where = ""
        params: tuple[Any, ...] = ()
        if approved_only:
            where = "WHERE active = 1 AND status = 'APPROVED'"
        rows = self._all(
            f"SELECT * FROM product_specifications {where} ORDER BY product_type, version",
            params,
        )
        for row in rows:
            row["active"] = bool(row["active"])
            row["requirement_count"] = self._one(
                "SELECT COUNT(*) AS count FROM product_specification_requirements WHERE specification_id = ? AND active = 1",
                (row["id"],),
            )["count"]
            row["visual_requirement_count"] = self._one(
                "SELECT COUNT(*) AS count FROM product_specification_requirements WHERE specification_id = ? AND active = 1 AND ml_eligible = 1",
                (row["id"],),
            )["count"]
        return rows

    def get_product_specification(self, specification_code: str) -> dict[str, Any] | None:
        row = self._one(
            "SELECT * FROM product_specifications WHERE specification_code = ?",
            (specification_code,),
        )
        if not row:
            return None
        row["active"] = bool(row["active"])
        row["requirements"] = self.product_specification_requirements(row["id"])
        row["snapshot_hash"] = self.product_specification_snapshot_hash(row)
        return row

    def product_specification_requirements(self, specification_id: int) -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT * FROM product_specification_requirements
            WHERE specification_id = ? AND active = 1 ORDER BY display_order
            """,
            (specification_id,),
        )
        for row in rows:
            row["required"] = bool(row["required"])
            row["ml_eligible"] = bool(row["ml_eligible"])
            row["active"] = bool(row["active"])
            row["defect_categories"] = json.loads(row.pop("defect_categories_json") or "[]")
        return rows

    def product_specification_snapshot_hash(self, specification: dict[str, Any]) -> str:
        requirements = specification.get("requirements") or self.product_specification_requirements(specification["id"])
        snapshot = {
            "specification_code": specification["specification_code"],
            "version": specification["version"],
            "product_type": specification["product_type"],
            "requirements": [
                {
                    "requirement_code": item["requirement_code"],
                    "description": item["description"],
                    "expected_characteristic": item["expected_characteristic"],
                    "required": bool(item["required"]),
                    "visual_component": item.get("visual_component"),
                    "defect_categories": item.get("defect_categories", []),
                }
                for item in requirements
            ],
        }
        return metadata_hash(snapshot)

    def create_product_specification(
        self, specification: dict[str, Any], requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not specification.get("change_summary", "").strip():
            raise ValueError("Product specification change summary is required")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO product_specifications (
                    specification_code, product_category, product_subcategory, product_type,
                    specification_name, version, status, effective_from, effective_until,
                    created_by_user_id, approved_at, approved_by_user_id,
                    supersedes_specification_code, change_summary, disclaimer, active
                ) VALUES (
                    :specification_code, :product_category, :product_subcategory, :product_type,
                    :specification_name, :version, :status, :effective_from, :effective_until,
                    :created_by_user_id, :approved_at, :approved_by_user_id,
                    :supersedes_specification_code, :change_summary, :disclaimer, :active
                )
                """,
                specification,
            )
            for item in requirements:
                requirement_cursor = connection.execute(
                    """
                    INSERT INTO product_specification_requirements (
                        specification_id, requirement_code, category, description,
                        requirement_type, package_component, expected_characteristic,
                        evidence_expectation, required, display_order, ml_eligible,
                        visual_component, defect_categories_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cursor.lastrowid, item["requirement_code"], item["category"],
                        item["description"], item["requirement_type"], item.get("package_component"),
                        item["expected_characteristic"], item["evidence_expectation"],
                        int(item.get("required", True)), item["display_order"],
                        int(item.get("ml_eligible", False)), item.get("visual_component"),
                        json.dumps(item.get("defect_categories", [])),
                    ),
                )
                for check_code in item.get("quality_check_codes", []):
                    standard = connection.execute(
                        "SELECT id FROM quality_standards WHERE code = ?", (check_code,)
                    ).fetchone()
                    if standard:
                        connection.execute(
                            """
                            INSERT OR IGNORE INTO quality_standard_specification_requirements (
                                standard_id, specification_requirement_id
                            ) VALUES (?, ?)
                            """,
                            (standard["id"], requirement_cursor.lastrowid),
                        )
        return self.get_product_specification(specification["specification_code"])

    def evidence_issuers(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        where = "" if include_inactive else "WHERE active = 1"
        rows = self._all(f"SELECT * FROM evidence_issuers {where} ORDER BY issuer_name")
        for row in rows:
            row["active"] = bool(row["active"])
        return rows

    def get_evidence_issuer(self, issuer_code: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM evidence_issuers WHERE issuer_code = ?", (issuer_code,))
        if row:
            row["active"] = bool(row["active"])
        return row

    def update_evidence_issuer_status(self, issuer_code: str, trust_status: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE evidence_issuers SET trust_status = ?, updated_at = CURRENT_TIMESTAMP WHERE issuer_code = ?",
                (trust_status, issuer_code),
            )
        return self.get_evidence_issuer(issuer_code)

    def source_reviews(self) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT q.source_code, q.authority, q.title, q.edition, q.status AS source_status,
                   q.review_owner_user_id, owner.display_name AS review_owner_name,
                   q.reviewed_by_user_id, reviewer.display_name AS reviewed_by_name,
                   q.reviewed_at, q.review_status, q.next_review_due
            FROM quality_sources q
            LEFT JOIN users owner ON owner.id = q.review_owner_user_id
            LEFT JOIN users reviewer ON reviewer.id = q.reviewed_by_user_id
            ORDER BY q.next_review_due, q.source_code
            """
        )

    def quality_change_records(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT c.*, requester.display_name AS requested_by_name,
                   approver.display_name AS approved_by_name
            FROM quality_change_records c
            LEFT JOIN users requester ON requester.id = c.requested_by_user_id
            LEFT JOIN users approver ON approver.id = c.approved_by_user_id
            ORDER BY c.created_at DESC, c.id DESC LIMIT ?
            """,
            (limit,),
        )

    def add_quality_change_record(self, record: dict[str, Any]) -> dict[str, Any]:
        if not record.get("reason", "").strip():
            raise ValueError("Change-control reason is required")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO quality_change_records (
                    id, change_type, target_type, target_code, previous_version,
                    new_version, change_summary, reason, requested_by_user_id,
                    approved_by_user_id, status, approved_at
                ) VALUES (
                    :id, :change_type, :target_type, :target_code, :previous_version,
                    :new_version, :change_summary, :reason, :requested_by_user_id,
                    :approved_by_user_id, :status,
                    CASE WHEN :status IN ('APPROVED', 'IMPLEMENTED') THEN CURRENT_TIMESTAMP END
                )
                """,
                record,
            )
        return self._one("SELECT * FROM quality_change_records WHERE id = ?", (record["id"],))

    def create_product(self, product: dict[str, Any]) -> None:
        values = {
            **product,
            "category": product.get("category", "SKINCARE"),
            "subcategory": product.get("subcategory", "FACIAL_SERUM"),
            "product_type": product.get("product_type", "ANTI_AGING_SERUM"),
            "manufactured_date": product.get("manufactured_date"),
            "expiry_date": product.get("expiry_date"),
            "current_stage": product.get("current_stage", "MANUFACTURER"),
            "final_sale_status": product.get("final_sale_status", "NOT_READY"),
            "lineage_hash": product.get("lineage_hash"),
            "registered_by_user_id": product.get("registered_by_user_id"),
            "specification_code": product.get("specification_code"),
            "specification_version": product.get("specification_version"),
            "specification_snapshot_hash": product.get("specification_snapshot_hash"),
            "specification_assigned_at": product.get("specification_assigned_at"),
        }
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO products (
                    product_code, name, brand, batch_number, description, metadata_json,
                    product_key, metadata_hash, registration_tx_hash, registration_block_number,
                    category, subcategory, product_type, manufactured_date, expiry_date,
                    current_stage, final_sale_status, lineage_hash, registered_by_user_id,
                    specification_code, specification_version, specification_snapshot_hash,
                    specification_assigned_at
                ) VALUES (
                    :product_code, :name, :brand, :batch_number, :description, :metadata_json,
                    :product_key, :metadata_hash, :registration_tx_hash, :registration_block_number,
                    :category, :subcategory, :product_type, :manufactured_date, :expiry_date,
                    :current_stage, :final_sale_status, :lineage_hash, :registered_by_user_id,
                    :specification_code, :specification_version, :specification_snapshot_hash,
                    :specification_assigned_at
                )
                """,
                values,
            )

    def get_product(self, product_code: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM products WHERE product_code = ?", (product_code,))

    def list_products(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM products ORDER BY created_at DESC")

    def link_raw_materials(self, product_code: str, material_ids: list[str]) -> None:
        with self.connect() as connection:
            for material_id in material_ids:
                connection.execute(
                    "INSERT INTO product_raw_materials (product_code, raw_material_batch_id) VALUES (?, ?)",
                    (product_code, material_id),
                )

    def product_raw_materials(self, product_code: str) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT r.* FROM raw_material_batches r
            JOIN product_raw_materials p ON p.raw_material_batch_id = r.id
            WHERE p.product_code = ? ORDER BY r.material_name
            """,
            (product_code,),
        )

    def quality_standards(self, stage: str) -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT s.*, p.profile_code, p.version AS profile_version,
                   p.jurisdiction AS profile_jurisdiction, p.disclaimer AS profile_disclaimer,
                   pr.display_order
            FROM quality_standards s
            JOIN quality_profile_requirements pr ON pr.standard_id = s.id
            JOIN quality_profiles p ON p.profile_code = pr.profile_code AND p.active = 1
            WHERE s.supply_chain_stage = ? AND s.active = 1
            ORDER BY pr.display_order
            """,
            (stage,),
        )
        return [self._hydrate_standard(row) for row in rows]

    def get_standard(self, standard_id: int) -> dict[str, Any] | None:
        row = self._one(
            """
            SELECT s.*, p.profile_code, p.version AS profile_version,
                   p.jurisdiction AS profile_jurisdiction, p.disclaimer AS profile_disclaimer,
                   pr.display_order
            FROM quality_standards s
            JOIN quality_profile_requirements pr ON pr.standard_id = s.id
            JOIN quality_profiles p ON p.profile_code = pr.profile_code AND p.active = 1
            WHERE s.id = ? AND s.active = 1
            """,
            (standard_id,),
        )
        return self._hydrate_standard(row) if row else None

    def quality_sources(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        where = "" if include_inactive else "WHERE active = 1"
        rows = self._all(
            f"SELECT * FROM quality_sources {where} ORDER BY authority, title, edition"
        )
        for row in rows:
            row["active"] = bool(row["active"])
            row["mapped_requirement_count"] = self._one(
                "SELECT COUNT(*) AS count FROM quality_standard_sources WHERE source_code = ?",
                (row["source_code"],),
            )["count"]
        return rows

    def get_quality_source(self, source_code: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM quality_sources WHERE source_code = ?", (source_code,))
        if not row:
            return None
        row["active"] = bool(row["active"])
        row["mapped_requirements"] = self._all(
            """
            SELECT s.id AS standard_id, s.code, s.check_name, s.supply_chain_stage,
                   s.classification, m.mapping_precision, m.interpretation
            FROM quality_standard_sources m
            JOIN quality_standards s ON s.id = m.standard_id
            WHERE m.source_code = ? ORDER BY s.id
            """,
            (source_code,),
        )
        return row

    def quality_profiles(self) -> list[dict[str, Any]]:
        rows = self._all("SELECT * FROM quality_profiles WHERE active = 1 ORDER BY profile_code")
        for row in rows:
            row["active"] = bool(row["active"])
            row["requirement_count"] = self._one(
                "SELECT COUNT(*) AS count FROM quality_profile_requirements WHERE profile_code = ?",
                (row["profile_code"],),
            )["count"]
        return rows

    def get_quality_profile(self, profile_code: str) -> dict[str, Any] | None:
        row = self._one(
            "SELECT * FROM quality_profiles WHERE profile_code = ? AND active = 1",
            (profile_code,),
        )
        if not row:
            return None
        row["active"] = bool(row["active"])
        row["requirements"] = self._all(
            """
            SELECT s.id AS standard_id, s.code, s.check_name, s.supply_chain_stage,
                   s.category, s.classification, pr.display_order
            FROM quality_profile_requirements pr
            JOIN quality_standards s ON s.id = pr.standard_id
            WHERE pr.profile_code = ? AND s.active = 1 ORDER BY pr.display_order
            """,
            (profile_code,),
        )
        return row

    def _sources_for_standard(self, standard_id: int) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT q.source_code, q.authority, q.title, q.jurisdiction, q.source_type,
                   q.edition, q.publication_year, q.status, q.source_url,
                   q.last_verified_at, q.revision_of_source_code, q.notes,
                   m.mapping_precision, m.interpretation
            FROM quality_standard_sources m
            JOIN quality_sources q ON q.source_code = m.source_code
            WHERE m.standard_id = ? AND q.active = 1 ORDER BY q.authority, q.title
            """,
            (standard_id,),
        )

    def _snapshot_sources_for_result(self, quality_result_id: str) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT source_code, authority, title, edition, publication_year,
                   jurisdiction, source_type, status_at_submission AS status,
                   mapping_precision, source_url, last_verified_at,
                   snapshotted_at
            FROM quality_result_sources WHERE quality_result_id = ? ORDER BY authority, title
            """,
            (quality_result_id,),
        )

    def _spec_requirements_for_standard(
        self, standard_id: int, specification_code: str = DEFAULT_PRODUCT_SPECIFICATION_CODE
    ) -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT r.requirement_code, r.category, r.description, r.requirement_type,
                   r.package_component, r.expected_characteristic, r.evidence_expectation,
                   r.required, r.ml_eligible, r.visual_component, r.defect_categories_json,
                   s.specification_code, s.specification_name, s.version AS specification_version
            FROM quality_standard_specification_requirements m
            JOIN product_specification_requirements r ON r.id = m.specification_requirement_id
            JOIN product_specifications s ON s.id = r.specification_id
            WHERE m.standard_id = ? AND s.specification_code = ? AND r.active = 1
            ORDER BY r.display_order
            """,
            (standard_id, specification_code),
        )
        for row in rows:
            row["required"] = bool(row["required"])
            row["ml_eligible"] = bool(row["ml_eligible"])
            row["defect_categories"] = json.loads(row.pop("defect_categories_json") or "[]")
        return rows

    def _hydrate_standard(self, row: dict[str, Any]) -> dict[str, Any]:
        row["required"] = bool(row["required"])
        row["evidence_required"] = bool(row["evidence_required"])
        row["trusted_issuer_required"] = bool(row.get("trusted_issuer_required"))
        row["active"] = bool(row["active"])
        row["defect_categories"] = json.loads(row.pop("defect_categories_json") or "[]")
        row["sources"] = self._sources_for_standard(row["id"])
        row["specification_requirements"] = self._spec_requirements_for_standard(row["id"])
        return row

    def upsert_quality_result(self, result: dict[str, Any]) -> dict[str, Any]:
        existing = self._one(
            "SELECT id FROM quality_results WHERE context_type = ? AND context_id = ? AND standard_id = ?",
            (result["context_type"], result["context_id"], result["standard_id"]),
        )
        result_id = existing["id"] if existing else result["id"]
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO quality_results (
                    id, context_type, context_id, standard_id, result, notes, inspector_stage,
                    submitted_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(context_type, context_id, standard_id) DO UPDATE SET
                    result = excluded.result, notes = excluded.notes,
                    inspector_stage = excluded.inspector_stage,
                    submitted_by_user_id = excluded.submitted_by_user_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    result_id, result["context_type"], result["context_id"], result["standard_id"],
                    result["result"], result.get("notes"), result["inspector_stage"],
                    result.get("submitted_by_user_id"),
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO quality_result_sources (
                    quality_result_id, source_code, authority, title, jurisdiction,
                    source_type, edition, publication_year, status_at_submission,
                    mapping_precision, source_url, last_verified_at
                )
                SELECT ?, q.source_code, q.authority, q.title, q.jurisdiction,
                       q.source_type, q.edition, q.publication_year, q.status,
                       m.mapping_precision, q.source_url, q.last_verified_at
                FROM quality_standard_sources m
                JOIN quality_sources q ON q.source_code = m.source_code
                WHERE m.standard_id = ?
                """,
                (result_id, result["standard_id"]),
            )
        return self.get_quality_result(result_id)

    def get_quality_result(self, result_id: str) -> dict[str, Any] | None:
        row = self._one(
            """
            SELECT q.*, s.code AS standard_code, s.category, s.check_name,
                   s.required, s.evidence_required, s.supply_chain_stage,
                   s.classification, s.expected_document_type, s.trusted_issuer_required
            FROM quality_results q JOIN quality_standards s ON s.id = q.standard_id
            WHERE q.id = ?
            """,
            (result_id,),
        )
        if row:
            row["required"] = bool(row["required"])
            row["evidence_required"] = bool(row["evidence_required"])
            row["trusted_issuer_required"] = bool(row["trusted_issuer_required"])
            row["sources"] = self._snapshot_sources_for_result(result_id)
        return row

    def quality_results(self, context_type: str, context_id: str, stage: str) -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT q.id, q.context_type, q.context_id, q.standard_id, q.result, q.notes,
                   q.inspector_stage, q.submitted_by_user_id, q.created_at, q.updated_at,
                   s.id AS template_id, s.code AS standard_code, s.category, s.check_name,
                   s.requirement_description, s.required, s.evidence_required,
                   s.classification, s.requirement_rationale, s.evidence_expectation,
                   s.expected_document_type, s.package_component,
                   s.expected_visual_characteristic, s.defect_categories_json,
                   s.trusted_issuer_required,
                   p.profile_code, p.version AS profile_version,
                   p.jurisdiction AS profile_jurisdiction, p.disclaimer AS profile_disclaimer,
                   pr.display_order
            FROM quality_standards s
            JOIN quality_profile_requirements pr ON pr.standard_id = s.id
            JOIN quality_profiles p ON p.profile_code = pr.profile_code AND p.active = 1
            LEFT JOIN quality_results q
              ON q.standard_id = s.id AND q.context_type = ? AND q.context_id = ?
            WHERE s.supply_chain_stage = ? AND s.active = 1 ORDER BY pr.display_order
            """,
            (context_type, context_id, stage),
        )
        specification_code = DEFAULT_PRODUCT_SPECIFICATION_CODE
        if context_type == "PRODUCT":
            product = self.get_product(context_id)
            if product and product.get("specification_code"):
                specification_code = product["specification_code"]
        for row in rows:
            row["defect_categories"] = json.loads(row.pop("defect_categories_json") or "[]")
            row["sources"] = (
                self._snapshot_sources_for_result(row["id"])
                if row.get("id")
                else self._sources_for_standard(row["template_id"])
            )
            row["source_snapshot"] = bool(row.get("id"))
            row["trusted_issuer_required"] = bool(row["trusted_issuer_required"])
            row["specification_requirements"] = self._spec_requirements_for_standard(
                row["template_id"], specification_code
            ) if context_type == "PRODUCT" else []
        return rows

    def add_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_files (
                    id, quality_result_id, original_filename, stored_filename, content_type,
                    file_size, file_hash, uploader_stage, visibility,
                    blockchain_tx_hash, blockchain_block_number, uploaded_by_user_id,
                    document_type, laboratory_name, report_reference, test_date,
                    test_method_source_code, result_summary, accreditation_status_text,
                    document_notes, issuer_id, issuer_code_snapshot, issuer_name_snapshot,
                    issuer_type_snapshot, issuer_trust_status_at_submission,
                    issuer_report_number, issuer_document_date, verification_status,
                    verified_by_user_id, verified_at, verification_notes
                ) VALUES (
                    :id, :quality_result_id, :original_filename, :stored_filename, :content_type,
                    :file_size, :file_hash, :uploader_stage, :visibility,
                    :blockchain_tx_hash, :blockchain_block_number, :uploaded_by_user_id,
                    :document_type, :laboratory_name, :report_reference, :test_date,
                    :test_method_source_code, :result_summary, :accreditation_status_text,
                    :document_notes, :issuer_id, :issuer_code_snapshot, :issuer_name_snapshot,
                    :issuer_type_snapshot, :issuer_trust_status_at_submission,
                    :issuer_report_number, :issuer_document_date, :verification_status,
                    :verified_by_user_id, :verified_at, :verification_notes
                )
                """,
                evidence,
            )
        return self.get_evidence(evidence["id"])

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT e.*, i.trust_status AS issuer_current_trust_status,
                   i.active AS issuer_current_active
            FROM evidence_files e LEFT JOIN evidence_issuers i ON i.id = e.issuer_id
            WHERE e.id = ?
            """,
            (evidence_id,),
        )

    def evidence_for_result(self, result_id: str, public_only: bool = False) -> list[dict[str, Any]]:
        sql = """
            SELECT e.*, i.trust_status AS issuer_current_trust_status,
                   i.active AS issuer_current_active
            FROM evidence_files e LEFT JOIN evidence_issuers i ON i.id = e.issuer_id
            WHERE e.quality_result_id = ?
        """
        if public_only:
            sql += " AND visibility = 'CONSUMER_VISIBLE'"
        return self._all(sql + " ORDER BY uploaded_at", (result_id,))

    def evidence_for_context(self, context_type: str, context_id: str, public_only: bool = False) -> list[dict[str, Any]]:
        sql = """
            SELECT e.*, q.inspector_stage, s.category, s.check_name,
                   i.trust_status AS issuer_current_trust_status,
                   i.active AS issuer_current_active
            FROM evidence_files e JOIN quality_results q ON q.id = e.quality_result_id
            JOIN quality_standards s ON s.id = q.standard_id
            LEFT JOIN evidence_issuers i ON i.id = e.issuer_id
            WHERE q.context_type = ? AND q.context_id = ?
        """
        if public_only:
            sql += " AND e.visibility = 'CONSUMER_VISIBLE'"
        return self._all(sql + " ORDER BY e.uploaded_at", (context_type, context_id))

    def set_stage_approval(self, approval: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO stage_approvals (
                    context_type, context_id, stage, status, commitment_hash,
                    blocking_reasons_json, blockchain_tx_hash, blockchain_block_number,
                    approved_at, approved_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? = 'APPROVED' THEN CURRENT_TIMESTAMP END, ?)
                ON CONFLICT(context_type, context_id, stage) DO UPDATE SET
                    status = excluded.status, commitment_hash = excluded.commitment_hash,
                    blocking_reasons_json = excluded.blocking_reasons_json,
                    blockchain_tx_hash = excluded.blockchain_tx_hash,
                    blockchain_block_number = excluded.blockchain_block_number,
                    approved_by_user_id = excluded.approved_by_user_id,
                    approved_at = CASE WHEN excluded.status = 'APPROVED' THEN CURRENT_TIMESTAMP ELSE NULL END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    approval["context_type"], approval["context_id"], approval["stage"],
                    approval["status"], approval["commitment_hash"], approval["blocking_reasons_json"],
                    approval.get("blockchain_tx_hash"), approval.get("blockchain_block_number"),
                    approval["status"], approval.get("approved_by_user_id"),
                ),
            )
        return self.get_stage_approval(approval["context_type"], approval["context_id"], approval["stage"])

    def invalidate_stage_approval(
        self, context_type: str, context_id: str, stage: str, status: str, reason: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE stage_approvals
                SET status = ?, blocking_reasons_json = ?, approved_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE context_type = ? AND context_id = ? AND stage = ?
                """,
                (status, json.dumps([reason]), context_type, context_id, stage),
            )

    def get_stage_approval(self, context_type: str, context_id: str, stage: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM stage_approvals WHERE context_type = ? AND context_id = ? AND stage = ?",
            (context_type, context_id, stage),
        )

    def stage_approvals(self, context_type: str, context_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM stage_approvals WHERE context_type = ? AND context_id = ? ORDER BY id",
            (context_type, context_id),
        )

    def update_product_stage(self, product_code: str, stage: str, sale_status: str | None = None) -> None:
        with self.connect() as connection:
            if sale_status is None:
                connection.execute(
                    "UPDATE products SET current_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE product_code = ?",
                    (stage, product_code),
                )
            else:
                connection.execute(
                    "UPDATE products SET current_stage = ?, final_sale_status = ?, updated_at = CURRENT_TIMESTAMP WHERE product_code = ?",
                    (stage, sale_status, product_code),
                )

    def add_transfer(self, transfer: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO ownership_transfers (
                    product_code, from_role, from_address, to_role, to_address,
                    transaction_hash, block_number, initiated_by_user_id
                ) VALUES (
                    :product_code, :from_role, :from_address, :to_role, :to_address,
                    :transaction_hash, :block_number, :initiated_by_user_id
                )
                """,
                transfer,
            )

    def transfers(self, product_code: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM ownership_transfers WHERE product_code = ? ORDER BY id", (product_code,))

    def tamper_product(self, product_code: str) -> dict[str, Any] | None:
        product = self.get_product(product_code)
        if not product:
            return None
        tampered_brand = f"{product['brand']} - ALTERED"
        tampered_description = f"{product['description']} (DEMO TAMPERED OFF-CHAIN)"
        current_metadata = product_metadata(
            product_code=product["product_code"], name=product["name"], brand=tampered_brand,
            batch_number=product["batch_number"], description=tampered_description,
        )
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE products SET brand = ?, description = ?, metadata_json = ?,
                    updated_at = CURRENT_TIMESTAMP WHERE product_code = ?
                """,
                (tampered_brand, tampered_description, canonical_metadata(current_metadata), product_code),
            )
        return self.get_product(product_code)

    def reset_demo(self) -> None:
        with self.connect() as connection:
            for table in (
                "evidence_files", "quality_results", "stage_approvals", "ownership_transfers",
                "product_raw_materials", "products", "raw_material_batches",
            ):
                connection.execute(f"DELETE FROM {table}")

    def _one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
