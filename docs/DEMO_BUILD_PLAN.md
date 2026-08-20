# OriginChain Emergency Demo Build Plan

Audit date: 2026-08-20

This plan is based on the repository contents inspected at `C:\Users\aryan\OneDrive\Desktop\OriginChain-main`. The current repository is a planning skeleton, not an implemented application.

## Current Repo Structure

```text
OriginChain-main/
  .gitignore
  README.md
  ai/
    .gitkeep
  assets/
    .gitkeep
  backend/
    .gitkeep
  blockchain/
    .gitkeep
  docs/
    .gitkeep
    OriginChain_SRS_v1.0.pdf
    Database/
      .gitkeep
      OriginChain_Database_Design_v1.1.pdf
  frontend/
    .gitkeep
```

Observed documentation:

- `README.md` describes the intended system as Next.js/React, FastAPI, PostgreSQL, Solidity/Hardhat/Polygon, IPFS, OpenCV/PyTorch, and Isolation Forest.
- `README.md` marks the current project phase as "Design & Planning".
- `docs/OriginChain_SRS_v1.0.pdf` exists and identifies itself as the OriginChain Software Requirements Specification, Version 1.0, 24 pages.
- `docs/Database/OriginChain_Database_Design_v1.1.pdf` exists and identifies itself as the OriginChain Database Design Document, Version 1.1, PostgreSQL, 9 tables, 18 pages.

## Current Functionality

There is no runnable frontend, backend, blockchain project, AI module, database schema, or integration code in the inspected tree.

The only files under `frontend/`, `backend/`, `blockchain/`, `ai/`, and `assets/` are `.gitkeep` placeholders.

No baseline application behavior currently works from this repository because there are no implementation files or dependency manifests.

## Existing Frontend

`frontend/` exists as a directory but contains only `.gitkeep`.

No Next.js app, React components, static HTML, CSS, JavaScript, `package.json`, route files, or build configuration were found.

## Existing Backend

`backend/` exists as a directory but contains only `.gitkeep`.

No FastAPI app, Python modules, API routes, database code, Web3 bridge, authentication code, `requirements.txt`, `pyproject.toml`, or environment loader were found.

## Existing Blockchain

`blockchain/` exists as a directory but contains only `.gitkeep`.

No Solidity contracts, Hardhat config, deployment scripts, generated ABI files, blockchain tests, or `package.json` were found.

## Package And Dependency Files

No package or dependency manifests were found:

- No `package.json`
- No `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`
- No `requirements.txt`
- No `pyproject.toml`
- No `Pipfile`
- No Hardhat config
- No Dockerfile or Compose file

Local tools available during audit:

- Node.js `v24.18.0`
- npm `11.16.0`
- Python `3.13.13`
- Git `2.54.0.windows.1`

## Tests And Baseline Checks

There are no test files in the inspected repository.

No build or test command could be run because there is no frontend package, backend package, blockchain package, or test configuration.

Safe checks performed:

- Recursive file inventory
- README inspection
- `.gitignore` inspection
- Dependency/config/contract/test file search
- PDF title/page-count extraction for the two existing documentation PDFs
- Local tool version check
- Git repository check

Git check result:

- `git branch --show-current` failed because the current directory is not a Git repository.
- `git status --short --branch` failed for the same reason.
- No `.git` directory was found under the inspected project tree.

## Usable Existing Components

The following can be reused:

- `README.md` for intended project scope, actor model, and stack description.
- Existing top-level directories: `frontend/`, `backend/`, `blockchain/`, `ai/`, `assets/`, `docs/`.
- `docs/OriginChain_SRS_v1.0.pdf` as requirements reference.
- `docs/Database/OriginChain_Database_Design_v1.1.pdf` as database reference, though the emergency prototype should not implement the full 9-table design.
- `.gitignore` already covers Python virtual environments, Python cache files, SQLite default `db.sqlite3`, test caches, build outputs, and `.env`.

## Broken Or Missing Components

Missing for the target demo:

- Smart contract implementing product registration, transfer, verification, and ownership history.
- Hardhat local project, compile/test/deploy scripts, and local network workflow.
- FastAPI backend.
- SQLite persistence for off-chain product metadata.
- Deterministic metadata serialization and hashing.
- Web3 bridge between FastAPI and the local Hardhat contract.
- Minimal user interface for manufacturer registration, ownership transfers, and consumer verification.
- Demo seed flow for `OC-DEMO-0001`.
- Tests for duplicate registration, unauthorized transfer, zero-address transfer, unknown transfer, genuine verification, not-found verification, and suspicious metadata hash mismatch.
- Run instructions.

Not present and intentionally out of scope for the emergency demo:

- AI/OpenCV/PyTorch verification.
- Isolation Forest anomaly detection.
- IPFS/Pinata storage.
- JWT authentication.
- Role-based dashboards.
- PostgreSQL production schema.
- Polygon deployment.

## Precise Demo Architecture

Use a narrow local prototype that preserves the important production boundary:

```text
Browser
  |
  v
FastAPI app
  |-- serves minimal HTML/CSS/JS
  |-- stores off-chain product metadata in SQLite
  |-- deterministically serializes metadata and computes keccak256 hash
  |-- calls local Hardhat contract through Web3.py
  |
  v
Hardhat local EVM
  |
  v
OriginChain Solidity contract
```

On-chain data:

- Product code hash or product identifier
- Manufacturer wallet
- Current owner wallet
- Metadata hash
- Registration timestamp
- Ownership history stored directly or reconstructable from events

Off-chain SQLite data:

- Product code
- Product name
- Brand
- Batch
- Description/demo metadata
- Optional image URL
- Last stored metadata hash

Demo actors:

- Hardhat account 0: Manufacturer
- Hardhat account 1: Distributor
- Hardhat account 2: Retailer

Recommended demo endpoints:

- `GET /` serves the interface.
- `POST /api/demo/reset` clears SQLite demo state if needed and registers/loads contract state for a clean demo.
- `POST /api/products/register` registers `OC-DEMO-0001` metadata off-chain and on-chain.
- `POST /api/products/{code}/transfer` transfers from current owner to a selected actor wallet.
- `GET /api/products/{code}/verify` returns `GENUINE`, `NOT_FOUND`, or `SUSPICIOUS`.
- `POST /api/products/{code}/tamper` intentionally modifies off-chain metadata for the metadata-integrity demo.

Verification result should include:

- `status`
- `blockchainVerified`
- Product information from SQLite
- Manufacturer wallet
- Current owner wallet
- Ownership history
- Stored off-chain metadata hash
- Immutable on-chain metadata hash
- Metadata integrity result
- Contract address
- Registration transaction hash/block number if available
- Transfer transaction hashes/block numbers if available

## Files That Will Probably Need Modification

Create under `blockchain/`:

- `package.json`
- `hardhat.config.js`
- `contracts/OriginChain.sol`
- `scripts/deploy.js`
- `test/OriginChain.test.js`
- Possibly `artifacts/` generated locally, not committed unless required for demo simplicity

Create under `backend/`:

- `requirements.txt`
- `main.py`
- `database.py`
- `blockchain_client.py`
- `metadata_hash.py`
- `static/index.html`
- `static/styles.css`
- `static/app.js`
- SQLite database generated locally at runtime, preferably ignored

Potentially update:

- `README.md` with emergency demo run instructions after implementation.
- `.gitignore` if generated Hardhat/cache/database files are not already covered.

Do not modify:

- `ai/` for this demo.
- Production SRS/database PDFs.

## Dependency Changes Required

Blockchain dependencies:

- `hardhat`
- `@nomicfoundation/hardhat-toolbox`
- `ethers`

Backend dependencies:

- `fastapi`
- `uvicorn`
- `web3`
- `python-dotenv`

Optional backend dependency:

- `sqlalchemy` if using ORM models; otherwise Python `sqlite3` is sufficient and faster for this prototype.

Frontend dependencies:

- None if served as static HTML/CSS/JS from FastAPI.

## Estimated Phase Sequence

Phase 1: Scaffold local blockchain

- Create Hardhat project files.
- Implement `OriginChain.sol` with `registerProduct`, `transferOwnership`, `getProduct`, and `getOwnershipHistory`.
- Emit `ProductRegistered` and `OwnershipTransferred`.
- Add tests for required contract security behavior.

Phase 2: Deploy workflow

- Add local deployment script.
- Save contract address and ABI in a backend-readable location.
- Confirm Hardhat local account mapping for Manufacturer, Distributor, Retailer.

Phase 3: Backend prototype

- Create FastAPI app.
- Add SQLite metadata table.
- Implement deterministic JSON serialization and keccak256 hashing.
- Add Web3.py contract client.
- Implement register, transfer, verify, and tamper endpoints.

Phase 4: Minimal UI

- Serve a single FastAPI static page.
- Add controls for registering `OC-DEMO-0001`, transferring Manufacturer to Distributor, transferring Distributor to Retailer, verifying known/unknown product, and tampering metadata.
- Display status, ownership history, hashes, contract address, and transaction details.

Phase 5: Demo hardening

- Add one-command or short-command run instructions.
- Add a seed/reset action for repeatable demonstration.
- Run contract tests and backend smoke checks.
- Manually execute the target demo flow end to end.

## Phase 1 Blockchain Core Instructions

Implemented under `blockchain/`:

- `contracts/OriginChain.sol`
- `hardhat.config.js`
- `scripts/deploy.js`
- `test/OriginChain.test.js`
- `package.json`
- `package-lock.json`
- `deployments/local.json` after local deployment

Installed blockchain tooling:

- Hardhat `2.29.1`
- `@nomicfoundation/hardhat-toolbox` `6.1.2`
- ethers `6.17.0` through Hardhat toolbox

Contract capabilities now covered:

- `registerProduct(bytes32 productKey, bytes32 metadataHash)`
- `transferOwnership(bytes32 productKey, address newOwner)`
- `getProduct(bytes32 productKey)`
- `verifyProduct(bytes32 productKey)`
- `getOwnershipHistory(bytes32 productKey)`
- Events: `ProductRegistered`, `OwnershipTransferred`

Blockchain commands:

```powershell
cd blockchain
npm install
npm run compile
npm test
```

Local deployment commands:

```powershell
cd blockchain
npx hardhat node
```

In a second terminal:

```powershell
cd blockchain
npm run deploy:local
```

Deployment discovery:

- `blockchain/deployments/local.json` contains `network`, `chainId`, `contractAddress`, deployer/demo actor addresses, deployment transaction hash, deployment block number, `abiPath`, and embedded `abi`.
- The latest successful localhost deployment wrote contract address `0x5FbDB2315678afecb367f032d93F642f64180aa3` on network `localhost`, chain ID `31337`, transaction `0xa378899861c044c6a77621dd7d1c668885df375c70bf8757ebec01913140b7a5`, block `1`.

## Phase 2 Blockchain Application Bridge Instructions

Implemented under `backend/`:

- `main.py`: FastAPI app and routes.
- `blockchain_client.py`: Web3.py bridge to local Hardhat JSON-RPC and deployed `OriginChain` contract.
- `database.py`: SQLite persistence using built-in `sqlite3`.
- `metadata_hash.py`: one canonical metadata serialization and keccak256 hashing path.
- `requirements.txt`: FastAPI, Uvicorn, Web3.py, pytest, and HTTPX test dependency.
- `tests/test_metadata_hash.py`: deterministic hashing tests.
- `tests/test_verify_logic.py`: focused verification status tests with a fake blockchain client.

Backend routes:

- `GET /api/health`
- `POST /api/products/register`
- `POST /api/ownership-transfers`
- `GET /api/verify/{product_code}`
- `POST /api/demo/tamper/{product_code}`
- `POST /api/demo/reset`

SQLite data:

- Default database path: `backend/originchain_demo.sqlite3`.
- `products` stores product code, name, brand, batch number, description, canonical metadata JSON, product key, metadata hash, registration transaction hash, and registration block number.
- `ownership_transfers` stores local transaction references for demo transfers.
- The demo tamper route updates off-chain brand/description and canonical metadata JSON only. It does not change the blockchain metadata hash.

Hashing:

- `metadata_hash.canonical_metadata()` uses `json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- `metadata_hash.metadata_hash()` computes Web3.py `keccak` over the canonical JSON text.
- `metadata_hash.product_key()` computes Web3.py `keccak` over the trimmed external product code, such as `OC-DEMO-0001`.

Backend run commands:

```powershell
python -m pip install -r backend\requirements.txt
```

Terminal 1:

```powershell
cd blockchain
npx hardhat node
```

Terminal 2:

```powershell
cd blockchain
npm run deploy:local
```

Terminal 3 from repository root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Backend test commands:

```powershell
python -m pytest backend\tests -q
cd blockchain
npm test
```

Manual smoke results from Phase 2:

- Latest smoke deployment: `0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9` on `localhost`, chain ID `31337`.
- Deployment transaction: `0xa4fac38cb7eb05de8a1dd701669c3e48fcc646098766cd3f34a7a851597636c9`, block `5`.
- `GET /api/health`: blockchain connected `true`, contract loaded `true`.
- `POST /api/products/register`: registered `OC-DEMO-0001`, block `6`.
- `POST /api/ownership-transfers` to `DISTRIBUTOR`: block `7`.
- `POST /api/ownership-transfers` to `RETAILER`: block `8`.
- `GET /api/verify/OC-DEMO-0001`: returned `GENUINE`, current owner `RETAILER`, history length `3`.
- `POST /api/demo/tamper/OC-DEMO-0001`: returned `DEMO ONLY - NOT PRODUCTION`.
- `GET /api/verify/OC-DEMO-0001` after tamper: returned `SUSPICIOUS`, metadata integrity `false`.
- `GET /api/verify/OC-UNKNOWN-9999`: returned `NOT_FOUND`.

## Phase 3 Demonstration UI Instructions

Frontend inspection:

- `frontend/` still contains only `.gitkeep`.
- No functioning Next.js application, package manifest, routes, or components exist.
- Phase 3 therefore uses a FastAPI-served single-page HTML/CSS/JavaScript interface under `backend/static/`.

Implemented UI files:

- `backend/static/index.html`
- `backend/static/styles.css`
- `backend/static/app.js`
- `backend/tests/ui_smoke_cdp.js` for headless Chrome click-flow smoke testing through Chrome DevTools Protocol.

Backend UI support:

- `GET /` serves the demo page.
- `GET /static/styles.css` serves page styling.
- `GET /static/app.js` serves UI behavior.
- `GET /api/qr/{product_code}` returns a PNG QR code for the product code.
- `GET /favicon.ico` returns no content to avoid demo-terminal 404 noise.

UI flow:

1. Status bar calls `GET /api/health` and displays blockchain connection, network, contract address, and current block.
2. Product form registers `OC-DEMO-0001` through `POST /api/products/register`.
3. Registration result displays real transaction hash, block, metadata hash, and manufacturer wallet.
4. Supply-chain panel shows Manufacturer -> Distributor -> Retailer and reveals only the next valid transfer button based on current blockchain owner.
5. Transfer buttons call `POST /api/ownership-transfers` and display real transaction hashes/blocks.
6. QR panel displays PNG from `GET /api/qr/OC-DEMO-0001`.
7. Consumer verification calls `GET /api/verify/{product_code}` and renders `GENUINE`, `NOT_FOUND`, or `SUSPICIOUS`.
8. Tamper panel calls `POST /api/demo/tamper/{product_code}` and then automatically verifies again.
9. Reset button calls `POST /api/demo/reset`; it clears local SQLite metadata only. If the same product was already registered on the active Hardhat chain, redeploy the contract before registering the same code again.

UI run command:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

Phase 3 test commands:

```powershell
node --check backend\static\app.js
node --check backend\tests\ui_smoke_cdp.js
python -m pytest backend\tests -q
cd blockchain
npm test
```

Full UI smoke sequence:

1. Start `npx hardhat node`.
2. Run `npm run deploy:local` from `blockchain/`.
3. Start `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
4. Run `node backend\tests\ui_smoke_cdp.js` from repository root.

Latest Phase 3 UI smoke result:

- Contract used by UI: `0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9`.
- Registration tx: `0x266cba629e4c375ed0cbd85944b18a6122a9cd3f0aa380f8f299a8f9d195541f`, block `5`.
- Manufacturer -> Distributor tx: `0x0cf47b5fb1ec7604f3a1bf39d593c30cb1bdf8f9bc4fd707cd4ed8bb361e45a8`, block `6`.
- Distributor -> Retailer tx: `0x3867c273e5736f207ce68d34400df0673e3c360e3fa120ac96e50fd53c03c412`, block `7`.
- Browser smoke clicked registration, transfer 1, transfer 2, genuine verification, unknown verification, tamper simulation, and suspicious verification.
- Headless Chrome smoke reported no JavaScript console/runtime errors.

## Risks

- There is no existing implementation, so the prototype must be scaffolded from zero.
- The current folder is not a Git repository; branch/status protections cannot be verified from this path.
- Python `3.13.13` is installed. If `web3` or transitive dependencies have Python 3.13 issues, backend setup may slow down. Fallback is to use a Node/ethers bridge or keep blockchain interaction in scripts, but FastAPI plus Web3.py remains the preferred prototype path.
- Hardhat compatibility with Node `v24.18.0` may be an issue because many Hardhat projects are commonly run on LTS Node versions. If Hardhat fails under Node 24, use an installed LTS Node if available or adjust quickly.
- No committed run instructions exist yet.
- No existing UI can be reused, so the demo page must be created.
- No existing contract ABI/address generation exists, so backend and blockchain wiring must be designed carefully to avoid demo-time mismatch.

## BASELINE

- Current branch: unavailable; `OriginChain-main` is not a Git repository.
- Git status: unavailable; `git status` fails because no `.git` directory exists in or under this project tree.
- Relevant stack from README: Next.js/React/Tailwind, FastAPI/Python/SQLAlchemy/JWT, PostgreSQL, Solidity/Hardhat/Polygon/IPFS, OpenCV/PyTorch/Isolation Forest.
- Actual stack currently implemented: none.
- Tests/build results: no tests or builds were run because no package manifests, test files, source files, or build configs exist.

## REUSE

- Reuse the existing directory layout.
- Reuse README as intended architecture reference.
- Reuse docs as planning references.
- Reuse `.gitignore` for Python environment/cache protection; extend later only if generated Hardhat or SQLite artifacts need coverage.

## MISSING

- Complete local Hardhat contract layer.
- Complete FastAPI backend.
- Complete SQLite off-chain metadata store.
- Complete deterministic metadata hashing.
- Complete local Web3 bridge.
- Complete minimal browser demo UI.
- Complete demo tests/smoke checks.
- Complete emergency run instructions.

## DEMO PLAN

Implement the smallest working vertical slice:

1. Build `blockchain/contracts/OriginChain.sol` with duplicate-registration prevention, current-owner-only transfer, zero-address rejection, unknown-product rejection, product getter, and ownership history getter.
2. Add Hardhat compile/test/deploy workflow using local accounts for Manufacturer, Distributor, and Retailer.
3. Build FastAPI app in `backend/` using SQLite for product metadata and Web3.py for contract calls.
4. Use deterministic JSON serialization for metadata hashing before registration and during verification.
5. Serve a single static interface from FastAPI instead of building a Next.js app.
6. Support the exact demo flow: register `OC-DEMO-0001`, transfer Manufacturer to Distributor, transfer Distributor to Retailer, verify genuine product, verify unknown product as `NOT_FOUND`, tamper metadata, verify tampered product as `SUSPICIOUS`.
7. Display contract address, metadata hash comparison, owner history, and transaction/block details where available.

## RISKS

- The project is currently documentation-only, so all demo behavior must be built.
- Local dependency installation may consume time because there are no lockfiles.
- Node 24 and Python 3.13 may expose dependency compatibility problems.
- If Hardhat local node, deploy script, and FastAPI are not started in the right order, the backend may point at a missing or stale contract address.
- The demo must avoid scope creep into AI, IPFS, auth, full dashboards, PostgreSQL, or Polygon deployment.
