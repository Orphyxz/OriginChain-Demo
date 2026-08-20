const state = {
  registered: null,
  verification: null,
  transfers: [],
  health: null,
  busy: false,
};

const els = {
  chainStatus: document.querySelector("#chainStatus"),
  networkName: document.querySelector("#networkName"),
  contractAddress: document.querySelector("#contractAddress"),
  currentBlock: document.querySelector("#currentBlock"),
  errorBox: document.querySelector("#errorBox"),
  registrationForm: document.querySelector("#registrationForm"),
  registerButton: document.querySelector("#registerButton"),
  registrationResult: document.querySelector("#registrationResult"),
  transferDistributorButton: document.querySelector("#transferDistributorButton"),
  transferRetailerButton: document.querySelector("#transferRetailerButton"),
  transferLog: document.querySelector("#transferLog"),
  verifyForm: document.querySelector("#verifyForm"),
  verifyCode: document.querySelector("#verifyCode"),
  verifyButton: document.querySelector("#verifyButton"),
  verificationResult: document.querySelector("#verificationResult"),
  tamperButton: document.querySelector("#tamperButton"),
  resetButton: document.querySelector("#resetButton"),
  tamperResult: document.querySelector("#tamperResult"),
  qrImage: document.querySelector("#qrImage"),
  qrCodeText: document.querySelector("#qrCodeText"),
  productCode: document.querySelector("#productCode"),
  walletManufacturer: document.querySelector("#walletManufacturer"),
  walletDistributor: document.querySelector("#walletDistributor"),
  walletRetailer: document.querySelector("#walletRetailer"),
};

function shortAddress(value) {
  if (!value || value === "-") return "-";
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setBusy(isBusy) {
  state.busy = isBusy;
  [
    els.registerButton,
    els.transferDistributorButton,
    els.transferRetailerButton,
    els.verifyButton,
    els.tamperButton,
    els.resetButton,
  ].forEach((button) => {
    button.disabled = isBusy;
  });
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof body === "object" && body !== null ? body.detail : body;
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }

  return body;
}

function showError(error) {
  els.errorBox.textContent = error.message || String(error);
  els.errorBox.classList.remove("hidden");
}

function clearError() {
  els.errorBox.textContent = "";
  els.errorBox.classList.add("hidden");
}

async function refreshHealth() {
  try {
    const health = await requestJson("/api/health");
    state.health = health;
    els.chainStatus.textContent = health.blockchain_connected ? "Connected" : "Offline";
    els.networkName.textContent = health.network === "localhost" ? "Hardhat Local" : (health.network || "-");
    els.contractAddress.textContent = shortAddress(health.contract_address);
    els.currentBlock.textContent = health.current_block ?? "-";
  } catch (error) {
    els.chainStatus.textContent = "Offline";
    els.networkName.textContent = "-";
    els.contractAddress.textContent = "-";
    els.currentBlock.textContent = "-";
    showError(error);
  }
}

function formPayload() {
  return {
    product_code: els.productCode.value.trim(),
    name: document.querySelector("#productName").value.trim(),
    brand: document.querySelector("#brand").value.trim(),
    batch_number: document.querySelector("#batchNumber").value.trim(),
    description: document.querySelector("#description").value.trim(),
  };
}

function updateQr() {
  const code = els.productCode.value.trim() || "OC-DEMO-0001";
  els.qrImage.src = `/api/qr/${encodeURIComponent(code)}?t=${Date.now()}`;
  els.qrCodeText.textContent = code;
  els.verifyCode.value = code;
}

function renderRegistration(result) {
  if (!result) {
    els.registrationResult.className = "result-box hidden";
    els.registrationResult.innerHTML = "";
    return;
  }

  els.registrationResult.className = "result-box success";
  els.registrationResult.innerHTML = `
    <div class="result-title">Product registered on blockchain</div>
    <div class="kv">
      <span>Transaction Hash</span><code>${escapeHtml(result.transaction_hash)}</code>
      <span>Block</span><code>${escapeHtml(result.block_number)}</code>
      <span>Metadata Hash</span><code>${escapeHtml(result.metadata_hash)}</code>
      <span>Manufacturer</span><code>${escapeHtml(result.manufacturer_wallet)}</code>
    </div>
  `;
}

function renderWalletsFromVerification(verification) {
  const history = verification?.ownership_history || [];
  const byRole = new Map(history.map((item) => [item.role, item.wallet]));
  if (verification?.manufacturer) byRole.set("MANUFACTURER", verification.manufacturer.wallet);
  if (verification?.current_owner) byRole.set(verification.current_owner.role, verification.current_owner.wallet);

  els.walletManufacturer.textContent = shortAddress(byRole.get("MANUFACTURER"));
  els.walletDistributor.textContent = shortAddress(byRole.get("DISTRIBUTOR"));
  els.walletRetailer.textContent = shortAddress(byRole.get("RETAILER"));

  document.querySelectorAll(".chain-node").forEach((node) => {
    const role = node.dataset.role;
    node.classList.toggle("active", byRole.has(role));
    node.classList.toggle("current", verification?.current_owner?.role === role);
  });
}

function renderTransferButtons(verification = state.verification) {
  els.transferDistributorButton.classList.add("hidden");
  els.transferRetailerButton.classList.add("hidden");

  if (!verification || verification.status === "NOT_FOUND") return;
  const currentRole = verification.current_owner?.role;
  if (currentRole === "MANUFACTURER") {
    els.transferDistributorButton.classList.remove("hidden");
  } else if (currentRole === "DISTRIBUTOR") {
    els.transferRetailerButton.classList.remove("hidden");
  }
}

function renderTransferLog() {
  if (!state.transfers.length) {
    els.transferLog.textContent = "Transfers will appear here after blockchain transactions.";
    return;
  }

  els.transferLog.innerHTML = state.transfers.map((transfer) => `
    <div>
      <strong>${escapeHtml(transfer.from_role)} → ${escapeHtml(transfer.to_role)}</strong>
      <div>Tx: <code>${escapeHtml(transfer.transaction_hash)}</code></div>
      <div>Block: <code>${escapeHtml(transfer.block_number)}</code></div>
    </div>
  `).join("");
}

function renderVerification(result) {
  state.verification = result;

  if (result.status === "NOT_FOUND") {
    els.verificationResult.className = "verification not-found";
    els.verificationResult.innerHTML = `
      <div class="result-title">Product not found</div>
      <p>${escapeHtml(result.message || "No blockchain-backed product record was found.")}</p>
    `;
    renderWalletsFromVerification(null);
    renderTransferButtons(null);
    return;
  }

  const isGenuine = result.status === "GENUINE";
  els.verificationResult.className = `verification ${isGenuine ? "genuine" : "suspicious"}`;
  const title = isGenuine ? "Genuine Product" : "Suspicious";
  const subtitle = isGenuine
    ? "Blockchain authenticity confirmed"
    : "Blockchain record exists, but stored metadata no longer matches its immutable on-chain hash.";

  const timeline = (result.ownership_history || []).map((item, index, list) => {
    const isCurrent = item.wallet === result.current_owner.wallet;
    const label = index === 0 ? "Registered" : (isCurrent ? "Current Owner" : "");
    const arrow = index < list.length - 1 ? '<div class="timeline-arrow">↓ blockchain transfer</div>' : "";
    return `
      <div class="timeline-item">
        <strong>${escapeHtml(item.role)}</strong>
        <code>${escapeHtml(shortAddress(item.wallet))}</code>
        <span>${escapeHtml(label)}</span>
      </div>
      ${arrow}
    `;
  }).join("");

  els.verificationResult.innerHTML = `
    <div class="result-title">${escapeHtml(title)}</div>
    <p>${escapeHtml(subtitle)}</p>
    <div class="kv">
      <span>Product</span><strong>${escapeHtml(result.product.name)}</strong>
      <span>Brand</span><strong>${escapeHtml(result.product.brand)}</strong>
      <span>Batch</span><strong>${escapeHtml(result.product.batch_number)}</strong>
      <span>Manufacturer</span><code>${escapeHtml(shortAddress(result.manufacturer.wallet))}</code>
      <span>Current Owner</span><code>${escapeHtml(result.current_owner.role)} / ${escapeHtml(shortAddress(result.current_owner.wallet))}</code>
      <span>Metadata Integrity</span><strong>${result.metadata_integrity ? "Matched" : "Mismatch"}</strong>
      <span>Metadata Hash</span><code>${escapeHtml(result.blockchain.metadata_hash)}</code>
      <span>Contract</span><code>${escapeHtml(result.blockchain.contract_address)}</code>
    </div>
    <div class="timeline-list">${timeline}</div>
  `;

  renderWalletsFromVerification(result);
  renderTransferButtons(result);
}

async function verifyCurrent(code = els.verifyCode.value.trim()) {
  const result = await requestJson(`/api/verify/${encodeURIComponent(code)}`);
  renderVerification(result);
  return result;
}

els.registrationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setBusy(true);
  try {
    updateQr();
    const result = await requestJson("/api/products/register", {
      method: "POST",
      body: JSON.stringify(formPayload()),
    });
    state.registered = result;
    state.transfers = [];
    renderRegistration(result);
    renderTransferLog();
    await verifyCurrent(result.product_code);
    await refreshHealth();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

async function transferTo(role) {
  clearError();
  setBusy(true);
  try {
    const productCode = els.productCode.value.trim();
    const transfer = await requestJson("/api/ownership-transfers", {
      method: "POST",
      body: JSON.stringify({
        product_code: productCode,
        to_role: role,
      }),
    });
    state.transfers.push(transfer);
    renderTransferLog();
    await verifyCurrent(productCode);
    await refreshHealth();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

els.transferDistributorButton.addEventListener("click", () => transferTo("DISTRIBUTOR"));
els.transferRetailerButton.addEventListener("click", () => transferTo("RETAILER"));

els.verifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  setBusy(true);
  try {
    await verifyCurrent();
    await refreshHealth();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

els.tamperButton.addEventListener("click", async () => {
  clearError();
  setBusy(true);
  try {
    const code = els.productCode.value.trim();
    const result = await requestJson(`/api/demo/tamper/${encodeURIComponent(code)}`, {
      method: "POST",
    });
    els.tamperResult.textContent = result.message;
    await verifyCurrent(code);
    await refreshHealth();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

els.resetButton.addEventListener("click", async () => {
  clearError();
  setBusy(true);
  try {
    const result = await requestJson("/api/demo/reset", { method: "POST" });
    state.registered = null;
    state.verification = null;
    state.transfers = [];
    renderRegistration(null);
    renderTransferLog();
    renderWalletsFromVerification(null);
    renderTransferButtons(null);
    els.verificationResult.className = "verification empty";
    els.verificationResult.textContent = "Local metadata cleared. Redeploy Hardhat contract before reusing the same product code if it was already registered on this chain.";
    els.tamperResult.textContent = result.message;
    await refreshHealth();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

els.productCode.addEventListener("change", updateQr);
els.productCode.addEventListener("blur", updateQr);

renderTransferLog();
refreshHealth();
