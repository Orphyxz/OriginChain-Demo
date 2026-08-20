import json
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .blockchain_client import BlockchainClient, BlockchainUnavailable
from .database import ProductRepository
from .metadata_hash import canonical_metadata, metadata_hash, product_key, product_metadata

STATIC_DIR = Path(__file__).with_name("static")


class ProductRegistrationRequest(BaseModel):
    product_code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1)
    batch_number: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class OwnershipTransferRequest(BaseModel):
    product_code: str = Field(..., min_length=1)
    to_role: str = Field(..., min_length=1)


def create_app(
    repository: ProductRepository | None = None,
    blockchain: BlockchainClient | None = None,
) -> FastAPI:
    app = FastAPI(title="OriginChain Demo API", version="0.2.0")
    app.state.repository = repository or ProductRepository()
    app.state.blockchain = blockchain or BlockchainClient()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.on_event("startup")
    def startup() -> None:
        app.state.repository.init_db()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        chain = request.app.state.blockchain
        chain_health = chain.health()
        return {
            "api_status": "ok",
            **chain_health,
        }

    @app.get("/api/qr/{product_code}")
    def product_qr(product_code: str) -> Response:
        image = qrcode.make(product_code.strip())
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return Response(content=buffer.getvalue(), media_type="image/png")

    @app.post("/api/products/register")
    def register_product(payload: ProductRegistrationRequest, request: Request) -> dict[str, Any]:
        repository = request.app.state.repository
        chain = request.app.state.blockchain
        repository.init_db()

        product_code = payload.product_code.strip()
        if repository.get_product(product_code):
            raise HTTPException(status_code=409, detail="Product already exists in local database")

        metadata = product_metadata(
            product_code=product_code,
            name=payload.name.strip(),
            brand=payload.brand.strip(),
            batch_number=payload.batch_number.strip(),
            description=payload.description.strip(),
        )
        product_key_value = product_key(product_code)
        metadata_hash_value = metadata_hash(metadata)

        try:
            receipt = chain.register_product(product_key_value, metadata_hash_value)
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain registration failed: {exc}") from exc

        repository.create_product(
            {
                "product_code": product_code,
                "name": metadata["name"],
                "brand": metadata["brand"],
                "batch_number": metadata["batch_number"],
                "description": metadata["description"],
                "metadata_json": canonical_metadata(metadata),
                "product_key": product_key_value,
                "metadata_hash": metadata_hash_value,
                "registration_tx_hash": receipt["transaction_hash"],
                "registration_block_number": receipt["block_number"],
            }
        )

        roles = chain.demo_roles()
        return {
            "product_code": product_code,
            "product_key": product_key_value,
            "metadata_hash": metadata_hash_value,
            "manufacturer_wallet": roles["MANUFACTURER"],
            "transaction_hash": receipt["transaction_hash"],
            "block_number": receipt["block_number"],
            "blockchain_registered": True,
        }

    @app.post("/api/ownership-transfers")
    def transfer_ownership(payload: OwnershipTransferRequest, request: Request) -> dict[str, Any]:
        repository = request.app.state.repository
        chain = request.app.state.blockchain
        product_code = payload.product_code.strip()
        local_product = repository.get_product(product_code)

        if not local_product:
            raise HTTPException(status_code=404, detail="Product not found in local database")

        try:
            receipt = chain.transfer_ownership(local_product["product_key"], payload.to_role)
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain transfer failed: {exc}") from exc

        repository.add_transfer(
            {
                "product_code": product_code,
                "from_role": receipt["from_role"],
                "from_address": receipt["from_address"],
                "to_role": receipt["to_role"],
                "to_address": receipt["to_address"],
                "transaction_hash": receipt["transaction_hash"],
                "block_number": receipt["block_number"],
            }
        )

        return receipt

    @app.get("/api/verify/{product_code}")
    def verify_product(product_code: str, request: Request) -> dict[str, Any]:
        repository = request.app.state.repository
        chain = request.app.state.blockchain
        local_product = repository.get_product(product_code.strip())

        if not local_product:
            return {
                "status": "NOT_FOUND",
                "product_code": product_code,
                "blockchain_verified": False,
                "metadata_integrity": False,
                "message": "No off-chain product metadata found.",
            }

        try:
            blockchain_product = chain.get_product(local_product["product_key"])
            history = chain.get_ownership_history(local_product["product_key"])
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain verification failed: {exc}") from exc

        if not blockchain_product["exists"]:
            return {
                "status": "NOT_FOUND",
                "product_code": local_product["product_code"],
                "blockchain_verified": False,
                "metadata_integrity": False,
                "product": _public_product(local_product),
                "message": "Product metadata exists locally, but the product is not registered on-chain.",
            }

        current_metadata = _metadata_from_row(local_product)
        recomputed_hash = metadata_hash(current_metadata)
        metadata_integrity = recomputed_hash.lower() == blockchain_product["metadata_hash"].lower()
        status = "GENUINE" if metadata_integrity else "SUSPICIOUS"

        return {
            "status": status,
            "product_code": local_product["product_code"],
            "blockchain_verified": True,
            "metadata_integrity": metadata_integrity,
            "product": _public_product(local_product),
            "manufacturer": _actor(chain, blockchain_product["manufacturer"]),
            "current_owner": _actor(chain, blockchain_product["current_owner"]),
            "ownership_history": [_actor(chain, address) for address in history],
            "blockchain": {
                **chain.network_info(),
                "product_key": local_product["product_key"],
                "metadata_hash": blockchain_product["metadata_hash"],
                "recomputed_metadata_hash": recomputed_hash,
                "registered_at": blockchain_product["registered_at"],
                "transfer_count": blockchain_product["transfer_count"],
                "registration_tx_hash": local_product["registration_tx_hash"],
                "registration_block_number": local_product["registration_block_number"],
            },
        }

    @app.post("/api/demo/tamper/{product_code}")
    def tamper_product(product_code: str, request: Request) -> dict[str, Any]:
        repository = request.app.state.repository
        repository.init_db()
        product = repository.tamper_product(product_code.strip())
        if not product:
            raise HTTPException(status_code=404, detail="Product not found in local database")

        return {
            "warning": "DEMO ONLY - NOT PRODUCTION",
            "message": "Off-chain metadata changed. Blockchain metadata hash was not updated.",
            "product_code": product["product_code"],
            "modified_fields": ["brand", "description"],
            "product": _public_product(product),
        }

    @app.post("/api/demo/reset")
    def reset_demo(request: Request) -> dict[str, Any]:
        request.app.state.repository.init_db()
        request.app.state.repository.reset_demo()
        return {
            "warning": "DEMO ONLY - NOT PRODUCTION",
            "message": "Local SQLite demo metadata was cleared. Blockchain state is unchanged.",
        }

    return app


def _metadata_from_row(row: dict[str, Any]) -> dict[str, str]:
    return product_metadata(
        product_code=row["product_code"],
        name=row["name"],
        brand=row["brand"],
        batch_number=row["batch_number"],
        description=row["description"],
    )


def _public_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_code": row["product_code"],
        "name": row["name"],
        "brand": row["brand"],
        "batch_number": row["batch_number"],
        "description": row["description"],
        "metadata_json": json.loads(row["metadata_json"]),
        "registration_tx_hash": row["registration_tx_hash"],
        "registration_block_number": row["registration_block_number"],
    }


def _actor(chain: BlockchainClient, address: str) -> dict[str, str]:
    return {
        "role": chain.role_for_address(address),
        "wallet": address,
    }


app = create_app()
