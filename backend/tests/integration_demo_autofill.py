"""Real-stack smoke for the exact five-minute role-by-role presentation path."""

import json
import os
import sys

import httpx


BASE_URL = os.environ.get("ORIGINCHAIN_API_URL", "http://127.0.0.1:8000")
PASSWORD = "OriginDemo2026!"


def expect(response: httpx.Response, status: int = 200) -> dict:
    if response.status_code != status:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}: {response.text}"
        )
    return response.json()


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        headers = {}

        def login(username: str) -> dict[str, str]:
            result = expect(
                client.post(
                    "/api/auth/login",
                    json={"username": username, "password": PASSWORD},
                )
            )
            return {"Authorization": f"Bearer {result['access_token']}"}

        for role in ("admin", "supplier", "manufacturer", "distributor", "retailer"):
            headers[role] = login(role)

        readiness = expect(client.get("/api/demo/readiness", headers=headers["admin"]))
        assert readiness["status"] == "READY", readiness

        expect(client.post("/api/demo/reset", headers=headers["admin"]))
        supplier = expect(client.post("/api/demo/auto-fill", headers=headers["supplier"]))
        assert supplier["status"] == "APPROVED"

        manufacturer = expect(
            client.post("/api/demo/auto-fill", headers=headers["manufacturer"])
        )
        product_code = manufacturer["product_code"]
        assert manufacturer["current_stage"] == "MANUFACTURER"
        expect(
            client.post(
                "/api/ownership-transfers",
                json={"product_code": product_code, "to_role": "DISTRIBUTOR"},
                headers=headers["manufacturer"],
            )
        )

        distributor = expect(
            client.post("/api/demo/auto-fill", headers=headers["distributor"])
        )
        assert distributor["status"] == "APPROVED"
        expect(
            client.post(
                "/api/ownership-transfers",
                json={"product_code": product_code, "to_role": "RETAILER"},
                headers=headers["distributor"],
            )
        )

        hold = expect(
            client.post("/api/demo/retailer-hold", headers=headers["retailer"])
        )
        assert hold["final_sale_status"] == "HOLD"
        corrected = expect(
            client.post("/api/demo/auto-fill", headers=headers["retailer"])
        )
        assert corrected["corrected_hold"] is True
        assert corrected["final_sale_status"] == "APPROVED_FOR_SALE"

        genuine = expect(client.get(f"/api/verify/{product_code}"))
        assert genuine["status"] == "GENUINE"
        assert genuine["approved_for_sale"] is True
        assert [item["status"] for item in genuine["quality_journey"]] == ["APPROVED"] * 4
        serialized = json.dumps(genuine).lower()
        for private_name in (
            "stored_filename",
            "submitted_by_user_id",
            "approved_by_user_id",
            "inspector_stage",
            "document_notes",
        ):
            assert private_name not in serialized
        assert "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266" not in serialized

        expect(client.post(f"/api/demo/tamper/{product_code}", headers=headers["admin"]))
        suspicious = expect(client.get(f"/api/verify/{product_code}"))
        assert suspicious["status"] == "SUSPICIOUS"
        assert suspicious["metadata_integrity"] is False

        progress = expect(client.get("/api/demo/progress", headers=headers["admin"]))
        assert progress["completed"] == 4  # Consumer authenticity is no longer complete after tamper.

        print(
            json.dumps(
                {
                    "readiness": readiness["status"],
                    "supplier": supplier["status"],
                    "manufacturer": manufacturer["status"],
                    "distributor": distributor["status"],
                    "retail_hold": hold["final_sale_status"],
                    "retail_fix": corrected["final_sale_status"],
                    "consumer_before_tamper": genuine["status"],
                    "consumer_after_tamper": suspicious["status"],
                    "product_code": product_code,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Integration demo smoke failed: {exc}", file=sys.stderr)
        raise
