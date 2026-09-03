from datetime import timedelta
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.auth import AuthService, DEMO_ACCOUNTS
from backend.database import ProductRepository
from backend.evidence import EvidenceStore
from backend.main import create_app
from backend.tests.test_quality_workflow import (
    WorkflowBlockchain,
    approved_material,
    auth_headers,
    complete_stage,
    get_standards,
    registered_product,
)


@pytest.fixture
def secured_workflow(tmp_path: Path):
    repository = ProductRepository(tmp_path / "auth.sqlite3")
    chain = WorkflowBlockchain()
    store = EvidenceStore(tmp_path / "uploads")
    auth = AuthService(secret="test-secret-that-is-long-enough-for-originchain")
    app = create_app(repository, chain, store, auth)
    with TestClient(app) as client:
        yield client, repository, chain, store, auth


def login(client, username, password="OriginDemo2026!"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_seeded_users_are_hashed_and_login_returns_safe_expiring_token(secured_workflow):
    client, repository, *_ = secured_workflow
    assert {repository.get_user_by_username(item["username"])["role"] for item in DEMO_ACCOUNTS} == {
        "ADMIN", "RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER"
    }
    manufacturer = repository.get_user_by_username("manufacturer")
    supplier = repository.get_user_by_username("supplier")
    assert manufacturer["password_hash"] != "OriginDemo2026!"
    assert manufacturer["password_hash"].startswith("$argon2")
    assert manufacturer["password_hash"] != supplier["password_hash"]

    response = login(client, "manufacturer")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800
    assert "password" not in str(body).lower()
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert {"sub", "role", "iat", "exp", "iss"} <= claims.keys()
    assert "password" not in str(claims).lower() and "hash" not in str(claims).lower()

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "MANUFACTURER"
    assert "password_hash" not in me.json()


def test_invalid_credentials_are_generic(secured_workflow):
    client, *_ = secured_workflow
    wrong = login(client, "manufacturer", "wrong-password")
    unknown = login(client, "not-a-user", "wrong-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Invalid username or password."


def test_missing_malformed_expired_and_inactive_tokens_are_rejected(secured_workflow):
    client, repository, _chain, _store, auth = secured_workflow
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer malformed"}).status_code == 401

    user = repository.get_user_by_username("supplier")
    expired = auth.create_access_token(user, expires_delta=timedelta(seconds=-1))
    expired_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert expired_response.status_code == 401
    assert "expired" in expired_response.json()["detail"].lower()

    valid = auth.create_access_token(user)
    with repository.connect() as connection:
        connection.execute("UPDATE users SET active = 0 WHERE id = ?", (user["id"],))
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid}"}).status_code == 401


def test_operational_endpoints_require_login_and_role_spoofing_fails(secured_workflow):
    client, *_ = secured_workflow
    material_payload = {
        "internal_batch_id": "AUTH-RM-1", "material_name": "Demo Active",
        "material_category": "ACTIVE_INGREDIENT", "supplier_name": "Lumina Actives",
        "supplier_lot_number": "AUTH-LOT", "quantity": 1, "unit": "kg",
        "received_date": "2026-08-20", "expiry_retest_date": "2027-08-20",
    }
    assert client.post("/api/raw-materials", json=material_payload).status_code == 401
    assert client.post(
        "/api/raw-materials", json=material_payload, headers=auth_headers(client, "supplier")
    ).status_code == 201
    assert client.post(
        "/api/raw-materials", json={**material_payload, "internal_batch_id": "AUTH-RM-2"},
        headers=auth_headers(client, "manufacturer"),
    ).status_code == 403

    manufacturer_standard = get_standards(client, "MANUFACTURER").json()[0]
    retailer_standard = get_standards(client, "RETAILER").json()[0]
    spoof_payload = {
        "context_type": "PRODUCT", "context_id": "forged-context",
        "standard_id": manufacturer_standard["id"], "result": "PASS",
    }
    assert client.post(
        "/api/quality/results", json=spoof_payload, headers=auth_headers(client, "supplier")
    ).status_code == 403
    assert client.post(
        "/api/quality/results",
        json={**spoof_payload, "standard_id": retailer_standard["id"]},
        headers=auth_headers(client, "supplier"),
    ).status_code == 403
    assert client.post(
        "/api/quality/results",
        json={**spoof_payload, "standard_id": retailer_standard["id"]},
        headers=auth_headers(client, "distributor"),
    ).status_code == 403

    registration = {"product_code": "FORGED-PRODUCT", "raw_material_batch_ids": []}
    assert client.post(
        "/api/products/register", json=registration, headers=auth_headers(client, "retailer")
    ).status_code == 403
    assert client.post("/api/demo/reset").status_code == 401
    assert client.post("/api/demo/tamper/FORGED-PRODUCT").status_code == 401


def test_attribution_audit_and_evidence_access_follow_actor_role(secured_workflow):
    client, repository, *_ = secured_workflow
    material = approved_material(client)
    raw_row = repository.get_raw_material(material["id"])
    assert raw_row["created_by_user_id"] == "user_supplier"
    raw_approval = repository.get_stage_approval("RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER")
    assert raw_approval["approved_by_user_id"] == "user_supplier"

    registered_product(client, material["id"])
    assert repository.get_product("OC-LUX-SERUM-0001")["registered_by_user_id"] == "user_manufacturer"
    complete_stage(client, "PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")
    result = repository.quality_results("PRODUCT", "OC-LUX-SERUM-0001", "MANUFACTURER")[0]
    assert result["submitted_by_user_id"] == "user_manufacturer"
    evidence = repository.evidence_for_context("PRODUCT", "OC-LUX-SERUM-0001")[0]
    assert evidence["uploaded_by_user_id"] == "user_manufacturer"

    assert client.get(f"/api/evidence/{evidence['id']}/integrity").status_code == 401
    assert client.get(
        f"/api/evidence/{evidence['id']}/integrity", headers=auth_headers(client, "distributor")
    ).status_code == 403
    actor_view = client.get(
        f"/api/evidence/{evidence['id']}/integrity", headers=auth_headers(client, "manufacturer")
    )
    assert actor_view.status_code == 200
    assert "stored_filename" not in actor_view.json()
    assert client.get(
        f"/api/evidence/{evidence['id']}/integrity", headers=auth_headers(client, "admin")
    ).status_code == 200

    restricted_summary = client.get(
        "/api/quality/PRODUCT/OC-LUX-SERUM-0001/summary",
        params={"stage": "MANUFACTURER"}, headers=auth_headers(client, "distributor"),
    ).json()
    assert all(check["notes"] is None for check in restricted_summary["checks"])
    assert "stored_filename" not in str(restricted_summary)
    assert "MFG-PACK.pdf" not in str(restricted_summary)

    audit = client.get("/api/audit", headers=auth_headers(client, "admin"))
    assert audit.status_code == 200
    quality_events = [item for item in audit.json() if item["action"] == "QUALITY_RESULT_SUBMITTED"]
    assert quality_events
    assert quality_events[0]["actor_user_id"] == "user_manufacturer"
    assert quality_events[0]["actor_role"] == "MANUFACTURER"


def test_admin_reset_is_audited_and_preserves_seeded_users(secured_workflow):
    client, repository, *_ = secured_workflow
    response = client.post("/api/demo/reset", headers=auth_headers(client, "admin"))
    assert response.status_code == 200
    assert login(client, "supplier").status_code == 200
    events = repository.list_audit_events(20)
    assert any(item["action"] == "DEMO_RESET" and item["actor_role"] == "ADMIN" for item in events)
