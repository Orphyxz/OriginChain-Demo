# Luxury Cosmetics Quality Architecture

## Scope

This phase models one fictional luxury anti-aging facial serum. Its evidence gates can reference verified metadata for official sources, while the requirements remain educational interpretations rather than legal, laboratory, medical, therapeutic, certification, or regulatory conclusions.

OriginChain remains a local educational demonstration. It does not implement enterprise identity verification, production custody, secure multi-tenancy, or a production deployment architecture.

## Authentication and authorization path

```text
Browser
   ↓ username + password
FastAPI authentication
   ↓ short-lived signed JWT
Authenticated application user
   ↓ server-side role + target-stage rules
Role-specific business operation
   ├─→ SQLite + evidence storage
   └─→ Blockchain client → server-held Hardhat signer
```

Operational actors are persistent SQLite users with Argon2 password hashes, normalized roles, an organization label, and an active flag. A valid JWT is necessary but not sufficient: each protected request reloads the user, validates that the account is active, checks that its current role matches the signed role claim, then evaluates the operation's role and context. Client request bodies do not select the acting role.

Public consumer verification follows a separate read-only path and does not require a user or token.

## Application identity versus blockchain execution identity

These are deliberately separate layers:

| Application role | Application identity | Demo blockchain execution |
|---|---|---|
| Raw Material Supplier | Seeded `supplier` user | Off-chain raw-material work; no finished-product owner signer |
| Manufacturer | Seeded `manufacturer` user | FastAPI uses the configured Hardhat Manufacturer account for authorized registration, commitments, and transfer |
| Distributor | Seeded `distributor` user | FastAPI uses the configured Hardhat Distributor account for authorized commitments and transfer |
| Retailer | Seeded `retailer` user | FastAPI uses the configured Hardhat Retailer account for authorized commitments |
| Admin | Seeded `admin` user | Read/admin controls only; does not impersonate an operational blockchain owner |

Passwords and JWTs are never blockchain credentials. Private keys stay inside the server-side local blockchain client and never reach browser JavaScript. The Solidity contract independently requires the current owner for transfers and commitment writes. Production wallet ownership, custody, organizational identity, key rotation, and signer isolation are not implemented.

## Data placement

### On-chain

- Hashed product key and canonical product metadata hash
- Manufacturer and current owner
- Ownership history
- Stage key, normalized approval status, and deterministic stage snapshot commitment
- Evidence byte hashes and their stage keys
- Registration, transfer, stage, and evidence events

Only the current product owner can record a product-stage or evidence commitment in the demonstration contract.

### Off-chain SQLite

- Seeded users and password hashes
- Application audit events and actor roles
- Product and raw-material descriptive data
- Versioned product specifications, normalized specification requirements, quality-check mappings, and per-batch specification snapshots
- Fictional evidence-issuer registry, immutable issuer-at-submission snapshots, source review schedules, and quality change records
- Ingredient/component batch relationships
- Quality templates, complete inspection results, and actor attribution
- Versioned source registry, profile definitions, normalized requirement mappings, and immutable per-result source snapshots
- Notes, approval summaries, transaction references, and timestamps
- Evidence document type, optional laboratory/report metadata, uploader attribution, visibility, safe stored filename, byte size, and digest

### Off-chain filesystem

- Actual PDF/PNG/JPEG evidence bytes under `backend/uploads/<stage>/`
- Random generated storage names; original names are metadata only
- 5 MiB maximum; extension, declared MIME type, and file signature must agree

## Status vocabulary

- Check: `PASS`, `FAIL`, `NOT_APPLICABLE`, `PENDING`
- Stage: `PENDING`, `APPROVED`, `HOLD`, `REJECTED`
- Sale: `NOT_READY`, `APPROVED_FOR_SALE`, `HOLD`, `REJECTED`
- Evidence: `VERIFIED`, `MISMATCH`, `FILE_MISSING`
- Evidence verification: `UNVERIFIED`, `VERIFIED_DEMO`, `REJECTED`
- Issuer trust: `TRUSTED_DEMO`, `UNVERIFIED`, `REVOKED`
- Product specification: `DRAFT`, `APPROVED`, `SUPERSEDED`, `RETIRED`
- Source review: `CURRENT`, `REVIEW_DUE`, `UNDER_REVIEW`, `SUPERSEDED`
- Visibility: `INTERNAL`, `CONSUMER_VISIBLE`
- Requirement: `REGULATORY`, `STANDARD_BASED`, `INDUSTRY_GUIDANCE`, `ORIGINCHAIN_INTERNAL`, `ORGANIZATION_INTERNAL`
- Source lifecycle: `PUBLISHED_CURRENT`, `PUBLISHED_UNDER_REVISION`, `DRAFT`, `SUPERSEDED`, `WITHDRAWN`, `UNKNOWN`

## Source-traceability model

```text
Quality Requirement
        ↓
Requirement Classification
        ↓
Source / Standard Version
        ↓
Inspection Result
        ↓
Evidence
        ↓
Stage Approval
        ↓
Snapshot Commitment
        ↓
Blockchain

quality_profiles
      │ one active serum profile
      ▼
quality_profile_requirements ──► quality_standards
                                      │ many-to-many
                                      ▼
                              quality_standard_sources
                                      │
                                      ▼
                                quality_sources

quality_results ── submission-time copy ──► quality_result_sources
```

`quality_sources` stores metadata and short, original interpretations only: authority, title, jurisdiction, source type, edition/year, lifecycle status, official URL, verification date, revision relationship, and notes. It does not store copyrighted standards text, test procedures, tables, or numeric acceptance limits.

`quality_standard_sources` deliberately supports multiple sources for a single gate (for example, Indian test-method context plus an international microbiological-limits source) and one source across multiple gates. Current mappings use `STANDARD_LEVEL`; the schema can later support section/clause precision only when a qualified reviewer can substantiate it.

`quality_result_sources` copies the source identity, edition, lifecycle state, mapping precision, and URL at first submission. Registry maintenance can update what future unsubmitted checks display but cannot change the frozen source edition for an existing result. A stage commitment includes the profile code/version and each check's classification plus sorted source code/edition pairs.

The registry can expose a draft or active revision project for lifecycle awareness. Drafts are excluded from active requirement mappings. A source mapping is traceability metadata, never evidence that the complete source applies or that the product complies.

## Product specification architecture

The seeded fictional serum specification is a versioned parent with normalized child requirements and many-to-many mappings to the reusable quality standards. Requirements carry stable codes, category/type, expected characteristic, evidence expectation, required flag, and optional visual component/defect taxonomy. Those visual fields are structured human-inspection metadata only; there are no predictions, scores, or ML endpoints.

Manufacturer registration accepts only an active, approved, effective specification matching the finished-product type. The batch freezes the specification code, version, deterministic requirement snapshot hash, and assignment time. Once a batch references a specification, SQLite triggers prevent semantic identity/content update, requirement update, or deletion. Governance may later change only lifecycle fields such as status/effective-until/active; a content revision is a new V2 row. Historical V1 batches and commitments continue referencing V1.

Approved product-stage commitments include the assigned specification code, version, and snapshot hash. The contract interface did not need to expand: these values are inside the deterministic off-chain snapshot whose compact hash is written on-chain.

## Evidence semantics and issuer trust

Evidence may be classified as Certificate of Analysis, microbiology report, preservative-efficacy report, raw-material specification, batch manufacturing record, packaging inspection, transport record, retail inspection, or other. Optional structured metadata includes report reference, dates, registered test-method source, result summary, and document notes.

OriginChain validates the upload container, hashes the actual bytes, and checks later byte integrity. This produces a **file integrity** status. Separately, selected critical document gates use the local fictional `evidence_issuers` registry to produce an **evidence verification** status. The server—not the browser—resolves issuer identity and current trust. `VERIFIED_DEMO` means accepted against these local reference controls only; it does not validate test execution, results, accreditation, signature, organization identity, or legal sufficiency.

COA evidence accepts a suitable trusted supplier or laboratory; microbiology and preservation-efficacy evidence require a trusted laboratory. These critical gates also require a report number. Ordinary photos and noncritical internal records are not forced to carry issuer metadata.

At submission, evidence freezes issuer code, name, type, trust status, report number, and document date. Mutable current registry status is joined separately. A later revocation therefore produces a warning on historical evidence without mutating its accepted snapshot or automatically rewriting an approved stage. Newly submitted critical evidence from the revoked issuer is `UNVERIFIED` and cannot satisfy the gate.

## Governance and change control

Admin owns source review visibility and issuer trust changes. Each source has a review owner, reviewer, last-reviewed time, review state, and next-review due date. `quality_change_records` captures change type, target, previous/new version, summary, mandatory reason, requester/approver, status, and approval time. The model is intentionally lightweight and read-heavy; it is traceability, not an electronic QMS approval/signature implementation.

Source registry maintenance changes what future results see, while existing `quality_result_sources` snapshots remain frozen. Specification revisions use a new version. Issuer updates preserve evidence snapshots. Demo reset clears operational records only and retains this governance/reference layer.

## Trust boundary

FastAPI enforces local-demo authentication, active-account checks, application roles, stage context, dependencies, and transfer gates. The contract independently restricts commitment writes and ownership changes to the current demo owner. Together these demonstrate layered authorization and integrity, but they are not a production identity, custody, or regulatory model.

The consumer response is purpose-built and redacted. It never returns internal specification rules, defect taxonomies, change reasons, review owners, issuer notes/trust-management fields, internal notes, stored filenames, internal evidence, raw database IDs, wallet addresses, or evidence files. It may show the recorded specification version and safe issuer name for explicitly public evidence. Authenticated users may inspect evidence metadata only for their matching stage; Admin may inspect all stage metadata. There is no public raw-file endpoint.

## Attribution and audit

Meaningful records capture the authenticated user that created the raw-material batch, registered the finished product, submitted a quality result, uploaded evidence, approved a stage, or initiated an ownership transfer. The append-only `audit_events` table records actor user ID, signed-in role, action, entity reference, result, safe metadata JSON, and timestamp. It records successful login and supply-chain/admin events without storing passwords, JWTs, private keys, or filesystem paths. Recent history is available only through the Admin-protected `/api/audit` endpoint.

Demo reset clears operational supply-chain tables and uploaded files but preserves users, audit events, specifications, issuers, quality sources/profiles, source reviews, and change records. It cannot reset the independent Hardhat process.

## Browser session boundary

The static frontend keeps the short-lived Bearer token in `localStorage` for demo convenience. It removes that token on logout or `401`, but this is not hardened production browser storage. A production system should replace the seeded accounts, fallback secret, local token storage, and local SQLite identity store with an audited identity/session architecture.

## Live gate evaluation

Stage approval is a recorded decision over a specific quality snapshot, not a permanent bypass. Editing a quality result or attaching new evidence invalidates an existing approval. Transfer and downstream dependency checks re-evaluate current required results, evidence presence, file integrity, frozen trusted-issuer acceptance where required, and prerequisite approvals. Raw-material eligibility is likewise rechecked before a finished batch can link it, including its expiry/retest date.

This protects the demonstration from stale local approvals after a failed correction or a modified evidence file. FastAPI remains the workflow orchestrator; the blockchain stores compact commitments rather than the full mutable inspection record.

## Local deployment hand-off

`blockchain/deployments/local.json` is generated by the local deploy script and read by the backend. It is tracked because it contains the ABI needed by the current demo, but its transaction hash is session-specific. A fresh Hardhat node requires a fresh deployment even if Hardhat assigns the familiar deterministic address. The file is not proof that a referenced node is still running.

## Future architecture — luxury-cosmetics ML (not implemented)

Future research may evaluate bottle/container consistency, cap/dropper geometry, label placement, seal condition, packaging-layout anomalies, and structured batch-risk signals. It requires a rights-cleared luxury-cosmetics-specific dataset, documented labels, train/validation/test separation, metrics, calibration, and human-review policy. No ML functionality is implemented in this phase.
