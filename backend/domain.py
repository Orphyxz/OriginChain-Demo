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
    STORAGE_RECORD = "STORAGE_RECORD"
    GOODS_RECEIPT = "GOODS_RECEIPT"
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
    _spec_requirement("SPEC-IDENTITY-PRODUCT", "Product Identity", "Product name matches the approved batch record.", "IDENTITY", "Aurelia Prestige Renewal Serum identity confirmed", 1, quality_check_codes=("MFG-FINISHED", "RTL-INSPECTION")),
    _spec_requirement("SPEC-IDENTITY-BRAND", "Product Identity", "Brand identity matches the approved fictional record.", "IDENTITY", "Aurelia Maison identity confirmed", 2, quality_check_codes=("MFG-FINISHED", "RTL-INSPECTION")),
    _spec_requirement("SPEC-IDENTITY-BATCH", "Product Identity", "Batch code is present and readable.", "TRACEABILITY", "Batch identity readable and consistent", 3, package_component="LABEL", ml_eligible=True, visual_component="PRINT", defects=("PRINT_DEFECT", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-LABEL")),
    _spec_requirement("SPEC-BOTTLE-CONFIG", "Primary Packaging", "Bottle model matches the approved fictional configuration.", "PACKAGING", "Fictional Aurelia serum bottle configuration present", 4, package_component="BOTTLE", ml_eligible=True, visual_component="BOTTLE", defects=("BOTTLE_DAMAGE", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-BOTTLE-CONDITION", "Primary Packaging", "Bottle shows no obvious visible crack or leakage.", "VISUAL", "Bottle visibly intact with no leakage", 5, package_component="BOTTLE", ml_eligible=True, visual_component="BOTTLE", defects=("BOTTLE_DAMAGE", "LEAKAGE", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-DROPPER-CONFIG", "Primary Packaging", "Dropper assembly matches the expected fictional configuration and is seated correctly.", "PACKAGING", "Dropper configuration matched and visibly seated", 6, package_component="DROPPER", ml_eligible=True, visual_component="DROPPER", defects=("DROPPER_MISMATCH", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-SEAL-PRESENT", "Security", "Security seal is present.", "PACKAGING", "Security seal present", 7, package_component="SECURITY_SEAL", ml_eligible=True, visual_component="SECURITY_SEAL", defects=("SEAL_DAMAGE", "MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-SEAL-INTEGRITY", "Security", "Security seal has no obvious visible tampering.", "VISUAL", "Seal visibly intact with no tampering indication", 8, package_component="SECURITY_SEAL", ml_eligible=True, visual_component="SECURITY_SEAL", defects=("SEAL_DAMAGE", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-PACK")),
    _spec_requirement("SPEC-LABEL-PRESENT", "Label Presentation", "Product label is present.", "LABEL", "Product label present", 9, package_component="LABEL", ml_eligible=True, visual_component="LABEL", defects=("MISSING_COMPONENT", "UNKNOWN"), quality_check_codes=("MFG-PACK", "RTL-LABEL")),
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
# Every stage has exactly five checks: two inspections, two certificates and one final review.
CHECK = "Check"
CERTIFICATE = "Certificate"
FINAL_REVIEW = "Final review"

DEMO_QUALITY_STANDARDS = [
    _requirement("RM-IDENTITY", CHECK, "Material identity", "Name, supplier and lot number match the delivery.", "ORIGINCHAIN_INTERNAL", "Lets the manufacturer reconcile each input with its supplier lot.", "Receiving record."),
    _requirement("RM-CONDITION", CHECK, "Container condition", "Container is sealed, clean and undamaged.", "ORIGINCHAIN_INTERNAL", "A visual receipt check, not an external-standard claim.", "Inspection note; optional photo.", package_component="INCOMING_CONTAINER", expected_visual_characteristic="Closed, clean and visibly undamaged", defect_categories=("CONTAINER_DAMAGE", "CONTAMINATION", "LEAKAGE")),
    _requirement("RM-COA", CERTIFICATE, "Certificate of Analysis", "Supplier lab certificate for this lot, from a trusted issuer.", "ORIGINCHAIN_INTERNAL", "Keeps upstream lab evidence without asserting laboratory validity.", "Certificate of Analysis from an accepted fictional issuer.", evidence_required=True, expected_document_type="CERTIFICATE_OF_ANALYSIS", trusted_issuer_required=True),
    _requirement("RM-RESTRICTIONS", CERTIFICATE, "Ingredient safety review", "Signed review that the ingredient is permitted for this use.", "STANDARD_BASED", "Traces the ingredient review to the Indian profile without reproducing controlled lists.", "Raw-material specification or signed review.", evidence_required=True, expected_document_type="RAW_MATERIAL_SPECIFICATION", sources=("BIS_IS_4707_PART2_2025",)),
    _requirement("RM-RELEASE", FINAL_REVIEW, "Supplier release", "All supplier checks reviewed; batch released to manufacturing.", "ORIGINCHAIN_INTERNAL", "A workflow release decision, not a certification.", "Release note."),
    _requirement("MFG-FINISHED", CHECK, "Product appearance", "Colour, scent and fill match the product specification.", "ORIGINCHAIN_INTERNAL", "Acceptance characteristics are organization-controlled, not invented external limits.", "Finished-product inspection note."),
    _requirement("MFG-PACK", CHECK, "Bottle, seal and label", "Bottle, dropper and seal intact; label shows product, maker, batch and expiry.", "REGULATORY", "Maps only the high-level label traceability fields in the Cosmetics Rules; not a full label assessment.", "Packaging inspection note or photo.", sources=("INDIA_COSMETICS_RULES_2020",), package_component="BOTTLE_DROPPER_LABEL_SEAL", expected_visual_characteristic="Sealed, aligned, legible and undamaged", defect_categories=("SEAL_DAMAGE", "LABEL_MISALIGNMENT", "DROPPER_DAMAGE", "MISSING_FIELD", "LEAKAGE")),
    _requirement("MFG-MICROBIOLOGY", CERTIFICATE, "Microbiology report", "Lab report for this batch, from a trusted laboratory.", "STANDARD_BASED", "Keeps batch microbiology evidence without encoding limits or declaring a lab result.", "Laboratory report with reference, method and date.", evidence_required=True, expected_document_type="MICROBIOLOGY_REPORT", sources=("BIS_IS_14648_2011", "ISO_17516_2014"), trusted_issuer_required=True),
    _requirement("MFG-PRESERVATION", CERTIFICATE, "Preservation test report", "Lab report showing the preservative protects the serum.", "STANDARD_BASED", "Records the evidence basis for antimicrobial protection; the aqueous serum is not presumed low-risk.", "Preservative-efficacy report from an accepted fictional laboratory.", evidence_required=True, expected_document_type="PRESERVATIVE_EFFICACY_REPORT", sources=("ISO_11930_2019_AMD1_2022", "ISO_29621_2017"), trusted_issuer_required=True),
    _requirement("MFG-RELEASE", FINAL_REVIEW, "Batch release", "Manufacturing record reviewed; batch released for shipping.", "STANDARD_BASED", "A documented manufacturing release, not a regulatory release.", "Reviewed batch record.", sources=("ISO_22716_2007",)),
    _requirement("DST-RECEIVING", CHECK, "Shipment received", "Batch and quantity match the shipping record.", "ORIGINCHAIN_INTERNAL", "An internal custody check; ISO 22716 excludes finished-product distribution.", "Receiving note."),
    _requirement("DST-DAMAGE", CHECK, "Damage inspection", "No damaged cartons, bottles, seals or leaks.", "ORIGINCHAIN_INTERNAL", "A visual check structured for possible future image assistance.", "Inspection note; optional photo.", package_component="SHIPPER_AND_PRIMARY_PACK", expected_visual_characteristic="Visibly intact with no leakage", defect_categories=("CARTON_DAMAGE", "BOTTLE_DAMAGE", "SEAL_DAMAGE", "LEAKAGE")),
    _requirement("DST-LOGISTICS", CERTIFICATE, "Shipping record", "Transport and custody document for this batch.", "ORIGINCHAIN_INTERNAL", "Preserves provenance between manufacturer and retailer.", "Shipping or transport record.", evidence_required=True, expected_document_type="TRANSPORT_RECORD"),
    _requirement("DST-STORAGE", CERTIFICATE, "Storage log", "Warehouse log showing the batch was stored correctly.", "ORIGINCHAIN_INTERNAL", "Storage criteria are organization-defined.", "Storage or temperature log.", evidence_required=True, expected_document_type="STORAGE_RECORD"),
    _requirement("DST-RELEASE", FINAL_REVIEW, "Release to retailer", "All distribution checks reviewed; ready to hand over.", "ORIGINCHAIN_INTERNAL", "A workflow release decision, not a certification.", "Release note."),
    _requirement("RTL-PACK", CHECK, "Seal and packaging", "Seal intact; bottle, dropper and box clean and undamaged.", "ORIGINCHAIN_INTERNAL", "The retail visual check with structured defect categories.", "Inspection note; optional photo.", package_component="BOTTLE_DROPPER_LABEL_SEAL", expected_visual_characteristic="Seal intact; pack clean, aligned and undamaged", defect_categories=("SEAL_DAMAGE", "LABEL_MISALIGNMENT", "DROPPER_DAMAGE", "LEAKAGE", "SURFACE_DEFECT")),
    _requirement("RTL-LABEL", CHECK, "Label and expiry date", "Label is legible and the expiry date has not passed.", "REGULATORY", "A narrow traceability-field review, not a legal label determination.", "Label inspection note.", sources=("INDIA_COSMETICS_RULES_2020",)),
    _requirement("RTL-RECEIPT", CERTIFICATE, "Goods receipt note", "Signed receipt for the delivered batch.", "ORIGINCHAIN_INTERNAL", "Closes the custody chain at the shop.", "Goods receipt note.", evidence_required=True, expected_document_type="GOODS_RECEIPT"),
    _requirement("RTL-INSPECTION", CERTIFICATE, "Retail inspection report", "Shop inspection record for this batch.", "ORIGINCHAIN_INTERNAL", "Retail evidence behind the sale decision.", "Retail inspection report.", evidence_required=True, expected_document_type="RETAIL_INSPECTION"),
    _requirement("RTL-FINAL", FINAL_REVIEW, "Approve for sale", "Everything above reviewed; product may go on sale.", "ORIGINCHAIN_INTERNAL", "Final internal decision; not market authorization.", "Release note."),
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
