from enum import StrEnum


class SupplyChainStage(StrEnum):
    RAW_MATERIAL_SUPPLIER = "RAW_MATERIAL_SUPPLIER"
    MANUFACTURER = "MANUFACTURER"
    DISTRIBUTOR = "DISTRIBUTOR"
    RETAILER = "RETAILER"


class InspectionResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class SaleStatus(StrEnum):
    NOT_READY = "NOT_READY"
    APPROVED_FOR_SALE = "APPROVED_FOR_SALE"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class EvidenceVisibility(StrEnum):
    INTERNAL = "INTERNAL"
    CONSUMER_VISIBLE = "CONSUMER_VISIBLE"


class EvidenceIntegrity(StrEnum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    FILE_MISSING = "FILE_MISSING"


class EvidenceDocumentType(StrEnum):
    CERTIFICATE_OF_ANALYSIS = "CERTIFICATE_OF_ANALYSIS"
    MICROBIOLOGY_REPORT = "MICROBIOLOGY_REPORT"
    PRESERVATIVE_EFFICACY_REPORT = "PRESERVATIVE_EFFICACY_REPORT"
    RAW_MATERIAL_SPECIFICATION = "RAW_MATERIAL_SPECIFICATION"
    BATCH_MANUFACTURING_RECORD = "BATCH_MANUFACTURING_RECORD"
    PACKAGING_INSPECTION = "PACKAGING_INSPECTION"
    TRANSPORT_RECORD = "TRANSPORT_RECORD"
    RETAIL_INSPECTION = "RETAIL_INSPECTION"
    OTHER = "OTHER"


class RequirementClassification(StrEnum):
    REGULATORY = "REGULATORY"
    STANDARD_BASED = "STANDARD_BASED"
    INDUSTRY_GUIDANCE = "INDUSTRY_GUIDANCE"
    ORIGINCHAIN_INTERNAL = "ORIGINCHAIN_INTERNAL"
    ORGANIZATION_INTERNAL = "ORGANIZATION_INTERNAL"


class QualitySourceType(StrEnum):
    REGULATION = "REGULATION"
    STANDARD = "STANDARD"
    GUIDANCE = "GUIDANCE"
    INTERNAL_DEMO_STANDARD = "INTERNAL_DEMO_STANDARD"


class Jurisdiction(StrEnum):
    INDIA = "INDIA"
    INTERNATIONAL = "INTERNATIONAL"
    UNITED_STATES = "UNITED_STATES"
    EUROPEAN_UNION = "EUROPEAN_UNION"
    ORIGINCHAIN = "ORIGINCHAIN"


class SourceLifecycle(StrEnum):
    PUBLISHED_CURRENT = "PUBLISHED_CURRENT"
    PUBLISHED_UNDER_REVISION = "PUBLISHED_UNDER_REVISION"
    DRAFT = "DRAFT"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"


class MappingPrecision(StrEnum):
    STANDARD_LEVEL = "STANDARD_LEVEL"
    SECTION_LEVEL = "SECTION_LEVEL"
    CLAUSE_LEVEL = "CLAUSE_LEVEL"


class ProductSpecificationStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class EvidenceIssuerType(StrEnum):
    SUPPLIER = "SUPPLIER"
    LABORATORY = "LABORATORY"
    MANUFACTURER = "MANUFACTURER"
    DISTRIBUTOR = "DISTRIBUTOR"
    RETAILER = "RETAILER"
    INTERNAL_TEST_FIXTURE = "INTERNAL_TEST_FIXTURE"
    OTHER = "OTHER"


class IssuerTrustStatus(StrEnum):
    TRUSTED_DEMO = "TRUSTED_DEMO"
    UNVERIFIED = "UNVERIFIED"
    REVOKED = "REVOKED"


class EvidenceVerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_DEMO = "VERIFIED_DEMO"
    REJECTED = "REJECTED"


class SourceReviewStatus(StrEnum):
    CURRENT = "CURRENT"
    REVIEW_DUE = "REVIEW_DUE"
    UNDER_REVIEW = "UNDER_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class QualityChangeType(StrEnum):
    SOURCE_UPDATE = "SOURCE_UPDATE"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    PRODUCT_SPEC_UPDATE = "PRODUCT_SPEC_UPDATE"
    REQUIREMENT_UPDATE = "REQUIREMENT_UPDATE"
    ISSUER_UPDATE = "ISSUER_UPDATE"


class QualityChangeStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"


class ContextType(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PRODUCT = "PRODUCT"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    RAW_MATERIAL_SUPPLIER = "RAW_MATERIAL_SUPPLIER"
    MANUFACTURER = "MANUFACTURER"
    DISTRIBUTOR = "DISTRIBUTOR"
    RETAILER = "RETAILER"


PRODUCT_CATEGORY = "SKINCARE"
PRODUCT_SUBCATEGORY = "FACIAL_SERUM"
PRODUCT_TYPE = "ANTI_AGING_SERUM"
DEFAULT_PRODUCT_SPECIFICATION_CODE = "AURELIA_PRESTIGE_RENEWAL_SERUM_SPEC_V1"


PRODUCT_SPECIFICATION = {
    "specification_code": DEFAULT_PRODUCT_SPECIFICATION_CODE,
    "product_category": PRODUCT_CATEGORY,
    "product_subcategory": PRODUCT_SUBCATEGORY,
    "product_type": PRODUCT_TYPE,
    "specification_name": "Aurelia Prestige Renewal Serum — Demo Product Specification v1",
    "version": "1.0",
    "status": "APPROVED",
    "effective_from": "2026-08-30",
    "effective_until": None,
    "created_by_user_id": "user_admin",
    "approved_at": "2026-08-30T00:00:00Z",
    "approved_by_user_id": "user_admin",
    "supersedes_specification_code": None,
    "change_summary": "Initial fictional internal product-quality and luxury-packaging configuration.",
    "disclaimer": "FICTIONAL DEMO SPECIFICATION — not a CDSCO specification, BIS/ISO standard, or commercial formulation.",
}


def _spec_requirement(
    code: str, category: str, description: str, requirement_type: str,
    expected_characteristic: str, order: int, *, package_component: str | None = None,
    evidence_expectation: str = "Human inspection record.", ml_eligible: bool = False,
    visual_component: str | None = None, defects: tuple[str, ...] = (),
    quality_check_codes: tuple[str, ...] = (),
) -> dict:
    return {
        "requirement_code": code, "category": category, "description": description,
        "requirement_type": requirement_type, "package_component": package_component,
        "expected_characteristic": expected_characteristic,
        "evidence_expectation": evidence_expectation, "required": True,
        "display_order": order, "ml_eligible": ml_eligible,
        "visual_component": visual_component, "defect_categories": defects,
        "quality_check_codes": quality_check_codes,
    }


PRODUCT_SPECIFICATION_REQUIREMENTS = [
    _spec_requirement("SPEC-IDENTITY-PRODUCT", "Product Identity", "Product name matches the approved batch record.", "IDENTITY", "Aurelia Prestige Renewal Serum identity confirmed", 1, quality_check_codes=("MFG-FINISHED", "RTL-AUTH")),
    _spec_requirement("SPEC-IDENTITY-BRAND", "Product Identity", "Brand identity matches the approved fictional record.", "IDENTITY", "Aurelia Maison identity confirmed", 2, quality_check_codes=("MFG-FINISHED", "RTL-AUTH")),
    _spec_requirement("SPEC-IDENTITY-BATCH", "Product Identity", "Batch code is present and readable.", "TRACEABILITY", "Batch identity readable and consistent", 3, package_component="LABEL", ml_eligible=True, visual_component="PRINT", defects=("PRINT_DEFECT", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-LABEL-TRACEABILITY", "RTL-LABEL")),
    _spec_requirement("SPEC-BOTTLE-CONFIG", "Primary Packaging", "Bottle model matches the approved fictional configuration.", "PACKAGING", "Fictional Aurelia serum bottle configuration present", 4, package_component="BOTTLE", ml_eligible=True, visual_component="BOTTLE", defects=("BOTTLE_DAMAGE", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-BOTTLE-CONDITION", "Primary Packaging", "Bottle shows no obvious visible crack or leakage.", "VISUAL", "Bottle visibly intact with no leakage", 5, package_component="BOTTLE", ml_eligible=True, visual_component="BOTTLE", defects=("BOTTLE_DAMAGE", "LEAKAGE", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-DROPPER-CONFIG", "Primary Packaging", "Dropper assembly matches the expected fictional configuration and is seated correctly.", "PACKAGING", "Dropper configuration matched and visibly seated", 6, package_component="DROPPER", ml_eligible=True, visual_component="DROPPER", defects=("DROPPER_MISMATCH", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-SEAL-PRESENT", "Security", "Security seal is present.", "PACKAGING", "Security seal present", 7, package_component="SECURITY_SEAL", ml_eligible=True, visual_component="SECURITY_SEAL", defects=("SEAL_DAMAGE", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-SEAL-INTEGRITY", "Security", "Security seal has no obvious visible tampering.", "VISUAL", "Seal visibly intact with no tampering indication", 8, package_component="SECURITY_SEAL", ml_eligible=True, visual_component="SECURITY_SEAL", defects=("SEAL_DAMAGE", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-LABEL-PRESENT", "Label Presentation", "Product label is present.", "LABEL", "Product label present", 9, package_component="LABEL", ml_eligible=True, visual_component="LABEL", defects=("MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-LABEL-TRACEABILITY", "RTL-LABEL")),
    _spec_requirement("SPEC-LABEL-ALIGNMENT", "Label Presentation", "Label alignment meets the fictional demo visual expectation.", "VISUAL", "Label visibly aligned on the primary pack", 10, package_component="LABEL", ml_eligible=True, visual_component="LABEL", defects=("LABEL_MISALIGNMENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-PRINT-CONDITION", "Label Presentation", "No obvious print defect is recorded.", "VISUAL", "Print visibly clear without obvious defect", 11, package_component="PRINT", ml_eligible=True, visual_component="PRINT", defects=("PRINT_DEFECT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-CARTON-PRESENT", "Secondary Packaging", "Outer carton is present where used for the fictional configuration.", "PACKAGING", "Matching outer carton present where applicable", 12, package_component="OUTER_CARTON", ml_eligible=True, visual_component="OUTER_CARTON", defects=("CARTON_DAMAGE", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "DST-DAMAGE", "RTL-PACK")),
    _spec_requirement("SPEC-CARTON-CONDITION", "Secondary Packaging", "Outer carton has no major visible crushing or tearing.", "VISUAL", "Carton visibly intact with acceptable fictional decorative presentation", 13, package_component="OUTER_CARTON", ml_eligible=True, visual_component="OUTER_CARTON", defects=("CARTON_DAMAGE", "PRINT_DEFECT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "DST-DAMAGE", "RTL-PACK")),
    _spec_requirement("SPEC-CARTON-IDENTITY", "Secondary Packaging", "Product and carton identities match.", "IDENTITY", "Carton and product identity consistent", 14, package_component="OUTER_CARTON", quality_check_codes=("MFG-PACK", "RTL-LABEL")),
    _spec_requirement("SPEC-APPEARANCE-RECORD", "Finished Product Appearance", "A finished-product appearance record is present.", "DOCUMENTATION", "Human appearance review recorded", 15, evidence_expectation="Finished-product inspection record.", quality_check_codes=("MFG-FINISHED",)),
    _spec_requirement("SPEC-VISIBLE-CONTAMINATION", "Finished Product Appearance", "No obvious visible contamination is recorded.", "PHYSICAL", "Expected fictional presentation confirmed without obvious visible contamination", 16, quality_check_codes=("MFG-FINISHED",)),
]


EVIDENCE_ISSUERS = [
    {"issuer_code": "LUMINA_ACTIVES", "issuer_name": "Lumina Actives", "issuer_type": "SUPPLIER", "organization_name": "Lumina Actives", "jurisdiction": "DEMO", "trust_status": "TRUSTED_DEMO", "verification_method": "Seeded local demo organization mapping", "notes": "Fictional supplier identity for educational evidence attribution."},
    {"issuer_code": "AURELIA_QC_LAB_DEMO", "issuer_name": "Aurelia QC Laboratory — Fictional Demo", "issuer_type": "LABORATORY", "organization_name": "Aurelia Manufacturing Atelier", "jurisdiction": "DEMO", "trust_status": "TRUSTED_DEMO", "verification_method": "Seeded fictional laboratory mapping", "notes": "Fictional Demo only. No accreditation, licence, or external laboratory verification is claimed."},
    {"issuer_code": "AURELIA_MANUFACTURING", "issuer_name": "Aurelia Manufacturing Atelier", "issuer_type": "MANUFACTURER", "organization_name": "Aurelia Manufacturing Atelier", "jurisdiction": "DEMO", "trust_status": "TRUSTED_DEMO", "verification_method": "Seeded local demo organization mapping", "notes": "Fictional manufacturer evidence issuer."},
    {"issuer_code": "PRESTIGE_BEAUTY_DISTRIBUTION", "issuer_name": "Prestige Beauty Distribution", "issuer_type": "DISTRIBUTOR", "organization_name": "Prestige Beauty Distribution", "jurisdiction": "DEMO", "trust_status": "TRUSTED_DEMO", "verification_method": "Seeded local demo organization mapping", "notes": "Fictional distributor evidence issuer."},
    {"issuer_code": "MAISON_LUXE_RETAIL", "issuer_name": "Maison Luxe Retail", "issuer_type": "RETAILER", "organization_name": "Maison Luxe Retail", "jurisdiction": "DEMO", "trust_status": "TRUSTED_DEMO", "verification_method": "Seeded local demo organization mapping", "notes": "Fictional retailer evidence issuer."},
    {"issuer_code": "UNVERIFIED_FIXTURE_ISSUER", "issuer_name": "Unverified Fixture Issuer — Fictional Demo", "issuer_type": "INTERNAL_TEST_FIXTURE", "organization_name": "OriginChain", "jurisdiction": "DEMO", "trust_status": "UNVERIFIED", "verification_method": "Not verified", "notes": "Negative-test issuer. Not trusted and not accredited."},
]


QUALITY_PROFILE = {
    "profile_code": "INDIA_LUXURY_FACIAL_SERUM_DEMO_V1",
    "name": "India Luxury Facial Serum Demonstration Profile",
    "description": "Evidence-oriented quality gates for a fictional aqueous luxury facial serum supply chain in India.",
    "jurisdiction": "INDIA",
    "version": "1.0",
    "status": "ACTIVE",
    "product_category": PRODUCT_CATEGORY,
    "product_subcategory": PRODUCT_SUBCATEGORY,
    "product_type": PRODUCT_TYPE,
    "disclaimer": (
        "Educational traceability profile only. A mapped source indicates why evidence may be relevant; "
        "it does not certify product compliance, laboratory validity, regulatory approval, or market authorization."
    ),
}


# Metadata and short interpretations only. Copyrighted standards text and numeric limits are not stored.
QUALITY_SOURCES = [
    {
        "source_code": "INDIA_COSMETICS_RULES_2020", "authority": "CDSCO / Ministry of Health and Family Welfare",
        "title": "Cosmetics Rules, 2020", "jurisdiction": "INDIA", "source_type": "REGULATION",
        "edition": "2020, as amended", "publication_year": 2020, "status": "PUBLISHED_CURRENT",
        "source_url": "https://www.cdsco.gov.in/opencms/en/Acts-and-rules/Cosmetics-Rules/",
        "last_verified_at": "2026-08-30", "revision_of_source_code": None,
        "notes": "Mapped only to high-level batch, product, manufacturer and date label traceability in this demo.",
    },
    {
        "source_code": "BIS_IS_4707_PART2_2025", "authority": "Bureau of Indian Standards",
        "title": "Classification of Cosmetic Raw Materials and Adjuncts — Part 2: List of GNRAS and Restricted Ingredients",
        "jurisdiction": "INDIA", "source_type": "STANDARD", "edition": "Fifth Revision, 2025",
        "publication_year": 2025, "status": "PUBLISHED_CURRENT",
        "source_url": "https://www.services.bis.gov.in/tmp/PCD5517644_19062025_1.pdf",
        "last_verified_at": "2026-08-30", "revision_of_source_code": None,
        "notes": "Used only to require documented ingredient specification/restriction review; no lists or limits are reproduced.",
    },
    {
        "source_code": "BIS_IS_14648_2011", "authority": "Bureau of Indian Standards",
        "title": "Microbiological Examination of Cosmetics and Cosmetic Raw Materials — Methods of Test",
        "jurisdiction": "INDIA", "source_type": "STANDARD", "edition": "Second Revision, 2011",
        "publication_year": 2011, "status": "PUBLISHED_UNDER_REVISION",
        "source_url": "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/Group_wise_standards_list/show_scope?row=NjU3Mw%3D%3D",
        "last_verified_at": "2026-08-30", "revision_of_source_code": None,
        "notes": "A third-revision project appears in the BIS programme of work; this demo stores no test procedure or limit.",
    },
    {
        "source_code": "ISO_22716_2007", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Good Manufacturing Practices (GMP) — Guidelines on Good Manufacturing Practices",
        "jurisdiction": "INTERNATIONAL", "source_type": "STANDARD", "edition": "Edition 1, 2007",
        "publication_year": 2007, "status": "PUBLISHED_CURRENT",
        "source_url": "https://www.iso.org/standard/36437.html", "last_verified_at": "2026-08-30",
        "revision_of_source_code": None,
        "notes": "Mapped to manufacturing controls only; the published scope excludes distribution of finished products.",
    },
    {
        "source_code": "ISO_17516_2014", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Microbiology — Microbiological Limits",
        "jurisdiction": "INTERNATIONAL", "source_type": "STANDARD", "edition": "Edition 1, 2014",
        "publication_year": 2014, "status": "PUBLISHED_UNDER_REVISION",
        "source_url": "https://www.iso.org/standard/59938.html", "last_verified_at": "2026-08-30",
        "revision_of_source_code": None,
        "notes": "Mapped as a reason to retain microbiology evidence; the app reproduces no limits.",
    },
    {
        "source_code": "ISO_FDIS_17516_ED2", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Microbiology — Microbiological Limits",
        "jurisdiction": "INTERNATIONAL", "source_type": "STANDARD", "edition": "Edition 2, Final Draft",
        "publication_year": 2026, "status": "DRAFT", "source_url": "https://www.iso.org/standard/93634.html",
        "last_verified_at": "2026-08-30", "revision_of_source_code": "ISO_17516_2014",
        "notes": "Lifecycle visibility only. A draft is never used as the active requirement mapping.",
    },
    {
        "source_code": "ISO_11930_2019_AMD1_2022", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Microbiology — Evaluation of the Antimicrobial Protection of a Cosmetic Product",
        "jurisdiction": "INTERNATIONAL", "source_type": "STANDARD", "edition": "Edition 2, 2019 + Amendment 1:2022",
        "publication_year": 2022, "status": "PUBLISHED_UNDER_REVISION",
        "source_url": "https://www.iso.org/standard/75058.html", "last_verified_at": "2026-08-30",
        "revision_of_source_code": None,
        "notes": "Mapped to preservation-efficacy evidence for the aqueous demo serum; no criteria or procedure are copied.",
    },
    {
        "source_code": "ISO_CD_11930_ED3", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Microbiology — Evaluation of the Antimicrobial Protection of a Cosmetic Product",
        "jurisdiction": "INTERNATIONAL", "source_type": "STANDARD", "edition": "Edition 3, Committee Draft",
        "publication_year": 2026, "status": "DRAFT", "source_url": "https://committee.iso.org/standard/91164.html",
        "last_verified_at": "2026-08-30", "revision_of_source_code": "ISO_11930_2019_AMD1_2022",
        "notes": "Lifecycle visibility only. Not mapped to an active requirement.",
    },
    {
        "source_code": "ISO_29621_2017", "authority": "International Organization for Standardization",
        "title": "Cosmetics — Microbiology — Guidelines for the Risk Assessment and Identification of Microbiologically Low-Risk Products",
        "jurisdiction": "INTERNATIONAL", "source_type": "GUIDANCE", "edition": "Edition 2, 2017",
        "publication_year": 2017, "status": "PUBLISHED_CURRENT",
        "source_url": "https://www.iso.org/standard/68310.html", "last_verified_at": "2026-08-30",
        "revision_of_source_code": None,
        "notes": "The fictional aqueous serum is not presumed low-risk; any exception would require a documented assessment.",
    },
]


def _requirement(
    code: str, category: str, check_name: str, requirement: str, classification: str,
    rationale: str, evidence_expectation: str, *, evidence_required: bool = False,
    expected_document_type: str = "OTHER", sources: tuple[str, ...] = (),
    trusted_issuer_required: bool = False,
    package_component: str | None = None, expected_visual_characteristic: str | None = None,
    defect_categories: tuple[str, ...] = (),
) -> dict:
    return {
        "code": code, "category": category, "check_name": check_name,
        "requirement_description": requirement, "required": True,
        "evidence_required": evidence_required, "classification": classification,
        "requirement_rationale": rationale, "evidence_expectation": evidence_expectation,
        "expected_document_type": expected_document_type, "sources": sources,
        "trusted_issuer_required": trusted_issuer_required,
        "package_component": package_component,
        "expected_visual_characteristic": expected_visual_characteristic,
        "defect_categories": defect_categories,
    }


# Each interpretation is deliberately high-level. Mappings mean traceability, never certification.
DEMO_QUALITY_STANDARDS = [
    _requirement("RM-IDENTITY", "Material Identity", "Material and Supplier Lot Traceability", "Material name, supplier and supplier-lot identifiers agree with the received record.", "ORIGINCHAIN_INTERNAL", "Creates upstream identifiers that a manufacturer can reconcile during incoming-material control.", "Receiving record or supplier identification documentation."),
    _requirement("RM-PHYSICAL", "Physical Inspection", "Physical Condition Inspection", "Appearance and received-container condition meet the fictional organization specification.", "ORIGINCHAIN_INTERNAL", "An operational demo gate for visible receipt condition.", "Inspection note; optional image evidence."),
    _requirement("RM-COA", "Documentation", "Certificate of Analysis Traceability", "A supplier Certificate of Analysis is attached and traceable to the supplier lot.", "ORIGINCHAIN_INTERNAL", "Retains upstream evidence for later manufacturer review without asserting laboratory validity.", "Certificate of Analysis associated with the supplier lot and an accepted fictional supplier/laboratory issuer.", evidence_required=True, expected_document_type="CERTIFICATE_OF_ANALYSIS", trusted_issuer_required=True),
    _requirement("RM-RESTRICTIONS", "Documentation", "Ingredient Specification and Restriction Review", "A documented raw-material specification/restriction review is attached for the intended cosmetic use.", "STANDARD_BASED", "Makes the ingredient review evidence traceable to the current Indian profile without reproducing controlled lists.", "Raw-material specification or signed review record.", evidence_required=True, expected_document_type="RAW_MATERIAL_SPECIFICATION", sources=("BIS_IS_4707_PART2_2025",)),
    _requirement("RM-PACKAGING", "Packaging Components", "Received Container Integrity", "The incoming container or component is intact under the fictional organization inspection procedure.", "ORIGINCHAIN_INTERNAL", "An operational visual gate, not an external-standard claim.", "Inspection note; optional packaging image.", package_component="INCOMING_CONTAINER", expected_visual_characteristic="Closed, clean and visibly undamaged", defect_categories=("CONTAINER_DAMAGE", "CONTAMINATION", "LEAKAGE")),
    _requirement("MFG-INCOMING", "Incoming Material Verification", "Approved Incoming Materials", "Every linked raw-material batch has completed the supplier evidence gates.", "STANDARD_BASED", "Connects upstream evidence to controlled manufacturing inputs.", "Linked supplier approvals and receiving records.", sources=("ISO_22716_2007",)),
    _requirement("MFG-LINEAGE", "Production Batch", "Ingredient and Component Lineage", "Ingredient and component identifiers are linked to the finished batch.", "STANDARD_BASED", "Provides auditable batch traceability for manufacturing records.", "Batch manufacturing record or lineage record.", sources=("ISO_22716_2007",)),
    _requirement("MFG-FINISHED", "Finished Product Quality", "Finished Product Inspection", "Appearance, colour, odour and fill are reviewed against the fictional approved product specification.", "ORIGINCHAIN_INTERNAL", "Product-specific acceptance characteristics are organization-controlled and are not invented as external limits.", "Finished-product inspection record."),
    _requirement("MFG-MICROBIOLOGY", "Finished Product Quality", "Microbiology Evidence Review", "A microbiology report is attached and traceable to the finished batch and stated test method.", "STANDARD_BASED", "Retains batch-specific microbiology evidence without encoding numeric limits or declaring a pass on behalf of a laboratory.", "Laboratory microbiology report with report reference, method, test date, and accepted fictional laboratory issuer.", evidence_required=True, expected_document_type="MICROBIOLOGY_REPORT", sources=("BIS_IS_14648_2011", "ISO_17516_2014"), trusted_issuer_required=True),
    _requirement("MFG-PRESERVATION", "Finished Product Quality", "Preservation-Efficacy Evidence Review", "Preservation-efficacy evidence is attached for the fictional aqueous serum; it is not presumed microbiologically low-risk.", "STANDARD_BASED", "Records the evidence basis for antimicrobial protection and any documented risk assessment.", "Preservative-efficacy report with accepted fictional laboratory issuer and, where used, a documented low-risk assessment rationale.", evidence_required=True, expected_document_type="PRESERVATIVE_EFFICACY_REPORT", sources=("ISO_11930_2019_AMD1_2022", "ISO_29621_2017"), trusted_issuer_required=True),
    _requirement("MFG-LABEL-TRACEABILITY", "Packaging and Labelling", "Indian Label Traceability Fields", "Product, manufacturer, batch and use-before/expiry fields are present and legible on the fictional batch label.", "REGULATORY", "Maps only high-level traceability fields represented in the Cosmetics Rules; it is not a complete label compliance assessment.", "Dated packaging/label inspection record.", evidence_required=True, expected_document_type="PACKAGING_INSPECTION", sources=("INDIA_COSMETICS_RULES_2020",), package_component="PRIMARY_LABEL", expected_visual_characteristic="Required traceability fields present and legible", defect_categories=("MISSING_FIELD", "ILLEGIBLE_PRINT", "BATCH_MISMATCH")),
    _requirement("MFG-PACK", "Packaging and Labelling", "Luxury Primary-Pack Inspection", "Bottle, dropper, label and security seal meet the fictional Aurelia packaging specification.", "ORIGINCHAIN_INTERNAL", "A product-specific visual quality gate prepared for future defect-detection assistance.", "Packaging inspection record or image evidence.", evidence_required=True, expected_document_type="PACKAGING_INSPECTION", package_component="BOTTLE_DROPPER_LABEL_SEAL", expected_visual_characteristic="Aligned, sealed, clean and visibly undamaged", defect_categories=("SEAL_DAMAGE", "LABEL_MISALIGNMENT", "DROPPER_DAMAGE", "LEAKAGE", "SURFACE_DEFECT")),
    _requirement("MFG-RELEASE", "Batch Release", "Manufacturing Record Review", "The batch manufacturing and quality evidence record has been reviewed for internal release.", "STANDARD_BASED", "Represents a documented manufacturing release decision without asserting regulatory release.", "Reviewed batch manufacturing record.", evidence_required=True, expected_document_type="BATCH_MANUFACTURING_RECORD", sources=("ISO_22716_2007",)),
    _requirement("DST-RECEIVING", "Receiving Inspection", "Distribution Receipt Inspection", "Batch identity, quantity and packaging condition match the shipment record.", "ORIGINCHAIN_INTERNAL", "An internal custody gate; ISO 22716 is deliberately not mapped because its scope excludes finished-product distribution.", "Receiving inspection record."),
    _requirement("DST-LOGISTICS", "Logistics", "Chain-of-Custody Documentation", "Shipment and custody documents are attached and traceable to the batch.", "ORIGINCHAIN_INTERNAL", "Preserves operational provenance between manufacturer and retailer.", "Shipment or transport record.", evidence_required=True, expected_document_type="TRANSPORT_RECORD"),
    _requirement("DST-STORAGE", "Storage", "Storage Condition Acknowledgement", "The fictional organization storage requirements were acknowledged and checked.", "ORIGINCHAIN_INTERNAL", "Product-specific storage controls require organization-defined criteria.", "Storage inspection note or log."),
    _requirement("DST-DAMAGE", "Damage Inspection", "Distribution Damage Inspection", "No visible carton, bottle, seal or leakage damage is recorded.", "ORIGINCHAIN_INTERNAL", "A visual operational gate structured for potential future image-assistance.", "Inspection note; optional image evidence.", package_component="SHIPPER_AND_PRIMARY_PACK", expected_visual_characteristic="Visibly intact with no leakage", defect_categories=("CARTON_DAMAGE", "BOTTLE_DAMAGE", "SEAL_DAMAGE", "LEAKAGE")),
    _requirement("DST-RELEASE", "Distributor Release", "Retailer Transfer Release", "The distributor has reviewed the internal receiving, custody, storage and damage gates.", "ORIGINCHAIN_INTERNAL", "A workflow release decision, not a regulatory certification.", "Distributor release note."),
    _requirement("RTL-AUTH", "Authenticity Verification", "Blockchain Authenticity and Custody", "Blockchain identity and custody history match the received fictional product.", "ORIGINCHAIN_INTERNAL", "OriginChain-specific provenance control.", "Automated blockchain verification record."),
    _requirement("RTL-PACK", "Packaging Inspection", "Security Seal and Luxury Pack Inspection", "The received bottle, dropper, label and security seal meet the fictional retail visual specification.", "ORIGINCHAIN_INTERNAL", "A retail visual gate with structured defect categories for possible future image assistance.", "Retail packaging inspection evidence.", evidence_required=True, expected_document_type="RETAIL_INSPECTION", package_component="BOTTLE_DROPPER_LABEL_SEAL", expected_visual_characteristic="Seal intact; pack clean, aligned and undamaged", defect_categories=("SEAL_DAMAGE", "LABEL_MISALIGNMENT", "DROPPER_DAMAGE", "LEAKAGE", "SURFACE_DEFECT")),
    _requirement("RTL-LABEL", "Label Inspection", "Retail Label Traceability Review", "Product, manufacturer, batch and use-before/expiry fields are present, legible and consistent with the batch record.", "REGULATORY", "A narrow traceability-field review, not a full legal label determination.", "Retail label inspection note or image.", sources=("INDIA_COSMETICS_RULES_2020",)),
    _requirement("RTL-EXPIRY", "Shelf / Sale Readiness", "Stored Expiry-Date Review", "The stored use-before/expiry value is present and has not passed at the time of retail review.", "REGULATORY", "Connects the demo's expiry gate to the high-level date-labelling source while leaving legal interpretation to qualified reviewers.", "Retail date-field inspection record.", sources=("INDIA_COSMETICS_RULES_2020",)),
    _requirement("RTL-SHELF", "Shelf / Sale Readiness", "Upstream Quality-Gate Review", "No upstream stage is pending, held or rejected before sale readiness is considered.", "ORIGINCHAIN_INTERNAL", "An OriginChain workflow dependency independent of external compliance status.", "Automated upstream approval summary."),
    _requirement("RTL-FINAL", "Retail Final Approval", "Retail Release Review", "The retailer has reviewed authenticity, packaging, label, date and upstream quality gates before sale.", "ORIGINCHAIN_INTERNAL", "Final internal demo decision; it is not market authorization or compliance certification.", "Retail release record.", evidence_required=True, expected_document_type="RETAIL_INSPECTION"),
]


STAGE_PREFIX = {
    SupplyChainStage.RAW_MATERIAL_SUPPLIER: "RM-",
    SupplyChainStage.MANUFACTURER: "MFG-",
    SupplyChainStage.DISTRIBUTOR: "DST-",
    SupplyChainStage.RETAILER: "RTL-",
}


STAGE_DISPLAY = {
    SupplyChainStage.RAW_MATERIAL_SUPPLIER: "Raw Materials",
    SupplyChainStage.MANUFACTURER: "Manufacturing",
    SupplyChainStage.DISTRIBUTOR: "Distribution",
    SupplyChainStage.RETAILER: "Retail Inspection",
}
