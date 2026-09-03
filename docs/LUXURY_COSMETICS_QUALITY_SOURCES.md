# Luxury Cosmetics Quality Sources

## Scope

This document records the official primary sources reviewed for `INDIA_LUXURY_FACIAL_SERUM_DEMO_V1`. All entries were last verified on **2026-08-30**. OriginChain stores source metadata and short original interpretations; it does not reproduce controlled standards, laboratory methods, tables, ingredient lists, or numeric limits.

A mapping means: “this source gives a defensible reason to retain or inspect this category of evidence.” It does **not** mean that OriginChain has established applicability, interpreted every obligation, certified compliance, validated a laboratory/report, granted approval, or authorized a cosmetic for sale. A qualified regulatory, quality, and laboratory team must make those decisions against licensed/current source material.

## Source Selection Method

Primary official authority pages and documents were preferred: CDSCO/MoHFW for Indian rules, BIS for Indian standards metadata/status, ISO for international standards metadata/status, FDA for US comparison, and EUR-Lex for EU comparison. Commercial certification sites, blogs, search snippets, social posts, and AI summaries are not canonical registry provenance. Exact clauses were not mapped because no licensed standards text was available in the repository.

## India

| Registry code | Official primary source | Lifecycle recorded | OriginChain use |
|---|---|---|---|
| `INDIA_COSMETICS_RULES_2020` | [CDSCO — Cosmetics Rules, 2020 landing page](https://www.cdsco.gov.in/opencms/en/Acts-and-rules/Cosmetics-Rules/) and [official PDF](https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2022/cos_rules/Cosmetics%20Rules%202020.pdf) | Published current; stored as “2020, as amended” | Narrow product/manufacturer/batch/use-before-or-expiry label-traceability gates only. Not a complete label or licensing assessment. |
| `BIS_IS_4707_PART2_2025` | [BIS official Part 2 document](https://www.services.bis.gov.in/tmp/PCD5517644_19062025_1.pdf) | Published current; Fifth Revision, 2025 | Requires a documented ingredient specification/restriction review. No controlled ingredient list or restriction is copied. |
| `BIS_IS_14648_2011` | [BIS official scope page](https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/Group_wise_standards_list/show_scope?row=NjU3Mw%3D%3D) | Published under revision; Second Revision, 2011 | Supports retaining a batch-linked microbiology report. No procedure or result criterion is encoded. |

The [BIS Cosmetics Sectional Committee programme of work](https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/pow_new/Pow/download_pow_pdf_dept_commtt/69/55/) was used to cross-check current editions and revision work. It also identifies IS 4707 Part 1:2020 (colourants), Part 3:2025 (preservatives with restrictions), and Part 4:2022 (UV filters). Those parts are not mapped to the default fictional serum profile because the implemented evidence gates do not make a sufficiently specific claim about a colourant, UV filter, or preservative ingredient. They should be added only when the formula/use case and qualified interpretation make them relevant.

## International

| Registry code | Official primary source | Lifecycle recorded | OriginChain use |
|---|---|---|---|
| `ISO_22716_2007` | [ISO 22716:2007 official page](https://www.iso.org/standard/36437.html) | Published current; Edition 1, confirmed 2022 | High-level manufacturing incoming-material, lineage, and batch-release evidence. It is deliberately not mapped to finished-product distribution. |
| `ISO_17516_2014` | [ISO 17516:2014 official page](https://www.iso.org/standard/59938.html) | Published under revision; Edition 1 | Supports retaining microbiology evidence. No limits are stored. |
| `ISO_FDIS_17516_ED2` | [ISO/FDIS 17516 official page](https://www.iso.org/standard/93634.html) | Draft; Edition 2 Final Draft | Registry lifecycle visibility only; never an active requirement mapping. |
| `ISO_11930_2019_AMD1_2022` | [ISO 11930:2019 official page](https://www.iso.org/standard/75058.html) and [Amendment 1:2022](https://www.iso.org/standard/83708.html) | Published under revision | Supports preservation-efficacy evidence for the fictional aqueous serum. No method or criteria are copied. |
| `ISO_CD_11930_ED3` | [ISO/CD 11930 official committee page](https://committee.iso.org/standard/91164.html) | Draft; Edition 3 Committee Draft | Registry lifecycle visibility only; never an active requirement mapping. |
| `ISO_29621_2017` | [ISO 29621:2017 official page](https://www.iso.org/standard/68310.html) | Published current; Edition 2 | Supports documented low-risk reasoning. This aqueous demo serum is not automatically presumed low-risk. |

## OriginChain Mapping

### Regulatory traceability

`MFG-LABEL-TRACEABILITY`, `RTL-LABEL`, and `RTL-EXPIRY` map to the Cosmetics Rules, 2020. Their wording is limited to the demo's stored identity/date fields. The system does not assess the full label, licence, claims, warnings, pack sizes, ingredient declaration, import status, or amendments.

### Raw-material restriction review

`RM-RESTRICTIONS` maps to IS 4707 Part 2:2025. It requires a traceable specification/review document but stores no ingredient conclusion. A `PASS` means the fictional actor recorded completion of the OriginChain gate; it is not a BIS compliance determination.

### Manufacturing practice

`MFG-INCOMING`, `MFG-LINEAGE`, and `MFG-RELEASE` map to ISO 22716:2007 at standard level. Supplier checks remain upstream/internal evidence gates, while distributor checks remain internal custody/storage/visual gates. This avoids extending ISO 22716 beyond its published scope.

### Microbiology

`MFG-MICROBIOLOGY` maps to IS 14648:2011 and ISO 17516:2014. The combination represents method-context and microbiological-limits context at a high level, but OriginChain performs neither test nor result interpretation. The expected evidence is a microbiology report with optional issuer, reference, date, and registered method-source metadata.

### Preservation and low-risk reasoning

`MFG-PRESERVATION` maps to ISO 11930:2019 with Amendment 1:2022 and ISO 29621:2017. The fictional product is an aqueous facial serum, so the profile requests preservation-efficacy evidence and does not silently invoke a low-risk exception. The application contains no challenge-test protocol or acceptance criteria.

### Internal visual and workflow gates

Luxury bottle/dropper/label/seal inspection, transport custody, storage acknowledgement, damage inspection, upstream approval, blockchain authenticity, and final workflow release remain `ORIGINCHAIN_INTERNAL`. Structured package components, expected visual characteristics, and defect-category labels are included for consistency and possible future rights-cleared ML research. They are not external requirements and no AI model is currently implemented.

### Concise mapping matrix

| Stage | Requirement code(s) | Classification | Active source(s) | Expected evidence |
|---|---|---|---|---|
| Raw material | `RM-RESTRICTIONS` | Standard-based | IS 4707 Part 2:2025 | Raw-material specification/review |
| Raw material | `RM-IDENTITY`, `RM-PHYSICAL`, `RM-COA`, `RM-PACKAGING` | OriginChain internal | — | Receipt record, COA, inspection as defined by the demo |
| Manufacturer | `MFG-INCOMING`, `MFG-LINEAGE`, `MFG-RELEASE` | Standard-based | ISO 22716:2007 | Linked approvals, lineage, batch record |
| Manufacturer | `MFG-MICROBIOLOGY` | Standard-based | IS 14648:2011; ISO 17516:2014 | Microbiology report |
| Manufacturer | `MFG-PRESERVATION` | Standard-based | ISO 11930:2019/Amd 1:2022; ISO 29621:2017 | Preservation-efficacy report/risk rationale |
| Manufacturer | `MFG-LABEL-TRACEABILITY` | Regulatory traceability | Cosmetics Rules, 2020 | Packaging/label inspection |
| Manufacturer | `MFG-FINISHED`, `MFG-PACK` | OriginChain internal | — | Product/pack inspection |
| Distributor | all `DST-*` | OriginChain internal | — | Receipt, transport, storage, damage and release records |
| Retailer | `RTL-LABEL`, `RTL-EXPIRY` | Regulatory traceability | Cosmetics Rules, 2020 | Retail label/date inspection |
| Retailer | remaining `RTL-*` | OriginChain internal | — | Authenticity, pack, upstream and final retail records |

## Source Status

Published-under-revision sources can remain mapped while their lifecycle badge warns the reviewer to check for a replacement. Draft successors appear in the registry but are not active mappings. When a quality result is first submitted, OriginChain snapshots its mapped source code, authority, title, edition, year, lifecycle status, mapping precision, and official URL. Later registry edits do not alter that snapshot.

The seeded governance schedule assigns the fictional OriginChain Admin as review owner/reviewer, records the 2026-08-30 review date, marks sources `CURRENT`, and sets the next review due date to 2027-02-28. These dates document the demo's reference-maintenance workflow; they are not a claim that a regulator, BIS, ISO, or an external professional reviewed this project. Admin can inspect review status and versioned change records. Historical result snapshots remain unchanged when registry metadata or a source lifecycle state later changes.

Maintainers should:

1. Re-verify official URLs and lifecycle states before the recorded review due date.
2. Record the review owner, reviewer, review date/status, and a reasoned change record.
3. Add a successor as a separate versioned source row; do not overwrite historical result snapshots.
4. Review each mapping with a qualified domain owner before changing it.
5. Keep mapping precision at `STANDARD_LEVEL` unless a defensible section/clause reference can be recorded without copying protected content.
6. Never add numeric limits or copyrighted tables unless the project has a lawful source/content strategy and qualified implementation review.

## Comparative Context

The [US FDA MoCRA page](https://www.fda.gov/cosmetics/cosmetics-laws-regulations/modernization-cosmetics-regulation-act-2022-mocra) was reviewed for comparative context. It describes US statutory changes and FDA's cosmetics GMP rulemaking/guidance work; OriginChain does not represent a final US GMP rule and does not map MoCRA into the India profile.

The [EU Cosmetics Regulation (EC) No 1223/2009](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009R1223) was reviewed for comparative GMP, safety-assessment, and product-information-file context. It is not an active source for the India demonstration profile.

These comparative sources may support future jurisdiction-specific profiles. They must not be mixed into a profile merely to make its source list look broader.

## Exclusions

The profile intentionally excludes automated legal interpretation, product registration/licensing, market authorization, government filing/API integration, complete label assessment, formulation safety assessment, numeric product specifications, microbial calculations, challenge-test calculations, heavy-metal/pH/viscosity limits, and automatic laboratory-result evaluation. Unmapped IS 4707 parts and US/EU sources remain research context rather than decorative mappings.

## Limitations

Source URLs and lifecycle states can change after the verification date. Official metadata pages do not replace licensed standards content or professional interpretation. Uploaded evidence can be byte-integrity verified; selected critical documents can also be accepted against the local fictional issuer registry. That `VERIFIED_DEMO` acceptance does not authenticate the real organization, signature, accreditation, method, sample, result, or applicability. All product actors and entered results are fictional educational data; no real laboratory result is seeded.
