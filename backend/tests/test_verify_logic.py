from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import ProductRepository
from backend.main import create_app
from backend.metadata_hash import canonical_metadata, metadata_hash, product_key, product_metadata


class FakeBlockchain:
    def __init__(self, metadata_hash_value: str, exists: bool = True):
        self.metadata_hash_value = metadata_hash_value
        self.exists = exists

    def health(self):
        return {
            "blockchain_connected": True,
            "chain_id": 31337,
            "current_block": 1,
            "contract_loaded": True,
            "contract_address": "0x0000000000000000000000000000000000001234",
            "rpc_url": "fake",
            "network": "test",
        }

    def get_product(self, _product_key: str):
        if not self.exists:
            return {
                "exists": False,
                "manufacturer": "0x0000000000000000000000000000000000000000",
                "current_owner": "0x0000000000000000000000000000000000000000",
                "metadata_hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
                "registered_at": 0,
                "transfer_count": 0,
            }
        return {
            "exists": True,
            "manufacturer": "0x0000000000000000000000000000000000000001",
            "current_owner": "0x0000000000000000000000000000000000000003",
            "metadata_hash": self.metadata_hash_value,
            "registered_at": 123,
            "transfer_count": 2,
        }

    def get_ownership_history(self, _product_key: str):
        return [
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
            "0x0000000000000000000000000000000000000003",
        ]

    def role_for_address(self, address: str):
        roles = {
            "0x0000000000000000000000000000000000000001": "MANUFACTURER",
            "0x0000000000000000000000000000000000000002": "DISTRIBUTOR",
            "0x0000000000000000000000000000000000000003": "RETAILER",
        }
        return roles.get(address, "UNKNOWN")

    def network_info(self):
        return {
            "network": "test",
            "chain_id": 31337,
            "current_block": 1,
            "contract_address": "0x0000000000000000000000000000000000001234",
        }


def make_client(tmp_path: Path, fake_chain: FakeBlockchain) -> tuple[TestClient, ProductRepository]:
    repository = ProductRepository(tmp_path / "test.sqlite3")
    repository.init_db()
    app = create_app(repository=repository, blockchain=fake_chain)
    return TestClient(app), repository


def insert_demo_product(repository: ProductRepository, brand: str = "Origin Labs") -> str:
    metadata = product_metadata(
        product_code="OC-DEMO-0001",
        name="OriginChain Demo Sneakers",
        brand=brand,
        batch_number="B001",
        description="Blockchain authentication demo",
    )
    hash_value = metadata_hash(metadata)
    repository.create_product(
        {
            "product_code": "OC-DEMO-0001",
            "name": metadata["name"],
            "brand": metadata["brand"],
            "batch_number": metadata["batch_number"],
            "description": metadata["description"],
            "metadata_json": canonical_metadata(metadata),
            "product_key": product_key("OC-DEMO-0001"),
            "metadata_hash": hash_value,
            "registration_tx_hash": "0xtx",
            "registration_block_number": 1,
        }
    )
    return hash_value


def test_unknown_code_returns_not_found(tmp_path):
    client, _repository = make_client(
        tmp_path,
        FakeBlockchain("0x0000000000000000000000000000000000000000000000000000000000000000"),
    )

    response = client.get("/api/verify/OC-UNKNOWN")

    assert response.status_code == 200
    assert response.json()["status"] == "NOT_FOUND"


def test_genuine_matching_record_returns_genuine(tmp_path):
    client, repository = make_client(
        tmp_path,
        FakeBlockchain("0x0000000000000000000000000000000000000000000000000000000000000000"),
    )
    hash_value = insert_demo_product(repository)
    client.app.state.blockchain.metadata_hash_value = hash_value

    response = client.get("/api/verify/OC-DEMO-0001")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "GENUINE"
    assert body["blockchain_verified"] is True
    assert body["metadata_integrity"] is True
    assert body["current_owner"]["role"] == "RETAILER"


def test_integrity_mismatch_returns_suspicious(tmp_path):
    client, repository = make_client(
        tmp_path,
        FakeBlockchain("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    )
    insert_demo_product(repository)

    response = client.get("/api/verify/OC-DEMO-0001")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUSPICIOUS"
    assert body["blockchain_verified"] is True
    assert body["metadata_integrity"] is False
