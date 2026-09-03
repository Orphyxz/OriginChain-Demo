import sqlite3

import pytest

from backend.database import ProductRepository
from backend.domain import (
    DEFAULT_PRODUCT_SPECIFICATION_CODE,
    PRODUCT_SPECIFICATION_REQUIREMENTS,
)
from backend.metadata_hash import product_key
from backend.tests.test_quality_workflow import (
    approve,
    approved_material,
    auth_headers,
    complete_stage,
    create_material,
    get_standards,
    registered_product,
    stage_headers,
    workflow,
)


def specification_payload(code, version, status="APPROVED", product_type="ANTI_AGING_SERUM"):
    return {
        "specification_code": code,
        "product_category": "SKINCARE",
        "product_subcategory": "FACIAL_SERUM",
        "product_type": product_type,
        "specification_name": f"Aurelia fictional demo specification {version}",
        "version": version,
        "status": status,
        "effective_from": "2026-08-30",
        "effective_until": None,
        "created_by_user_id": "user_admin",
        "approved_at": "2026-08-30T00:00:00Z" if status == "APPROVED" else None,
        "approved_by_user_id": "user_admin" if status == "APPROVED" else None,
        "supersedes_specification_code": DEFAULT_PRODUCT_SPECIFICATION_CODE,
        "change_summary": f"TEST FIXTURE — FICTIONAL DEMO version {version}.",
        "disclaimer": "TEST FIXTURE — FICTIONAL DEMO. Not a regulatory or commercial specification.",
        "active": 1,
    }


def minimal_requirement(code="TEST-REQ", check_codes=()):
    return {
        "requirement_code": code,
        "category": "Test Fixture",
        "description": "Fictional stable test requirement.",
        "requirement_type": "VISUAL",
        "package_component": "BOTTLE",
        "expected_characteristic": "Fictional bottle visibly intact.",
        "evidence_expectation": "Human inspection record.",
        "required": True,
        "display_order": 1,
        "ml_eligible": True,
        "visual_component": "BOTTLE",
        "defect_categories": ["BOTTLE_DAMAGE", "UNKNOWN"],
        "quality_check_codes": list(check_codes),
    }


def test_specification_registry_requirements_and_api_are_stable(workflow):
    client, repository, *_ = workflow
    assert client.get("/api/product-specifications").status_code == 401
    headers = auth_headers(client, "manufacturer")
    response = client.get("/api/product-specifications?approved_only=true", headers=headers)
    assert response.status_code == 200
    assert [item["specification_code"] for item in response.json()] == [
        DEFAULT_PRODUCT_SPECIFICATION_CODE
    ]

    first = client.get(
        f"/api/product-specifications/{DEFAULT_PRODUCT_SPECIFICATION_CODE}", headers=headers
    ).json()
    second = repository.get_product_specification(DEFAULT_PRODUCT_SPECIFICATION_CODE)
    assert first["version"] == "1.0" and first["status"] == "APPROVED"
    assert first["snapshot_hash"] == second["snapshot_hash"]
    assert len(first["requirements"]) == len(PRODUCT_SPECIFICATION_REQUIREMENTS) == 16
    assert len({item["requirement_code"] for item in first["requirements"]}) == 16
    visual = [item for item in first["requirements"] if item["ml_eligible"]]
    assert visual and all(item["visual_component"] for item in visual)
    assert all(item["expected_characteristic"] and item["required"] for item in first["requirements"])
    assert any(item["defect_categories"] for item in visual)
    assert all("prediction" not in key.lower() for item in first["requirements"] for key in item)


def test_issuer_registry_seeds_unique_trust_states_and_server_owned_status(workflow):
    client, repository, *_ = workflow
    assert client.get("/api/evidence/issuers").status_code == 401
    issuers = client.get(
        "/api/evidence/issuers", headers=auth_headers(client, "manufacturer")
    ).json()
    assert len(issuers) == 6
    assert len({item["issuer_code"] for item in issuers}) == 6
    assert repository.get_evidence_issuer("AURELIA_QC_LAB_DEMO")["trust_status"] == "TRUSTED_DEMO"
    assert repository.get_evidence_issuer("UNVERIFIED_FIXTURE_ISSUER")["trust_status"] == "UNVERIFIED"
    with repository.connect() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO evidence_issuers (
                issuer_code, issuer_name, issuer_type, organization_name,
                jurisdiction, trust_status, verification_method, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "AURELIA_QC_LAB_DEMO", "Duplicate", "LABORATORY", "Duplicate",
                "DEMO", "REVOKED", "TEST FIXTURE", "Must violate unique code",
            ),
        )


def test_registration_rejects_invalid_draft_superseded_and_type_mismatch(workflow):
    client, repository, *_ = workflow
    material = approved_material(client)
    manufacturer = auth_headers(client, "manufacturer")
    base = {"product_code": "OC-SPEC-NEGATIVE", "raw_material_batch_ids": [material["id"]]}

    missing = client.post(
        "/api/products/register",
        json={**base, "specification_code": "NOT_REGISTERED"},
        headers=manufacturer,
    )
    assert missing.status_code == 422

    repository.create_product_specification(
        specification_payload("AURELIA_DRAFT_FIXTURE", "0.9", "DRAFT"),
        [minimal_requirement("DRAFT-REQ")],
    )
    draft = client.post(
        "/api/products/register",
        json={**base, "specification_code": "AURELIA_DRAFT_FIXTURE"},
        headers=manufacturer,
    )
    assert draft.status_code == 409

    repository.create_product_specification(
        specification_payload("AURELIA_SUPERSEDED_FIXTURE", "0.8", "SUPERSEDED"),
        [minimal_requirement("SUPERSEDED-REQ")],
    )
    superseded = client.post(
        "/api/products/register",
        json={**base, "specification_code": "AURELIA_SUPERSEDED_FIXTURE"},
        headers=manufacturer,
    )
    assert superseded.status_code == 409

    repository.create_product_specification(
        specification_payload("AURELIA_OTHER_TYPE_FIXTURE", "1.0", product_type="BODY_LOTION"),
        [minimal_requirement("TYPE-REQ")],
    )
    mismatch = client.post(
        "/api/products/register",
        json={**base, "specification_code": "AURELIA_OTHER_TYPE_FIXTURE"},
        headers=manufacturer,
    )
    assert mismatch.status_code == 422


def test_batches_freeze_v1_while_v2_is_created_and_used(workflow):
    client, repository, *_ = workflow
    first_material = approved_material(client)
    registered_product(client, first_material["id"])
    first = repository.get_product("OC-LUX-SERUM-0001")
    first_hash = first["specification_snapshot_hash"]

    v2 = repository.create_product_specification(
        specification_payload("AURELIA_PRESTIGE_RENEWAL_SERUM_SPEC_V2", "2.0"),
        [minimal_requirement("V2-BOTTLE", ("MFG-PACK", "RTL-PACK"))],
    )
    assert v2["snapshot_hash"] != first_hash
    assert repository.get_product("OC-LUX-SERUM-0001")["specification_version"] == "1.0"
    with repository.connect() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE product_specifications SET version = '1.1' WHERE specification_code = ?",
            (DEFAULT_PRODUCT_SPECIFICATION_CODE,),
        )
    with repository.connect() as connection:
        connection.execute(
            "UPDATE product_specifications SET status = 'SUPERSEDED', active = 0 WHERE specification_code = ?",
            (DEFAULT_PRODUCT_SPECIFICATION_CODE,),
        )
    assert repository.get_product("OC-LUX-SERUM-0001")["specification_version"] == "1.0"
    assert repository.get_product_specification(DEFAULT_PRODUCT_SPECIFICATION_CODE)["status"] == "SUPERSEDED"

    second_material = create_material(client, batch="HA-260802")
    complete_stage(client, "RAW_MATERIAL", second_material["id"], "RAW_MATERIAL_SUPPLIER")
    assert approve(client, "RAW_MATERIAL", second_material["id"], "RAW_MATERIAL_SUPPLIER").status_code == 200
    created = client.post(
        "/api/products/register",
        json={
            "product_code": "OC-LUX-SERUM-0002",
            "batch_number": "APR-2026-002",
            "raw_material_batch_ids": [second_material["id"]],
            "specification_code": "AURELIA_PRESTIGE_RENEWAL_SERUM_SPEC_V2",
        },
        headers=auth_headers(client, "manufacturer"),
    )
    assert created.status_code == 200
    assert created.json()["product_specification"]["version"] == "2.0"
    products = {item["product_code"]: item for item in client.get(
        "/api/products", headers=auth_headers(client, "retailer")
    ).json()}
    assert products["OC-LUX-SERUM-0001"]["product_specification"]["version"] == "1.0"
    assert products["OC-LUX-SERUM-0002"]["product_specification"]["version"] == "2.0"


def test_trusted_issuer_snapshot_survives_revocation_and_new_evidence_is_blocked(workflow):
    client, repository, *_ = workflow
    first = create_material(client)
    result_ids = complete_stage(client, "RAW_MATERIAL", first["id"], "RAW_MATERIAL_SUPPLIER")
    assert approve(client, "RAW_MATERIAL", first["id"], "RAW_MATERIAL_SUPPLIER").status_code == 200
    historical = repository.evidence_for_result(result_ids["RM-COA"])[0]
    assert historical["verification_status"] == "VERIFIED_DEMO"
    assert historical["issuer_trust_status_at_submission"] == "TRUSTED_DEMO"
    assert historical["issuer_code_snapshot"] == "LUMINA_ACTIVES"

    revoked = client.post(
        "/api/evidence/issuers/LUMINA_ACTIVES/status",
        json={
            "trust_status": "REVOKED",
            "reason": "TEST FIXTURE — FICTIONAL DEMO revocation drill.",
        },
        headers=auth_headers(client, "admin"),
    )
    assert revoked.status_code == 200 and revoked.json()["trust_status"] == "REVOKED"
    frozen = repository.get_evidence(historical["id"])
    assert frozen["issuer_trust_status_at_submission"] == "TRUSTED_DEMO"
    assert frozen["issuer_current_trust_status"] == "REVOKED"
    historical_summary = client.get(
        f"/api/quality/RAW_MATERIAL/{first['id']}/summary",
        params={"stage": "RAW_MATERIAL_SUPPLIER"},
        headers=auth_headers(client, "supplier"),
    ).json()
    assert historical_summary["status"] == "APPROVED"
    assert historical_summary["eligible_for_approval"] is True
    coa_check = next(item for item in historical_summary["checks"] if item["code"] == "RM-COA")
    assert coa_check["trust_warnings"] and "current registry status is Revoked" in coa_check["trust_warnings"][0]

    second = create_material(client, batch="HA-REVOKED-02")
    second_results = complete_stage(client, "RAW_MATERIAL", second["id"], "RAW_MATERIAL_SUPPLIER")
    new_evidence = repository.evidence_for_result(second_results["RM-COA"])[0]
    assert new_evidence["issuer_trust_status_at_submission"] == "REVOKED"
    assert new_evidence["verification_status"] == "UNVERIFIED"
    blocked = approve(client, "RAW_MATERIAL", second["id"], "RAW_MATERIAL_SUPPLIER")
    assert blocked.status_code == 409
    assert any("Trusted Demo issuer" in reason for reason in blocked.json()["detail"]["blocking_reasons"])


def test_integrity_and_issuer_trust_are_separate_and_optional_photo_needs_no_issuer(workflow):
    client, repository, _chain, store = workflow
    material = create_material(client)
    standards = get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
    identity = next(item for item in standards if item["code"] == "RM-IDENTITY")
    result = client.post(
        "/api/quality/results",
        json={
            "context_type": "RAW_MATERIAL", "context_id": material["id"],
            "standard_id": identity["id"], "result": "PASS",
        },
        headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"),
    ).json()
    photo = client.post(
        f"/api/quality/results/{result['id']}/evidence",
        data={"document_type": "OTHER"},
        files={"file": ("fixture.png", b"\x89PNG\r\n\x1a\nFICTIONAL-DEMO", "image/png")},
        headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"),
    )
    assert photo.status_code == 201
    assert photo.json()["integrity"] == "VERIFIED"
    assert photo.json()["issuer"] is None
    assert photo.json()["verification_status"] == "UNVERIFIED"
    record = repository.get_evidence(photo.json()["id"])
    (store.root / record["stored_filename"]).write_bytes(b"\x89PNG\r\n\x1a\nCHANGED")
    assert store.integrity(record["stored_filename"], record["file_hash"]).value == "MISMATCH"
    assert record["issuer_code_snapshot"] is None


def test_governance_rbac_source_reviews_change_control_and_reset(workflow):
    client, repository, *_ = workflow
    supplier = auth_headers(client, "supplier")
    admin = auth_headers(client, "admin")
    assert client.get("/api/quality/source-reviews").status_code == 401
    assert client.get("/api/quality/change-records").status_code == 401
    assert client.get("/api/quality/source-reviews", headers=supplier).status_code == 403
    assert client.get("/api/quality/change-records", headers=supplier).status_code == 403
    assert client.post(
        "/api/evidence/issuers/LUMINA_ACTIVES/status",
        json={"trust_status": "REVOKED", "reason": "Forbidden supplier mutation"},
        headers=supplier,
    ).status_code == 403

    reviews = client.get("/api/quality/source-reviews", headers=admin).json()
    assert len(reviews) == 9
    assert all(item["review_owner_user_id"] == "user_admin" for item in reviews)
    assert all(item["reviewed_at"] and item["next_review_due"] for item in reviews)
    assert all(item["review_status"] == "CURRENT" for item in reviews)

    missing_reason = client.post(
        "/api/quality/change-records",
        json={
            "change_type": "SOURCE_UPDATE", "target_type": "QUALITY_SOURCE",
            "target_code": "ISO_22716_2007", "change_summary": "Fixture review",
        },
        headers=admin,
    )
    assert missing_reason.status_code == 422
    change = client.post(
        "/api/quality/change-records",
        json={
            "change_type": "SOURCE_UPDATE", "target_type": "QUALITY_SOURCE",
            "target_code": "ISO_22716_2007", "previous_version": "2007",
            "new_version": "2007-reviewed", "change_summary": "Fixture review recorded",
            "reason": "TEST FIXTURE — FICTIONAL DEMO governance test.",
            "status": "APPROVED",
        },
        headers=admin,
    )
    assert change.status_code == 201
    assert change.json()["previous_version"] == "2007"
    assert change.json()["approved_by_user_id"] == "user_admin"
    assert change.json()["status"] == "APPROVED"

    before = (len(repository.product_specifications()), len(repository.evidence_issuers()), len(repository.source_reviews()))
    assert client.post("/api/demo/reset", headers=admin).status_code == 200
    after = (len(repository.product_specifications()), len(repository.evidence_issuers()), len(repository.source_reviews()))
    assert after == before


def test_public_verification_redacts_internal_governance(workflow):
    client, *_ = workflow
    material = approved_material(client)
    registered_product(client, material["id"])
    payload = client.get("/api/verify/OC-LUX-SERUM-0001").json()
    assert payload["product"]["product_configuration"] == {
        "verified_against_recorded_specification": True,
        "specification_version": "1.0",
    }
    serialized = str(payload).lower()
    assert all(term not in serialized for term in (
        "defect_categories", "change_summary", "review_owner", "verification_method",
        "issuer_trust_status_at_submission", "user_admin", "internal test fixture",
    ))


def test_additive_governance_upgrade_preserves_legacy_product(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE products (
                product_code TEXT PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL,
                batch_number TEXT NOT NULL, description TEXT NOT NULL,
                metadata_json TEXT NOT NULL, product_key TEXT NOT NULL,
                metadata_hash TEXT NOT NULL, registration_tx_hash TEXT NOT NULL,
                registration_block_number INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            INSERT INTO products (
                product_code, name, brand, batch_number, description, metadata_json,
                product_key, metadata_hash, registration_tx_hash, registration_block_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "LEGACY-001", "Legacy Serum", "Aurelia Maison", "LEG-001",
            "Preserved migration fixture", "{}", "0xlegacy-key", "0xlegacy-hash",
            "0xlegacy-transaction", 1,
        ))

    repository = ProductRepository(path)
    repository.init_db()
    preserved = repository.get_product("LEGACY-001")
    assert preserved["description"] == "Preserved migration fixture"
    assert preserved["specification_code"] == DEFAULT_PRODUCT_SPECIFICATION_CODE
    assert preserved["specification_version"] == "1.0"
    assert len(repository.evidence_issuers()) == 6


def test_admin_can_load_complete_presentation_demo_in_one_click(workflow):
    client, repository, chain, _store = workflow
    assert client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "supplier")
    ).status_code == 403

    loaded = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert loaded.status_code == 200
    result = loaded.json()
    assert result["already_loaded"] is False
    assert result["final_sale_status"] == "APPROVED_FOR_SALE"
    assert result["stage_approvals"] == 4

    product = repository.get_product("OC-LUX-SERUM-0001")
    assert product["current_stage"] == "RETAILER"
    assert product["final_sale_status"] == "APPROVED_FOR_SALE"
    assert repository.get_raw_material("rm_presentation_hyaluronic_acid")["quality_status"] == "APPROVED"
    assert len(chain.quality_records) == 3
    assert len(repository.transfers("OC-LUX-SERUM-0001")) == 2

    verification = client.get("/api/verify/OC-LUX-SERUM-0001").json()
    assert verification["status"] == "GENUINE"
    assert verification["approved_for_sale"] is True
    assert [item["status"] for item in verification["quality_journey"]] == ["APPROVED"] * 4
    assert verification["public_evidence"]
    evidence_count = len(repository.evidence_for_context("PRODUCT", "OC-LUX-SERUM-0001"))

    repeated = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert repeated.status_code == 200
    assert repeated.json()["already_loaded"] is True
    assert len(repository.evidence_for_context("PRODUCT", "OC-LUX-SERUM-0001")) == evidence_count


def test_presentation_loader_detects_damaged_completed_evidence(workflow):
    client, repository, _chain, store = workflow
    loaded = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert loaded.status_code == 200
    evidence = repository.evidence_for_context("PRODUCT", loaded.json()["product_code"])[0]
    (store.root / evidence["stored_filename"]).write_bytes(
        b"%PDF-1.4\ndamaged presentation evidence\n%%EOF"
    )

    repeated = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert repeated.status_code == 409
    assert "Reset Local Demo Data" in repeated.json()["detail"]


def test_presentation_loader_finishes_an_existing_manufacturer_stage(workflow):
    client, repository, chain, _store = workflow
    material = approved_material(client)
    registered_product(client, material["id"])
    assert repository.get_product("OC-LUX-SERUM-0001")["current_stage"] == "MANUFACTURER"

    loaded = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert loaded.status_code == 200
    assert loaded.json()["final_sale_status"] == "APPROVED_FOR_SALE"
    assert repository.get_product("OC-LUX-SERUM-0001")["current_stage"] == "RETAILER"
    assert len(chain.quality_records) == 3
    assert len(repository.transfers("OC-LUX-SERUM-0001")) == 2


def test_presentation_loader_reuses_material_and_avoids_stale_chain_code(workflow):
    client, repository, chain, _store = workflow
    existing_material = create_material(client)
    chain.register_product(product_key("OC-LUX-SERUM-0001"), "0x" + "1" * 64)

    loaded = client.post(
        "/api/demo/presentation-seed", headers=auth_headers(client, "admin")
    )
    assert loaded.status_code == 200
    result = loaded.json()
    assert result["product_code"] == "OC-LUX-SERUM-PRESENTATION-0001"
    assert result["final_sale_status"] == "APPROVED_FOR_SALE"
    assert repository.get_raw_material(existing_material["id"])["quality_status"] == "APPROVED"
    assert len(repository.list_raw_materials()) == 1
    verification = client.get(f"/api/verify/{result['product_code']}").json()
    assert verification["status"] == "GENUINE"
    assert verification["approved_for_sale"] is True
