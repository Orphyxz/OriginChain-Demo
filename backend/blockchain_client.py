import json
import os
from pathlib import Path
from typing import Any

from web3 import Web3


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DEPLOYMENT_PATH = ROOT_DIR / "blockchain" / "deployments" / "local.json"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class BlockchainUnavailable(RuntimeError):
    pass


class BlockchainClient:
    def __init__(
        self,
        rpc_url: str | None = None,
        deployment_path: str | os.PathLike[str] | None = None,
        receipt_timeout: int = 60,
    ):
        self.rpc_url = rpc_url or os.environ.get("ORIGINCHAIN_RPC_URL", "http://127.0.0.1:8545")
        self.deployment_path = Path(
            deployment_path
            or os.environ.get("ORIGINCHAIN_DEPLOYMENT_PATH", DEFAULT_DEPLOYMENT_PATH)
        )
        self.receipt_timeout = receipt_timeout
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 5}))
        self.deployment = self._load_deployment()
        self.contract_address = self.deployment.get("contractAddress")
        self.contract = self._load_contract()

    def _load_deployment(self) -> dict[str, Any]:
        if not self.deployment_path.exists():
            return {}
        with self.deployment_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_contract(self):
        if not self.contract_address or not self.deployment.get("abi"):
            return None
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=self.deployment["abi"],
        )

    def is_connected(self) -> bool:
        try:
            return bool(self.w3.is_connected())
        except Exception:
            return False

    def require_ready(self) -> None:
        if not self.is_connected():
            raise BlockchainUnavailable("Hardhat JSON-RPC is not connected")
        if self.contract is None:
            raise BlockchainUnavailable("OriginChain contract is not loaded")

    def health(self) -> dict[str, Any]:
        connected = self.is_connected()
        chain_id = None
        current_block = None
        if connected:
            try:
                chain_id = self.w3.eth.chain_id
                current_block = self.w3.eth.block_number
            except Exception:
                connected = False

        return {
            "blockchain_connected": connected,
            "chain_id": chain_id,
            "current_block": current_block,
            "contract_loaded": self.contract is not None,
            "contract_address": self.contract_address,
            "rpc_url": self.rpc_url,
            "network": self.deployment.get("network"),
        }

    def accounts(self) -> list[str]:
        self.require_ready()
        return [Web3.to_checksum_address(account) for account in self.w3.eth.accounts]

    def demo_roles(self) -> dict[str, str]:
        accounts = self.accounts()
        if len(accounts) >= 3:
            return {
                "MANUFACTURER": accounts[0],
                "DISTRIBUTOR": accounts[1],
                "RETAILER": accounts[2],
            }

        deployment_roles = self.deployment.get("demoActors", {})
        return {
            "MANUFACTURER": Web3.to_checksum_address(deployment_roles["manufacturer"]),
            "DISTRIBUTOR": Web3.to_checksum_address(deployment_roles["distributor"]),
            "RETAILER": Web3.to_checksum_address(deployment_roles["retailer"]),
        }

    def role_for_address(self, address: str) -> str:
        if not address:
            return "UNKNOWN"
        checksum = Web3.to_checksum_address(address)
        for role, wallet in self.demo_roles().items():
            if checksum == Web3.to_checksum_address(wallet):
                return role
        return "UNKNOWN"

    def register_product(self, product_key: str, metadata_hash: str) -> dict[str, Any]:
        self.require_ready()
        manufacturer = self.demo_roles()["MANUFACTURER"]
        tx_hash = self.contract.functions.registerProduct(product_key, metadata_hash).transact(
            {"from": manufacturer}
        )
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.receipt_timeout)
        if receipt.status != 1:
            raise BlockchainUnavailable("registerProduct transaction failed")
        return {
            "transaction_hash": Web3.to_hex(receipt.transactionHash),
            "block_number": receipt.blockNumber,
            "from_address": manufacturer,
        }

    def transfer_ownership(self, product_key: str, to_role: str) -> dict[str, Any]:
        self.require_ready()
        product = self.get_product(product_key)
        if not product["exists"]:
            raise ValueError("Product not registered on blockchain")

        roles = self.demo_roles()
        current_owner = Web3.to_checksum_address(product["current_owner"])
        current_role = self.role_for_address(current_owner)
        target_role = to_role.strip().upper()

        allowed_next_role = {
            "MANUFACTURER": "DISTRIBUTOR",
            "DISTRIBUTOR": "RETAILER",
        }.get(current_role)

        if target_role not in roles:
            raise ValueError("Unsupported demo role")
        if target_role != allowed_next_role:
            raise ValueError(f"Demo sequence requires {current_role} -> {allowed_next_role}")

        new_owner = roles[target_role]
        tx_hash = self.contract.functions.transferOwnership(product_key, new_owner).transact(
            {"from": current_owner}
        )
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.receipt_timeout)
        if receipt.status != 1:
            raise BlockchainUnavailable("transferOwnership transaction failed")

        return {
            "from_role": current_role,
            "from_address": current_owner,
            "to_role": target_role,
            "to_address": new_owner,
            "transaction_hash": Web3.to_hex(receipt.transactionHash),
            "block_number": receipt.blockNumber,
            "new_current_owner": new_owner,
        }

    def get_product(self, product_key: str) -> dict[str, Any]:
        self.require_ready()
        result = self.contract.functions.verifyProduct(product_key).call()
        return {
            "exists": bool(result[0]),
            "manufacturer": Web3.to_checksum_address(result[1]) if result[1] != ZERO_ADDRESS else result[1],
            "current_owner": Web3.to_checksum_address(result[2]) if result[2] != ZERO_ADDRESS else result[2],
            "metadata_hash": Web3.to_hex(result[3]),
            "registered_at": int(result[4]),
            "transfer_count": int(result[5]),
        }

    def get_ownership_history(self, product_key: str) -> list[str]:
        self.require_ready()
        history = self.contract.functions.getOwnershipHistory(product_key).call()
        return [Web3.to_checksum_address(address) for address in history]

    def network_info(self) -> dict[str, Any]:
        health = self.health()
        return {
            "network": health["network"],
            "chain_id": health["chain_id"],
            "current_block": health["current_block"],
            "contract_address": health["contract_address"],
        }
