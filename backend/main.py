import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import qrcode
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from web3 import Web3

from .auth import AuthService, authenticated_user, require_roles, safe_user, seed_demo_users
from .blockchain_client import BlockchainClient, BlockchainUnavailable
from .database import ProductRepository
from .domain import (
    ApprovalStatus,
    ContextType,
    DEFAULT_PRODUCT_SPECIFICATION_CODE,
    EvidenceDocumentType,
    EvidenceVerificationStatus,
    EvidenceVisibility,
    InspectionResult,
    PRODUCT_CATEGORY,
    PRODUCT_SUBCATEGORY,
    PRODUCT_TYPE,
    IssuerTrustStatus,
    QualityChangeStatus,
    QualityChangeType,
    SaleStatus,
    SupplyChainStage,
    UserRole,
)
from .evidence import MAX_UPLOAD_BYTES, EvidenceStore, EvidenceValidationError
from .metadata_hash import canonical_metadata, metadata_hash, product_key, product_metadata
from .presentation_demo import PresentationDemoError, PresentationDemoSeeder
from .quality_service import QualityGateError, QualityService


STATIC_DIR = Path(__file__).with_name("static")


class RawMaterialRequest(BaseModel):
    internal_batch_id: str = Field(min_length=1, max_length=80)
    material_name: str = Field(min_length=1, max_length=160)
    material_category: str = Field(min_length=1, max_length=80)
    supplier_name: str = Field(min_length=1, max_length=160)
    supplier_identifier: str | None = Field(default=None, max_length=80)
    supplier_lot_number: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    manufacturing_date: date | None = None
    received_date: date
    expiry_retest_date: date | None = None
    country_source: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class ProductRegistrationRequest(BaseModel):
    product_code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(default="Aurelia Prestige Renewal Serum", min_length=1, max_length=180)
    brand: str = Field(default="Aurelia Maison", min_length=1, max_length=160)
    batch_number: str = Field(default="APR-2026-001", min_length=1, max_length=80)
    description: str = Field(default="Luxury anti-aging facial serum demonstration batch", min_length=1, max_length=1000)
    category: str = PRODUCT_CATEGORY
    subcategory: str = PRODUCT_SUBCATEGORY
    product_type: str = PRODUCT_TYPE
    manufactured_date: date | None = None
    expiry_date: date | None = None
    raw_material_batch_ids: list[str] = Field(default_factory=list)
    specification_code: str = Field(default=DEFAULT_PRODUCT_SPECIFICATION_CODE, min_length=1, max_length=120)


class OwnershipTransferRequest(BaseModel):
    product_code: str = Field(..., min_length=1)
    to_role: str = Field(..., min_length=1)


class QualityResultRequest(BaseModel):
    context_type: ContextType
    context_id: str = Field(min_length=1)
    standard_id: int = Field(gt=0)
    result: InspectionResult
    notes: str | None = Field(default=None, max_length=1000)


class StageApprovalRequest(BaseModel):
    context_type: ContextType
    context_id: str = Field(min_length=1)
    stage: SupplyChainStage


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class IssuerStatusRequest(BaseModel):
    trust_status: IssuerTrustStatus
    reason: str = Field(min_length=3, max_length=500)


class QualityChangeRequest(BaseModel):
    change_type: QualityChangeType
    target_type: str = Field(min_length=1, max_length=80)
    target_code: str = Field(min_length=1, max_length=160)
    previous_version: str | None = Field(default=None, max_length=40)
    new_version: str | None = Field(default=None, max_length=40)
    change_summary: str = Field(min_length=3, max_length=500)
    reason: str = Field(min_length=3, max_length=1000)
    status: QualityChangeStatus = QualityChangeStatus.APPROVED


STAGE_ACTOR = {
    SupplyChainStage.RAW_MATERIAL_SUPPLIER: UserRole.RAW_MATERIAL_SUPPLIER,
    SupplyChainStage.MANUFACTURER: UserRole.MANUFACTURER,
    SupplyChainStage.DISTRIBUTOR: UserRole.DISTRIBUTOR,
    SupplyChainStage.RETAILER: UserRole.RETAILER,
}


def _require_stage_actor(user: dict[str, Any], stage: SupplyChainStage) -> None:
    required = STAGE_ACTOR[stage]
    if user["role"] != required.value:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "You do not have permission to perform this action.",
                "required_roles": [required.value],
                "guidance": f"This quality operation is restricted to the {required.value.replace('_', ' ').title()} role.",
            },
        )


def _require_valid_quality_context(
    repo: ProductRepository,
    context_type: ContextType,
    context_id: str,
    stage: SupplyChainStage,
    *,
    require_current_stage: bool = False,
) -> dict[str, Any]:
    """Validate quality context/stage compatibility and write custody."""
    context_id = context_id.strip()
    if not context_id:
        raise HTTPException(status_code=422, detail="Quality-check context ID is required")
    if context_type == ContextType.RAW_MATERIAL:
        if stage != SupplyChainStage.RAW_MATERIAL_SUPPLIER:
            raise HTTPException(
                status_code=422,
                detail="Raw-material batches can only use the raw-material quality stage",
            )
        material = repo.get_raw_material(context_id)
        if not material:
            raise HTTPException(status_code=404, detail="Quality-check context not found")
        return material

    if stage == SupplyChainStage.RAW_MATERIAL_SUPPLIER:
        raise HTTPException(
            status_code=422,
            detail="Finished products cannot use the raw-material quality stage",
        )
    product = repo.get_product(context_id)
    if not product:
        raise HTTPException(status_code=404, detail="Quality-check context not found")
    if require_current_stage and product["current_stage"] != stage.value:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Product custody is {product['current_stage']}; "
                f"{stage.value} quality records cannot be changed at this stage."
            ),
        )
    return product


def _audit(
    repo: ProductRepository,
    user: dict[str, Any],
    action: str,
    entity_type: str,
    entity_id: str | None,
    *,
    result: str = "SUCCESS",
    metadata: dict[str, Any] | None = None,
) -> None:
    repo.add_audit_event(
        {
            "actor_user_id": user["id"],
            "actor_role": user["role"],
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "result": result,
            "metadata": metadata or {},
        }
    )


def create_app(
    repository: ProductRepository | None = None,
    blockchain: BlockchainClient | None = None,
    evidence_store: EvidenceStore | None = None,
    auth_service: AuthService | None = None,
) -> FastAPI:
    repo = repository or ProductRepository()
    chain = blockchain or BlockchainClient()
    store = evidence_store or EvidenceStore()
    auth = auth_service or AuthService()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        repo.init_db()
        seed_demo_users(repo)
        yield

    app = FastAPI(
        title="OriginChain Luxury Cosmetics Demo API",
        description="Educational quality assurance and traceability demo; not a regulatory compliance system.",
        version="0.4.0",
        lifespan=lifespan,
    )
    app.state.repository = repo
    app.state.blockchain = chain
    app.state.evidence_store = store
    app.state.quality = QualityService(repo, store)
    app.state.auth = auth
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        return {"api_status": "ok", **request.app.state.blockchain.health()}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, request: Request) -> dict[str, Any]:
        repo = request.app.state.repository
        user = repo.get_user_by_username(payload.username)
        if (
            not user
            or not user["active"]
            or not request.app.state.auth.verify_password(payload.password, user["password_hash"])
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = request.app.state.auth.create_access_token(user)
        _audit(repo, user, "LOGIN_SUCCESS", "USER", user["id"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": request.app.state.auth.access_token_minutes * 60,
            "user": safe_user(user),
        }

    @app.get("/api/auth/me")
    def auth_me(user: dict[str, Any] = Depends(authenticated_user)) -> dict[str, Any]:
        return safe_user(user)

    @app.get("/api/demo/catalog")
    def catalog() -> dict[str, Any]:
        return {
            "notice": "Fictional educational demonstration data only.",
            "product": {
                "brand": "Aurelia Maison",
                "name": "Aurelia Prestige Renewal Serum",
                "product_code": "OC-LUX-SERUM-0001",
                "batch_number": "APR-2026-001",
                "category": PRODUCT_CATEGORY,
                "subcategory": PRODUCT_SUBCATEGORY,
                "product_type": PRODUCT_TYPE,
            },
            "categories": {
                "SKINCARE": ["FACIAL_SERUM", "MOISTURIZER", "EYE_CREAM", "CLEANSER"],
                "MAKEUP": ["FOUNDATION", "LIPSTICK", "CONCEALER"],
                "FRAGRANCE": ["EAU_DE_PARFUM", "PARFUM"],
            },
            "implemented_workflow": "SKINCARE / FACIAL_SERUM / ANTI_AGING_SERUM",
        }

    @app.get("/api/qr/{product_code}")
    def product_qr(product_code: str) -> Response:
        image = qrcode.make(product_code.strip())
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return Response(content=buffer.getvalue(), media_type="image/png")

    @app.post("/api/raw-materials", status_code=201)
    def create_raw_material(
        payload: RawMaterialRequest,
        request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.RAW_MATERIAL_SUPPLIER)),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        repo.init_db()
        item = payload.model_dump(mode="json")
        item["id"] = f"rm_{uuid4().hex}"
        item["created_by_user_id"] = user["id"]
        for field in ("internal_batch_id", "material_name", "material_category", "supplier_name", "supplier_lot_number", "unit"):
            item[field] = item[field].strip()
        if any(not item[field] for field in (
            "internal_batch_id", "material_name", "material_category",
            "supplier_name", "supplier_lot_number", "unit",
        )):
            raise HTTPException(status_code=422, detail="Required text fields cannot be blank")
        if payload.manufacturing_date and payload.manufacturing_date > payload.received_date:
            raise HTTPException(
                status_code=422,
                detail="Manufacturing date cannot be after the received date",
            )
        if payload.expiry_retest_date and payload.expiry_retest_date < payload.received_date:
            raise HTTPException(
                status_code=422,
                detail="Expiry/retest date cannot be before the received date",
            )
        try:
            created = repo.create_raw_material(item)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Raw-material internal batch ID already exists") from exc
        _audit(repo, user, "RAW_MATERIAL_REGISTERED", "RAW_MATERIAL", created["id"])
        return created

    @app.get("/api/raw-materials")
    def list_raw_materials(
        request: Request, _user: dict[str, Any] = Depends(authenticated_user)
    ) -> list[dict[str, Any]]:
        request.app.state.repository.init_db()
        return request.app.state.repository.list_raw_materials()

    @app.get("/api/raw-materials/{material_id}")
    def get_raw_material(
        material_id: str, request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        item = request.app.state.repository.get_raw_material(material_id)
        if not item:
            raise HTTPException(status_code=404, detail="Raw-material batch not found")
        return item

    @app.get("/api/products")
    def list_products(
        request: Request, _user: dict[str, Any] = Depends(authenticated_user)
    ) -> list[dict[str, Any]]:
        repo = request.app.state.repository
        return [_operational_product(item, repo) for item in repo.list_products()]

    @app.get("/api/product-specifications")
    def product_specifications(
        request: Request,
        approved_only: bool = Query(default=False),
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.product_specifications(approved_only=approved_only)

    @app.get("/api/product-specifications/{specification_code}")
    def product_specification(
        specification_code: str, request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        specification = request.app.state.repository.get_product_specification(specification_code)
        if not specification:
            raise HTTPException(status_code=404, detail="Product specification not found")
        return specification

    @app.post("/api/products/register")
    def register_product(
        payload: ProductRegistrationRequest,
        request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.MANUFACTURER)),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        chain = request.app.state.blockchain
        repo.init_db()
        code = payload.product_code.strip()
        text_values = {
            "product code": code,
            "name": payload.name.strip(),
            "brand": payload.brand.strip(),
            "batch number": payload.batch_number.strip(),
            "description": payload.description.strip(),
        }
        blank_fields = [name for name, value in text_values.items() if not value]
        if blank_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Required fields cannot be blank: {', '.join(blank_fields)}",
            )
        if (
            payload.category != PRODUCT_CATEGORY
            or payload.subcategory != PRODUCT_SUBCATEGORY
            or payload.product_type != PRODUCT_TYPE
        ):
            raise HTTPException(
                status_code=422,
                detail="Only the implemented skincare/facial-serum/anti-aging-serum workflow is supported",
            )
        if payload.manufactured_date and payload.expiry_date and payload.manufactured_date > payload.expiry_date:
            raise HTTPException(
                status_code=422,
                detail="Manufactured date cannot be after the expiry date",
            )
        material_ids = [item.strip() for item in payload.raw_material_batch_ids if item.strip()]
        if not material_ids:
            raise HTTPException(
                status_code=422,
                detail="At least one approved raw-material batch must be linked",
            )
        if len(material_ids) != len(payload.raw_material_batch_ids) or len(set(material_ids)) != len(material_ids):
            raise HTTPException(
                status_code=422,
                detail="Raw-material batch selections must be non-blank and unique",
            )
        if repo.get_product(code):
            raise HTTPException(status_code=409, detail="Product already exists in local database")
        specification = repo.get_product_specification(payload.specification_code.strip())
        if not specification:
            raise HTTPException(status_code=422, detail="Product specification was not found")
        if specification["product_type"] != payload.product_type:
            raise HTTPException(status_code=422, detail="Product specification does not match the product type")
        if not specification["active"] or specification["status"] != "APPROVED":
            raise HTTPException(status_code=409, detail="Only an active approved product specification can be assigned")
        today = date.today()
        if specification.get("effective_from") and date.fromisoformat(specification["effective_from"]) > today:
            raise HTTPException(status_code=409, detail="Product specification is not yet effective")
        if specification.get("effective_until") and date.fromisoformat(specification["effective_until"]) < today:
            raise HTTPException(status_code=409, detail="Product specification is no longer effective")
        materials = []
        for material_id in material_ids:
            material = repo.get_raw_material(material_id)
            if not material:
                raise HTTPException(status_code=422, detail=f"Raw-material batch {material_id} was not found")
            if material.get("expiry_retest_date") and date.fromisoformat(material["expiry_retest_date"]) < date.today():
                raise HTTPException(
                    status_code=409,
                    detail=f"Raw-material batch {material['internal_batch_id']} is past its expiry/retest date",
                )
            approval = repo.get_stage_approval(
                ContextType.RAW_MATERIAL.value,
                material_id,
                SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
            )
            quality_summary = request.app.state.quality.summary(
                ContextType.RAW_MATERIAL,
                material_id,
                SupplyChainStage.RAW_MATERIAL_SUPPLIER,
            )
            if (
                material["quality_status"] != ApprovalStatus.APPROVED.value
                or not approval
                or approval["status"] != ApprovalStatus.APPROVED.value
                or not quality_summary["eligible_for_approval"]
            ):
                raise HTTPException(status_code=409, detail=f"Raw-material batch {material['internal_batch_id']} is not approved")
            materials.append(material)
        metadata = product_metadata(
            product_code=code, name=payload.name.strip(), brand=payload.brand.strip(),
            batch_number=payload.batch_number.strip(), description=payload.description.strip(),
        )
        product_key_value = product_key(code)
        metadata_hash_value = metadata_hash(metadata)
        lineage_snapshot = [
            {
                "id": item["id"], "batch": item["internal_batch_id"],
                "material": item["material_name"], "quality_status": item["quality_status"],
                "quality_commitment": (
                    repo.get_stage_approval(ContextType.RAW_MATERIAL.value, item["id"], SupplyChainStage.RAW_MATERIAL_SUPPLIER.value) or {}
                ).get("commitment_hash"),
            }
            for item in sorted(materials, key=lambda value: value["id"])
        ]
        lineage_hash = Web3.to_hex(Web3.keccak(text=canonical_metadata(lineage_snapshot)))
        try:
            receipt = chain.register_product(product_key_value, metadata_hash_value)
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain registration failed: {exc}") from exc
        repo.create_product(
            {
                "product_code": code, "name": metadata["name"], "brand": metadata["brand"],
                "batch_number": metadata["batch_number"], "description": metadata["description"],
                "metadata_json": canonical_metadata(metadata), "product_key": product_key_value,
                "metadata_hash": metadata_hash_value, "registration_tx_hash": receipt["transaction_hash"],
                "registration_block_number": receipt["block_number"], "category": payload.category,
                "subcategory": payload.subcategory, "product_type": payload.product_type,
                "manufactured_date": str(payload.manufactured_date) if payload.manufactured_date else None,
                "expiry_date": str(payload.expiry_date) if payload.expiry_date else None,
                "lineage_hash": lineage_hash,
                "registered_by_user_id": user["id"],
                "specification_code": specification["specification_code"],
                "specification_version": specification["version"],
                "specification_snapshot_hash": specification["snapshot_hash"],
                "specification_assigned_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if materials:
            repo.link_raw_materials(code, [item["id"] for item in materials])
        _audit(
            repo, user, "PRODUCT_REGISTERED", "PRODUCT", code,
            metadata={
                "linked_raw_materials": len(materials),
                "specification_code": specification["specification_code"],
                "specification_version": specification["version"],
            },
        )
        return {
            "product_code": code, "product_key": product_key_value,
            "metadata_hash": metadata_hash_value, "lineage_hash": lineage_hash,
            "linked_raw_materials": len(materials),
            "product_specification": {
                "specification_code": specification["specification_code"],
                "specification_name": specification["specification_name"],
                "version": specification["version"],
                "snapshot_hash": specification["snapshot_hash"],
            },
            "manufacturer_wallet": chain.demo_roles()["MANUFACTURER"],
            "transaction_hash": receipt["transaction_hash"], "block_number": receipt["block_number"],
            "blockchain_registered": True,
        }

    @app.get("/api/quality/standards")
    def quality_standards(
        request: Request,
        stage: SupplyChainStage = Query(...),
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.quality_standards(stage.value)

    @app.get("/api/quality/sources")
    def quality_sources(
        request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.quality_sources()

    @app.get("/api/quality/sources/{source_code}")
    def quality_source(
        source_code: str,
        request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        source = request.app.state.repository.get_quality_source(source_code)
        if not source:
            raise HTTPException(status_code=404, detail="Quality source not found")
        return source

    @app.get("/api/quality/profiles")
    def quality_profiles(
        request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.quality_profiles()

    @app.get("/api/quality/profiles/{profile_code}")
    def quality_profile(
        profile_code: str,
        request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        profile = request.app.state.repository.get_quality_profile(profile_code)
        if not profile:
            raise HTTPException(status_code=404, detail="Quality profile not found")
        return profile

    @app.get("/api/evidence/issuers")
    def evidence_issuers(
        request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.evidence_issuers()

    @app.get("/api/evidence/issuers/{issuer_code}")
    def evidence_issuer(
        issuer_code: str, request: Request,
        _user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        issuer = request.app.state.repository.get_evidence_issuer(issuer_code)
        if not issuer:
            raise HTTPException(status_code=404, detail="Evidence issuer not found")
        return issuer

    @app.post("/api/evidence/issuers/{issuer_code}/status")
    def update_evidence_issuer_status(
        issuer_code: str, payload: IssuerStatusRequest, request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        previous = repo.get_evidence_issuer(issuer_code)
        if not previous:
            raise HTTPException(status_code=404, detail="Evidence issuer not found")
        if len(payload.reason.strip()) < 3:
            raise HTTPException(status_code=422, detail="A meaningful change-control reason is required")
        updated = repo.update_evidence_issuer_status(issuer_code, payload.trust_status.value)
        change = repo.add_quality_change_record({
            "id": f"chg_{uuid4().hex}", "change_type": "ISSUER_UPDATE",
            "target_type": "EVIDENCE_ISSUER", "target_code": issuer_code,
            "previous_version": previous["trust_status"], "new_version": payload.trust_status.value,
            "change_summary": f"Issuer trust status changed to {payload.trust_status.value}.",
            "reason": payload.reason.strip(), "requested_by_user_id": user["id"],
            "approved_by_user_id": user["id"], "status": "IMPLEMENTED",
        })
        _audit(
            repo, user, "ISSUER_STATUS_CHANGED", "EVIDENCE_ISSUER", issuer_code,
            metadata={"previous": previous["trust_status"], "current": updated["trust_status"], "change_id": change["id"]},
        )
        return updated

    @app.get("/api/quality/source-reviews")
    def source_reviews(
        request: Request,
        _user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.source_reviews()

    @app.get("/api/quality/change-records")
    def quality_change_records(
        request: Request,
        limit: int = Query(default=100, ge=1, le=200),
        _user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.quality_change_records(limit)

    @app.post("/api/quality/change-records", status_code=201)
    def create_quality_change_record(
        payload: QualityChangeRequest, request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> dict[str, Any]:
        if len(payload.reason.strip()) < 3 or len(payload.change_summary.strip()) < 3:
            raise HTTPException(status_code=422, detail="A meaningful change summary and reason are required")
        record = request.app.state.repository.add_quality_change_record({
            "id": f"chg_{uuid4().hex}", "change_type": payload.change_type.value,
            "target_type": payload.target_type.strip(), "target_code": payload.target_code.strip(),
            "previous_version": payload.previous_version, "new_version": payload.new_version,
            "change_summary": payload.change_summary.strip(), "reason": payload.reason.strip(),
            "requested_by_user_id": user["id"], "approved_by_user_id": user["id"],
            "status": payload.status.value,
        })
        _audit(
            request.app.state.repository, user, "QUALITY_CHANGE_APPROVED", "QUALITY_CHANGE", record["id"],
            metadata={"change_type": record["change_type"], "target_code": record["target_code"]},
        )
        return record

    @app.post("/api/quality/results")
    def submit_quality_result(
        payload: QualityResultRequest,
        request: Request,
        user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        standard = request.app.state.repository.get_standard(payload.standard_id)
        if not standard:
            raise HTTPException(status_code=422, detail="Unknown or inactive quality standard")
        stage = SupplyChainStage(standard["supply_chain_stage"])
        _require_stage_actor(user, stage)
        _require_valid_quality_context(
            request.app.state.repository,
            payload.context_type,
            payload.context_id,
            stage,
            require_current_stage=True,
        )
        context_id = payload.context_id.strip()
        try:
            saved = request.app.state.quality.submit_result(
                payload.context_type, context_id, payload.standard_id,
                payload.result, payload.notes, f"qr_{uuid4().hex}", user["id"],
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _audit(
            request.app.state.repository, user, "QUALITY_RESULT_SUBMITTED", "QUALITY_RESULT", saved["id"],
            metadata={
                "stage": stage.value, "result": payload.result.value,
                "standard_code": saved["standard_code"],
                "sources": [
                    {"source_code": source["source_code"], "edition": source["edition"]}
                    for source in saved.get("sources", [])
                ],
            },
        )
        return saved

    @app.get("/api/quality/{context_type}/{context_id}/summary")
    def quality_summary(
        context_type: ContextType, context_id: str, stage: SupplyChainStage,
        request: Request, user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        context_id = context_id.strip()
        _require_valid_quality_context(
            request.app.state.repository, context_type, context_id, stage
        )
        summary = request.app.state.quality.summary(context_type, context_id, stage)
        reveal_internal = user["role"] in {UserRole.ADMIN.value, STAGE_ACTOR[stage].value}
        return _safe_quality_summary(summary, request.app.state.evidence_store, reveal_internal)

    @app.post("/api/quality/stages/approve")
    def approve_stage(
        payload: StageApprovalRequest,
        request: Request,
        user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        quality = request.app.state.quality
        chain = request.app.state.blockchain
        _require_stage_actor(user, payload.stage)
        _require_valid_quality_context(
            repo,
            payload.context_type,
            payload.context_id,
            payload.stage,
            require_current_stage=True,
        )
        context_id = payload.context_id.strip()
        try:
            approval, commitment = quality.approve(
                payload.context_type, context_id, payload.stage, user["id"]
            )
        except QualityGateError as exc:
            if payload.context_type == ContextType.PRODUCT and payload.stage == SupplyChainStage.RETAILER:
                has_failure = any(check["result"] == InspectionResult.FAIL.value for check in exc.summary["checks"])
                repo.update_product_stage(
                    context_id, payload.stage.value,
                    SaleStatus.HOLD.value if has_failure else SaleStatus.NOT_READY.value,
                )
            _audit(
                repo, user, "STAGE_APPROVAL_BLOCKED", "QUALITY_STAGE", context_id,
                result="BLOCKED", metadata={"stage": payload.stage.value},
            )
            raise HTTPException(
                status_code=409,
                detail={"message": str(exc), "blocking_reasons": exc.summary["blocking_reasons"], "summary": exc.summary},
            ) from exc
        if payload.context_type == ContextType.PRODUCT:
            product = repo.get_product(context_id)
            try:
                receipt = chain.record_quality_stage(product["product_key"], payload.stage.value, 1, commitment)
            except Exception as exc:
                repo.set_stage_approval(
                    {
                        "context_type": payload.context_type.value, "context_id": context_id,
                        "stage": payload.stage.value, "status": ApprovalStatus.HOLD.value,
                        "commitment_hash": commitment,
                        "blocking_reasons_json": json.dumps(["Blockchain quality commitment failed."]),
                        "approved_by_user_id": user["id"],
                    }
                )
                if payload.stage == SupplyChainStage.RETAILER:
                    repo.update_product_stage(context_id, payload.stage.value, SaleStatus.HOLD.value)
                raise HTTPException(status_code=502, detail=f"Blockchain quality commitment failed: {exc}") from exc
            approval = repo.set_stage_approval(
                {
                    **approval,
                    "context_type": payload.context_type.value, "context_id": context_id,
                    "stage": payload.stage.value, "status": ApprovalStatus.APPROVED.value,
                    "commitment_hash": commitment, "blocking_reasons_json": "[]",
                    "blockchain_tx_hash": receipt["transaction_hash"],
                    "blockchain_block_number": receipt["block_number"],
                    "approved_by_user_id": user["id"],
                }
            )
        _audit(
            repo, user, "STAGE_APPROVED", "QUALITY_STAGE", context_id,
            metadata={"stage": payload.stage.value},
        )
        return {
            "approval": approval,
            "summary": _safe_quality_summary(
                quality.summary(payload.context_type, context_id, payload.stage),
                request.app.state.evidence_store,
                True,
            ),
        }

    @app.post("/api/quality/results/{result_id}/evidence", status_code=201)
    async def upload_evidence(
        result_id: str, request: Request,
        visibility: EvidenceVisibility = Form(EvidenceVisibility.INTERNAL),
        document_type: EvidenceDocumentType | None = Form(None),
        laboratory_name: str | None = Form(None),
        report_reference: str | None = Form(None),
        test_date: date | None = Form(None),
        test_method_source_code: str | None = Form(None),
        result_summary: str | None = Form(None),
        accreditation_status_text: str | None = Form(None),
        document_notes: str | None = Form(None),
        issuer_code: str | None = Form(None),
        issuer_report_number: str | None = Form(None),
        issuer_document_date: date | None = Form(None),
        file: UploadFile = File(...),
        user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        result = repo.get_quality_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Quality result not found")
        stage = SupplyChainStage(result["supply_chain_stage"])
        _require_stage_actor(user, stage)
        _require_valid_quality_context(
            repo,
            ContextType(result["context_type"]),
            result["context_id"],
            stage,
            require_current_stage=True,
        )
        metadata_fields = {
            "laboratory_name": (laboratory_name, 180),
            "report_reference": (report_reference, 120),
            "test_method_source_code": (test_method_source_code, 120),
            "result_summary": (result_summary, 500),
            "accreditation_status_text": (accreditation_status_text, 300),
            "document_notes": (document_notes, 1000),
            "issuer_code": (issuer_code, 120),
            "issuer_report_number": (issuer_report_number, 160),
        }
        for field_name, (field_value, maximum) in metadata_fields.items():
            if field_value and len(field_value.strip()) > maximum:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field_name.replace('_', ' ').title()} exceeds {maximum} characters.",
                )
        if test_method_source_code and not repo.get_quality_source(test_method_source_code.strip()):
            raise HTTPException(status_code=422, detail="Test-method source is not registered.")
        resolved_document_type = document_type or EvidenceDocumentType(result["expected_document_type"])
        issuer = repo.get_evidence_issuer(issuer_code.strip()) if issuer_code else None
        if issuer_code and not issuer:
            raise HTTPException(status_code=422, detail="Evidence issuer is not registered.")
        allowed_issuer_types = {
            EvidenceDocumentType.CERTIFICATE_OF_ANALYSIS: {"SUPPLIER", "LABORATORY"},
            EvidenceDocumentType.MICROBIOLOGY_REPORT: {"LABORATORY"},
            EvidenceDocumentType.PRESERVATIVE_EFFICACY_REPORT: {"LABORATORY"},
        }.get(resolved_document_type)
        appropriate_type = bool(
            issuer and (not allowed_issuer_types or issuer["issuer_type"] in allowed_issuer_types)
        )
        report_number = (issuer_report_number or report_reference or "").strip() or None
        trusted_acceptance = bool(
            issuer and issuer["active"] and appropriate_type
            and issuer["trust_status"] == IssuerTrustStatus.TRUSTED_DEMO.value
            and (not result["trusted_issuer_required"] or report_number)
        )
        verification_status = (
            EvidenceVerificationStatus.VERIFIED_DEMO.value
            if trusted_acceptance else EvidenceVerificationStatus.UNVERIFIED.value
        )
        verification_notes = (
            "Accepted by OriginChain's local demo issuer/reference controls; no external accreditation or certification is claimed."
            if trusted_acceptance
            else "Not accepted by the demo issuer/reference controls; issuer, trust, type, or report reference is missing or unsuitable."
        )
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        try:
            stored_name, digest = request.app.state.evidence_store.save(
                SupplyChainStage(result["supply_chain_stage"]), file.filename or "", file.content_type or "", data
            )
        except EvidenceValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        receipt = {"transaction_hash": None, "block_number": None}
        if result["context_type"] == ContextType.PRODUCT.value:
            product = repo.get_product(result["context_id"])
            try:
                receipt = request.app.state.blockchain.record_evidence_hash(
                    product["product_key"], result["supply_chain_stage"], digest
                )
            except Exception as exc:
                request.app.state.evidence_store.delete(stored_name)
                raise HTTPException(status_code=502, detail=f"Blockchain evidence commitment failed: {exc}") from exc
        evidence = repo.add_evidence(
            {
                "id": f"ev_{uuid4().hex}", "quality_result_id": result_id,
                "original_filename": Path(file.filename or "evidence").name,
                "stored_filename": stored_name, "content_type": file.content_type,
                "file_size": len(data), "file_hash": digest,
                "uploader_stage": result["supply_chain_stage"], "visibility": visibility.value,
                "blockchain_tx_hash": receipt["transaction_hash"],
                "blockchain_block_number": receipt["block_number"],
                "uploaded_by_user_id": user["id"],
                "document_type": resolved_document_type.value,
                "laboratory_name": laboratory_name.strip() if laboratory_name else None,
                "report_reference": report_reference.strip() if report_reference else None,
                "test_date": str(test_date) if test_date else None,
                "test_method_source_code": test_method_source_code.strip() if test_method_source_code else None,
                "result_summary": result_summary.strip() if result_summary else None,
                "accreditation_status_text": accreditation_status_text.strip() if accreditation_status_text else None,
                "document_notes": document_notes.strip() if document_notes else None,
                "issuer_id": issuer["id"] if issuer else None,
                "issuer_code_snapshot": issuer["issuer_code"] if issuer else None,
                "issuer_name_snapshot": issuer["issuer_name"] if issuer else None,
                "issuer_type_snapshot": issuer["issuer_type"] if issuer else None,
                "issuer_trust_status_at_submission": issuer["trust_status"] if issuer else None,
                "issuer_report_number": report_number,
                "issuer_document_date": str(issuer_document_date) if issuer_document_date else None,
                "verification_status": verification_status,
                "verified_by_user_id": user["id"] if trusted_acceptance else None,
                "verified_at": datetime.now(timezone.utc).isoformat() if trusted_acceptance else None,
                "verification_notes": verification_notes,
            }
        )
        repo.invalidate_stage_approval(
            result["context_type"], result["context_id"], result["supply_chain_stage"],
            ApprovalStatus.PENDING.value,
            "Supporting evidence changed; stage approval must be recorded again.",
        )
        if result["context_type"] == ContextType.RAW_MATERIAL.value:
            repo.update_raw_material_status(result["context_id"], ApprovalStatus.PENDING.value)
        elif result["supply_chain_stage"] == SupplyChainStage.RETAILER.value:
            stage_summary = request.app.state.quality.summary(
                ContextType.PRODUCT, result["context_id"], SupplyChainStage.RETAILER
            )
            has_failure = any(
                check["required"] and check["result"] == InspectionResult.FAIL.value
                for check in stage_summary["checks"]
            )
            repo.update_product_stage(
                result["context_id"], SupplyChainStage.RETAILER.value,
                SaleStatus.HOLD.value if has_failure else SaleStatus.NOT_READY.value,
            )
        _audit(
            repo, user, "EVIDENCE_UPLOADED", "EVIDENCE", evidence["id"],
            metadata={
                "stage": stage.value, "visibility": visibility.value,
                "document_type": resolved_document_type.value,
                "issuer_code": issuer["issuer_code"] if issuer else None,
                "evidence_verification": verification_status,
            },
        )
        return {**_evidence_view(evidence, request.app.state.evidence_store), "on_chain": bool(receipt["transaction_hash"])}

    @app.get("/api/evidence/{evidence_id}/integrity")
    def evidence_integrity(
        evidence_id: str, request: Request,
        user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        evidence = request.app.state.repository.get_evidence(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence record not found")
        stage = SupplyChainStage(evidence["uploader_stage"])
        if user["role"] not in {UserRole.ADMIN.value, STAGE_ACTOR[stage].value}:
            _require_stage_actor(user, stage)
        return _evidence_view(evidence, request.app.state.evidence_store)

    @app.post("/api/ownership-transfers")
    def transfer_ownership(
        payload: OwnershipTransferRequest,
        request: Request,
        user: dict[str, Any] = Depends(authenticated_user),
    ) -> dict[str, Any]:
        repo = request.app.state.repository
        chain = request.app.state.blockchain
        code = payload.product_code.strip()
        product = repo.get_product(code)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found in local database")
        target = payload.to_role.strip().upper()
        expected_target = {
            UserRole.MANUFACTURER.value: UserRole.DISTRIBUTOR.value,
            UserRole.DISTRIBUTOR.value: UserRole.RETAILER.value,
        }.get(user["role"])
        if target != expected_target:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "You do not have permission to perform this transfer.",
                    "required_roles": [
                        UserRole.MANUFACTURER.value if target == UserRole.DISTRIBUTOR.value
                        else UserRole.DISTRIBUTOR.value
                    ],
                    "guidance": "Transfers must be initiated by the authenticated current-stage actor.",
                },
            )
        if product["current_stage"] != user["role"]:
            raise HTTPException(
                status_code=409,
                detail=f"Product custody is {product['current_stage']}; the {user['role']} actor cannot transfer it.",
            )
        required_stage = {
            "DISTRIBUTOR": SupplyChainStage.MANUFACTURER,
            "RETAILER": SupplyChainStage.DISTRIBUTOR,
        }.get(target)
        if required_stage is None:
            raise HTTPException(status_code=422, detail="Unsupported transfer target")
        try:
            request.app.state.quality.require_approved(code, required_stage)
        except QualityGateError as exc:
            raise HTTPException(status_code=409, detail={"message": str(exc), "blocking_reasons": exc.summary["blocking_reasons"]}) from exc
        try:
            receipt = chain.transfer_ownership(product["product_key"], target)
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain transfer failed: {exc}") from exc
        repo.add_transfer({"product_code": code, **receipt, "initiated_by_user_id": user["id"]})
        repo.update_product_stage(code, target)
        _audit(
            repo, user, "OWNERSHIP_TRANSFERRED", "PRODUCT", code,
            metadata={"from_role": user["role"], "to_role": target},
        )
        return receipt

    @app.get("/api/verify/{product_code}")
    def verify_product(product_code: str, request: Request) -> dict[str, Any]:
        repo = request.app.state.repository
        chain = request.app.state.blockchain
        product = repo.get_product(product_code.strip())
        if not product:
            return {
                "status": "NOT_FOUND", "product_code": product_code,
                "blockchain_verified": False, "metadata_integrity": False,
                "message": "No off-chain product metadata found.",
            }
        try:
            blockchain_product = chain.get_product(product["product_key"])
            history = chain.get_ownership_history(product["product_key"])
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Blockchain verification failed: {exc}") from exc
        if not blockchain_product["exists"]:
            return {
                "status": "NOT_FOUND", "product_code": product["product_code"],
                "blockchain_verified": False, "metadata_integrity": False,
                "product": _public_product(product),
                "message": "Product metadata exists locally, but the product is not registered on-chain.",
            }
        recomputed_hash = metadata_hash(_metadata_from_row(product))
        integrity = recomputed_hash.lower() == blockchain_product["metadata_hash"].lower()
        journey = _quality_journey(repo, request.app.state.quality, product)
        public_evidence = [
            _public_evidence(item, request.app.state.evidence_store)
            for item in repo.evidence_for_context(ContextType.PRODUCT.value, product["product_code"], True)
        ]
        all_evidence = repo.evidence_for_context(ContextType.PRODUCT.value, product["product_code"])
        all_integrities = [
            request.app.state.evidence_store.integrity(item["stored_filename"], item["file_hash"]).value
            for item in all_evidence
        ]
        return {
            "status": "GENUINE" if integrity else "SUSPICIOUS",
            "product_code": product["product_code"], "blockchain_verified": True,
            "metadata_integrity": integrity, "final_sale_status": product["final_sale_status"],
            "approved_for_sale": product["final_sale_status"] == SaleStatus.APPROVED_FOR_SALE.value,
            "current_stage": product["current_stage"], "product": _public_product(product),
            "quality_journey": journey, "public_evidence": public_evidence,
            "document_integrity": _document_integrity(journey, all_integrities),
            "manufacturer": _public_actor(chain, blockchain_product["manufacturer"]),
            "current_owner": _public_actor(chain, blockchain_product["current_owner"]),
            "ownership_history": [_public_actor(chain, address) for address in history],
            "provenance": {"raw_material_batches": len(repo.product_raw_materials(product["product_code"])), "lineage_hash": product["lineage_hash"]},
            "blockchain": {
                **chain.network_info(), "product_key": product["product_key"],
                "metadata_hash": blockchain_product["metadata_hash"],
                "recomputed_metadata_hash": recomputed_hash,
                "registered_at": blockchain_product["registered_at"],
                "transfer_count": blockchain_product["transfer_count"],
                "registration_tx_hash": product["registration_tx_hash"],
                "registration_block_number": product["registration_block_number"],
            },
        }

    @app.post("/api/demo/tamper/{product_code}")
    def tamper_product(
        product_code: str, request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> dict[str, Any]:
        product = request.app.state.repository.tamper_product(product_code.strip())
        if not product:
            raise HTTPException(status_code=404, detail="Product not found in local database")
        _audit(
            request.app.state.repository, user, "DEMO_METADATA_TAMPERED", "PRODUCT",
            product["product_code"],
        )
        return {
            "warning": "DEMO ONLY - NOT PRODUCTION",
            "message": "Off-chain metadata changed; the immutable blockchain hash was not updated.",
            "product_code": product["product_code"], "modified_fields": ["brand", "description"],
            "product": _public_product(product),
        }

    @app.post("/api/demo/reset")
    def reset_demo(
        request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> dict[str, Any]:
        request.app.state.repository.init_db()
        request.app.state.repository.reset_demo()
        removed = request.app.state.evidence_store.clear_demo_files()
        _audit(
            request.app.state.repository, user, "DEMO_RESET", "DEMO", "local",
            metadata={"uploads_removed": removed, "blockchain_reset": False},
        )
        return {
            "warning": "DEMO ONLY - NOT PRODUCTION",
            "message": "Local SQLite data and demo uploads were cleared. Blockchain state is unchanged.",
            "uploads_removed": removed,
        }

    @app.post("/api/demo/presentation-seed")
    def seed_presentation_demo(
        request: Request,
        user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> dict[str, Any]:
        try:
            result = PresentationDemoSeeder(
                request.app.state.repository,
                request.app.state.blockchain,
                request.app.state.evidence_store,
            ).seed()
        except BlockchainUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PresentationDemoError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Presentation data could not be loaded: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Presentation blockchain operation failed: {exc}",
            ) from exc
        _audit(
            request.app.state.repository,
            user,
            "PRESENTATION_DEMO_LOADED",
            "DEMO",
            result["product_code"],
            metadata={
                "already_loaded": result["already_loaded"],
                "final_sale_status": result["final_sale_status"],
            },
        )
        return result

    @app.get("/api/audit")
    def audit_events(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        _user: dict[str, Any] = Depends(require_roles(UserRole.ADMIN)),
    ) -> list[dict[str, Any]]:
        return request.app.state.repository.list_audit_events(limit)

    return app


def _metadata_from_row(row: dict[str, Any]) -> dict[str, str]:
    return product_metadata(
        product_code=row["product_code"], name=row["name"], brand=row["brand"],
        batch_number=row["batch_number"], description=row["description"],
    )


def _public_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_code": row["product_code"], "name": row["name"], "brand": row["brand"],
        "batch_number": row["batch_number"], "description": row["description"],
        "category": row.get("category", PRODUCT_CATEGORY),
        "subcategory": row.get("subcategory", PRODUCT_SUBCATEGORY),
        "product_type": row.get("product_type", PRODUCT_TYPE),
        "manufactured_date": row.get("manufactured_date"), "expiry_date": row.get("expiry_date"),
        "metadata_json": json.loads(row["metadata_json"]),
        "registration_tx_hash": row["registration_tx_hash"],
        "registration_block_number": row["registration_block_number"],
        "product_configuration": {
            "verified_against_recorded_specification": bool(row.get("specification_code")),
            "specification_version": row.get("specification_version"),
        },
    }


def _operational_product(row: dict[str, Any], repo: ProductRepository) -> dict[str, Any]:
    assigned_specification = (
        repo.get_product_specification(row["specification_code"])
        if row.get("specification_code") else None
    )
    return {
        **_public_product(row),
        "current_stage": row["current_stage"],
        "final_sale_status": row["final_sale_status"],
        "product_specification": (
            {
                "specification_code": row.get("specification_code"),
                "version": row.get("specification_version"),
                "snapshot_hash": row.get("specification_snapshot_hash"),
                "assigned_at": row.get("specification_assigned_at"),
                "specification_name": assigned_specification["specification_name"] if assigned_specification else None,
            }
            if row.get("specification_code") else None
        ),
        "linked_raw_materials": [
            {
                "id": material["id"],
                "material_name": material["material_name"],
                "internal_batch_id": material["internal_batch_id"],
                "quality_status": material["quality_status"],
                "expiry_retest_date": material.get("expiry_retest_date"),
            }
            for material in repo.product_raw_materials(row["product_code"])
        ],
    }


def _public_actor(chain: BlockchainClient, address: str) -> dict[str, str]:
    return {"role": chain.role_for_address(address)}


def _evidence_view(evidence: dict[str, Any], store: EvidenceStore) -> dict[str, Any]:
    return {
        "id": evidence["id"], "original_filename": evidence["original_filename"],
        "content_type": evidence["content_type"], "file_size": evidence["file_size"],
        "file_hash": evidence["file_hash"], "visibility": evidence["visibility"],
        "uploader_stage": evidence["uploader_stage"], "uploaded_at": evidence["uploaded_at"],
        "integrity": store.integrity(evidence["stored_filename"], evidence["file_hash"]).value,
        "blockchain_tx_hash": evidence.get("blockchain_tx_hash"),
        "document_type": evidence.get("document_type", EvidenceDocumentType.OTHER.value),
        "laboratory_name": evidence.get("laboratory_name"),
        "report_reference": evidence.get("report_reference"),
        "test_date": evidence.get("test_date"),
        "test_method_source_code": evidence.get("test_method_source_code"),
        "result_summary": evidence.get("result_summary"),
        "accreditation_status_text": evidence.get("accreditation_status_text"),
        "document_notes": evidence.get("document_notes"),
        "issuer": (
            {
                "issuer_code": evidence.get("issuer_code_snapshot"),
                "issuer_name": evidence.get("issuer_name_snapshot"),
                "issuer_type": evidence.get("issuer_type_snapshot"),
                "trust_status_at_submission": evidence.get("issuer_trust_status_at_submission"),
                "current_trust_status": evidence.get("issuer_current_trust_status"),
                "report_number": evidence.get("issuer_report_number"),
                "document_date": evidence.get("issuer_document_date"),
            }
            if evidence.get("issuer_code_snapshot") else None
        ),
        "verification_status": evidence.get("verification_status", EvidenceVerificationStatus.UNVERIFIED.value),
        "verification_notes": evidence.get("verification_notes"),
    }


def _safe_quality_summary(
    summary: dict[str, Any], store: EvidenceStore, reveal_internal: bool
) -> dict[str, Any]:
    checks = []
    for check in summary["checks"]:
        checks.append(
            {
                **check,
                "notes": check.get("notes") if reveal_internal else None,
                "evidence": (
                    [_evidence_view(item, store) for item in check.get("evidence", [])]
                    if reveal_internal
                    else [
                        {
                            "original_filename": "Restricted evidence",
                            "integrity": item.get("integrity", "VERIFIED"),
                            "visibility": "INTERNAL",
                        }
                        for item in check.get("evidence", [])
                    ]
                ),
            }
        )
    return {**summary, "checks": checks}


def _public_evidence(evidence: dict[str, Any], store: EvidenceStore) -> dict[str, Any]:
    return {
        "filename": evidence["original_filename"], "category": evidence["category"],
        "check_name": evidence["check_name"], "stage": evidence["inspector_stage"],
        "file_hash": evidence["file_hash"], "uploaded_at": evidence["uploaded_at"],
        "document_type": evidence.get("document_type", EvidenceDocumentType.OTHER.value),
        "issuer_name": evidence.get("issuer_name_snapshot"),
        "evidence_verification": evidence.get("verification_status", EvidenceVerificationStatus.UNVERIFIED.value),
        "integrity": store.integrity(evidence["stored_filename"], evidence["file_hash"]).value,
    }


def _quality_journey(repo: ProductRepository, quality: QualityService, product: dict[str, Any]) -> list[dict[str, Any]]:
    materials = repo.product_raw_materials(product["product_code"])
    raw_summaries = [
        quality.summary(
            ContextType.RAW_MATERIAL,
            item["id"],
            SupplyChainStage.RAW_MATERIAL_SUPPLIER,
        )
        for item in materials
    ]
    raw_passed = sum(
        item["quality_status"] == ApprovalStatus.APPROVED.value and summary["eligible_for_approval"]
        for item, summary in zip(materials, raw_summaries)
    )
    raw_approved = bool(materials) and raw_passed == len(materials)
    journey = [{
        "stage": SupplyChainStage.RAW_MATERIAL_SUPPLIER.value, "display_name": "Raw Materials",
        "status": ApprovalStatus.APPROVED.value if raw_approved else ApprovalStatus.PENDING.value,
        "required_passed": raw_passed,
        "required_total": len(materials), "approved_at": None,
    }]
    for stage in (SupplyChainStage.MANUFACTURER, SupplyChainStage.DISTRIBUTOR, SupplyChainStage.RETAILER):
        summary = quality.summary(ContextType.PRODUCT, product["product_code"], stage)
        journey.append({key: summary[key] for key in ("stage", "display_name", "status", "required_passed", "required_total", "approved_at")})
    return journey


def _document_integrity(journey: list[dict[str, Any]], integrities: list[str]) -> str:
    if any(item != "VERIFIED" for item in integrities):
        return "ATTENTION_REQUIRED"
    return "VERIFIED" if all(item["status"] == ApprovalStatus.APPROVED.value for item in journey) else "PENDING"


app = create_app()
