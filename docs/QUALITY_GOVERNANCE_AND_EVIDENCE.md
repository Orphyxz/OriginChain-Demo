# Quality Governance and Evidence Trust

## Scope and disclaimer

This design applies to the fictional `Aurelia Prestige Renewal Serum` local demonstration. The specification, actors, issuers, reports, and test data are fictional. `TRUSTED_DEMO` and `VERIFIED_DEMO` are OriginChain workflow states; they do not mean certified, accredited, legally compliant, regulator-approved, or laboratory-validated.

## Product specifications

`product_specifications` is the versioned parent. `product_specification_requirements` holds stable normalized requirements, and `quality_standard_specification_requirements` maps them to reusable stage checks.

Seeded V1 is `AURELIA_PRESTIGE_RENEWAL_SERUM_SPEC_V1`, version `1.0`, with 16 requirements covering:

- product/brand/batch identity;
- bottle and dropper configuration/condition;
- security-seal presence and visible integrity;
- label presence/alignment and print condition;
- carton presence, condition, and identity;
- finished-product appearance and visible-contamination review.

Selected requirements contain `ml_eligible`, `visual_component`, expected characteristics, and defect-category metadata. These support consistent human inspections and possible future dataset design. No model, inference, score, synthetic result, or compliance prediction exists.

Manufacturer registration can select only an active, approved, effective specification matching `ANTI_AGING_SERUM`. Each product stores the assigned code, version, deterministic snapshot hash, and timestamp. Once assigned, database guards prevent semantic identity/content changes, requirement changes, or deletion. Lifecycle fields may mark V1 superseded/retired for future use, but a content revision must be V2 and an existing V1 batch remains V1.

## Evidence issuer registry

The registry contains six fictional issuers:

| Code | Type | Initial state |
|---|---|---|
| `LUMINA_ACTIVES` | Supplier | `TRUSTED_DEMO` |
| `AURELIA_QC_LAB_DEMO` | Laboratory | `TRUSTED_DEMO` |
| `AURELIA_MANUFACTURING` | Manufacturer | `TRUSTED_DEMO` |
| `PRESTIGE_BEAUTY_DISTRIBUTION` | Distributor | `TRUSTED_DEMO` |
| `MAISON_LUXE_RETAIL` | Retailer | `TRUSTED_DEMO` |
| `UNVERIFIED_FIXTURE_ISSUER` | Internal test fixture | `UNVERIFIED` |

The laboratory name and notes explicitly identify it as a Fictional Demo with no accreditation claim. The backend resolves an issuer code to registry metadata; clients cannot submit their own trust state.

## File integrity is not issuer trust

| Question | Stored result | Meaning |
|---|---|---|
| Do the bytes still match? | `VERIFIED`, `MISMATCH`, `FILE_MISSING` | Keccak-256 comparison of the actual stored file bytes |
| Did local reference controls accept the attribution? | `VERIFIED_DEMO`, `UNVERIFIED`, `REJECTED` | Server decision using registered issuer, issuer type, local trust state, and required report reference |

A valid hash cannot prove who created a document. A trusted demo issuer cannot prove that later-modified bytes are intact. Both concepts are displayed independently.

Critical gates:

- raw-material COA: trusted supplier or laboratory plus report number;
- microbiology report: trusted laboratory plus report number;
- preservation-efficacy report: trusted laboratory plus report number.

Optional photographs and ordinary visual records do not need a trusted issuer merely because they are files.

## Frozen issuer snapshots and revocation

Evidence stores issuer ID for lookup and freezes issuer code, name, type, trust-at-submission, report number, and document date. The live registry status is joined separately.

If an issuer changes from `TRUSTED_DEMO` to `REVOKED`:

1. Existing evidence still records that it was accepted while the issuer was Trusted Demo.
2. Existing approved stages are not silently rewritten; operational views display a current-status warning.
3. New critical evidence from the issuer is stored as `UNVERIFIED` and cannot satisfy its stage gate.
4. The Admin mutation requires a reason and creates both a governance change record and an audit event.

This preserves historical truth while making the current risk visible.

## Source review and change control

Every seeded source records a review owner, reviewer, review date, review state, and next-review due date. The Admin-only governance view displays these fields.

`quality_change_records` captures:

- change type and target;
- previous and new version/state;
- concise change summary and mandatory reason;
- requester, approver, status, creation time, and approval time.

Source changes affect future unsubmitted checks; existing `quality_result_sources` keep their frozen edition/status. Product changes use a new specification version. Issuer changes do not mutate evidence snapshots. This is lightweight demonstrator governance, not a validated electronic QMS, digital-signature, or formal CAPA system.

## API and RBAC boundary

Authenticated actors can read applicable specification and issuer registries. Manufacturer assigns an approved spec during product registration. Distributor and Retailer see the assigned summary and mapped checks. Admin alone can read source reviews/change records and mutate issuer trust. Public verification has no governance endpoints.

The consumer response may state that the product configuration was verified against recorded specification version 1 and may show a safe issuer name on public evidence. It excludes internal requirements/defects, change reasons, review ownership, issuer notes, registry-management state, internal user IDs, and internal evidence.

## Reset and blockchain boundary

Demo reset removes products, links, results, approvals, evidence rows, transfers, raw-material batches, and uploaded files. It preserves product specifications/requirements, issuer registry, sources/profiles, source reviews, change records, users, and audit history.

The Solidity schema is unchanged in this phase. Stage commitments already store a compact deterministic hash; the hashed snapshot now includes specification code/version/hash and compact issuer trust-at-submission fields. Full specifications, issuer notes, reviews, and change reasons remain off-chain.

## Future production work

Production use would require verified organizational identity, cryptographic document signing, certificate/key lifecycle and revocation semantics, accredited-lab verification, qualified regulatory ownership, formal approval workflows/e-signatures, immutable external audit storage, malware scanning, secure object storage, production IAM and custody, and jurisdiction-specific legal review.
