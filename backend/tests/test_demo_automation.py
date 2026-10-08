import json
from collections import Counter

from backend.tests.test_quality_workflow import auth_headers, workflow


def test_application_has_no_duplicate_api_method_routes(workflow):
    client, *_ = workflow
    routes = [
        (method, route.path)
        for route in client.app.routes
        for method in getattr(route, "methods", set())
        if route.path.startswith("/api/")
    ]
    duplicates = [route for route, count in Counter(routes).items() if count > 1]
    assert duplicates == []


def test_demo_auto_fill_requires_auth_and_operational_role(workflow, monkeypatch):
    monkeypatch.setenv("ORIGINCHAIN_DEMO_MODE", "1")
    client, *_ = workflow

    assert client.post("/api/demo/auto-fill").status_code == 401
    wrong_role = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "admin")
    )
    assert wrong_role.status_code == 403


def test_manufacturer_demo_auto_fill_requires_approved_material_and_audits_failure(
    workflow, monkeypatch
):
    monkeypatch.setenv("ORIGINCHAIN_DEMO_MODE", "1")
    client, repository, *_ = workflow

    response = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "manufacturer")
    )
    assert response.status_code == 409
    assert "Complete the Supplier stage first" in response.json()["detail"]
    actions = [event["action"] for event in repository.list_audit_events(20)]
    assert "DEMO_AUTO_FILL_STARTED" in actions
    assert "DEMO_AUTO_FILL_FAILED" in actions


def test_role_by_role_demo_auto_fill_hold_correction_and_privacy(workflow, monkeypatch):
    monkeypatch.setenv("ORIGINCHAIN_DEMO_MODE", "1")
    client, repository, chain, store = workflow

    supplier_headers = auth_headers(client, "supplier")
    supplier = client.post("/api/demo/auto-fill", headers=supplier_headers)
    assert supplier.status_code == 200
    assert supplier.json()["status"] == "APPROVED"
    assert supplier.json()["internal_batch_id"] == "HA-260801"
    material_id = supplier.json()["context_id"]
    supplier_result_count = len(
        repository.quality_results(
            "RAW_MATERIAL", material_id, "RAW_MATERIAL_SUPPLIER"
        )
    )
    supplier_evidence_count = len(
        repository.evidence_for_context("RAW_MATERIAL", material_id)
    )
    assert supplier_evidence_count > 0
    for evidence in repository.evidence_for_context("RAW_MATERIAL", material_id):
        assert store.integrity(evidence["stored_filename"], evidence["file_hash"]).value == "VERIFIED"
        assert evidence["uploaded_by_user_id"] == "user_supplier"
        fixture = (store.root / evidence["stored_filename"]).read_text()
        assert "TEST FIXTURE - FICTIONAL DEMO" in fixture
        assert "certification" in fixture.lower()

    repeated = client.post("/api/demo/auto-fill", headers=supplier_headers)
    assert repeated.status_code == 200
    assert repeated.json()["already_complete"] is True
    assert len(repository.quality_results("RAW_MATERIAL", material_id, "RAW_MATERIAL_SUPPLIER")) == supplier_result_count
    assert len(repository.evidence_for_context("RAW_MATERIAL", material_id)) == supplier_evidence_count
    assert len(repository.list_raw_materials()) == 1

    manufacturer = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "manufacturer")
    )
    assert manufacturer.status_code == 200, manufacturer.text
    manufacturer_data = manufacturer.json()
    assert manufacturer_data["status"] == "APPROVED"
    assert manufacturer_data["current_stage"] == "MANUFACTURER"
    product_code = manufacturer_data["product_code"]
    product = repository.get_product(product_code)
    assert product["specification_code"]
    assert repository.product_raw_materials(product_code)[0]["id"] == material_id
    assert len(repository.transfers(product_code)) == 0
    assert all(
        result["submitted_by_user_id"] == "user_manufacturer"
        for result in repository.quality_results("PRODUCT", product_code, "MANUFACTURER")
    )

    distributor_too_early = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "distributor")
    )
    assert distributor_too_early.status_code == 409
    assert "preceding transfer" in distributor_too_early.json()["detail"]

    transfer = client.post(
        "/api/ownership-transfers",
        json={"product_code": product_code, "to_role": "DISTRIBUTOR"},
        headers=auth_headers(client, "manufacturer"),
    )
    assert transfer.status_code == 200

    distributor = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "distributor")
    )
    assert distributor.status_code == 200
    assert distributor.json()["status"] == "APPROVED"
    assert repository.get_product(product_code)["current_stage"] == "DISTRIBUTOR"
    assert len(repository.transfers(product_code)) == 1

    hold_too_early = client.post(
        "/api/demo/retailer-hold", headers=auth_headers(client, "retailer")
    )
    assert hold_too_early.status_code == 409
    retailer_too_early = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "retailer")
    )
    assert retailer_too_early.status_code == 409

    transfer = client.post(
        "/api/ownership-transfers",
        json={"product_code": product_code, "to_role": "RETAILER"},
        headers=auth_headers(client, "distributor"),
    )
    assert transfer.status_code == 200

    hold = client.post(
        "/api/demo/retailer-hold", headers=auth_headers(client, "retailer")
    )
    assert hold.status_code == 200
    assert hold.json()["status"] == "HOLD"
    assert repository.get_product(product_code)["final_sale_status"] == "HOLD"
    retail_summary = client.get(
        f"/api/quality/PRODUCT/{product_code}/summary?stage=RETAILER",
        headers=auth_headers(client, "retailer"),
    ).json()
    seal = next(check for check in retail_summary["checks"] if check["code"] == "RTL-PACK")
    assert seal["result"] == "FAIL"
    assert any("Security Seal" in reason for reason in retail_summary["blocking_reasons"])

    correction = client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "retailer")
    )
    assert correction.status_code == 200
    corrected = correction.json()
    assert corrected["corrected_hold"] is True
    assert corrected["status"] == "APPROVED"
    assert corrected["final_sale_status"] == "APPROVED_FOR_SALE"
    assert len(repository.transfers(product_code)) == 2

    verification = client.get(f"/api/verify/{product_code}")
    assert verification.status_code == 200
    public = verification.json()
    assert public["status"] == "GENUINE"
    assert public["approved_for_sale"] is True
    assert [stage["status"] for stage in public["quality_journey"]] == ["APPROVED"] * 4
    serialized = json.dumps(public).lower()
    assert "stored_filename" not in serialized
    assert "submitted_by_user_id" not in serialized
    assert "private key" not in serialized
    assert not any(wallet.lower() in serialized for wallet in chain.owners.values())

    progress = client.get("/api/demo/progress", headers=supplier_headers)
    assert progress.status_code == 200
    assert progress.json()["completed"] == 5
    assert all(stage["complete"] for stage in progress.json()["stages"])

    audits = repository.list_audit_events(200)
    action_actor = {(event["action"], event["actor_user_id"]) for event in audits}
    assert ("DEMO_AUTO_FILL_COMPLETED", "user_supplier") in action_actor
    assert ("DEMO_AUTO_FILL_COMPLETED", "user_manufacturer") in action_actor
    assert ("DEMO_AUTO_FILL_COMPLETED", "user_distributor") in action_actor
    assert ("DEMO_HOLD_CREATED", "user_retailer") in action_actor
    assert ("DEMO_HOLD_CORRECTED", "user_retailer") in action_actor


def test_demo_readiness_and_environment_guard(workflow, monkeypatch):
    client, *_ = workflow
    monkeypatch.setenv("ORIGINCHAIN_DEMO_MODE", "1")
    readiness = client.get(
        "/api/demo/readiness", headers=auth_headers(client, "admin")
    )
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "READY"
    assert all(item["ok"] for item in readiness.json()["checks"])

    monkeypatch.setenv("ORIGINCHAIN_DEMO_MODE", "0")
    assert client.post(
        "/api/demo/auto-fill", headers=auth_headers(client, "supplier")
    ).status_code == 404
    assert client.post(
        "/api/demo/retailer-hold", headers=auth_headers(client, "retailer")
    ).status_code == 404
    assert client.post(
        "/api/demo/reset", headers=auth_headers(client, "admin")
    ).status_code == 404
    assert client.get("/api/demo/catalog").json()["demo_mode"] is False
