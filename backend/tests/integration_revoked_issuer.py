"""Run the historical/new-evidence issuer revocation drill against a live local API."""

import httpx

from backend.tests.integration_smoke import BASE_URL, complete_stage, expect, login


def material_payload(batch: str) -> dict:
    return {
        "internal_batch_id": batch,
        "material_name": "Hyaluronic Acid Solution",
        "material_category": "ACTIVE_INGREDIENT",
        "supplier_name": "Lumina Actives",
        "supplier_identifier": "LUM-DEMO",
        "supplier_lot_number": f"LOT-{batch}",
        "quantity": 25,
        "unit": "kg",
        "received_date": "2026-08-30",
        "expiry_retest_date": "2027-08-30",
        "country_source": "Demo Origin",
        "notes": "TEST FIXTURE — FICTIONAL DEMO issuer-revocation drill.",
    }


def summary(client: httpx.Client, material_id: str, headers: dict[str, str]) -> dict:
    return expect(client.get(
        f"/api/quality/RAW_MATERIAL/{material_id}/summary",
        params={"stage": "RAW_MATERIAL_SUPPLIER"},
        headers=headers,
    ))


def coa_evidence(stage_summary: dict) -> dict:
    coa = next(item for item in stage_summary["checks"] if item["code"] == "RM-COA")
    return coa["evidence"][0]


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        admin = login(client, "admin")
        supplier = login(client, "supplier")
        expect(client.post(
            "/api/evidence/issuers/LUMINA_ACTIVES/status",
            json={
                "trust_status": "TRUSTED_DEMO",
                "reason": "TEST FIXTURE — FICTIONAL DEMO reset before revocation drill.",
            },
            headers=admin,
        ))
        expect(client.post("/api/demo/reset", headers=admin))

        historical_material = expect(client.post(
            "/api/raw-materials", json=material_payload("REV-HIST-001"), headers=supplier
        ))
        complete_stage(
            client, "RAW_MATERIAL", historical_material["id"], "RAW_MATERIAL_SUPPLIER",
            headers=supplier,
        )
        before = summary(client, historical_material["id"], supplier)
        historical_before = coa_evidence(before)
        assert before["status"] == "APPROVED"
        assert historical_before["verification_status"] == "VERIFIED_DEMO"
        assert historical_before["issuer"]["trust_status_at_submission"] == "TRUSTED_DEMO"

        expect(client.post(
            "/api/evidence/issuers/LUMINA_ACTIVES/status",
            json={
                "trust_status": "REVOKED",
                "reason": "TEST FIXTURE — FICTIONAL DEMO live revocation drill.",
            },
            headers=admin,
        ))
        after = summary(client, historical_material["id"], supplier)
        historical_after = coa_evidence(after)
        historical_coa = next(item for item in after["checks"] if item["code"] == "RM-COA")
        assert after["status"] == "APPROVED" and after["eligible_for_approval"] is True
        assert historical_after["issuer"]["trust_status_at_submission"] == "TRUSTED_DEMO"
        assert historical_after["issuer"]["current_trust_status"] == "REVOKED"
        assert historical_coa["trust_warnings"]

        new_material = expect(client.post(
            "/api/raw-materials", json=material_payload("REV-NEW-002"), headers=supplier
        ))
        complete_stage(
            client, "RAW_MATERIAL", new_material["id"], "RAW_MATERIAL_SUPPLIER",
            approve_stage=False, headers=supplier,
        )
        new_summary = summary(client, new_material["id"], supplier)
        new_evidence = coa_evidence(new_summary)
        assert new_evidence["integrity"] == "VERIFIED"
        assert new_evidence["issuer"]["trust_status_at_submission"] == "REVOKED"
        assert new_evidence["verification_status"] == "UNVERIFIED"
        blocked = client.post(
            "/api/quality/stages/approve",
            json={
                "context_type": "RAW_MATERIAL",
                "context_id": new_material["id"],
                "stage": "RAW_MATERIAL_SUPPLIER",
            },
            headers=supplier,
        )
        assert blocked.status_code == 409
        blockers = blocked.json()["detail"]["blocking_reasons"]
        assert any("Trusted Demo issuer" in item for item in blockers)

        print({
            "historical_stage": after["status"],
            "historical_trust_at_submission": historical_after["issuer"]["trust_status_at_submission"],
            "historical_current_issuer_status": historical_after["issuer"]["current_trust_status"],
            "historical_warning": historical_coa["trust_warnings"][0],
            "new_file_integrity": new_evidence["integrity"],
            "new_evidence_verification": new_evidence["verification_status"],
            "new_stage_approval": "BLOCKED",
            "blocking_reason": next(item for item in blockers if "Trusted Demo issuer" in item),
        })


if __name__ == "__main__":
    main()
