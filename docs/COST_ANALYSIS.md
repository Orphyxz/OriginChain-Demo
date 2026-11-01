# OriginChain: Cost Analysis

*Prepared 14 October 2026; gas re-measured 18 October 2026 after the five-checks-per-stage redesign. Gas figures are measured; prices are market snapshots and change daily.*

## 1. Summary

| Scenario | Cost |
|---|---|
| **Current demo (local)** | **$0.** Every component is free and open-source and runs on one laptop |
| Blockchain cost per batch on **Polygon PoS** | **≈ $0.025** (about 2.5 cents) |
| Blockchain cost per batch on **Base** (Ethereum L2) | ≈ $0.02–$0.25 |
| Blockchain cost per batch on **Ethereum mainnet** | ≈ $0.80–$4.40 at recent gas; ≈ $23 when congested |
| Small hosted pilot on Polygon (server + 100 batches/month) | **≈ $15/month** |

On a low-fee chain, the blockchain is the *cheapest* part of the system. The server costs more than the ledger.

## 2. Current cost: $0

| Component | Tool | Licence / cost |
|---|---|---|
| Smart contract and local chain | Solidity, Hardhat | Free, open source |
| Backend | Python, FastAPI, Web3.py | Free, open source |
| Database and files | SQLite, local disk | Free |
| Frontend | Plain HTML/CSS/JS | Free |
| Blockchain fees | Hardhat test ETH | Free (test value only) |
| Hosting | Runs on a laptop | Free |

There are no paid APIs, cloud services or subscriptions.

## 3. Measured blockchain usage

I ran the full five-role workflow on the local chain: register, three stage approvals, six certificate commitments (two per on-chain stage), two custody transfers, and the retail HOLD and correction. I then added up the gas from every transaction for that product.

| Contract call | Calls per batch | Gas each | Gas total |
|---|---:|---:|---:|
| `registerProduct` | 1 | 160,072 | 160,072 |
| `recordQualityStage` (Manufacturer, Distributor, Retailer) | 3 | ≈ 96,870 | 290,622 |
| `recordEvidenceHash` (2 certificates × 3 stages) | 6 | ≈ 52,270 | 313,602 |
| `transferOwnership` | 2 | 64,575 / 81,687 | 146,262 |
| **Total per batch** | **12 transactions** | | **910,558** |
| Contract deployment (one-off) | 1 | 726,445 | 726,445 |

Notes:
- The raw-material stage has no on-chain transaction of its own, because the product doesn't exist on-chain until the Manufacturer registers it.
- A HOLD and its correction adds no extra transactions. Only the final approval is committed.
- Each extra evidence file adds about 52k gas.

## 4. Cost per batch by network

Formula: **cost = gas used × gas price × token price**

| Network | Gas price assumed | Token price | Per batch (0.91M gas) | One-off deployment |
|---|---|---|---:|---:|
| **Polygon PoS** | 272 gwei (≈ 250–400 range) | POL ≈ $0.10 | **$0.025** (up to ≈ $0.036) | ≈ $0.02 |
| **Base** (L2) | n/a; priced per transaction | — | $0.02–$0.24 (12 tx × $0.0016–$0.02) | Cents |
| **Ethereum mainnet**, quiet | 0.36 gwei | ETH ≈ $2,504 | $0.82 | ≈ $0.65 |
| **Ethereum mainnet**, recent typical | 1.92 gwei | ETH ≈ $2,504 | $4.38 | ≈ $3.49 |
| **Ethereum mainnet**, congested | 10 gwei | ETH ≈ $2,504 | $22.80 | ≈ $18.19 |

**Per bottle:** one on-chain record covers a whole batch, so the fee is shared. A 1,000-bottle batch on Polygon costs about **$0.000025 per bottle**. If each bottle were later given its own on-chain identity (serialisation), add about 160k gas per bottle for registration, which is roughly $0.004 per bottle on Polygon.

## 5. Running costs at scale (Polygon PoS)

| Item | Pilot (100 batches/month) | Growth (1,000 batches/month) |
|---|---:|---:|
| Blockchain fees | $2.50–$3.60 | $25–$36 |
| Server (2 GB cloud VM, e.g. DigitalOcean Basic) | $12 | $24–$48 (bigger VM or two VMs) |
| Hosted RPC node | Provider free tier is usually enough; check its limits | Paid tier may be needed |
| Database | SQLite on the VM: $0 | Managed PostgreSQL: extra |
| Evidence storage | On the VM disk: $0 | Object storage: extra, by GB |
| **Approximate total** | **≈ $15/month** | **≈ $50–$85/month + managed DB/storage** |

Not included: a domain name, TLS certificate (free with Let's Encrypt), backups, monitoring, and staff time.

## 6. Cost drivers and ways to cut them

1. **Certificate commitments are 34% of the gas.** Folding each stage's certificate hashes into its stage record (a Merkle root) would cut a batch from 12 transactions to 6 and save roughly 250k gas.
2. **Network choice matters most.** The same workload costs about 2.5¢ on Polygon and up to about $23 on a congested Ethereum mainnet: a gap of over 900×.
3. **Fees are volatile.** Gas price and token price both move. Budget 2–3× the table figures for safety, and pay fees from a monitored hot wallet.
4. **Off-chain storage keeps it cheap.** Only 32-byte hashes go on-chain. Storing the evidence files themselves on-chain would cost orders of magnitude more.

## 7. Recommendation

For a pilot, **Polygon PoS (or the Amoy testnet first)** gives real public verifiability for a few cents per batch. The total running cost is dominated by a ~$12/month server. Ethereum mainnet is only justified if a partner specifically requires it.

## 8. Method and sources

- Gas was first measured on 14 October 2026 (old 24-check catalogue: 14 tx, 1,015,116 gas) and re-measured on 18 October 2026 from the full UI walkthrough (`ORIGINCHAIN_UI_FULL_DEMO=1 node backend/tests/ui_smoke_cdp.js`), summing `gasUsed` from every transaction receipt for that product. Gas is chain-independent for EVM networks, so it carries over to Polygon, Base and Ethereum.
- Polygon gas price: [PolygonScan gas tracker](https://polygonscan.com/gastracker) (272 gwei on 7 Oct 2026) and [ChainGate](https://chaingate.dev/gas-tracker/polygon).
- POL price: [MetaMask](https://metamask.io/price/polygon-ecosystem-token) (≈ $0.10 on 14 Oct 2026).
- Ethereum gas: [Etherscan gas tracker](https://etherscan.io/gastracker?v=1649187329) (1.92 gwei on 7 Oct 2026; 0.36 gwei on 1 Oct 2026).
- ETH price: [Fortune, 13 Oct 2026](https://fortune.com/article/price-of-ethereum-10-13-2026) (≈ $2,504).
- Base fees: [arXiv study of L2 fees](https://arxiv.org/html/2606.22206v1) (median ≈ $0.0016) and the [Ethereum L2 Scorecard 2026](https://www.spotedcrypto.com/ethereum-l2-scorecard-2026-tvl-fees-security/) (≈ $0.02).
- Server: DigitalOcean Basic 2 GB at $12/month, per [VPSBenchmarks](https://www.vpsbenchmarks.com/hosters/digitalocean/plans/63). Confirm on the official pricing page before budgeting.
