# OriginChain

**Blockchain-Based Quality Assurance, Authentication, and Supply-Chain Traceability for Luxury Cosmetics**

OriginChain is an educational local demonstration built around one fictional flagship product: **Aurelia Prestige Renewal Serum**, a luxury anti-aging facial serum. It records product authenticity and compact quality commitments on a local blockchain while keeping operational records and evidence files off-chain.

For a one-page overview of what the project is and how it works, see the [Project Report](docs/PROJECT_REPORT.md), or click **About** in the app header.

> This project does not claim production readiness, legal compliance, laboratory validation, regulatory approval, market authorization, or affiliation with any real cosmetics brand. The source metadata is real and official; the product, companies, inspection results, and evidence are fictional demonstration data.

## Working demonstration

The implemented workflow is:

```text
Raw-material supplier QC
        ↓ approved materials only
Manufacturer QC and batch release
        ↓ gated transfer
Distributor receiving/storage/logistics QC
        ↓ gated transfer
Retail final inspection
        ↓
Approved for sale
        ↓
Consumer read-only verification
```

The consumer can verify authenticity, provenance, the stage-quality journey, final retail status, and explicitly public evidence. Consumers cannot perform QC and cannot see internal notes, stored paths, internal evidence, or private database identifiers.

## Flagship domain model

- Category: `SKINCARE`
- Subcategory: `FACIAL_SERUM`
- Product type: `ANTI_AGING_SERUM`
- Product: `Aurelia Prestige Renewal Serum`
- Product code: `OC-LUX-SERUM-0001`
- Batch: `APR-2026-001`

The category model can later represent moisturizer, eye cream, cleanser, makeup, and fragrance products, but only the serum workflow is implemented in this phase.

## Implemented now

- Seeded operational users with Argon2 password hashing
- Short-lived signed JWT access tokens and active-user validation
- Server-enforced role and target-stage authorization
- Per-action user attribution and an Admin-only audit log
- Raw-material batch registration and supplier provenance
- Finished-batch linkage to approved raw-material batches
- Immutable, versioned finished-product specifications assigned per batch
- Six fictional evidence issuers with server-owned `TRUSTED_DEMO`, `UNVERIFIED`, and `REVOKED` states
- Frozen issuer identity/trust snapshots on submitted evidence
- Separate evidence byte-integrity and demo issuer-verification results
- Admin-owned source-review dates and lightweight governed change records
- Deterministic ingredient-lineage commitment
- Reusable stage/category/check quality templates
- Versioned official-source registry and an India luxury facial-serum demonstration profile
- Many-to-many requirement/source mappings with regulatory, standard-based, guidance, and internal classifications
- Explicit published, under-revision, and draft lifecycle states
- Immutable source-edition snapshots on submitted results
- High-level microbiology and preservation-efficacy evidence gates without copied limits or fabricated results
- Structured evidence document types and optional laboratory/report metadata
- Normalized inspection, approval, sale, evidence-visibility, and integrity statuses
- Required-check and required-evidence enforcement
- Safe PDF/PNG/JPEG uploads with a 5 MiB limit and generated filenames
- Keccak-256 hashing of actual evidence bytes
- Later evidence integrity verification (`VERIFIED`, `MISMATCH`, `FILE_MISSING`)
- Manufacturer and distributor transfer gates
- Retail `APPROVED_FOR_SALE` decision
- Correctable `HOLD` flow after a failed check
- Consumer-safe verification with evidence redaction
- Existing product metadata tamper demonstration
- Compact on-chain quality-stage and evidence commitments/events

## Architecture

```text
Static HTML/CSS/JavaScript
             │ login / Bearer JWT
             ▼
 FastAPI authentication + RBAC
       ┌─────┴─────────────┐
       ▼                   ▼
SQLite + uploads      Web3.py signing layer
 (users, audit,            │
  operational data,        ▼
  full evidence)      Hardhat local EVM
                     (hashes, ownership,
                      quality commitments)
```

Large metadata structures and evidence files are never stored on-chain. See [docs/LUXURY_COSMETICS_ARCHITECTURE.md](docs/LUXURY_COSMETICS_ARCHITECTURE.md), [docs/LUXURY_COSMETICS_QUALITY_SOURCES.md](docs/LUXURY_COSMETICS_QUALITY_SOURCES.md), and [docs/QUALITY_GOVERNANCE_AND_EVIDENCE.md](docs/QUALITY_GOVERNANCE_AND_EVIDENCE.md).

## Requirements

- Node.js 22.13 or newer (Node.js 22 LTS recommended)
- npm
- Python 3.13 (Python 3.10+ is required)
- `uv` or `pip`

## Install

```bash
git clone https://github.com/Orphyxz/OriginChain-Demo.git
cd OriginChain-Demo

uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r backend/requirements.lock

cd blockchain
npm ci
npm run compile
```

## Run on macOS/Linux

Open three terminals.

Terminal 1 — local blockchain:

```bash
cd /Users/aryxzing/Desktop/OriginChain-Demo/blockchain
npx hardhat node
```

Terminal 2 — deploy the current contract ABI:

```bash
cd /Users/aryxzing/Desktop/OriginChain-Demo/blockchain
npm run deploy:local
```

Terminal 3 — API and interface:

```bash
cd /Users/aryxzing/Desktop/OriginChain-Demo
source .venv/bin/activate
uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is at <http://127.0.0.1:8000/docs>.

Always redeploy after changing/recompiling the contract. `blockchain/deployments/local.json` supplies the backend with the current address and ABI.

## Authentication

Operational work requires a seeded fictional actor account. FastAPI verifies an Argon2 password hash, issues a signed JWT Bearer token, reloads the user from SQLite on every protected request, checks that the account remains active and its role still matches the token, and enforces role and target-stage rules server-side. Access tokens expire after 30 minutes by default. Public product verification, QR generation, health, the fictional catalog, static assets, and login remain unauthenticated.

The static frontend keeps the Bearer token in `localStorage` for presentation convenience, supplies it to protected requests, restores the actor through `/api/auth/me`, and removes it on logout or any `401`. This storage choice is acceptable only for the local educational demo: browser script compromise could read the token. A production design should use a hardened identity provider and an appropriate HttpOnly-cookie or equivalent token strategy.

Set a unique local signing secret before starting FastAPI:

```bash
export ORIGINCHAIN_JWT_SECRET="$(openssl rand -hex 32)"
export ORIGINCHAIN_ACCESS_TOKEN_MINUTES=30
uvicorn backend.main:app --reload
```

If `ORIGINCHAIN_JWT_SECRET` is absent, the server logs a warning and uses a deliberately unsafe demo fallback. Never use that fallback outside this local demonstration. See [.env.example](.env.example); it contains placeholders, not a real secret.

## Demo accounts

**LOCAL DEMO CREDENTIALS — NOT FOR PRODUCTION**

All five fictional accounts use the password `OriginDemo2026!`.

| Username | Display name | Organization | Role |
|---|---|---|---|
| `supplier` | Lumina Supplier Operator | Lumina Actives | Raw Material Supplier |
| `manufacturer` | Aurelia Manufacturing Operator | Aurelia Manufacturing Atelier | Manufacturer |
| `distributor` | Prestige Distribution Operator | Prestige Beauty Distribution | Distributor |
| `retailer` | Maison Luxe Retail Operator | Maison Luxe Retail | Retailer |
| `admin` | OriginChain Demo Admin | OriginChain | Admin |

Seeding is deterministic and idempotent. Startup updates the known display metadata but does not overwrite an existing non-empty password hash or deliberately changed active status. Admin reset preserves users and audit history while clearing operational supply-chain records and uploaded evidence.

## Permission matrix

| Action | Supplier | Manufacturer | Distributor | Retailer | Admin |
|---|---:|---:|---:|---:|---:|
| View permitted operational records | Yes | Yes | Yes | Yes | All |
| Register raw material | Yes | No | No | No | No |
| Register finished product | No | Yes | No | No | No |
| Submit/upload/approve Supplier QC | Yes | No | No | No | Read only |
| Submit/upload/approve Manufacturer QC | No | Yes | No | No | Read only |
| Transfer Manufacturer → Distributor | No | Yes | No | No | No |
| Submit/upload/approve Distributor QC | No | No | Yes | No | Read only |
| Transfer Distributor → Retailer | No | No | Yes | No | No |
| Submit/upload/approve Retail QC | No | No | No | Yes | Read only |
| Inspect evidence metadata | Relevant stage | Relevant stage | Relevant stage | Relevant stage | All |
| Inspect quality source/profile metadata | Yes | Yes | Yes | Yes | Yes |
| Read approved product specification / issuer registry | Yes | Yes | Yes | Yes | Yes |
| View source reviews / change records | No | No | No | No | Yes |
| Change issuer trust status | No | No | No | No | Yes |
| View audit / reset / tamper demo | No | No | No | No | Yes |

Admin is intentionally not an all-powerful supply-chain actor. It can inspect all stages and run demonstration administration, but it cannot impersonate Manufacturer, Distributor, or Retailer contract actions.

## Supervisor demonstration guide

### 5-Minute Presentation Flow

Demo Auto-Fill exists solely to speed up the local university presentation. It uses the real quality service, evidence-integrity checks, approval gates, actor attribution, custody rules, and blockchain writes. It does not replace the manual workflow. Keep `ORIGINCHAIN_DEMO_MODE=1` only for the local demo.

1. Start a fresh Hardhat node, deploy the contract, and start FastAPI.
2. Admin → **Run Demo Readiness Check** → confirm `READY` → **Prepare Fresh Demo**.
3. Supplier → **Demo Auto-Fill** → sign out.
4. Manufacturer → **Demo Auto-Fill** → **Transfer to Distributor** → sign out.
5. Distributor → **Demo Auto-Fill** → **Transfer to Retailer** → sign out.
6. Retailer → **Demo HOLD Case** → show the failed seal and `HOLD` → **Fix Demo Issue** → sign out.
7. Public verification → verify the product code shown by the app → show `Authentic` and `Approved for Sale`.
8. Admin → **Demo: Tamper Local Metadata** → sign out.
9. Public verification → verify again → show `Suspicious` and the blockchain hash mismatch.

The overview's **Demo Progress** row is calculated from live approvals, custody, sale status, and blockchain metadata integrity. Transfers intentionally remain manual so custody changes are visible during the presentation.

### Fast presentation mode

For a presentation without manual data entry, sign in as `admin` and click **Load Complete Presentation Demo** in the Admin section. The server creates or finishes the fictional material/product records, required evidence, four stage approvals, Manufacturer → Distributor → Retailer transfers, and the final `APPROVED_FOR_SALE` state against the running local Hardhat chain. You can then use the Admin stage tabs to inspect every stage and use the product code automatically placed in Public Verification. This is normally `OC-LUX-SERUM-0001`; after a local-only reset, the loader safely chooses an unused `OC-LUX-SERUM-PRESENTATION-####` code if the canonical code still exists on-chain. The fixture is explicitly fictional and creates no certification or accreditation claim.

The button is idempotent after completion and can also finish a normal partially registered batch at Manufacturer, Distributor, or Retailer stage. It remains Admin-only and requires a connected, deployed local blockchain.

The recommended live walkthrough is the role-by-role flow above. The Admin full loader remains available as a fallback when only the final state needs to be shown.

### Manual role-by-role mode

1. Sign in as `supplier`. Register `Hyaluronic Acid Solution` batch `HA-260801`, complete Raw Material QC, upload the required evidence, approve, then sign out.
2. Sign in as `manufacturer`. Select the approved material, register `Aurelia Prestige Renewal Serum`, complete Manufacturer QC/evidence, approve, transfer to Distributor, then sign out.
3. Sign in as `distributor`. Complete Distribution QC/evidence, approve, transfer to Retailer, then sign out.
4. Sign in as `retailer`. Save **Security Seal Inspection** as `FAIL`, confirm `HOLD` and the approval blocker, correct it to `PASS`, approve to reach `APPROVED_FOR_SALE`, then sign out.
5. Without signing in, verify `OC-LUX-SERUM-0001`. Show the authentic result, four approved stages, role-only provenance, and consumer-visible evidence.
6. Sign in as `admin`. Show the attributed audit history, run **Demo: Tamper Local Metadata**, then sign out.
7. Without signing in, verify again and show `SUSPICIOUS` with a blockchain hash mismatch.

Evidence-required checks cannot be approved without an uploaded PDF/PNG/JPEG of the expected document type. The COA, microbiology, and preservation-efficacy gates additionally require a suitable issuer currently accepted as `TRUSTED_DEMO` plus a report number at submission. “Verified for Demo” means only that OriginChain accepted the record against its local fictional registry controls; it is not certification, accreditation, or laboratory validation. Internal evidence stays absent from consumer responses; only `CONSUMER_VISIBLE` evidence is summarized publicly.

## Product specification and evidence trust

Every finished batch is bound at registration to an approved, effective specification. The seeded `AURELIA_PRESTIGE_RENEWAL_SERUM_SPEC_V1` contains 16 stable requirements for identity, bottle/dropper, seal, label/print, carton, and finished appearance. Its normalized mappings enrich applicable Manufacturer and Retailer checks. A batch stores the specification code, version, deterministic snapshot hash, and assignment timestamp. Database guards prevent an assigned specification's semantic identity/content or requirements from being edited or deleted; lifecycle state may later mark it superseded/retired, while a meaningful content revision is created as V2 without rewriting V1 batches.

Evidence has two independent properties:

- **File integrity** answers whether the stored bytes still match the recorded Keccak-256 digest.
- **Evidence verification** answers whether the submitted issuer, issuer type, current local trust status, and required report reference passed OriginChain's demo controls.

The submission freezes issuer code, name, type, trust-at-submission, report number, and document date. If Admin later revokes an issuer, historical evidence retains its original `TRUSTED_DEMO` acceptance and displays a current-status warning. New critical evidence from that issuer is stored as `UNVERIFIED` and cannot satisfy its approval gate. Ordinary photos are not forced to have an issuer.

Admin's Quality Governance view is read-heavy: specifications, issuers, source-review ownership/due dates, and change history. Admin can change issuer trust only with a reason; the action creates a change record and audit event. Demo reset preserves specifications, issuers, sources, reviews, profiles, change records, users, and audit history.

## Quality Standards and Sources

The active `INDIA_LUXURY_FACIAL_SERUM_DEMO_V1` profile maps selected gates to metadata for the Cosmetics Rules, 2020, relevant BIS standards, and relevant ISO cosmetics standards. A source badge means only that OriginChain records a defensible reason to request or inspect evidence. It never means that OriginChain interpreted the complete source, performed a laboratory test, certified compliance, or authorized sale.

### Default Quality Profile

`India Luxury Facial Serum Demonstration Profile` version `1.0` applies only to the fictional skincare/facial-serum/anti-aging-serum demo. It combines India-specific traceability and ingredient-review references, technically relevant international cosmetics standards, and clearly separated OriginChain internal luxury/custody controls. International ISO sources are not represented as Indian law.

Mappings are intentionally narrow:

- Cosmetics Rules metadata supports selected product/manufacturer/batch/date label-traceability checks.
- IS 4707 Part 2 supports a documented ingredient specification/restriction review without reproducing controlled lists.
- IS 14648 and ISO 17516 support retaining microbiology evidence without encoding methods or numeric limits.
- ISO 11930 and ISO 29621 support preservation-efficacy evidence and documented low-risk reasoning; the aqueous serum is not automatically treated as low risk.
- ISO 22716 is mapped to manufacturing controls, not finished-product distribution.
- Distributor and luxury-pack visual gates remain explicitly `ORIGINCHAIN_INTERNAL`.
- Draft ISO revisions are visible in the registry but are never mapped as active requirements.

Result submissions freeze the mapped source code, title, edition, status, URL, and mapping precision. Later registry maintenance therefore cannot silently rewrite the evidence basis of an older result. Approved stage commitments include profile/version and source-code/edition identifiers in addition to results and evidence hashes.

### Sources

- `INDIA_COSMETICS_RULES_2020` — CDSCO/MoHFW Cosmetics Rules, 2020
- `BIS_IS_4707_PART2_2025` — BIS IS 4707 Part 2:2025
- `BIS_IS_14648_2011` — BIS IS 14648:2011
- `ISO_22716_2007` — ISO 22716:2007
- `ISO_17516_2014` and `ISO_FDIS_17516_ED2` — published edition plus visible draft successor
- `ISO_11930_2019_AMD1_2022` and `ISO_CD_11930_ED3` — published/amended edition plus visible draft successor
- `ISO_29621_2017` — ISO 29621:2017

Official URLs, status research, applicability, exclusions, and the full mapping matrix are in [docs/LUXURY_COSMETICS_QUALITY_SOURCES.md](docs/LUXURY_COSMETICS_QUALITY_SOURCES.md).

### Important Disclaimer

- No ISO certification is claimed.
- No BIS certification is claimed.
- No CDSCO approval is claimed.
- No FDA approval is claimed.
- No legal compliance or laboratory-validity determination is made.

### Source Lifecycle

`PUBLISHED_CURRENT` identifies the published reference found current during the recorded manual verification. `PUBLISHED_UNDER_REVISION` warns that revision work exists while retaining the published edition mapping. `DRAFT` sources are visible for change awareness but are never active requirement mappings. The registry also supports `SUPERSEDED`, `WITHDRAWN`, and `UNKNOWN`; new editions must receive new versioned source codes, while historical result snapshots keep the edition originally referenced.

## Quality gates

- Raw-material approval requires every mandatory supplier check to pass and all required evidence to exist.
- Manufacturer approval additionally requires at least one linked, approved raw-material batch.
- Transfer to Distributor requires approved Manufacturer QC.
- Distributor approval requires approved Manufacturer QC.
- Transfer to Retailer requires approved Distributor QC.
- Retail approval requires approved Distributor QC and every mandatory retail check.
- A failed mandatory check results in `HOLD`; incomplete work remains `PENDING`.
- Editing an approved result or adding evidence invalidates the prior approval. Transfers re-evaluate the live checks and evidence integrity rather than trusting a stale approval row.
- Critical COA, microbiology, and preservation evidence must also have a frozen Trusted Demo issuer acceptance; a current registry revocation does not rewrite old acceptance, but it blocks newly submitted critical evidence.
- The retailer is the final operational checkpoint. The customer never performs QC.

Gate orchestration and application RBAC are enforced by FastAPI. Approved product-stage snapshots and evidence digests are also committed to the contract by the current demo owner. Login passwords never derive blockchain keys: FastAPI maps authorized actions to server-held Hardhat signers, and the contract separately enforces current-owner rules. No private key is returned to the browser.

## API summary

Public:

- `GET /`, `/static/*`, `/favicon.ico`
- `GET /api/health`, `/api/demo/catalog`, `/api/qr/{product_code}`
- `POST /api/auth/login`
- `GET /api/verify/{product_code}`

Authenticated operational reads:

- `GET /api/auth/me`
- `GET /api/raw-materials` and `/api/raw-materials/{id}`
- `GET /api/products`
- `GET /api/quality/standards?stage=...`
- `GET /api/quality/sources` and `/api/quality/sources/{source_code}`
- `GET /api/quality/profiles` and `/api/quality/profiles/{profile_code}`
- `GET /api/product-specifications` and `/api/product-specifications/{specification_code}`
- `GET /api/evidence/issuers` and `/api/evidence/issuers/{issuer_code}`
- `GET /api/quality/{context_type}/{context_id}/summary?stage=...`
- `GET /api/evidence/{evidence_id}/integrity` — Admin or matching stage actor

Role-enforced writes and administration:

- `POST /api/raw-materials` — Supplier
- `POST /api/products/register` — Manufacturer
- `POST /api/quality/results` — actor matching the standard's server-derived stage and current product custody
- `POST /api/quality/stages/approve` — actor matching the requested stage and current product custody
- `POST /api/quality/results/{result_id}/evidence` — actor matching the result's stored stage and current product custody
- `POST /api/ownership-transfers` — Manufacturer → Distributor or Distributor → Retailer, with current-custody and live-quality checks
- `POST /api/demo/auto-fill` — signed-in Supplier, Manufacturer, Distributor, or Retailer; completes only that actor's current stage
- `POST /api/demo/retailer-hold` — Retailer-only fictional security-seal failure using the normal quality gate
- `POST /api/demo/presentation-seed` — Admin-only; loads the complete fictional presentation state
- `GET /api/demo/progress` — authenticated, live presentation progress
- `GET /api/demo/readiness` — Admin-only preflight check
- `GET /api/audit`, `POST /api/demo/tamper/{product_code}`, `POST /api/demo/reset` — Admin
- `GET /api/quality/source-reviews`, `GET/POST /api/quality/change-records` — Admin
- `POST /api/evidence/issuers/{issuer_code}/status` — Admin, with mandatory reason

Swagger UI at `/docs` exposes the Bearer authorization scheme for protected routes.

## Tests

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q backend/tests

cd blockchain
npm run compile
npm test
npm audit --audit-level=high
```

The contract toolchain uses Hardhat 3 with its Node test runner and Ethers plugin. The lockfile is reproducible with `npm ci`; the current dependency audit reports zero known npm vulnerabilities.

The backend suite additionally covers specification seeding and V1/V2 immutability, invalid/draft/superseded/type-mismatch assignment, requirement metadata without fake ML output, issuer uniqueness/trust states, frozen issuer snapshots, revoked-issuer behavior, integrity-versus-trust separation, source reviews, governance RBAC/change records, reset preservation, and consumer redaction.

With all three local services running, execute the real API smoke separately:

```bash
cd /Users/aryxzing/Desktop/OriginChain-Demo
source .venv/bin/activate
python backend/tests/integration_smoke.py
python backend/tests/integration_demo_autofill.py
PYTHONPATH=. .venv/bin/python backend/tests/integration_revoked_issuer.py
```

Run the revoked-issuer drill after (or independently of) the primary smoke while the same local API is running. It intentionally leaves `LUMINA_ACTIVES` in `REVOKED` state in that temporary demo database; Admin can restore it with a reason, or restart with a fresh database.

## Reset boundary

Admin-authenticated `POST /api/demo/reset` removes local SQLite operational records and files under `backend/uploads/`. It preserves users, audit history, product specifications, specification requirements, source/profile governance, evidence issuers, source reviews, and change records. It does **not** reset blockchain state. To reuse the same product code from a fully clean chain, restart the Hardhat node and redeploy the contract.

The Admin UI labels this action **Prepare Fresh Demo** and repeats the boundary before running it. For a completely fresh presentation: stop FastAPI, restart `npx hardhat node`, run `npm run deploy:local`, start FastAPI, then click **Prepare Fresh Demo**. The browser never attempts to stop or restart system processes.

### Duplicate product troubleshooting

If registration says the product already exists after a local reset, the same product key still exists in the running Hardhat session. Stop and restart `npx hardhat node`, run `npm run deploy:local` again, then reset/refresh the local app before repeating the demo. No Git operation is required.

## Local deployment file

`blockchain/deployments/local.json` is a tracked runtime hand-off: the backend reads its deployed address, demo actor addresses, and current contract ABI. The deploy script regenerates it, so its transaction hash changes between fresh Hardhat sessions even when the deterministic local contract address stays the same. Its ABI also changes when the contract interface changes. Treat a diff as generated local deployment state, inspect it before sharing, and always redeploy after restarting Hardhat or changing the contract.

## Security limitations

OriginChain remains a local, single-machine educational demonstration. Implemented controls include Argon2 password hashing, signed/expiring JWT validation, active-user and token-role checks, server-side role/stage gates, parameterized SQLite operations, evidence redaction, safe upload names, and server-held blockchain signing. These controls do **not** provide enterprise IAM or production custody.

Not implemented: a hardened identity provider, MFA, public registration, password recovery, account administration UI, revocation lists, refresh tokens, production secrets management, hardened browser token storage, secure multi-tenancy, rate limiting, TLS termination, PostgreSQL, cloud evidence storage, malware scanning, verified corporate identity, wallet login, or production blockchain key custody. The shared seeded credentials, local SQLite database, `localStorage` token, fallback JWT secret, and Hardhat keys are expressly demo-only.

## Future architecture — not implemented

- Production identity verification, IAM, hardened session management, or key custody
- Automated legal interpretation, compliance certification, or standards-content engine
- PostgreSQL or Alembic
- Polygon deployment
- IPFS/object storage
- Production malware scanning or cloud file storage
- Production audit/legal retention controls
- AI/ML packaging inspection
- Mobile application

The future ML scope is intentionally limited to luxury-cosmetics packaging and structured anomaly research. No fake confidence scores or simulated AI endpoints exist.

## Team

| Name | Role |
|---|---|
| Durva Waghchaure | Backend Lead & Project Lead |
| Aradhya | Frontend Lead |
| Aryan | Blockchain Lead |
| Purvika | AI Lead |

## License

Developed for educational purposes as part of a Bachelor of Engineering project.
