from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from web3 import Web3

from backend.database import ProductRepository
from backend.domain import ContextType, EvidenceIntegrity, SupplyChainStage
from backend.evidence import EvidenceStore
from backend.main import create_app


DEMO_PASSWORD = "OriginDemo2026!"
STAGE_USER = {
    "RAW_MATERIAL_SUPPLIER": "supplier",
    "MANUFACTURER": "manufacturer",
    "DISTRIBUTOR": "distributor",
    "RETAILER": "retailer",
}


def auth_headers(client, username):
    cache = getattr(client, "_originchain_auth_headers", {})
    if username not in cache:
        response = client.post("/api/auth/login", json={
            "username": username, "password": DEMO_PASSWORD,
        })
        assert response.status_code == 200
        cache[username] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        client._originchain_auth_headers = cache
    return cache[username]


def stage_headers(client, stage):
    return auth_headers(client, STAGE_USER[stage])


def get_standards(client, stage):
    return client.get(
        "/api/quality/standards", params={"stage": stage}, headers=stage_headers(client, stage)
    )


class WorkflowBlockchain:
    def __init__(self):
        self.products = {}
        self.quality_records = []
        self.evidence_records = []
        self.owners = {
            "MANUFACTURER": "0x0000000000000000000000000000000000000001",
            "DISTRIBUTOR": "0x0000000000000000000000000000000000000002",
            "RETAILER": "0x0000000000000000000000000000000000000003",
        }

    def health(self):
        return {"blockchain_connected": True, "chain_id": 31337, "current_block": 1,
                "contract_loaded": True, "contract_address": "0x0000000000000000000000000000000000001234",
                "rpc_url": "fake", "network": "test"}

    def require_ready(self):
        return None

    def demo_roles(self):
        return self.owners

    def role_for_address(self, address):
        return next((role for role, wallet in self.owners.items() if wallet == address), "UNKNOWN")

    def register_product(self, key, metadata_hash):
        self.products[key] = {"metadata_hash": metadata_hash, "owner": self.owners["MANUFACTURER"],
                              "history": [self.owners["MANUFACTURER"]]}
        return {"transaction_hash": "0xregister", "block_number": 1}

    def get_product(self, key):
        item = self.products.get(key)
        if not item:
            return {"exists": False, "manufacturer": "0x" + "0" * 40, "current_owner": "0x" + "0" * 40,
                    "metadata_hash": "0x" + "0" * 64, "registered_at": 0, "transfer_count": 0}
        return {"exists": True, "manufacturer": self.owners["MANUFACTURER"], "current_owner": item["owner"],
                "metadata_hash": item["metadata_hash"], "registered_at": 1,
                "transfer_count": len(item["history"]) - 1}

    def get_ownership_history(self, key):
        return self.products[key]["history"]

    def transfer_ownership(self, key, role):
        item = self.products[key]
        from_role = self.role_for_address(item["owner"])
        item["owner"] = self.owners[role]
        item["history"].append(item["owner"])
        return {"from_role": from_role, "from_address": self.owners[from_role], "to_role": role,
                "to_address": self.owners[role], "transaction_hash": f"0x{role.lower()}",
                "block_number": len(item["history"])}

    def record_quality_stage(self, key, stage, status, commitment):
        self.quality_records.append((key, stage, status, commitment))
        return {"transaction_hash": "0xquality", "block_number": 9}

    def record_evidence_hash(self, key, stage, digest):
        self.evidence_records.append((key, stage, digest))
        return {"transaction_hash": "0xevidence", "block_number": 8}

    def network_info(self):
        return {"network": "test", "chain_id": 31337, "current_block": 9,
                "contract_address": "0x0000000000000000000000000000000000001234"}


@pytest.fixture
def workflow(tmp_path: Path):
    repository = ProductRepository(tmp_path / "quality.sqlite3")
    repository.init_db()
    chain = WorkflowBlockchain()
    store = EvidenceStore(tmp_path / "uploads")
    app = create_app(repository, chain, store)
    with TestClient(app) as client:
        yield client, repository, chain, store


def create_material(client, batch="HA-260801", expiry_retest_date="2027-08-01"):
    response = client.post("/api/raw-materials", json={
        "internal_batch_id": batch, "material_name": "Hyaluronic Acid Solution",
        "material_category": "ACTIVE_INGREDIENT", "supplier_name": "Lumina Actives",
        "supplier_identifier": "LUM-DEMO", "supplier_lot_number": f"LOT-{batch}",
        "quantity": 25, "unit": "kg", "manufacturing_date": "2026-08-01",
        "received_date": "2026-08-12", "expiry_retest_date": expiry_retest_date,
        "country_source": "Demo Origin", "notes": "Fictional demonstration material",
    }, headers=auth_headers(client, "supplier"))
    assert response.status_code == 201
    return response.json()


def complete_stage(client, context_type, context_id, stage, fail_code=None):
    headers = stage_headers(client, stage)
    standards = get_standards(client, stage).json()
    result_ids = {}
    for standard in standards:
        result = "FAIL" if standard["code"] == fail_code else "PASS"
        response = client.post("/api/quality/results", json={
            "context_type": context_type, "context_id": context_id,
            "standard_id": standard["id"], "result": result,
            "notes": "Inspected for the educational demo",
        }, headers=headers)
        assert response.status_code == 200
        item = response.json()
        result_ids[standard["code"]] = item["id"]
        if standard["evidence_required"]:
            evidence_data = {
                "visibility": "CONSUMER_VISIBLE" if stage == "RETAILER" else "INTERNAL",
                "document_type": standard["expected_document_type"],
            }
            if standard.get("trusted_issuer_required"):
                evidence_data.update({
                    "issuer_code": (
                        "LUMINA_ACTIVES"
                        if standard["expected_document_type"] == "CERTIFICATE_OF_ANALYSIS"
                        else "AURELIA_QC_LAB_DEMO"
                    ),
                    "issuer_report_number": f"TEST-{standard['code']}",
                    "issuer_document_date": "2026-08-25",
                })
            upload = client.post(
                f"/api/quality/results/{item['id']}/evidence",
                data=evidence_data,
                files={"file": (f"{standard['code']}.pdf", b"%PDF-1.4\nOriginChain demo evidence\n%%EOF", "application/pdf")},
                headers=headers,
            )
            assert upload.status_code == 201
    return result_ids


def approve(client, context_type, context_id, stage):
    return client.post("/api/quality/stages/approve", json={
        "context_type": context_type, "context_id": context_id, "stage": stage,
    }, headers=stage_headers(client, stage))


def approved_material(client):
    material = create_material(client)
    complete_stage(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    response = approve(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    assert response.status_code == 200
    return material


def registered_product(client, material_id):
    response = client.post("/api/products/register", json={
        "product_code": "OC-LUX-SERUM-0001", "name": "Aurelia Prestige Renewal Serum",
        "brand": "Aurelia Maison", "batch_number": "APR-2026-001",
        "description": "Luxury anti-aging facial serum demonstration batch",
        "manufactured_date": "2026-08-20", "expiry_date": "2028-08-20",
        "raw_material_batch_ids": [material_id],
    }, headers=auth_headers(client, "manufacturer"))
    assert response.status_code == 200
    return response.json()


def test_raw_material_registration_and_duplicate_handling(workflow):
    client, *_ = workflow
    material = create_material(client)
    assert material["quality_status"] == "PENDING"
    assert client.post("/api/raw-materials", json={
        "internal_batch_id": "HA-260801", "material_name": "Duplicate", "material_category": "ACTIVE",
        "supplier_name": "Supplier", "supplier_lot_number": "LOT-2", "quantity": 1,
        "unit": "kg", "received_date": "2026-08-12",
    }, headers=auth_headers(client, "supplier")).status_code == 409


def test_registration_rejects_blank_fields_invalid_dates_and_material_selection(workflow):
    client, *_ = workflow
    blank = client.post("/api/raw-materials", json={
        "internal_batch_id": "   ", "material_name": "Material",
        "material_category": "ACTIVE", "supplier_name": "Supplier",
        "supplier_lot_number": "LOT-1", "quantity": 1, "unit": "kg",
        "received_date": "2026-08-12",
    }, headers=auth_headers(client, "supplier"))
    assert blank.status_code == 422

    invalid_dates = client.post("/api/raw-materials", json={
        "internal_batch_id": "BAD-DATES", "material_name": "Material",
        "material_category": "ACTIVE", "supplier_name": "Supplier",
        "supplier_lot_number": "LOT-2", "quantity": 1, "unit": "kg",
        "manufacturing_date": "2026-08-13", "received_date": "2026-08-12",
    }, headers=auth_headers(client, "supplier"))
    assert invalid_dates.status_code == 422

    material = approved_material(client)
    missing_material = client.post("/api/products/register", json={
        "product_code": "NO-MATERIAL", "raw_material_batch_ids": [],
    }, headers=auth_headers(client, "manufacturer"))
    assert missing_material.status_code == 422

    duplicate_material = client.post("/api/products/register", json={
        "product_code": "DUPLICATE-MATERIAL",
        "raw_material_batch_ids": [material["id"], material["id"]],
    }, headers=auth_headers(client, "manufacturer"))
    assert duplicate_material.status_code == 422

    unsupported_taxonomy = client.post("/api/products/register", json={
        "product_code": "UNSUPPORTED-TYPE", "product_type": "FRAGRANCE",
        "raw_material_batch_ids": [material["id"]],
    }, headers=auth_headers(client, "manufacturer"))
    assert unsupported_taxonomy.status_code == 422


def test_quality_writes_are_restricted_to_current_custody_stage(workflow):
    client, repository, *_ = workflow
    material = approved_material(client)
    registered_product(client, material["id"])

    distributor_standard = get_standards(client, "DISTRIBUTOR").json()[0]
    premature = client.post("/api/quality/results", json={
        "context_type": "PRODUCT", "context_id": "OC-LUX-SERUM-0001",
        "standard_id": distributor_standard["id"], "result": "PASS",
    }, headers=stage_headers(client, "DISTRIBUTOR"))
    assert premature.status_code == 409
    assert "Product custody is MANUFACTURER" in premature.json()["detail"]

    wrong_context_stage = client.post("/api/quality/stages/approve", json={
        "context_type": "RAW_MATERIAL", "context_id": material["id"],
        "stage": "MANUFACTURER",
    }, headers=stage_headers(client, "MANUFACTURER"))
    assert wrong_context_stage.status_code == 422

    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER").status_code == 200
    manufacturer_result = repository.quality_results(
        "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER"
    )[0]
    assert client.post(
        "/api/ownership-transfers",
        json={"product_code": "OC-LUX-SERUM-0001", "to_role": "DISTRIBUTOR"},
        headers=auth_headers(client, "manufacturer"),
    ).status_code == 200

    late_edit = client.post("/api/quality/results", json={
        "context_type": "PRODUCT", "context_id": "OC-LUX-SERUM-0001",
        "standard_id": manufacturer_result["template_id"], "result": "FAIL",
    }, headers=stage_headers(client, "MANUFACTURER"))
    assert late_edit.status_code == 409

    late_upload = client.post(
        f"/api/quality/results/{manufacturer_result['id']}/evidence",
        files={"file": ("late.pdf", b"%PDF-1.4\nlate\n%%EOF", "application/pdf")},
        headers=stage_headers(client, "MANUFACTURER"),
    )
    assert late_upload.status_code == 409


def test_templates_are_stage_specific_and_reusable(workflow):
    client, *_ = workflow
    manufacturer = get_standards(client, "MANUFACTURER").json()
    retailer = get_standards(client, "RETAILER").json()
    assert {item["category"] for item in manufacturer} >= {"Production Batch", "Packaging and Labelling"}
    assert {item["code"] for item in manufacturer}.isdisjoint({item["code"] for item in retailer})
    assert all(item["name"] == "OriginChain Demo Quality Standard" for item in retailer)


def test_incomplete_and_failed_qc_block_then_correction_allows_approval(workflow):
    client, *_ = workflow
    material = create_material(client)
    incomplete = approve(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"]["blocking_reasons"]
    complete_stage(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER", "RM-PHYSICAL")
    failed = approve(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    assert failed.status_code == 409
    standards = get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
    physical = next(item for item in standards if item["code"] == "RM-PHYSICAL")
    client.post("/api/quality/results", json={"context_type": "RAW_MATERIAL", "context_id": material["id"],
                "standard_id": physical["id"], "result": "PASS", "notes": "Corrected inspection"},
                headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"))
    assert approve(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER").status_code == 200


def test_evidence_validation_hash_and_tamper_detection(workflow):
    client, repository, _chain, store = workflow
    material = create_material(client)
    standards = get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
    coa = next(item for item in standards if item["code"] == "RM-COA")
    result = client.post("/api/quality/results", json={"context_type": "RAW_MATERIAL", "context_id": material["id"],
                         "standard_id": coa["id"], "result": "PASS"},
                         headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER")).json()
    rejected = client.post(f"/api/quality/results/{result['id']}/evidence",
                           files={"file": ("attack.exe", b"bad", "application/octet-stream")},
                           headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"))
    assert rejected.status_code == 422
    uploaded = client.post(f"/api/quality/results/{result['id']}/evidence",
                           files={"file": ("coa.pdf", b"%PDF-1.4\nquality\n%%EOF", "application/pdf")},
                           headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"))
    assert uploaded.status_code == 201
    evidence = uploaded.json()
    assert evidence["file_hash"].startswith("0x") and evidence["integrity"] == "VERIFIED"
    record = repository.get_evidence(evidence["id"])
    (store.root / record["stored_filename"]).write_bytes(b"%PDF-1.4\nmodified\n%%EOF")
    assert client.get(
        f"/api/evidence/{evidence['id']}/integrity",
        headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER"),
    ).json()["integrity"] == "MISMATCH"
    assert store.integrity("../outside.pdf", evidence["file_hash"]) == EvidenceIntegrity.FILE_MISSING


def test_unapproved_material_and_manufacturer_gate_block_progression(workflow):
    client, *_ = workflow
    pending = create_material(client)
    registration = client.post("/api/products/register", json={
        "product_code": "OC-LUX-SERUM-0001", "raw_material_batch_ids": [pending["id"]]
    }, headers=auth_headers(client, "manufacturer"))
    assert registration.status_code == 409
    complete_stage(client, "RAW_MATERIAL", pending["id"], "RAW_MATERIAL_SUPPLIER")
    assert approve(client, "RAW_MATERIAL", pending["id"], "RAW_MATERIAL_SUPPLIER").status_code == 200
    material = pending
    registered_product(client, material["id"])
    blocked = client.post("/api/ownership-transfers", json={
        "product_code": "OC-LUX-SERUM-0001", "to_role": "DISTRIBUTOR"
    }, headers=auth_headers(client, "manufacturer"))
    assert blocked.status_code == 409
    assert "Transfer blocked" in blocked.json()["detail"]["message"]


def test_full_quality_gated_flow_and_consumer_redaction(workflow):
    client, _repository, chain, _store = workflow
    material = approved_material(client)
    registered_product(client, material["id"])

    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER").status_code == 200
    transfer = client.post("/api/ownership-transfers", json={"product_code": "OC-LUX-SERUM-0001", "to_role": "DISTRIBUTOR"}, headers=auth_headers(client, "manufacturer"))
    assert transfer.status_code == 200

    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "DISTRIBUTOR")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "DISTRIBUTOR").status_code == 200
    assert client.post("/api/ownership-transfers", json={"product_code": "OC-LUX-SERUM-0001", "to_role": "RETAILER"}, headers=auth_headers(client, "distributor")).status_code == 200

    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "RETAILER")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "RETAILER").status_code == 200
    verification = client.get("/api/verify/OC-LUX-SERUM-0001").json()
    assert verification["status"] == "GENUINE"
    assert verification["approved_for_sale"] is True
    assert [item["status"] for item in verification["quality_journey"]] == ["APPROVED"] * 4
    assert verification["public_evidence"]
    assert all("stored_filename" not in item and "id" not in item for item in verification["public_evidence"])
    assert all(item["stage"] == "RETAILER" for item in verification["public_evidence"])
    consumer_text = str(verification).lower()
    assert all(term not in consumer_text for term in (
        "iso_", "bis_is_", "cdsco", "certified compliant", "regulatory approval",
        "requirement_rationale", "source_url",
    ))
    assert len(chain.quality_records) == 3


def test_retail_failure_holds_sale_until_corrected(workflow):
    client, *_ = workflow
    material = approved_material(client)
    registered_product(client, material["id"])
    for stage, target in (("MANUFACTURER", "DISTRIBUTOR"), ("DISTRIBUTOR", "RETAILER")):
        complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", stage)
        assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", stage).status_code == 200
        actor = "manufacturer" if target == "DISTRIBUTOR" else "distributor"
        assert client.post("/api/ownership-transfers", json={"product_code": "OC-LUX-SERUM-0001", "to_role": target}, headers=auth_headers(client, actor)).status_code == 200
    result_ids = complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "RETAILER", "RTL-PACK")
    product = client.get("/api/products", headers=auth_headers(client, "retailer")).json()[0]
    assert product["current_stage"] == "RETAILER"
    assert product["final_sale_status"] == "HOLD"
    held = approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "RETAILER")
    assert held.status_code == 409
    assert client.get("/api/verify/OC-LUX-SERUM-0001").json()["approved_for_sale"] is False
    standards = get_standards(client, "RETAILER").json()
    packaging = next(item for item in standards if item["code"] == "RTL-PACK")
    client.post("/api/quality/results", json={"context_type": "PRODUCT", "context_id": "OC-LUX-SERUM-0001",
                "standard_id": packaging["id"], "result": "PASS", "notes": "Replacement seal inspected"},
                headers=stage_headers(client, "RETAILER"))
    assert client.get("/api/products", headers=auth_headers(client, "retailer")).json()[0]["final_sale_status"] == "NOT_READY"
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "RETAILER").status_code == 200
    assert client.get("/api/products", headers=auth_headers(client, "retailer")).json()[0]["final_sale_status"] == "APPROVED_FOR_SALE"


def test_editing_approved_check_invalidates_gate_and_blocks_transfer(workflow):
    client, repository, *_ = workflow
    material = approved_material(client)
    registered_product(client, material["id"])
    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER").status_code == 200

    standards = get_standards(client, "MANUFACTURER").json()
    changed = next(item for item in standards if not item["evidence_required"])
    response = client.post("/api/quality/results", json={
        "context_type": "PRODUCT", "context_id": "OC-LUX-SERUM-0001",
        "standard_id": changed["id"], "result": "FAIL", "notes": "Regression found after approval",
    }, headers=stage_headers(client, "MANUFACTURER"))
    assert response.status_code == 200
    approval = repository.get_stage_approval("PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    assert approval["status"] == "HOLD"
    blocked = client.post("/api/ownership-transfers", json={
        "product_code": "OC-LUX-SERUM-0001", "to_role": "DISTRIBUTOR",
    }, headers=auth_headers(client, "manufacturer"))
    assert blocked.status_code == 409
    assert any("failed" in reason for reason in blocked.json()["detail"]["blocking_reasons"])


def test_modified_approved_evidence_is_rechecked_before_transfer(workflow):
    client, repository, _chain, store = workflow
    material = approved_material(client)
    registered_product(client, material["id"])
    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    assert approve(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER").status_code == 200

    evidence = repository.evidence_for_context("PRODUCT", "OC-LUX-SERUM-0001")[0]
    (store.root / evidence["stored_filename"]).write_bytes(b"%PDF-1.4\nmodified after approval\n%%EOF")
    blocked = client.post("/api/ownership-transfers", json={
        "product_code": "OC-LUX-SERUM-0001", "to_role": "DISTRIBUTOR",
    }, headers=auth_headers(client, "manufacturer"))
    assert blocked.status_code == 409
    assert any("evidence" in reason.lower() for reason in blocked.json()["detail"]["blocking_reasons"])


def test_expired_approved_material_cannot_be_linked_to_product(workflow):
    client, repository, *_ = workflow
    material = create_material(client)
    complete_stage(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    assert approve(client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER").status_code == 200
    with repository.connect() as connection:
        connection.execute(
            "UPDATE raw_material_batches SET expiry_retest_date = ? WHERE id = ?",
            ("2026-08-29", material["id"]),
        )
    response = client.post("/api/products/register", json={
        "product_code": "OC-LUX-SERUM-0001", "raw_material_batch_ids": [material["id"]],
    }, headers=auth_headers(client, "manufacturer"))
    assert response.status_code == 409
    assert "expiry/retest date" in response.json()["detail"]


def test_editing_approved_raw_material_invalidates_product_eligibility(workflow):
    client, repository, *_ = workflow
    material = approved_material(client)
    standards = get_standards(client, "RAW_MATERIAL_SUPPLIER").json()
    identity = next(item for item in standards if item["code"] == "RM-IDENTITY")
    assert client.post("/api/quality/results", json={
        "context_type": "RAW_MATERIAL", "context_id": material["id"],
        "standard_id": identity["id"], "result": "FAIL", "notes": "Identity mismatch found",
    }, headers=stage_headers(client, "RAW_MATERIAL_SUPPLIER")).status_code == 200
    assert repository.get_raw_material(material["id"])["quality_status"] == "HOLD"
    response = client.post("/api/products/register", json={
        "product_code": "OC-LUX-SERUM-0001", "raw_material_batch_ids": [material["id"]],
    }, headers=auth_headers(client, "manufacturer"))
    assert response.status_code == 409


def test_reset_clears_local_records_but_explicitly_not_chain(workflow):
    client, *_ = workflow
    create_material(client)
    response = client.post("/api/demo/reset", headers=auth_headers(client, "admin"))
    assert response.status_code == 200
    assert "Blockchain state is unchanged" in response.json()["message"]
    assert client.get("/api/raw-materials", headers=auth_headers(client, "admin")).json() == []
