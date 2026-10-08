# OriginChain: Project Report

**Blockchain-Based Quality Assurance, Authentication and Supply-Chain Traceability for Luxury Cosmetics**

| | |
|---|---|
| Type | University educational demonstration (local, single machine) |
| Status | Working end-to-end demo; all automated tests passing (October 2026) |
| Stack | FastAPI · SQLite · Web3.py · Solidity on Hardhat · vanilla HTML/CSS/JS |
| Flagship product | *Aurelia Prestige Renewal Serum* (fictional), code `OC-LUX-SERUM-0001`, batch `APR-2026-001` |

---

## 1. Summary

Counterfeit and mishandled luxury cosmetics are hard for a buyer to detect. A bottle can look perfect while its contents, batch history or storage conditions are not what the label claims.

OriginChain tracks one fictional luxury serum from raw-material receipt to the retail shelf. At each hand-off a responsible party must pass a set of quality checks, with supporting evidence, before the product can move on. A compact fingerprint of the product, each approved stage and each evidence file is written to a blockchain. Anyone can later enter the product code and see whether the product is authentic, whether every stage was approved, and whether any record has been altered since it was committed.

## 2. Objectives

1. Record product identity and custody on an append-only ledger that the application database cannot silently rewrite.
2. Enforce stage-by-stage quality gates (Supplier → Manufacturer → Distributor → Retailer). A product cannot be transferred or sold until the current stage is approved.
3. Tie every approval to evidence (certificates, reports, inspection photos) whose integrity can be re-checked later.
4. Give consumers a read-only, privacy-preserving verification view.
5. Show tamper detection: an edited database record must be visibly flagged as **Suspicious**.

## 3. System architecture

```text
 Browser (static HTML/CSS/JS)
        │  Bearer JWT (operational users)    │  no auth (consumer verify)
        ▼                                    ▼
 ┌──────────────────────────── FastAPI ────────────────────────────┐
 │  auth.py           login, Argon2 hashing, JWT, role checks      │
 │  quality_service   stage gates, required checks and evidence    │
 │  evidence.py       safe uploads, Keccak-256 file hashing        │
 │  metadata_hash.py  deterministic product-metadata hash          │
 │  presentation_demo one-click demo seeding / auto-fill           │
 └───────┬─────────────────────────────────────────┬───────────────┘
         ▼                                         ▼
  SQLite + uploads/                     blockchain_client.py (Web3.py)
  full records, evidence files,                    │ server-held signer
  users, audit log                                 ▼
                                       OriginChain.sol on Hardhat (local EVM)
                                       product hashes, custody, stage and
                                       evidence commitments
```

**Design principle: details off-chain, fingerprints on-chain.** Full records and files stay in SQLite and on disk. The chain stores only 32-byte hashes, owner addresses and status codes. This keeps the ledger small and private while still making tampering detectable.

## 4. Components

### 4.1 Smart contract: `blockchain/contracts/OriginChain.sol`

| Function | Purpose |
|---|---|
| `registerProduct(productKey, metadataHash)` | Creates the product with its metadata fingerprint; the caller becomes the owner |
| `transferOwnership(productKey, newOwner)` | Current owner hands custody to the next actor; history is appended |
| `recordQualityStage(...)` | Owner commits an approved stage's status and snapshot hash |
| `recordEvidenceHash(productKey, stageKey, hash)` | Owner commits an evidence file's hash; duplicates are rejected |
| `verifyProduct`, `getProduct`, `getOwnershipHistory`, `getQualityStage`, `isEvidenceRegistered` | Read-only queries used for verification |

Events: `ProductRegistered`, `OwnershipTransferred`, `QualityStageRecorded`, `EvidenceHashRecorded`. The contract enforces current-owner rules independently of the API.

### 4.2 Backend: `backend/`

- **`main.py`**: FastAPI app with roughly 40 routes (auth, records, quality, evidence, transfers, verification, admin and demo).
- **`database.py`**: SQLite schema (20 tables) and repositories. Includes database guards that stop an assigned product specification from being edited.
- **`domain.py`**: Roles, statuses, stage definitions and the seeded quality templates (24 checks: 5 supplier, 8 manufacturer, 5 distributor, 6 retail).
- **`quality_service.py`**: Evaluates a stage. It decides whether every required check has passed, has valid evidence and, where needed, a trusted issuer.
- **`auth.py`**: Argon2 password hashing, 30-minute JWTs, and per-request reloading of the user to confirm they are still active and still hold the same role.
- **`evidence.py`**: Accepts PDF/PNG/JPEG files up to 5 MiB, stores them under generated names and hashes the bytes.
- **`blockchain_client.py`**: Web3.py wrapper. It maps each role to a server-held Hardhat account, so the browser never sees a private key.

### 4.3 Frontend: `backend/static/`

A single page (`index.html`, `app.js`, `styles.css`) served by FastAPI. It adapts to the signed-in role: each actor sees only their sections and actions. It includes a public **Verify Product** panel, an Admin audit and governance view, presenter shortcuts, and an **About** dialog that explains the project inside the app.

## 5. How it works, end to end

1. **Supplier** registers a raw-material batch (for example Hyaluronic Acid `HA-260801`) and completes 5 checks. One check requires a Certificate of Analysis from a *Trusted Demo* issuer. The supplier then approves the stage.
2. **Manufacturer** links only approved, unexpired materials and registers the serum batch against the approved product specification. The backend hashes the product metadata and calls `registerProduct` on-chain. The manufacturer completes 8 checks, including microbiology and preservation-efficacy evidence, approves the stage, and transfers custody to the distributor (`transferOwnership`).
3. **Distributor** completes 5 receiving, storage, damage and custody checks, approves the stage, and transfers to the retailer.
4. **Retailer** completes 6 final checks. A failed mandatory check (such as a broken security seal) puts the batch on **HOLD**. After correction and approval it becomes **Approved for Sale**.
5. At every approval, the stage snapshot hash and the hash of each evidence file are committed on-chain.
6. **Consumer** enters the product code. The server recomputes the metadata hash from the database, compares it with the on-chain value, and returns authenticity, the four-stage quality journey, provenance by role, and any evidence marked public. Internal notes and files are never exposed.
7. **Tamper demo:** Admin edits the local product record. Verification now finds a hash mismatch and reports **Suspicious**.

### Quality-gate rules

- Every mandatory check must be `PASS`. A `FAIL` results in `HOLD`; incomplete work stays `PENDING`.
- Checks that require evidence need an uploaded file of the right type whose bytes still match the stored hash.
- Critical reports (COA, microbiology, preservation efficacy) also need an issuer currently trusted in the registry, plus a report number. If Admin later revokes an issuer, historical approvals keep their original acceptance (with a warning), but new evidence from that issuer cannot satisfy a gate.
- Editing an approved result or adding evidence invalidates the approval. Transfers re-check live state rather than trusting a stored approval.

## 6. Roles and access

| Role | Can do |
|---|---|
| Supplier | Register raw materials; Raw-Material QC |
| Manufacturer | Register product; Manufacturing QC; transfer to Distributor |
| Distributor | Distribution QC; transfer to Retailer |
| Retailer | Retail QC; final sale decision |
| Admin | Read all stages, audit log, issuer trust, governance records, demo controls. Cannot perform supply-chain actions |
| Consumer | Public verification only, with no account |

All five demo accounts use a shared local password documented in the README. Every action is attributed to the signed-in user in an Admin-only audit log.

## 7. Quality references

The demo uses an *India Luxury Facial Serum Demonstration Profile* that maps selected checks to real source metadata: the CDSCO Cosmetics Rules 2020, BIS IS 4707-2 and IS 14648, and ISO 22716, 17516, 11930 and 29621. These mappings only explain *why* evidence is requested. The project makes **no** certification, compliance or laboratory-validity claim. See [LUXURY_COSMETICS_QUALITY_SOURCES.md](LUXURY_COSMETICS_QUALITY_SOURCES.md).

## 8. Testing and verification status

Results from the handover review (5 October 2026), all on a fresh Hardhat chain:

| Suite | Result |
|---|---|
| Backend unit and integration tests (`pytest backend/tests`) | 51 passed |
| Smart-contract tests (`npm test`) | 17 passed |
| Live API smoke: full workflow, HOLD and fix, tamper detection | Passed |
| Live demo auto-fill flow | Passed |
| Live revoked-issuer drill | Passed |
| Headless-Chrome UI smoke (`ui_smoke_cdp.js`) | Passed |
| Manual UI review (desktop 1440px and mobile 375px) | Passed after fixes listed in §10 |

## 9. Running the project

```bash
# Terminal 1
cd blockchain && npx hardhat node
# Terminal 2
cd blockchain && npm run deploy:local
# Terminal 3 (from repo root)
source .venv/bin/activate && uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000>. The full install steps, the role-by-role walkthrough and the 5-minute presentation script are in the [README](../README.md). The same script is available in the app under **About → Demo guide**.

## 10. Handover changes (October 2026)

- Added an **About** button in the header. It opens a tabbed dialog (Overview, How it works, Demo guide, Scope & limits) with live blockchain status.
- Notifications now have a dismiss button and can be closed early.
- Anchor navigation no longer hides section headings under the sticky header.
- Fixed the empty "select a batch" quality summary, which was squeezed into one grid column.
- Admin now opens on the product's current QC stage instead of an empty panel.
- The Admin source registry no longer overflows on phone-width screens.
- Added this report.

## 11. Limitations

- Local and single-machine only: SQLite, local files, Hardhat test keys, a shared demo password, and a token stored in the browser.
- No MFA, rate limiting, TLS, password recovery or production key custody.
- Only the serum workflow is implemented. The category model anticipates other product types.
- The blockchain proves records have *not changed since commitment*. It cannot prove the original inspection was honest.

## 12. Future work

- Deploy to a public testnet (for example Polygon Amoy) with proper key management.
- Use PostgreSQL with migrations, and object storage or IPFS for evidence.
- Use a real identity provider with HttpOnly-cookie sessions.
- Add QR codes on packaging that link straight to the verification page. The `/api/qr/{code}` endpoint already exists.
- Add packaging-defect image assistance, only with a rights-cleared, human-labelled dataset. See [ai/README.md](../ai/README.md).
