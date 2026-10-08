"""One-click, fully populated presentation fixture for the local demo only."""

from datetime import date, datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from .database import ProductRepository
from .domain import (
    ApprovalStatus,
    ContextType,
    DEFAULT_PRODUCT_SPECIFICATION_CODE,
    EvidenceVisibility,
    InspectionResult,
    SaleStatus,
    SupplyChainStage,
    UserRole,
)
from .evidence import EvidenceStore
from .metadata_hash import canonical_metadata, metadata_hash, product_key, product_metadata
from .quality_service import QualityGateError, QualityService


PRODUCT_CODE = "OC-LUX-SERUM-0001"
MATERIAL_ID = "rm_presentation_hyaluronic_acid"
_SEED_LOCK = Lock()


class PresentationDemoError(RuntimeError):
    pass


class PresentationDemoSeeder:
    def __init__(self, repository: ProductRepository, blockchain: Any, store: EvidenceStore):
        self.repository = repository
        self.blockchain = blockchain
        self.store = store
        self.quality = QualityService(repository, store)
        self.product_code = PRODUCT_CODE

    def seed(self) -> dict[str, Any]:
        with _SEED_LOCK:
            return self._seed()

    def _seed(self) -> dict[str, Any]:
        self.blockchain.require_ready()
        existing_products = self.repository.list_products()
        existing = self.repository.get_product(PRODUCT_CODE) or (
            existing_products[0] if existing_products else None
        )
        if existing:
            self.product_code = existing["product_code"]
        else:
            self.product_code = self._available_product_code()
        users = {
            name: self.repository.get_user_by_username(name)
            for name in ("supplier", "manufacturer", "distributor", "retailer")
        }
        if any(user is None for user in users.values()):
            raise PresentationDemoError("Seeded demo users are unavailable.")

        if existing:
            self._require_chain_alignment(existing)
            if self._is_complete(existing):
                return self._result(already_loaded=True)
            if existing["final_sale_status"] == SaleStatus.APPROVED_FOR_SALE.value:
                raise PresentationDemoError(
                    "The completed local presentation data no longer passes its quality or evidence "
                    "checks. Use Reset Local Demo Data, then load the presentation demo again."
                )
            materials = self.repository.product_raw_materials(self.product_code)
            if not materials:
                raise PresentationDemoError(
                    "The partial product has no linked raw material and cannot be completed safely."
                )
            for material in materials:
                summary = self.quality.summary(
                    ContextType.RAW_MATERIAL,
                    material["id"],
                    SupplyChainStage.RAW_MATERIAL_SUPPLIER,
                )
                approval = self.repository.get_stage_approval(
                    ContextType.RAW_MATERIAL.value,
                    material["id"],
                    SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
                )
                if (
                    material["quality_status"] != ApprovalStatus.APPROVED.value
                    or not approval
                    or approval["status"] != ApprovalStatus.APPROVED.value
                    or not summary["eligible_for_approval"]
                ):
                    self._complete_stage(
                        ContextType.RAW_MATERIAL,
                        material["id"],
                        SupplyChainStage.RAW_MATERIAL_SUPPLIER,
                        users["supplier"]["id"],
                        record_on_chain=False,
                    )
            self._finish_product(existing, users)
            return self._result(already_loaded=False)

        material = self.repository.get_raw_material_by_batch("HA-260801")
        if not material:
            material = self.repository.create_raw_material({
                "id": MATERIAL_ID,
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
                "notes": "TEST FIXTURE — FICTIONAL DEMO presentation material.",
                "created_by_user_id": users["supplier"]["id"],
            })
        material_summary = self.quality.summary(
            ContextType.RAW_MATERIAL,
            material["id"],
            SupplyChainStage.RAW_MATERIAL_SUPPLIER,
        )
        material_approval = self.repository.get_stage_approval(
            ContextType.RAW_MATERIAL.value,
            material["id"],
            SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
        )
        if (
            material["quality_status"] != ApprovalStatus.APPROVED.value
            or not material_approval
            or material_approval["status"] != ApprovalStatus.APPROVED.value
            or not material_summary["eligible_for_approval"]
        ):
            self._complete_stage(
                ContextType.RAW_MATERIAL, material["id"], SupplyChainStage.RAW_MATERIAL_SUPPLIER,
                users["supplier"]["id"], record_on_chain=False,
            )

        specification = self.repository.get_product_specification(DEFAULT_PRODUCT_SPECIFICATION_CODE)
        if not specification or not specification.get("active") or specification.get("status") != "APPROVED":
            raise PresentationDemoError(
                "The approved presentation product specification is unavailable."
            )
        metadata = product_metadata(
            product_code=self.product_code,
            name="Aurelia Prestige Renewal Serum",
            brand="Aurelia Maison",
            batch_number="APR-2026-001",
            description="Luxury anti-aging facial serum demonstration batch",
        )
        product_key_value = product_key(self.product_code)
        metadata_hash_value = metadata_hash(metadata)
        lineage_snapshot = [{
            "id": material["id"],
            "batch": material["internal_batch_id"],
            "material": material["material_name"],
            "quality_status": ApprovalStatus.APPROVED.value,
            "quality_commitment": self.repository.get_stage_approval(
                ContextType.RAW_MATERIAL.value,
                material["id"],
                SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
            )["commitment_hash"],
        }]
        registration = self.blockchain.register_product(product_key_value, metadata_hash_value)
        self.repository.create_product({
            "product_code": self.product_code,
            "name": metadata["name"],
            "brand": metadata["brand"],
            "batch_number": metadata["batch_number"],
            "description": metadata["description"],
            "metadata_json": canonical_metadata(metadata),
            "product_key": product_key_value,
            "metadata_hash": metadata_hash_value,
            "registration_tx_hash": registration["transaction_hash"],
            "registration_block_number": registration["block_number"],
            "category": "SKINCARE",
            "subcategory": "FACIAL_SERUM",
            "product_type": "ANTI_AGING_SERUM",
            "manufactured_date": "2026-08-20",
            "expiry_date": "2028-08-20",
            "lineage_hash": metadata_hash(lineage_snapshot),
            "registered_by_user_id": users["manufacturer"]["id"],
            "specification_code": specification["specification_code"],
            "specification_version": specification["version"],
            "specification_snapshot_hash": specification["snapshot_hash"],
            "specification_assigned_at": datetime.now(timezone.utc).isoformat(),
        })
        self.repository.link_raw_materials(self.product_code, [material["id"]])

        self._finish_product(self.repository.get_product(self.product_code), users)

        return self._result(already_loaded=False)

    def _require_chain_alignment(self, product: dict[str, Any]) -> None:
        chain_product = self.blockchain.get_product(product["product_key"])
        if not chain_product["exists"]:
            raise PresentationDemoError(
                "The local product is not present on the running Hardhat chain. "
                "Use Reset Local Demo Data, then load the presentation demo again."
            )
        current_metadata = product_metadata(
            product_code=product["product_code"],
            name=product["name"],
            brand=product["brand"],
            batch_number=product["batch_number"],
            description=product["description"],
        )
        if metadata_hash(current_metadata).lower() != chain_product["metadata_hash"].lower():
            raise PresentationDemoError(
                "The local product metadata does not match its blockchain commitment. "
                "Use Reset Local Demo Data, then load the presentation demo again."
            )
        chain_role = self.blockchain.role_for_address(chain_product["current_owner"])
        if chain_role != product["current_stage"]:
            raise PresentationDemoError(
                f"Local custody is {product['current_stage']} but blockchain custody is {chain_role}. "
                "Use Reset Local Demo Data, then load the presentation demo again."
            )

    def _is_complete(self, product: dict[str, Any]) -> bool:
        if (
            product["current_stage"] != SupplyChainStage.RETAILER.value
            or product["final_sale_status"] != SaleStatus.APPROVED_FOR_SALE.value
        ):
            return False
        contexts = [
            (
                ContextType.RAW_MATERIAL,
                item["id"],
                SupplyChainStage.RAW_MATERIAL_SUPPLIER,
            )
            for item in self.repository.product_raw_materials(self.product_code)
        ]
        contexts.extend(
            (ContextType.PRODUCT, self.product_code, stage)
            for stage in (
                SupplyChainStage.MANUFACTURER,
                SupplyChainStage.DISTRIBUTOR,
                SupplyChainStage.RETAILER,
            )
        )
        if len(contexts) == 3:
            return False
        for context_type, context_id, stage in contexts:
            approval = self.repository.get_stage_approval(
                context_type.value, context_id, stage.value
            )
            summary = self.quality.summary(context_type, context_id, stage)
            if (
                not approval
                or approval["status"] != ApprovalStatus.APPROVED.value
                or not summary["eligible_for_approval"]
            ):
                return False
        return True

    def _finish_product(self, product: dict[str, Any], users: dict[str, dict[str, Any]]) -> None:
        stages = (
            (SupplyChainStage.MANUFACTURER, "manufacturer", "DISTRIBUTOR"),
            (SupplyChainStage.DISTRIBUTOR, "distributor", "RETAILER"),
            (SupplyChainStage.RETAILER, "retailer", None),
        )
        current_stage = product["current_stage"]
        start_index = next(
            (index for index, item in enumerate(stages) if item[0].value == current_stage),
            None,
        )
        if start_index is None:
            raise PresentationDemoError(f"Unsupported partial product stage: {current_stage}")
        for stage, actor, transfer_target in stages[start_index:]:
            self._complete_stage(
                ContextType.PRODUCT, self.product_code, stage, users[actor]["id"],
                record_on_chain=True,
            )
            if transfer_target:
                transfer = self.blockchain.transfer_ownership(product["product_key"], transfer_target)
                self.repository.add_transfer({
                    "product_code": self.product_code,
                    **transfer,
                    "initiated_by_user_id": users[actor]["id"],
                })
                self.repository.update_product_stage(self.product_code, transfer_target)

    def _available_product_code(self) -> str:
        if not self.blockchain.get_product(product_key(PRODUCT_CODE))["exists"]:
            return PRODUCT_CODE
        for index in range(1, 100):
            candidate = f"OC-LUX-SERUM-PRESENTATION-{index:04d}"
            if not self.blockchain.get_product(product_key(candidate))["exists"]:
                return candidate
        raise PresentationDemoError("No unused presentation product code is available on the local chain.")

    def _complete_stage(
        self,
        context_type: ContextType,
        context_id: str,
        stage: SupplyChainStage,
        user_id: str,
        *,
        record_on_chain: bool,
    ) -> dict[str, Any]:
        starting_summary = self.quality.summary(context_type, context_id, stage)
        starting_approval = self.repository.get_stage_approval(
            context_type.value, context_id, stage.value
        )
        if (
            starting_approval
            and starting_approval["status"] == ApprovalStatus.APPROVED.value
            and starting_summary["eligible_for_approval"]
        ):
            return {
                "already_complete": True,
                "checks_completed": starting_summary["required_passed"],
                "evidence_files": sum(
                    len(check.get("evidence", [])) for check in starting_summary["checks"]
                ),
                "status": ApprovalStatus.APPROVED.value,
            }
        current_results = {
            item["template_id"]: item
            for item in self.repository.quality_results(
                context_type.value, context_id, stage.value
            )
            if item.get("id")
        }
        for standard in self.repository.quality_standards(stage.value):
            result = current_results.get(standard["id"])
            if not result or result.get("result") != InspectionResult.PASS.value:
                result = self.quality.submit_result(
                    context_type,
                    context_id,
                    standard["id"],
                    InspectionResult.PASS,
                    "TEST FIXTURE — FICTIONAL DEMO presentation inspection passed.",
                    f"qr_{uuid4().hex}",
                    user_id,
                )
            if standard["evidence_required"] and not self._has_usable_evidence(result, standard):
                self._add_evidence(result, standard, stage, user_id, record_on_chain)

        approval, commitment = self.quality.approve(context_type, context_id, stage, user_id)
        if record_on_chain:
            product = self.repository.get_product(context_id)
            receipt = self.blockchain.record_quality_stage(
                product["product_key"], stage.value, 1, commitment
            )
            self.repository.set_stage_approval({
                **approval,
                "context_type": context_type.value,
                "context_id": context_id,
                "stage": stage.value,
                "status": ApprovalStatus.APPROVED.value,
                "commitment_hash": commitment,
                "blocking_reasons_json": "[]",
                "blockchain_tx_hash": receipt["transaction_hash"],
                "blockchain_block_number": receipt["block_number"],
                "approved_by_user_id": user_id,
            })
        completed_summary = self.quality.summary(context_type, context_id, stage)
        return {
            "already_complete": False,
            "checks_completed": completed_summary["required_passed"],
            "evidence_files": sum(
                len(check.get("evidence", [])) for check in completed_summary["checks"]
            ),
            "status": completed_summary["status"],
        }

    def _has_usable_evidence(
        self, result: dict[str, Any], standard: dict[str, Any]
    ) -> bool:
        for item in self.repository.evidence_for_result(result["id"]):
            if self.store.integrity(item["stored_filename"], item["file_hash"]).value != "VERIFIED":
                continue
            if item.get("document_type") != standard["expected_document_type"]:
                continue
            if standard["trusted_issuer_required"] and not (
                item.get("verification_status") == "VERIFIED_DEMO"
                and item.get("issuer_code_snapshot")
                and item.get("issuer_trust_status_at_submission") == "TRUSTED_DEMO"
            ):
                continue
            return True
        return False

    def _add_evidence(
        self,
        result: dict[str, Any],
        standard: dict[str, Any],
        stage: SupplyChainStage,
        user_id: str,
        record_on_chain: bool,
    ) -> None:
        document_type = standard["expected_document_type"]
        issuer = None
        if standard["trusted_issuer_required"]:
            issuer_code = (
                "LUMINA_ACTIVES"
                if document_type == "CERTIFICATE_OF_ANALYSIS"
                else "AURELIA_QC_LAB_DEMO"
            )
            issuer = self.repository.get_evidence_issuer(issuer_code)
            if not issuer or not issuer["active"] or issuer["trust_status"] != "TRUSTED_DEMO":
                raise PresentationDemoError(
                    f"Presentation issuer {issuer_code} must be active and TRUSTED_DEMO."
                )
        evidence_id = f"ev_{uuid4().hex}"
        content = (
            "%PDF-1.4\n"
            f"TEST FIXTURE - FICTIONAL DEMO PRESENTATION: {standard['code']}\n"
            f"Evidence record: {evidence_id}\n"
            "No certification, accreditation, or real laboratory result is claimed.\n%%EOF"
        ).encode()
        stored_name, digest = self.store.save(
            stage, f"{standard['code']}-FICTIONAL-DEMO.pdf", "application/pdf", content
        )
        try:
            receipt = {"transaction_hash": None, "block_number": None}
            if record_on_chain:
                product = self.repository.get_product(result["context_id"])
                receipt = self.blockchain.record_evidence_hash(
                    product["product_key"], stage.value, digest
                )
            report_number = f"DEMO-{standard['code']}-2026" if issuer else None
            evidence = {
                "id": evidence_id,
                "quality_result_id": result["id"],
                "original_filename": f"{standard['code']}-FICTIONAL-DEMO.pdf",
                "stored_filename": stored_name,
                "content_type": "application/pdf",
                "file_size": len(content),
                "file_hash": digest,
                "uploader_stage": stage.value,
                "visibility": (
                    EvidenceVisibility.CONSUMER_VISIBLE.value
                    if stage == SupplyChainStage.RETAILER
                    else EvidenceVisibility.INTERNAL.value
                ),
                "blockchain_tx_hash": receipt["transaction_hash"],
                "blockchain_block_number": receipt["block_number"],
                "uploaded_by_user_id": user_id,
                "document_type": document_type,
                "laboratory_name": issuer["issuer_name"] if issuer and issuer["issuer_type"] == "LABORATORY" else None,
                "report_reference": report_number,
                "test_date": "2026-08-25" if issuer else None,
                "test_method_source_code": standard["sources"][0]["source_code"] if issuer and standard["sources"] else None,
                "result_summary": "TEST FIXTURE — FICTIONAL DEMO presentation record." if issuer else None,
                "accreditation_status_text": "Fictional demo; no accreditation claimed." if issuer else None,
                "document_notes": "TEST FIXTURE — FICTIONAL DEMO only.",
                "issuer_id": issuer["id"] if issuer else None,
                "issuer_code_snapshot": issuer["issuer_code"] if issuer else None,
                "issuer_name_snapshot": issuer["issuer_name"] if issuer else None,
                "issuer_type_snapshot": issuer["issuer_type"] if issuer else None,
                "issuer_trust_status_at_submission": issuer["trust_status"] if issuer else None,
                "issuer_report_number": report_number,
                "issuer_document_date": "2026-08-25" if issuer else None,
                "verification_status": "VERIFIED_DEMO" if issuer else "UNVERIFIED",
                "verified_by_user_id": user_id if issuer else None,
                "verified_at": datetime.now(timezone.utc).isoformat() if issuer else None,
                "verification_notes": (
                    "Accepted by local fictional demo issuer controls; no certification is claimed."
                    if issuer else "Issuer verification is not required for this demo document."
                ),
            }
            self.repository.add_evidence(evidence)
        except Exception:
            self.store.delete(stored_name)
            raise

    def _result(self, *, already_loaded: bool) -> dict[str, Any]:
        product = self.repository.get_product(self.product_code)
        return {
            "warning": "TEST FIXTURE — FICTIONAL DEMO. Not production or certified data.",
            "already_loaded": already_loaded,
            "product_code": self.product_code,
            "batch_number": product["batch_number"],
            "current_stage": product["current_stage"],
            "final_sale_status": product["final_sale_status"],
            "raw_materials": len(self.repository.product_raw_materials(self.product_code)),
            "stage_approvals": (
                len(self.repository.stage_approvals(ContextType.PRODUCT.value, self.product_code))
                + sum(
                    len(self.repository.stage_approvals(ContextType.RAW_MATERIAL.value, item["id"]))
                    for item in self.repository.product_raw_materials(self.product_code)
                )
            ),
            "evidence_files": len(self.repository.evidence_for_context(ContextType.PRODUCT.value, self.product_code)),
            "message": "Complete presentation demo is ready. Use Admin stage tabs or public verification to click through it.",
        }


class StageDemoAutomation(PresentationDemoSeeder):
    """Role-scoped presentation shortcuts built on the normal quality service."""

    def auto_fill(self, role: str, user_id: str) -> dict[str, Any]:
        handlers = {
            UserRole.RAW_MATERIAL_SUPPLIER.value: self._supplier,
            UserRole.MANUFACTURER.value: self._manufacturer,
            UserRole.DISTRIBUTOR.value: self._distributor,
            UserRole.RETAILER.value: self._retailer,
        }
        handler = handlers.get(role)
        if not handler:
            raise PresentationDemoError(
                "Demo Auto-Fill is available only to Supplier, Manufacturer, Distributor, and Retailer accounts."
            )
        with _SEED_LOCK:
            return handler(user_id)

    def retailer_hold(self, user_id: str) -> dict[str, Any]:
        with _SEED_LOCK:
            product = self._product_for_stage(SupplyChainStage.RETAILER)
            self.product_code = product["product_code"]
            self._require_chain_alignment(product)
            standard = next(
                (
                    item
                    for item in self.repository.quality_standards(
                        SupplyChainStage.RETAILER.value
                    )
                    if item["code"] == "RTL-PACK"
                ),
                None,
            )
            if not standard:
                raise PresentationDemoError(
                    "Required demo fixture RTL-PACK is missing."
                )
            summary = self.quality.summary(
                ContextType.PRODUCT,
                self.product_code,
                SupplyChainStage.RETAILER,
            )
            existing = next(
                (check for check in summary["checks"] if check["code"] == "RTL-PACK"),
                None,
            )
            if existing and existing["result"] == InspectionResult.FAIL.value:
                return self._stage_result(
                    product,
                    SupplyChainStage.RETAILER,
                    already_complete=True,
                    action="DEMO_HOLD",
                    message="The fictional security-seal failure is already active.",
                )
            self.quality.submit_result(
                ContextType.PRODUCT,
                self.product_code,
                standard["id"],
                InspectionResult.FAIL,
                "TEST FIXTURE — FICTIONAL DEMO security seal failure for the HOLD walkthrough.",
                f"qr_{uuid4().hex}",
                user_id,
            )
            try:
                self.quality.approve(
                    ContextType.PRODUCT,
                    self.product_code,
                    SupplyChainStage.RETAILER,
                    user_id,
                )
            except QualityGateError:
                # A blocked approval is the expected service-layer outcome of this fixture.
                pass
            product = self.repository.get_product(self.product_code)
            if product["final_sale_status"] != SaleStatus.HOLD.value:
                raise PresentationDemoError(
                    "Retail HOLD could not be established through the quality gate."
                )
            return self._stage_result(
                product,
                SupplyChainStage.RETAILER,
                already_complete=False,
                action="DEMO_HOLD",
                message="Security Seal and Luxury Pack Inspection is FAIL; Retail status is HOLD.",
            )

    def _supplier(self, user_id: str) -> dict[str, Any]:
        material = self.repository.get_raw_material_by_batch("HA-260801")
        if not material:
            material = self.repository.create_raw_material(
                {
                    "id": MATERIAL_ID,
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
                    "notes": "TEST FIXTURE — FICTIONAL DEMO supplier material.",
                    "created_by_user_id": user_id,
                }
            )
        completed = self._complete_stage(
            ContextType.RAW_MATERIAL,
            material["id"],
            SupplyChainStage.RAW_MATERIAL_SUPPLIER,
            user_id,
            record_on_chain=False,
        )
        return {
            "warning": "DEMO ONLY — FICTIONAL TEST FIXTURES",
            "action": "DEMO_AUTO_FILL",
            "role": UserRole.RAW_MATERIAL_SUPPLIER.value,
            "stage": SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
            "context_type": ContextType.RAW_MATERIAL.value,
            "context_id": material["id"],
            "internal_batch_id": material["internal_batch_id"],
            **completed,
            "steps": [
                "Ensured the deterministic fictional raw-material batch",
                "Recorded PASS results through QualityService",
                "Generated integrity-checked fictional evidence",
                "Approved the supplier quality gate",
            ],
            "next_action": "Sign out and continue as Manufacturer.",
            "message": "Raw-material demo stage is approved.",
        }

    def _manufacturer(self, user_id: str) -> dict[str, Any]:
        product = self._completed_or_current_product(SupplyChainStage.MANUFACTURER)
        if product and product[1]:
            self.product_code = product[0]["product_code"]
            self._require_chain_alignment(product[0])
            return self._stage_result(
                product[0], SupplyChainStage.MANUFACTURER, already_complete=True,
                message="Manufacturer demo stage is already approved.",
            )
        if product:
            current = product[0]
        else:
            material = self._approved_material()
            if not material:
                raise PresentationDemoError(
                    "Manufacturer demo stage cannot be completed. No approved raw-material batch is available. Complete the Supplier stage first."
                )
            self.blockchain.require_ready()
            self.product_code = self._available_product_code()
            current = self._register_product(material, user_id)
        self.product_code = current["product_code"]
        self._require_chain_alignment(current)
        completed = self._complete_stage(
            ContextType.PRODUCT,
            self.product_code,
            SupplyChainStage.MANUFACTURER,
            user_id,
            record_on_chain=True,
        )
        return self._stage_result(
            self.repository.get_product(self.product_code),
            SupplyChainStage.MANUFACTURER,
            already_complete=completed["already_complete"],
            completion=completed,
            message="Manufacturer QC is approved. Transfer to Distributor remains a manual presentation step.",
        )

    def _distributor(self, user_id: str) -> dict[str, Any]:
        return self._complete_product_stage(
            SupplyChainStage.DISTRIBUTOR,
            user_id,
            "Distributor QC is approved. Transfer to Retailer remains a manual presentation step.",
        )

    def _retailer(self, user_id: str) -> dict[str, Any]:
        product = self._product_for_stage(SupplyChainStage.RETAILER, allow_completed=True)
        was_hold = product["final_sale_status"] == SaleStatus.HOLD.value
        self.product_code = product["product_code"]
        self._require_chain_alignment(product)
        completed = self._complete_stage(
            ContextType.PRODUCT,
            self.product_code,
            SupplyChainStage.RETAILER,
            user_id,
            record_on_chain=True,
        )
        return self._stage_result(
            self.repository.get_product(self.product_code),
            SupplyChainStage.RETAILER,
            already_complete=completed["already_complete"],
            completion=completed,
            corrected_hold=was_hold and not completed["already_complete"],
            message=(
                "The fictional seal issue was corrected and the product is Approved for Sale."
                if was_hold
                else "Retail QC is approved and the product is Approved for Sale."
            ),
        )

    def _complete_product_stage(
        self, stage: SupplyChainStage, user_id: str, message: str
    ) -> dict[str, Any]:
        selected = self._completed_or_current_product(stage)
        if not selected:
            raise PresentationDemoError(
                f"Product is not currently owned by {stage.value.replace('_', ' ').title()}. Complete the preceding transfer first."
            )
        product, already_progressed = selected
        self.product_code = product["product_code"]
        self._require_chain_alignment(product)
        if already_progressed:
            return self._stage_result(
                product, stage, already_complete=True,
                message=f"{stage.value.replace('_', ' ').title()} demo stage is already approved.",
            )
        completed = self._complete_stage(
            ContextType.PRODUCT,
            self.product_code,
            stage,
            user_id,
            record_on_chain=True,
        )
        return self._stage_result(
            self.repository.get_product(self.product_code),
            stage,
            already_complete=completed["already_complete"],
            completion=completed,
            message=message,
        )

    def _approved_material(self) -> dict[str, Any] | None:
        for material in self.repository.list_raw_materials():
            approval = self.repository.get_stage_approval(
                ContextType.RAW_MATERIAL.value,
                material["id"],
                SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
            )
            summary = self.quality.summary(
                ContextType.RAW_MATERIAL,
                material["id"],
                SupplyChainStage.RAW_MATERIAL_SUPPLIER,
            )
            if (
                material["quality_status"] == ApprovalStatus.APPROVED.value
                and approval
                and approval["status"] == ApprovalStatus.APPROVED.value
                and summary["eligible_for_approval"]
            ):
                return material
        return None

    def _register_product(self, material: dict[str, Any], user_id: str) -> dict[str, Any]:
        specification = self.repository.get_product_specification(
            DEFAULT_PRODUCT_SPECIFICATION_CODE
        )
        if (
            not specification
            or not specification.get("active")
            or specification.get("status") != "APPROVED"
        ):
            raise PresentationDemoError(
                "The approved presentation product specification is unavailable."
            )
        today = date.today()
        if (
            specification.get("effective_from")
            and date.fromisoformat(specification["effective_from"]) > today
        ):
            raise PresentationDemoError(
                "The approved presentation product specification is not yet effective."
            )
        if (
            specification.get("effective_until")
            and date.fromisoformat(specification["effective_until"]) < today
        ):
            raise PresentationDemoError(
                "The approved presentation product specification is no longer effective."
            )
        metadata = product_metadata(
            product_code=self.product_code,
            name="Aurelia Prestige Renewal Serum",
            brand="Aurelia Maison",
            batch_number="APR-2026-001",
            description="Luxury anti-aging facial serum demonstration batch",
        )
        material_approval = self.repository.get_stage_approval(
            ContextType.RAW_MATERIAL.value,
            material["id"],
            SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
        )
        lineage_snapshot = [
            {
                "id": material["id"],
                "batch": material["internal_batch_id"],
                "material": material["material_name"],
                "quality_status": material["quality_status"],
                "quality_commitment": material_approval["commitment_hash"],
            }
        ]
        key = product_key(self.product_code)
        digest = metadata_hash(metadata)
        registration = self.blockchain.register_product(key, digest)
        self.repository.create_product(
            {
                "product_code": self.product_code,
                "name": metadata["name"],
                "brand": metadata["brand"],
                "batch_number": metadata["batch_number"],
                "description": metadata["description"],
                "metadata_json": canonical_metadata(metadata),
                "product_key": key,
                "metadata_hash": digest,
                "registration_tx_hash": registration["transaction_hash"],
                "registration_block_number": registration["block_number"],
                "category": "SKINCARE",
                "subcategory": "FACIAL_SERUM",
                "product_type": "ANTI_AGING_SERUM",
                "manufactured_date": "2026-08-20",
                "expiry_date": "2028-08-20",
                "lineage_hash": metadata_hash(lineage_snapshot),
                "registered_by_user_id": user_id,
                "specification_code": specification["specification_code"],
                "specification_version": specification["version"],
                "specification_snapshot_hash": specification["snapshot_hash"],
                "specification_assigned_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.repository.link_raw_materials(self.product_code, [material["id"]])
        return self.repository.get_product(self.product_code)

    def _completed_or_current_product(
        self, stage: SupplyChainStage
    ) -> tuple[dict[str, Any], bool] | None:
        products = self.repository.list_products()
        for product in products:
            if product["current_stage"] == stage.value:
                return product, False
        stage_order = {
            SupplyChainStage.MANUFACTURER.value: 1,
            SupplyChainStage.DISTRIBUTOR.value: 2,
            SupplyChainStage.RETAILER.value: 3,
        }
        for product in products:
            approval = self.repository.get_stage_approval(
                ContextType.PRODUCT.value, product["product_code"], stage.value
            )
            summary = self.quality.summary(ContextType.PRODUCT, product["product_code"], stage)
            if (
                approval
                and approval["status"] == ApprovalStatus.APPROVED.value
                and summary["eligible_for_approval"]
                and stage_order.get(product["current_stage"], 0) > stage_order[stage.value]
            ):
                return product, True
        return None

    def _product_for_stage(
        self, stage: SupplyChainStage, *, allow_completed: bool = False
    ) -> dict[str, Any]:
        for product in self.repository.list_products():
            if product["current_stage"] == stage.value and (
                allow_completed
                or product["final_sale_status"] != SaleStatus.APPROVED_FOR_SALE.value
            ):
                return product
        if allow_completed:
            for product in self.repository.list_products():
                if (
                    product["current_stage"] == stage.value
                    and product["final_sale_status"] == SaleStatus.APPROVED_FOR_SALE.value
                ):
                    return product
        raise PresentationDemoError(
            f"Product is not currently owned by {stage.value.replace('_', ' ').title()}. Complete the preceding transfer first."
        )

    def _stage_result(
        self,
        product: dict[str, Any],
        stage: SupplyChainStage,
        *,
        already_complete: bool,
        action: str = "DEMO_AUTO_FILL",
        completion: dict[str, Any] | None = None,
        corrected_hold: bool = False,
        message: str,
    ) -> dict[str, Any]:
        summary = self.quality.summary(ContextType.PRODUCT, product["product_code"], stage)
        return {
            "warning": "DEMO ONLY — FICTIONAL TEST FIXTURES",
            "action": action,
            "stage": stage.value,
            "context_type": ContextType.PRODUCT.value,
            "context_id": product["product_code"],
            "product_code": product["product_code"],
            "current_stage": product["current_stage"],
            "final_sale_status": product["final_sale_status"],
            "already_complete": already_complete,
            "corrected_hold": corrected_hold,
            "checks_completed": summary["required_passed"],
            "evidence_files": sum(
                len(check.get("evidence", [])) for check in summary["checks"]
            ),
            "status": summary["status"],
            "steps": [
                "Recorded quality results through QualityService",
                "Generated integrity-checked fictional evidence where required",
                "Applied the normal stage approval gate",
                "Committed product-stage quality and evidence hashes on-chain",
            ],
            "next_action": (
                "Click Fix Demo Issue to correct the fictional seal failure."
                if action == "DEMO_HOLD"
                else {
                SupplyChainStage.MANUFACTURER: "Click Transfer to Distributor.",
                SupplyChainStage.DISTRIBUTOR: "Click Transfer to Retailer.",
                SupplyChainStage.RETAILER: "Sign out and verify the product as Consumer.",
                }[stage]
            ),
            "message": message,
            **({"completion": completion} if completion else {}),
        }
