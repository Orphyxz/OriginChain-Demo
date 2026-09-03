"""Run against a fresh local Hardhat deployment and a running FastAPI server."""

import httpx


BASE_URL = "http://127.0.0.1:8000"
DEMO_PASSWORD = "OriginDemo2026!"


def expect(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()


def login(client: httpx.Client, username: str) -> dict[str, str]:
    result = expect(client.post("/api/auth/login", json={
        "username": username, "password": DEMO_PASSWORD,
    }))
    assert result["user"]["username"] == username
    return {"Authorization": f"Bearer {result['access_token']}"}


def complete_stage(
    client: httpx.Client,
    context_type: str,
    context_id: str,
    stage: str,
    fail_code: str | None = None,
    approve_stage: bool = True,
    headers: dict[str, str] | None = None,
) -> dict[str, dict]:
    standards = expect(client.get(
        "/api/quality/standards", params={"stage": stage}, headers=headers
    ))
    results = {}
    for standard in standards:
        result = expect(client.post("/api/quality/results", json={
            "context_type": context_type,
            "context_id": context_id,
            "standard_id": standard["id"],
            "result": "FAIL" if standard["code"] == fail_code else "PASS",
            "notes": "End-to-end local integration smoke inspection",
        }, headers=headers))
        results[standard["code"]] = {"standard": standard, "result": result}
        if standard["evidence_required"]:
            evidence_metadata = {
                "visibility": "CONSUMER_VISIBLE" if stage == "RETAILER" else "INTERNAL",
                "document_type": standard["expected_document_type"],
                "document_notes": "TEST FIXTURE — FICTIONAL DEMO evidence only.",
            }
            if standard.get("trusted_issuer_required"):
                evidence_metadata.update({
                    "issuer_code": (
                        "LUMINA_ACTIVES"
                        if standard["expected_document_type"] == "CERTIFICATE_OF_ANALYSIS"
                        else "AURELIA_QC_LAB_DEMO"
                    ),
                    "issuer_report_number": f"TEST-{standard['code']}",
                    "issuer_document_date": "2026-08-25",
                })
            if standard["expected_document_type"] in {
                "MICROBIOLOGY_REPORT", "PRESERVATIVE_EFFICACY_REPORT"
            }:
                evidence_metadata.update({
                    "laboratory_name": "Fictional demonstration laboratory",
                    "report_reference": f"TEST-{standard['code']}",
                    "test_date": "2026-08-25",
                    "test_method_source_code": standard["sources"][0]["source_code"],
                    "result_summary": "FICTIONAL DEMO LAB DATA — workflow fixture, not a real result.",
                    "accreditation_status_text": "No real accreditation claimed; fictional test fixture.",
                })
            expect(client.post(
                f"/api/quality/results/{result['id']}/evidence",
                data=evidence_metadata,
                files={"file": (
                    f"{standard['code']}.pdf",
                    f"%PDF-1.4\nTEST FIXTURE - FICTIONAL DEMO: {standard['code']}\n%%EOF".encode(),
                    "application/pdf",
                )},
                headers=headers,
            ))
    if approve_stage:
        expect(client.post("/api/quality/stages/approve", json={
            "context_type": context_type,
            "context_id": context_id,
            "stage": stage,
        }, headers=headers))
    return results


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        health = expect(client.get("/api/health"))
        assert health["blockchain_connected"] is True
        admin = login(client, "admin")
        expect(client.post("/api/demo/reset", headers=admin))

        supplier = login(client, "supplier")

        material = expect(client.post("/api/raw-materials", json={
            "internal_batch_id": "HA-260801",
            "material_name": "Hyaluronic Acid Solution",
            "material_category": "ACTIVE_INGREDIENT",
            "supplier_name": "Lumina Actives",
            "supplier_identifier": "LUM-DEMO",
            "supplier_lot_number": "LUM-HA-801",
            "quantity": 25,
            "unit": "kg",
            "manufacturing_date": "2026-08-01",
            "received_date": "2026-08-12",
            "expiry_retest_date": "2027-08-01",
            "country_source": "Demo Origin",
            "notes": "Fictional integration-smoke material",
        }, headers=supplier))
        complete_stage(
            client, "RAW_MATERIAL", material["id"], "RAW_MATERIAL_SUPPLIER", headers=supplier
        )

        manufacturer = login(client, "manufacturer")
        product = expect(client.post("/api/products/register", json={
            "product_code": "OC-LUX-SERUM-0001",
            "name": "Aurelia Prestige Renewal Serum",
            "brand": "Aurelia Maison",
            "batch_number": "APR-2026-001",
            "description": "Luxury anti-aging facial serum demonstration batch",
            "manufactured_date": "2026-08-20",
            "expiry_date": "2028-08-20",
            "raw_material_batch_ids": [material["id"]],
        }, headers=manufacturer))

        complete_stage(
            client, "PRODUCT", product["product_code"], "MANUFACTURER", headers=manufacturer
        )
        expect(client.post("/api/ownership-transfers", json={
            "product_code": product["product_code"], "to_role": "DISTRIBUTOR",
        }, headers=manufacturer))

        distributor = login(client, "distributor")
        complete_stage(
            client, "PRODUCT", product["product_code"], "DISTRIBUTOR", headers=distributor
        )
        expect(client.post("/api/ownership-transfers", json={
            "product_code": product["product_code"], "to_role": "RETAILER",
        }, headers=distributor))

        retailer = login(client, "retailer")
        retail = complete_stage(
            client, "PRODUCT", product["product_code"], "RETAILER",
            fail_code="RTL-PACK", approve_stage=False, headers=retailer,
        )
        held_product = expect(client.get("/api/products", headers=retailer))[0]
        assert held_product["final_sale_status"] == "HOLD"
        blocked_approval = client.post("/api/quality/stages/approve", json={
            "context_type": "PRODUCT", "context_id": product["product_code"], "stage": "RETAILER",
        }, headers=retailer)
        assert blocked_approval.status_code == 409
        blocked_detail = blocked_approval.json()["detail"]
        assert any(
            "Security Seal" in reason and "failed" in reason
            for reason in blocked_detail["blocking_reasons"]
        )

        packaging = retail["RTL-PACK"]["standard"]
        expect(client.post("/api/quality/results", json={
            "context_type": "PRODUCT", "context_id": product["product_code"],
            "standard_id": packaging["id"], "result": "PASS",
            "notes": "Security seal re-inspected and correction confirmed",
        }, headers=retailer))
        corrected_product = expect(client.get("/api/products", headers=retailer))[0]
        assert corrected_product["final_sale_status"] == "NOT_READY"
        expect(client.post("/api/quality/stages/approve", json={
            "context_type": "PRODUCT", "context_id": product["product_code"], "stage": "RETAILER",
        }, headers=retailer))

        verification = expect(client.get(f"/api/verify/{product['product_code']}"))
        assert verification["status"] == "GENUINE"
        assert verification["approved_for_sale"] is True
        assert verification["document_integrity"] == "VERIFIED"
        assert [stage["status"] for stage in verification["quality_journey"]] == ["APPROVED"] * 4
        assert verification["current_owner"]["role"] == "RETAILER"
        assert verification["public_evidence"]
        serialized = str(verification).lower()
        assert "stored_filename" not in serialized
        assert "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266" not in serialized
        assert "0x70997970c51812dc3a010c7d01b50e0d17dc79c8" not in serialized
        assert "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc" not in serialized

        expect(client.post(f"/api/demo/tamper/{product['product_code']}", headers=admin))
        tampered = expect(client.get(f"/api/verify/{product['product_code']}"))
        assert tampered["status"] == "SUSPICIOUS"
        assert tampered["metadata_integrity"] is False
        audit = expect(client.get("/api/audit", headers=admin))
        assert {"RAW_MATERIAL_REGISTERED", "PRODUCT_REGISTERED", "OWNERSHIP_TRANSFERRED",
                "STAGE_APPROVED", "DEMO_METADATA_TAMPERED"} <= {item["action"] for item in audit}
        print({
            "health": "connected",
            "authenticated_roles": ["SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER", "ADMIN"],
            "product": product["product_code"],
            "retail_failure": "HOLD",
            "retail_correction_pending_approval": corrected_product["final_sale_status"],
            "retail_approval": verification["final_sale_status"],
            "quality_stages": [stage["status"] for stage in verification["quality_journey"]],
            "final_sale_status": verification["final_sale_status"],
            "current_owner": verification["current_owner"]["role"],
            "document_integrity": verification["document_integrity"],
            "public_evidence_count": len(verification["public_evidence"]),
            "tamper_status": tampered["status"],
            "audit_events": len(audit),
        })


if __name__ == "__main__":
    main()
