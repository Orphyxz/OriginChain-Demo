import json
from typing import Any, Mapping

from web3 import Web3


def canonical_metadata(metadata: Mapping[str, Any]) -> str:
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def metadata_hash(metadata: Mapping[str, Any]) -> str:
    canonical = canonical_metadata(metadata)
    return Web3.to_hex(Web3.keccak(text=canonical))


def product_key(product_code: str) -> str:
    return Web3.to_hex(Web3.keccak(text=product_code.strip()))


def product_metadata(
    product_code: str,
    name: str,
    brand: str,
    batch_number: str,
    description: str,
) -> dict[str, str]:
    return {
        "batch_number": batch_number,
        "brand": brand,
        "description": description,
        "name": name,
        "product_code": product_code,
    }
