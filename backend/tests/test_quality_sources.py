import sqlite3

import pytest

from backend.quality_service import QualityService
from backend.tests.test_quality_workflow import (
    auth_headers,
    create_material,
    get_standards,
    workflow,
)


def test_source_and_profile_registry_are_authenticated_and_versioned(workflow):
    client, repository, *_ = workflow
    assert client.get("/api/quality/sources").status_code == 401
    assert client.get("/api/quality/profiles").status_code == 401

    headers = auth_headers(client, "admin")
    sources = client.get("/api/quality/sources", headers=headers)
    profiles = client.get("/api/quality/profiles", headers=headers)
    assert sources.status_code == profiles.status_code == 200
    assert len(sources.json()) == 9
    assert profiles.json()[0]["profile_code"] == "INDIA_LUXURY_FACIAL_SERUM_DEMO_V1"
    assert profiles.json()[0]["version"] == "1.0"
    assert "does not certify" in profiles.json()[0]["disclaimer"]

    profile = client.get(
        "/api/quality/profiles/INDIA_LUXURY_FACIAL_SERUM_DEMO_V1", headers=headers
    ).json()
    assert len(profile["requirements"]) == 24
    assert repository.get_quality_source("ISO_FDIS_17516_ED2")["status"] == "DRAFT"

    iso = repository.get_quality_source("ISO_22716_2007")
    assert iso["authority"] == "International Organization for Standardization"
    assert iso["jurisdiction"] == "INTERNATIONAL"
    assert iso["source_type"] == "STANDARD"
    assert iso["edition"] == "Edition 1, 2007"
    assert iso["source_url"].startswith("https://www.iso.org/")
    assert iso["last_verified_at"] == "2026-08-30"

    with repository.connect() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO quality_sources (
                source_code, authority, title, jurisdiction, source_type, edition,
                publication_year, status, source_url, last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "DUPLICATE_VERSION", iso["authority"], iso["title"], iso["jurisdiction"],
                iso["source_type"], iso["edition"], iso["publication_year"], iso["status"],
                iso["source_url"], iso["last_verified_at"],
            ),
        )


def test_mappings_are_deliberate_many_to_many_and_drafts_are_not_active(workflow):
    client, *_ = workflow
    headers = auth_headers(client, "admin")
    manufacturer = get_standards(client, "MANUFACTURER").json()
    distributor = get_standards(client, "DISTRIBUTOR").json()
    retailer = get_standards(client, "RETAILER").json()

    microbiology = next(item for item in manufacturer if item["code"] == "MFG-MICROBIOLOGY")
    preservation = next(item for item in manufacturer if item["code"] == "MFG-PRESERVATION")
    assert {item["source_code"] for item in microbiology["sources"]} == {
        "BIS_IS_14648_2011", "ISO_17516_2014"
    }
    assert {item["source_code"] for item in preservation["sources"]} == {
        "ISO_11930_2019_AMD1_2022", "ISO_29621_2017"
    }
    assert all(item["mapping_precision"] == "STANDARD_LEVEL" for item in microbiology["sources"])
    assert all(not item["sources"] for item in distributor)
    assert all(
        source["source_code"] != "ISO_22716_2007"
        for standard in get_standards(client, "RAW_MATERIAL_SUPPLIER").json() + distributor + retailer
        for source in standard["sources"]
    )
    assert all(
        source["status"] != "DRAFT"
        for standard in manufacturer + retailer
        for source in standard["sources"]
    )
    rules = client.get(
        "/api/quality/sources/INDIA_COSMETICS_RULES_2020", headers=headers
    ).json()
    assert {item["code"] for item in rules["mapped_requirements"]} == {
        "MFG-LABEL-TRACEABILITY", "RTL-LABEL", "RTL-EXPIRY"
    }
    retail_pack = next(item for item in retailer if item["code"] == "RTL-PACK")
    assert retail_pack["classification"] == "ORIGINCHAIN_INTERNAL"
    assert retail_pack["sources"] == []
    assert {"SEAL_DAMAGE", "LABEL_MISALIGNMENT"} <= set(retail_pack["defect_categories"])


def test_source_lifecycle_warning_and_profile_reseed_are_supported(workflow):
    client, repository, *_ = workflow
    headers = auth_headers(client, "admin")
    with repository.connect() as connection:
        connection.execute(
            "UPDATE quality_sources SET status = 'SUPERSEDED' WHERE source_code = 'ISO_17516_2014'"
        )
    standards = client.get(
        "/api/quality/standards", params={"stage": "MANUFACTURER"}, headers=headers
    ).json()
    microbiology = next(item for item in standards if item["code"] == "MFG-MICROBIOLOGY")
    source = next(item for item in microbiology["sources"] if item["source_code"] == "ISO_17516_2014")
    assert source["status"] == "SUPERSEDED"

    repository.init_db()
    repository.init_db()
    assert len(repository.quality_profiles()) == 1
    assert len(repository.get_quality_profile("INDIA_LUXURY_FACIAL_SERUM_DEMO_V1")["requirements"]) == 24
    assert len(repository.quality_sources()) == 9


def test_result_freezes_source_edition_and_audit_records_source_codes(workflow):
    client, repository, *_ = workflow
    material = create_material(client)
    supplier_headers = auth_headers(client, "supplier")
    restriction = next(
        item for item in get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
        if item["code"] == "RM-RESTRICTIONS"
    )
    submitted = client.post("/api/quality/results", json={
        "context_type": "RAW_MATERIAL", "context_id": material["id"],
        "standard_id": restriction["id"], "result": "PASS",
        "notes": "Document review recorded; no compliance conclusion.",
    }, headers=supplier_headers)
    assert submitted.status_code == 200
    frozen = submitted.json()["sources"]
    assert frozen[0]["source_code"] == "BIS_IS_4707_PART2_2025"
    assert frozen[0]["edition"] == "Fifth Revision, 2025"

    with repository.connect() as connection:
        connection.execute(
            "UPDATE quality_sources SET edition = 'Future registry edit' WHERE source_code = ?",
            ("BIS_IS_4707_PART2_2025",),
        )
    summary = client.get(
        f"/api/quality/RAW_MATERIAL/{material['id']}/summary",
        params={"stage": "RAW_MATERIAL_SUPPLIER"}, headers=supplier_headers,
    ).json()
    check = next(item for item in summary["checks"] if item["code"] == "RM-RESTRICTIONS")
    assert check["source_snapshot"] is True
    assert check["sources"][0]["edition"] == "Fifth Revision, 2025"

    audit = client.get("/api/audit", headers=auth_headers(client, "admin")).json()
    event = next(item for item in audit if item["action"] == "QUALITY_RESULT_SUBMITTED")
    assert event["metadata"]["standard_code"] == "RM-RESTRICTIONS"
    assert event["metadata"]["sources"] == [{
        "source_code": "BIS_IS_4707_PART2_2025", "edition": "Fifth Revision, 2025"
    }]


def test_evidence_metadata_is_typed_and_consumer_output_stays_safe(workflow):
    client, repository, *_ = workflow
    material = create_material(client)
    headers = auth_headers(client, "supplier")
    restriction = next(
        item for item in get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
        if item["code"] == "RM-RESTRICTIONS"
    )
    result = client.post("/api/quality/results", json={
        "context_type": "RAW_MATERIAL", "context_id": material["id"],
        "standard_id": restriction["id"], "result": "PASS",
    }, headers=headers).json()
    uploaded = client.post(
        f"/api/quality/results/{result['id']}/evidence",
        data={
            "document_type": "RAW_MATERIAL_SPECIFICATION",
            "report_reference": "SPEC-DEMO-001",
            "test_method_source_code": "BIS_IS_4707_PART2_2025",
            "document_notes": "Fictional document metadata only.",
        },
        files={"file": ("spec.pdf", b"%PDF-1.4\ndemo specification\n%%EOF", "application/pdf")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["document_type"] == "RAW_MATERIAL_SPECIFICATION"
    assert uploaded.json()["report_reference"] == "SPEC-DEMO-001"
    stored = repository.get_evidence(uploaded.json()["id"])
    assert stored["test_method_source_code"] == "BIS_IS_4707_PART2_2025"
    assert "stored_filename" not in uploaded.json()

    bad_method = client.post(
        f"/api/quality/results/{result['id']}/evidence",
        data={"test_method_source_code": "NOT_REGISTERED"},
        files={"file": ("other.pdf", b"%PDF-1.4\ndemo\n%%EOF", "application/pdf")},
        headers=headers,
    )
    assert bad_method.status_code == 422


def test_source_metadata_contains_no_copyrighted_limits_or_fake_certification(workflow):
    client, *_ = workflow
    headers = auth_headers(client, "admin")
    payload = str(client.get("/api/quality/sources", headers=headers).json()).lower()
    forbidden = ["cfu/g", "acceptance criterion", "certified compliant", "passes iso"]
    assert all(term not in payload for term in forbidden)
    assert max(len(item["notes"]) for item in client.get(
        "/api/quality/sources", headers=headers
    ).json()) < 500


def test_source_aware_stage_commitment_is_deterministic(workflow):
    _client, repository, *_ = workflow
    quality = QualityService(repository)
    summary = {
        "context_type": "PRODUCT", "context_id": "DEMO", "stage": "MANUFACTURER",
        "lineage_hash": "0xlineage",
        "profile": {"profile_code": "INDIA_LUXURY_FACIAL_SERUM_DEMO_V1", "version": "1.0"},
        "checks": [{
            "code": "MFG-MICROBIOLOGY", "result": "PASS", "classification": "STANDARD_BASED",
            "sources": [{"source_code": "ISO_17516_2014", "edition": "Edition 1, 2014"}],
            "evidence": [{"file_hash": "0xabc"}],
        }],
    }
    original = quality.commitment_hash(summary)
    assert quality.commitment_hash(summary) == original
    changed = {**summary, "checks": [{
        **summary["checks"][0],
        "sources": [{"source_code": "ISO_17516_ED2", "edition": "Edition 2"}],
    }]}
    assert quality.commitment_hash(changed) != original
