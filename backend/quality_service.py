import json
from datetime import date
from typing import Any

from web3 import Web3

from .database import ProductRepository
from .domain import (
    ApprovalStatus,
    ContextType,
    InspectionResult,
    SaleStatus,
    STAGE_DISPLAY,
    SupplyChainStage,
)
from .metadata_hash import canonical_metadata
from .evidence import EvidenceStore


class QualityGateError(ValueError):
    def __init__(self, message: str, summary: dict[str, Any]):
        super().__init__(message)
        self.summary = summary


class QualityService:
    def __init__(self, repository: ProductRepository, evidence_store: EvidenceStore | None = None):
        self.repository = repository
        self.evidence_store = evidence_store

    def context_exists(self, context_type: ContextType, context_id: str) -> bool:
        if context_type == ContextType.RAW_MATERIAL:
            return self.repository.get_raw_material(context_id) is not None
        return self.repository.get_product(context_id) is not None

    def submit_result(
        self,
        context_type: ContextType,
        context_id: str,
        standard_id: int,
        result: InspectionResult,
        notes: str | None,
        result_id: str,
        submitted_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        standard = self.repository.get_standard(standard_id)
        if not standard:
            raise ValueError("Unknown or inactive quality standard")
        if not self.context_exists(context_type, context_id):
            raise ValueError("Quality-check context was not found")
        stage = SupplyChainStage(standard["supply_chain_stage"])
        if context_type == ContextType.RAW_MATERIAL and stage != SupplyChainStage.RAW_MATERIAL_SUPPLIER:
            raise ValueError("Raw-material batches can only use raw-material standards")
        if context_type == ContextType.PRODUCT and stage == SupplyChainStage.RAW_MATERIAL_SUPPLIER:
            raise ValueError("Finished products cannot use raw-material standards")
        saved = self.repository.upsert_quality_result(
            {
                "id": result_id,
                "context_type": context_type.value,
                "context_id": context_id,
                "standard_id": standard_id,
                "result": result.value,
                "notes": notes.strip() if notes else None,
                "inspector_stage": stage.value,
                "submitted_by_user_id": submitted_by_user_id,
            }
        )
        invalidated_status = (
            ApprovalStatus.HOLD if result == InspectionResult.FAIL else ApprovalStatus.PENDING
        )
        self.repository.invalidate_stage_approval(
            context_type.value,
            context_id,
            stage.value,
            invalidated_status.value,
            "Quality results changed; stage approval must be recorded again.",
        )
        if context_type == ContextType.RAW_MATERIAL:
            self.repository.update_raw_material_status(context_id, invalidated_status.value)
        elif stage == SupplyChainStage.RETAILER:
            stage_summary = self.summary(context_type, context_id, stage)
            has_failure = any(
                check["required"] and check["result"] == InspectionResult.FAIL.value
                for check in stage_summary["checks"]
            )
            self.repository.update_product_stage(
                context_id,
                stage.value,
                SaleStatus.HOLD.value if has_failure else SaleStatus.NOT_READY.value,
            )
        return saved

    def summary(
        self, context_type: ContextType, context_id: str, stage: SupplyChainStage
    ) -> dict[str, Any]:
        rows = self.repository.quality_results(context_type.value, context_id, stage.value)
        checks: list[dict[str, Any]] = []
        blockers: list[str] = []
        passed = 0
        required_total = sum(int(row["required"]) for row in rows)
        failed = False

        for row in rows:
            result = row.get("result") or InspectionResult.PENDING.value
            evidence = self.repository.evidence_for_result(row["id"]) if row.get("id") else []
            if self.evidence_store:
                for item in evidence:
                    item["integrity"] = self.evidence_store.integrity(
                        item["stored_filename"], item["file_hash"]
                    ).value
            expected_document_type = row.get("expected_document_type") or "OTHER"
            verified_evidence = [
                item for item in evidence
                if item.get("integrity", "VERIFIED") == "VERIFIED"
                and (
                    expected_document_type == "OTHER"
                    or item.get("document_type") == expected_document_type
                )
            ]
            trusted_evidence = [
                item for item in verified_evidence
                if item.get("verification_status") == "VERIFIED_DEMO"
                and item.get("issuer_code_snapshot")
                and item.get("issuer_trust_status_at_submission") == "TRUSTED_DEMO"
            ]
            trusted_issuer_missing = bool(row.get("trusted_issuer_required") and not trusted_evidence)
            evidence_missing = bool(
                row["evidence_required"]
                and (not verified_evidence or trusted_issuer_missing)
            )
            trust_warnings = [
                (
                    f"{item['issuer_name_snapshot']} was accepted as "
                    f"{item['issuer_trust_status_at_submission'].replace('_', ' ').title()}, "
                    f"but its current registry status is {item['issuer_current_trust_status'].replace('_', ' ').title()}."
                )
                for item in evidence
                if item.get("issuer_code_snapshot")
                and item.get("issuer_current_trust_status")
                and item.get("issuer_current_trust_status") != item.get("issuer_trust_status_at_submission")
            ]
            is_required_pass = not row["required"] or result == InspectionResult.PASS.value
            if row["required"] and result == InspectionResult.PASS.value and not evidence_missing:
                passed += 1
            if row["required"] and result == InspectionResult.FAIL.value:
                failed = True
                blockers.append(f"{row['check_name']} failed.")
            elif row["required"] and not is_required_pass:
                blockers.append(f"{row['check_name']} has not passed.")
            if evidence_missing:
                expected = expected_document_type.replace("_", " ").title()
                if trusted_issuer_missing:
                    blockers.append(
                        f"{row['check_name']} requires {expected} evidence accepted from an appropriate Trusted Demo issuer."
                    )
                else:
                    blockers.append(f"{row['check_name']} requires verified {expected} evidence.")
            checks.append(
                {
                    "standard_id": row["template_id"],
                    "result_id": row.get("id"),
                    "code": row["standard_code"],
                    "category": row["category"],
                    "check_name": row["check_name"],
                    "requirement": row["requirement_description"],
                    "classification": row["classification"],
                    "requirement_rationale": row["requirement_rationale"],
                    "evidence_expectation": row["evidence_expectation"],
                    "expected_document_type": row["expected_document_type"],
                    "package_component": row.get("package_component"),
                    "expected_visual_characteristic": row.get("expected_visual_characteristic"),
                    "defect_categories": row.get("defect_categories", []),
                    "sources": row.get("sources", []),
                    "source_snapshot": row.get("source_snapshot", False),
                    "required": bool(row["required"]),
                    "evidence_required": bool(row["evidence_required"]),
                    "trusted_issuer_required": bool(row.get("trusted_issuer_required")),
                    "specification_requirements": row.get("specification_requirements", []),
                    "trust_warnings": trust_warnings,
                    "result": result,
                    "notes": row.get("notes"),
                    "evidence": evidence,
                }
            )

        blockers.extend(self._dependency_blockers(context_type, context_id, stage))
        approval = self.repository.get_stage_approval(context_type.value, context_id, stage.value)
        calculated = ApprovalStatus.HOLD if failed else (
            ApprovalStatus.APPROVED if not blockers and rows else ApprovalStatus.PENDING
        )
        status = approval["status"] if approval and not blockers else calculated.value
        product_specification = None
        if context_type == ContextType.PRODUCT:
            product = self.repository.get_product(context_id)
            if product and product.get("specification_code"):
                current_spec = self.repository.get_product_specification(product["specification_code"])
                product_specification = {
                    "specification_code": product["specification_code"],
                    "specification_name": current_spec["specification_name"] if current_spec else "Recorded product specification",
                    "version": product["specification_version"],
                    "snapshot_hash": product["specification_snapshot_hash"],
                    "assigned_at": product["specification_assigned_at"],
                    "current_status": current_spec["status"] if current_spec else "UNKNOWN",
                    "disclaimer": current_spec["disclaimer"] if current_spec else "Fictional demo specification.",
                }
        return {
            "context_type": context_type.value,
            "context_id": context_id,
            "stage": stage.value,
            "display_name": STAGE_DISPLAY[stage],
            "profile": (
                {
                    "profile_code": rows[0]["profile_code"],
                    "version": rows[0]["profile_version"],
                    "jurisdiction": rows[0]["profile_jurisdiction"],
                    "disclaimer": rows[0]["profile_disclaimer"],
                }
                if rows else None
            ),
            "product_specification": product_specification,
            "required_passed": passed,
            "required_total": required_total,
            "status": status,
            "eligible_for_approval": not blockers and bool(rows),
            "blocking_reasons": list(dict.fromkeys(blockers)),
            "approved_at": approval.get("approved_at") if approval else None,
            "commitment_hash": approval.get("commitment_hash") if approval else None,
            "lineage_hash": (
                self.repository.get_product(context_id).get("lineage_hash")
                if context_type == ContextType.PRODUCT and self.repository.get_product(context_id)
                else None
            ),
            "checks": checks,
        }

    def _dependency_blockers(
        self, context_type: ContextType, context_id: str, stage: SupplyChainStage
    ) -> list[str]:
        if context_type == ContextType.RAW_MATERIAL:
            material = self.repository.get_raw_material(context_id)
            expiry = material.get("expiry_retest_date") if material else None
            return ["Raw material is past its expiry/retest date."] if expiry and date.fromisoformat(expiry) < date.today() else []
        if stage == SupplyChainStage.MANUFACTURER:
            product = self.repository.get_product(context_id)
            if not product or not product.get("specification_code") or not product.get("specification_version"):
                return ["An approved product specification must be assigned to the finished batch."]
            materials = self.repository.product_raw_materials(context_id)
            if not materials:
                return ["At least one approved raw-material batch must be linked."]
            unapproved = []
            for material in materials:
                approval = self.repository.get_stage_approval(
                    ContextType.RAW_MATERIAL.value,
                    material["id"],
                    SupplyChainStage.RAW_MATERIAL_SUPPLIER.value,
                )
                summary = self.summary(
                    ContextType.RAW_MATERIAL,
                    material["id"],
                    SupplyChainStage.RAW_MATERIAL_SUPPLIER,
                )
                if (
                    material["quality_status"] != ApprovalStatus.APPROVED.value
                    or not approval
                    or approval["status"] != ApprovalStatus.APPROVED.value
                    or not summary["eligible_for_approval"]
                ):
                    unapproved.append(material["internal_batch_id"])
            return [f"Raw-material batch {batch} is not approved." for batch in unapproved]
        prerequisite = {
            SupplyChainStage.DISTRIBUTOR: SupplyChainStage.MANUFACTURER,
            SupplyChainStage.RETAILER: SupplyChainStage.DISTRIBUTOR,
        }.get(stage)
        if prerequisite:
            approval = self.repository.get_stage_approval(
                ContextType.PRODUCT.value, context_id, prerequisite.value
            )
            prerequisite_summary = self.summary(ContextType.PRODUCT, context_id, prerequisite)
            if (
                not approval
                or approval["status"] != ApprovalStatus.APPROVED.value
                or not prerequisite_summary["eligible_for_approval"]
            ):
                return [f"{STAGE_DISPLAY[prerequisite]} must be approved first."]
        if stage == SupplyChainStage.RETAILER:
            product = self.repository.get_product(context_id)
            expiry = product.get("expiry_date") if product else None
            if expiry and date.fromisoformat(expiry) < date.today():
                return ["Finished product is past its stored expiry date."]
        return []

    def approve(
        self,
        context_type: ContextType,
        context_id: str,
        stage: SupplyChainStage,
        approved_by_user_id: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        summary = self.summary(context_type, context_id, stage)
        commitment = self.commitment_hash(summary)
        if not summary["eligible_for_approval"]:
            failed = any(check["result"] == InspectionResult.FAIL.value for check in summary["checks"])
            status = ApprovalStatus.HOLD if failed else ApprovalStatus.PENDING
            self.repository.set_stage_approval(
                {
                    "context_type": context_type.value,
                    "context_id": context_id,
                    "stage": stage.value,
                    "status": status.value,
                    "commitment_hash": commitment,
                    "blocking_reasons_json": json.dumps(summary["blocking_reasons"]),
                    "approved_by_user_id": approved_by_user_id,
                }
            )
            raise QualityGateError("Quality stage approval is blocked", summary)

        approval = self.repository.set_stage_approval(
            {
                "context_type": context_type.value,
                "context_id": context_id,
                "stage": stage.value,
                "status": ApprovalStatus.APPROVED.value,
                "commitment_hash": commitment,
                "blocking_reasons_json": "[]",
                "approved_by_user_id": approved_by_user_id,
            }
        )
        if context_type == ContextType.RAW_MATERIAL:
            self.repository.update_raw_material_status(context_id, ApprovalStatus.APPROVED.value)
        elif stage == SupplyChainStage.RETAILER:
            self.repository.update_product_stage(
                context_id, stage.value, SaleStatus.APPROVED_FOR_SALE.value
            )
        return approval, commitment

    @staticmethod
    def commitment_hash(summary: dict[str, Any]) -> str:
        snapshot = {
            "context_type": summary["context_type"],
            "context_id": summary["context_id"],
            "stage": summary["stage"],
            "lineage_hash": summary.get("lineage_hash"),
            "checks": [
                {
                    "code": check["code"],
                    "result": check["result"],
                    "classification": check["classification"],
                    "sources": sorted(
                        [{
                            "source_code": source["source_code"],
                            "edition": source["edition"],
                        }
                        for source in check.get("sources", [])
                        ],
                        key=lambda item: (item["source_code"], item["edition"]),
                    ),
                    "evidence_hashes": sorted(item["file_hash"] for item in check["evidence"]),
                    "evidence_issuers": sorted(
                        [
                            {
                                "issuer_code": item.get("issuer_code_snapshot"),
                                "trust_at_submission": item.get("issuer_trust_status_at_submission"),
                                "verification_status": item.get("verification_status"),
                            }
                            for item in check["evidence"] if item.get("issuer_code_snapshot")
                        ],
                        key=lambda item: item["issuer_code"],
                    ),
                }
                for check in summary["checks"]
            ],
            "profile": {
                "profile_code": summary.get("profile", {}).get("profile_code") if summary.get("profile") else None,
                "version": summary.get("profile", {}).get("version") if summary.get("profile") else None,
            },
            "product_specification": {
                "specification_code": summary.get("product_specification", {}).get("specification_code") if summary.get("product_specification") else None,
                "version": summary.get("product_specification", {}).get("version") if summary.get("product_specification") else None,
                "snapshot_hash": summary.get("product_specification", {}).get("snapshot_hash") if summary.get("product_specification") else None,
            },
        }
        return Web3.to_hex(Web3.keccak(text=canonical_metadata(snapshot)))

    def require_approved(self, product_code: str, stage: SupplyChainStage) -> None:
        approval = self.repository.get_stage_approval(ContextType.PRODUCT.value, product_code, stage.value)
        summary = self.summary(ContextType.PRODUCT, product_code, stage)
        if (
            not approval
            or approval["status"] != ApprovalStatus.APPROVED.value
            or not summary["eligible_for_approval"]
        ):
            detail = summary["blocking_reasons"] or [f"{STAGE_DISPLAY[stage]} has not been approved."]
            raise QualityGateError("Transfer blocked: " + " ".join(detail), summary)
