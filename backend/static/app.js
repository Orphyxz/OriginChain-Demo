const state = {
  materials: [], products: [], activeStage: null, contextType: null,
  contextId: null, activeSummary: null, verification: null, user: null,
  qualitySources: [], qualityProfiles: [], productSpecifications: [], evidenceIssuers: [],
  sourceReviews: [], changeRecords: [], journey: [],
  demoMode: false, demoAction: null, health: null, evidenceCheck: null,
  boardEnter: false, changedStandard: null,
  token: localStorage.getItem("originchain_demo_access_token") || null,
};
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const DEMO_PASSWORD = "OriginDemo2026!";
const STAGES = ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER"];
const STAGE_NAMES = {
  RAW_MATERIAL_SUPPLIER: "Raw Materials", MANUFACTURER: "Manufacturing",
  DISTRIBUTOR: "Distribution", RETAILER: "Retail",
};
const ROLE_STAGE = {
  RAW_MATERIAL_SUPPLIER: "RAW_MATERIAL_SUPPLIER", MANUFACTURER: "MANUFACTURER",
  DISTRIBUTOR: "DISTRIBUTOR", RETAILER: "RETAILER",
};
const ROLE_STAGE_VIEWS = {
  RAW_MATERIAL_SUPPLIER: ["RAW_MATERIAL_SUPPLIER"],
  MANUFACTURER: ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER"],
  DISTRIBUTOR: ["MANUFACTURER", "DISTRIBUTOR"],
  RETAILER: ["MANUFACTURER", "DISTRIBUTOR", "RETAILER"],
  ADMIN: STAGES,
};
const ROLE_NAMES = {
  RAW_MATERIAL_SUPPLIER: "Supplier", MANUFACTURER: "Manufacturer",
  DISTRIBUTOR: "Distributor", RETAILER: "Retailer", ADMIN: "Admin",
};
const OPERATIONAL_ROLES = ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER"];
const LANES = [
  { category: "Check", label: "Checks", cls: "kind-check", hint: "Hands-on inspections" },
  { category: "Certificate", label: "Certificates", cls: "kind-cert", hint: "Uploaded documents" },
  { category: "Final review", label: "Final review", cls: "kind-final", hint: "Sign-off" },
];
const LABELS = {
  APPROVED_FOR_SALE: "Approved for sale", NOT_READY: "Not ready", NOT_APPLICABLE: "N/A",
  CONSUMER_VISIBLE: "Public", INTERNAL: "Internal", FILE_MISSING: "File missing",
  PENDING: "Pending", APPROVED: "Approved", HOLD: "On hold", REJECTED: "Rejected",
  PASS: "Pass", FAIL: "Fail", VERIFIED: "Verified", MISMATCH: "Mismatch",
  SUSPICIOUS: "Suspicious", GENUINE: "Authentic", NOT_STARTED: "Not started", READY: "Ready to approve",
  CERTIFICATE_OF_ANALYSIS: "Certificate of Analysis", MICROBIOLOGY_REPORT: "Microbiology report",
  PRESERVATIVE_EFFICACY_REPORT: "Preservation report", RAW_MATERIAL_SPECIFICATION: "Ingredient review",
  BATCH_MANUFACTURING_RECORD: "Batch record", PACKAGING_INSPECTION: "Packaging inspection",
  TRANSPORT_RECORD: "Shipping record", STORAGE_RECORD: "Storage log", GOODS_RECEIPT: "Goods receipt",
  RETAIL_INSPECTION: "Retail inspection", OTHER: "Document",
  TRUSTED_DEMO: "Trusted", UNVERIFIED: "Unverified", REVOKED: "Revoked",
  PUBLISHED_CURRENT: "Current", PUBLISHED_UNDER_REVISION: "Under revision", DRAFT: "Draft",
  RAW_MATERIAL_SUPPLIER: "Supplier", MANUFACTURER: "Manufacturer", DISTRIBUTOR: "Distributor",
  RETAILER: "Retailer", ADMIN: "Admin",
};
const GOOD = ["APPROVED", "APPROVED_FOR_SALE", "PASS", "VERIFIED", "VERIFIED_DEMO", "TRUSTED_DEMO", "GENUINE", "SUCCESS", "PUBLISHED_CURRENT", "CURRENT", "IMPLEMENTED", "READY"];
const BAD = ["HOLD", "REJECTED", "FAIL", "MISMATCH", "SUSPICIOUS", "REVOKED", "FILE_MISSING", "BLOCKED", "FAILED", "DRAFT", "SUPERSEDED", "WITHDRAWN", "EXPIRED", "NOT_READY_CHECK"];

function esc(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function label(value) {
  if (!value) return "Not started";
  return LABELS[value] || String(value).toLowerCase().split("_")
    .map((part, i) => (i === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part)).join(" ");
}

function pill(value, text = label(value), extra = "") {
  const tone = GOOD.includes(value) ? "ok" : BAD.includes(value) ? "bad" : value ? "" : "idle";
  return `<span class="pill ${tone} ${extra}">${esc(text)}</span>`;
}

function stageStatus(summary) {
  return summary?.status === "PENDING" && summary.eligible_for_approval ? "READY" : summary?.status;
}

function short(hash) {
  return hash ? `${hash.slice(0, 8)}…${hash.slice(-6)}` : "—";
}

/* ---------- Feedback ---------- */
function showFeedback(title, detail = "", type = "error", items = []) {
  const box = $("#notice");
  box.setAttribute("role", type === "error" ? "alert" : "status");
  box.className = `toast ${type}`;
  const duration = type === "error" ? 9000 : 5000;
  box.style.setProperty("--toast-ms", `${duration}ms`);
  box.querySelector(".toast-icon")?.remove();
  box.insertAdjacentHTML("afterbegin", `<span class="toast-icon" aria-hidden="true">${{ success: "✓", warning: "!", error: "×" }[type] || "i"}</span>`);
  box.querySelector(".toast-timer")?.remove();
  box.insertAdjacentHTML("beforeend", '<i class="toast-timer" aria-hidden="true"></i>');
  $("#noticeBody").innerHTML = `<strong>${esc(title)}</strong>${detail ? `<span>${esc(detail)}</span>` : ""}${items.length ? `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}`;
  clearTimeout(showFeedback.timer);
  showFeedback.timer = setTimeout(() => box.classList.add("hidden"), duration);
}

class ApiError extends Error {
  constructor(title, detail, items, status) {
    super(detail || title);
    this.title = title; this.detail = detail; this.items = items; this.status = status;
  }
}

function parseApiError(body, status) {
  const detail = body?.detail ?? body;
  if (typeof detail === "string") return new ApiError("Couldn't complete that", detail, [], status);
  if (Array.isArray(detail)) {
    const items = detail.map((item) => `${(item.loc || []).slice(1).join(" → ")}: ${item.msg}`);
    return new ApiError("Please check the form", "", items, status);
  }
  if (detail?.message) {
    const items = detail.blocking_reasons || (detail.guidance ? [detail.guidance] : []);
    return new ApiError(detail.message, "", items, status);
  }
  return new ApiError("Couldn't complete that", `Server returned HTTP ${status}.`, [], status);
}

async function api(path, options = {}) {
  let response;
  const requestToken = state.token;
  const headers = new Headers(options.headers || {});
  if (requestToken) headers.set("Authorization", `Bearer ${requestToken}`);
  try { response = await fetch(path, { ...options, headers }); }
  catch (_) { throw new ApiError("App is offline", "Check that the FastAPI server is running.", [], 0); }
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("json") ? await response.json() : await response.text();
  if (response.status === 401 && path !== "/api/auth/login" && state.token === requestToken) showLoggedOut();
  if (!response.ok) throw parseApiError(body, response.status);
  return body;
}

function reportError(error, fallbackTitle = "Couldn't complete that") {
  showFeedback(error.title || fallbackTitle, error.detail || "", "error", error.items || []);
}

async function withButton(button, pendingText, work) {
  if (!button || button.getAttribute("aria-busy") === "true") return;
  const original = button.innerHTML;
  const originallyDisabled = button.disabled;
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  if (pendingText) button.textContent = pendingText;
  try { return await work(); }
  finally {
    button.removeAttribute("aria-busy");
    button.innerHTML = original;
    button.disabled = originallyDisabled;
    updateControls();
  }
}

function json(payload) {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) };
}

/* ---------- Routing ---------- */
const VIEW_IDS = { signin: "access", overview: "overview", batches: "batches", quality: "quality", verify: "verify", admin: "admin" };

function allowedView(name) {
  if (!state.user) return ["signin", "verify"].includes(name) ? name : "signin";
  if (name === "signin" || !VIEW_IDS[name]) return "overview";
  if (name === "admin" && state.user.role !== "ADMIN") return "overview";
  return name;
}

function go(name) {
  const target = `#${name}`;
  if (location.hash === target) route(); else location.hash = target;
}

function route() {
  const [rawName, ...rest] = location.hash.slice(1).split("/");
  const deepCode = rawName === "verify" && rest.length ? decodeURIComponent(rest.join("/")) : null;
  const name = allowedView(rawName);
  Object.entries(VIEW_IDS).forEach(([view, id]) => $(`#${id}`).classList.toggle("hidden", view !== name));
  $$("#primaryNav a").forEach((link) => {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (`#${name}` !== location.hash && !deepCode && !(name === "signin" && !location.hash)) history.replaceState(null, "", `#${name}`);
  if (deepCode) {
    $("#verifyCode").value = deepCode;
    runVerify(true);
  }
  if (name === "admin") refreshAudit();
}
window.addEventListener("hashchange", route);

/* ---------- Permissions ---------- */
function currentProduct() {
  return state.products.find((item) => item.product_code === "OC-LUX-SERUM-0001") || state.products[0] || null;
}
function canWriteStage(stage) {
  return Boolean(state.user && ROLE_STAGE[state.user.role] === stage);
}
function canViewStage(stage) {
  return Boolean(state.user && (ROLE_STAGE_VIEWS[state.user.role] || []).includes(stage));
}
function isExpired(dateValue) {
  if (!dateValue) return false;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return new Date(`${dateValue}T00:00:00`) < today;
}
function eligibleMaterials() {
  return state.materials.filter((item) => item.quality_status === "APPROVED" && !isExpired(item.expiry_retest_date));
}

/* ---------- Session ---------- */
function showLoggedOut(message = "") {
  Object.assign(state, {
    token: null, user: null, materials: [], products: [], activeStage: null, contextType: null,
    contextId: null, activeSummary: null, qualitySources: [], qualityProfiles: [],
    productSpecifications: [], evidenceIssuers: [], sourceReviews: [], changeRecords: [], journey: [],
  });
  localStorage.removeItem("originchain_demo_access_token");
  $("#operationalApp").hidden = true;
  $("#accountPanel").classList.add("hidden");
  $$(".auth-only, .admin-only").forEach((item) => item.classList.add("hidden"));
  document.body.removeAttribute("data-role");
  applyFabVisibility();
  route();
  if (message) showFeedback("Signed out", message, "warning");
}

function applyRoleUI() {
  const role = state.user?.role;
  if (!role) return showLoggedOut();
  document.body.dataset.role = role;
  $("#operationalApp").hidden = false;
  $("#accountPanel").classList.remove("hidden");
  $("#accountName").textContent = state.user.display_name;
  $("#accountRole").textContent = ROLE_NAMES[role];
  $("#accountAvatar").textContent = ROLE_NAMES[role].charAt(0);
  $$(".auth-only").forEach((item) => item.classList.remove("hidden"));
  $$(".admin-only").forEach((item) => item.classList.toggle("hidden", role !== "ADMIN"));
  $("#materials").classList.toggle("hidden", !["RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "ADMIN"].includes(role));
  $("#manufacturing").classList.toggle("hidden", role === "RAW_MATERIAL_SUPPLIER");
  $("#batches").style.gridTemplateColumns = ["RAW_MATERIAL_SUPPLIER", "DISTRIBUTOR", "RETAILER"].includes(role) ? "1fr" : "";
  $("#openMaterialForm").classList.toggle("hidden", role !== "RAW_MATERIAL_SUPPLIER");
  $$(".stage-tabs button").forEach((button) => { button.hidden = !canViewStage(button.dataset.stage); });
  applyFabVisibility();
  updateControls();
}

async function beginSession(token, user) {
  state.token = token; state.user = user;
  localStorage.setItem("originchain_demo_access_token", token);
  applyRoleUI();
  await Promise.all([refreshRecords(), refreshQualityReferences()]);
  await refreshDashboard();
  await selectDefaultStage();
  route();
}

async function selectDefaultStage() {
  const role = state.user?.role;
  const stage = ROLE_STAGE[role];
  const product = currentProduct();
  if (stage === "RAW_MATERIAL_SUPPLIER" && state.materials.length) {
    await selectQuality(stage, "RAW_MATERIAL", state.materials[0].id);
  } else if (stage && product) {
    await selectQuality(stage, "PRODUCT", product.product_code);
  } else if (role === "ADMIN" && product) {
    await selectQuality(STAGES.includes(product.current_stage) ? product.current_stage : "RETAILER", "PRODUCT", product.product_code);
  } else if (role === "ADMIN" && state.materials.length) {
    await selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", state.materials[0].id);
  } else {
    renderEmptyBoard();
  }
}

async function signIn(username, password) {
  const result = await api("/api/auth/login", json({ username, password }));
  await beginSession(result.access_token, result.user);
  return result.user;
}

$("#loginForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#loginButton"), "Signing in…", async () => {
    try {
      const user = await signIn($("#loginUsername").value.trim(), $("#loginPassword").value);
      showFeedback(`Welcome, ${ROLE_NAMES[user.role]}`, user.display_name, "success");
      go("overview");
    } catch (error) { reportError(error, "Sign in failed"); }
  });
});

$$(".demo-account").forEach((button) => button.addEventListener("click", () => {
  $("#loginUsername").value = button.dataset.username;
  $("#loginPassword").value = DEMO_PASSWORD;
  $("#loginForm").requestSubmit();
}));

$("#logoutButton").addEventListener("click", () => {
  showLoggedOut();
  $("#loginPassword").value = "";
  go("signin");
});

/* ---------- Health ---------- */
function applyHealth(health) {
  state.health = health;
  $("#chainPill").classList.toggle("online", health.blockchain_connected);
  $("#chainPill span").textContent = health.blockchain_connected ? `Block ${health.current_block}` : "Chain offline";
  $("#networkName").textContent = health.blockchain_connected ? `Hardhat local · block ${health.current_block}` : "Offline";
  $("#contractAddress").textContent = short(health.contract_address);
}

async function refreshHealth(quiet = false) {
  try {
    applyHealth(await api("/api/health"));
  } catch (error) {
    state.health = null;
    $("#chainPill").classList.remove("online");
    $("#chainPill span").textContent = "Offline";
    $("#networkName").textContent = "API unavailable";
    if (!quiet) reportError(error, "Connection check failed");
  }
}

/* ---------- Reference data ---------- */
async function refreshQualityReferences() {
  [state.qualitySources, state.qualityProfiles, state.productSpecifications, state.evidenceIssuers] = await Promise.all([
    api("/api/quality/sources"), api("/api/quality/profiles"),
    api(`/api/product-specifications?approved_only=${state.user?.role === "ADMIN" ? "false" : "true"}`), api("/api/evidence/issuers"),
  ]);
  if (state.user?.role === "ADMIN") {
    [state.sourceReviews, state.changeRecords] = await Promise.all([
      api("/api/quality/source-reviews"), api("/api/quality/change-records?limit=50"),
    ]);
    renderGovernance();
  }
  const applicable = state.productSpecifications.filter((item) => item.status === "APPROVED" && item.active);
  $("#specificationSelect").innerHTML = applicable.length
    ? applicable.map((item) => `<option value="${esc(item.specification_code)}">${esc(item.specification_name)} · v${esc(item.version)}</option>`).join("")
    : '<option value="">No approved specification</option>';
}

function miniRows(items, render, empty) {
  return items.length ? items.map(render).join("") : `<div class="empty-state">${empty}</div>`;
}

function renderGovernance() {
  $("#specificationRegistry").innerHTML = miniRows(state.productSpecifications, (item) => `<div class="mini-row"><div><strong>${esc(item.specification_name)}</strong><small>v${esc(item.version)} · ${esc(item.requirement_count)} requirements</small></div>${pill(item.status)}</div>`, "None.");
  $("#issuerRegistry").innerHTML = miniRows(state.evidenceIssuers, (item) => `<div class="mini-row"><div><strong>${esc(item.issuer_name)}</strong><small>${esc(label(item.issuer_type))}</small></div>${pill(item.trust_status)}</div>`, "None.");
  $("#sourceReviewRegistry").innerHTML = miniRows(state.sourceReviews, (item) => `<div class="mini-row"><div><strong>${esc(item.source_code)}</strong><small>Next review ${esc(item.next_review_due || "not set")}</small></div>${pill(item.review_status)}</div>`, "None.");
  $("#changeRegistry").innerHTML = miniRows(state.changeRecords, (item) => `<div class="mini-row"><div><strong>${esc(label(item.change_type))}</strong><small>${esc(item.target_code)} · ${esc(item.change_summary)}</small></div>${pill(item.status)}</div>`, "None.");
  const profile = state.qualityProfiles[0];
  $("#profileSummary").innerHTML = profile
    ? `<h2>${esc(profile.name)}</h2><small>v${esc(profile.version)} · ${esc(profile.requirement_count)} mapped checks · mappings explain evidence, not certification</small>`
    : "";
  $("#sourceRegistry").innerHTML = miniRows(state.qualitySources, (source) => `<div class="mini-row"><div><strong>${esc(source.title)}</strong><small>${esc(source.authority)} · ${esc(source.edition)} · <a href="${esc(source.source_url)}" target="_blank" rel="noopener noreferrer">official page ↗</a></small></div>${pill(source.status)}</div>`, "None.");
}

/* ---------- Records ---------- */
async function refreshRecords() {
  [state.materials, state.products] = await Promise.all([api("/api/raw-materials"), api("/api/products")]);
  renderMaterials();
  renderMaterialChoices();
  renderProductState();
  updateControls();
}

function renderMaterials() {
  const list = $("#materialList");
  if (!state.materials.length) {
    list.className = "record-list empty-state";
    list.textContent = state.user?.role === "RAW_MATERIAL_SUPPLIER" ? "No materials yet. Register one to begin." : "No raw materials yet.";
    return;
  }
  list.className = "record-list";
  list.innerHTML = state.materials.map((item) => {
    const status = isExpired(item.expiry_retest_date) ? "EXPIRED" : item.quality_status;
    return `<div class="record"><strong>${esc(item.material_name)}</strong>${pill(status)}
      <small>${esc(item.internal_batch_id)} · ${esc(item.supplier_name)} · ${esc(item.quantity)} ${esc(item.unit)}</small>
      <button class="btn btn-ghost btn-sm inspect-material" data-id="${esc(item.id)}" type="button">Checks</button></div>`;
  }).join("");
  $$(".inspect-material").forEach((button) => button.addEventListener("click", async () => {
    await selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", button.dataset.id);
    go("quality");
  }));
}

function renderMaterialChoices() {
  const approved = eligibleMaterials();
  $("#materialChoices").innerHTML = approved.length
    ? approved.map((item) => `<label><input type="checkbox" value="${esc(item.id)}" checked> ${esc(item.material_name)} · ${esc(item.internal_batch_id)}</label>`).join("")
    : "No approved materials yet. The supplier must approve one first.";
}

function renderProductState() {
  const product = currentProduct();
  const box = $("#productResult");
  if (!product) {
    box.className = "empty-state";
    box.textContent = state.user?.role === "MANUFACTURER"
      ? (eligibleMaterials().length ? "Ready to register the finished batch." : "Waiting for an approved raw material.")
      : "No finished batch yet.";
    $("#overviewProduct").textContent = "Aurelia Prestige Renewal Serum";
    return;
  }
  $("#verifyCode").value = product.product_code;
  const materials = product.linked_raw_materials || [];
  const spec = product.product_specification;
  box.className = "product-card";
  box.innerHTML = `<div class="title"><div><span class="eyebrow">${esc(product.brand || "Aurelia Maison")}</span><h3>${esc(product.name)}</h3></div>${pill(product.final_sale_status)}</div>
    <div class="kv">
      <div><small>Product code</small><span class="mono">${esc(product.product_code)}</span></div>
      <div><small>Batch</small><span>${esc(product.batch_number)}</span></div>
      <div><small>Held by</small><span>${esc(label(product.current_stage))}</span></div>
      <div><small>Expires</small><span>${esc(product.expiry_date || "—")} ${expiryBadge(product.expiry_date)}</span></div>
      <div><small>Specification</small><span>${spec ? `v${esc(spec.version)}` : "—"}</span></div>
      <div><small>Ingredients</small><span>${materials.length ? materials.map((item) => esc(item.internal_batch_id)).join(", ") : "—"}</span></div>
    </div>
    <div class="product-qr">
      <img src="/api/qr/${encodeURIComponent(product.product_code)}" alt="QR code for ${esc(product.product_code)}" width="88" height="88">
      <div><strong>Box QR code</strong><small>Customers scan this on the Verify page.</small>
        <div class="row-actions"><button class="btn btn-ghost btn-sm" type="button" data-cert="${esc(product.product_code)}">Certificate</button><a class="btn btn-ghost btn-sm" href="#verify/${encodeURIComponent(product.product_code)}">Verify</a></div></div>
    </div>`;
  box.querySelector("[data-cert]")?.addEventListener("click", (event) => openCertificate(event.currentTarget.dataset.cert));
  $("#overviewProduct").textContent = product.name;
}

$("#openMaterialForm").addEventListener("click", () => $("#materialDialog").showModal());
$("#openProductForm").addEventListener("click", () => { renderMaterialChoices(); $("#productDialog").showModal(); });
$$("dialog [data-close]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));

$("#materialForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#registerMaterialButton"), "Registering…", async () => {
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    ["expiry_retest_date", "country_source", "notes"].forEach((field) => { if (payload[field] === "") payload[field] = null; });
    payload.quantity = Number(payload.quantity);
    try {
      const created = await api("/api/raw-materials", json(payload));
      $("#materialDialog").close();
      await refreshRecords(); await refreshDashboard();
      await selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", created.id);
      showFeedback("Material registered", `${created.material_name} · now complete its 5 checks.`, "success");
      go("quality");
    } catch (error) { reportError(error, "Registration failed"); }
  });
});

$("#productForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#registerProductButton"), "Writing to blockchain…", async () => {
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    ["manufactured_date", "expiry_date"].forEach((field) => { if (payload[field] === "") payload[field] = null; });
    Object.assign(payload, {
      name: "Aurelia Prestige Renewal Serum", brand: "Aurelia Maison",
      description: "Luxury anti-aging facial serum demonstration batch",
      raw_material_batch_ids: $$("#materialChoices input:checked").map((input) => input.value),
    });
    if (!payload.raw_material_batch_ids.length) {
      showFeedback("Pick an approved material", "", "warning");
      return;
    }
    try {
      const created = await api("/api/products/register", json(payload));
      $("#productDialog").close();
      await refreshRecords(); await refreshDashboard();
      await selectQuality("MANUFACTURER", "PRODUCT", created.product_code);
      showFeedback("Batch registered on-chain", "Now complete the manufacturing checks.", "success");
      go("quality");
    } catch (error) { reportError(error, "Registration failed"); }
  });
});

/* ---------- Quality board ---------- */
// The server hides issuer-verification details of other stages' evidence from downstream roles.
// When that field is absent, the server's own gate already accepted the file, so treat it as accepted.
function issuerAccepted(item) {
  return item.verification_status === "VERIFIED_DEMO" || item.verification_status == null;
}
function validEvidence(check) {
  return (check.evidence || []).filter((item) => item.integrity === "VERIFIED"
    && (!check.trusted_issuer_required || issuerAccepted(item)));
}
function checkComplete(check) {
  return check.result === "PASS" && (!check.evidence_required || validEvidence(check).length > 0);
}

function renderEmptyBoard(message = "Pick a stage above to see its five checks.") {
  state.activeSummary = null;
  $("#qualityChecks").innerHTML = `<div class="empty-state board-empty">${esc(message)}</div>`;
  $("#qualityContext").textContent = "No batch selected.";
  $("#qualitySummary").innerHTML = '<span id="qualityContext" class="muted">No batch selected.</span>';
  $("#blockingPanel").className = "blockers muted";
  $("#blockingPanel").textContent = "Nothing to approve yet.";
  updateControls();
}

async function selectQuality(stage, type, id) {
  Object.assign(state, { activeStage: stage, contextType: type, contextId: id, activeSummary: null, boardEnter: true });
  $$(".stage-tabs button").forEach((button) => {
    const active = button.dataset.stage === stage;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  updateControls();
  await renderQuality();
}

function infoPopover(check) {
  const sources = (check.sources || []).map((source) => `<a href="${esc(source.source_url)}" target="_blank" rel="noopener noreferrer">${esc(source.source_code.replaceAll("_", " "))}</a>`).join(" · ");
  return `<details class="info"><summary aria-label="Why this check exists">i</summary><div class="info-pop">
    <span><strong>Why:</strong> ${esc(check.requirement_rationale)}</span>
    <span><strong>Evidence:</strong> ${esc(check.evidence_expectation)}</span>
    ${sources ? `<span><strong>Source:</strong> ${sources}</span>` : ""}
    <small>Explains why evidence is requested. Not a certification.</small></div></details>`;
}

function evidenceRow(check, writable) {
  const files = check.evidence || [];
  const chips = files.length
    ? files.slice(-2).map((item) => {
        const ok = item.integrity === "VERIFIED" && (!check.trusted_issuer_required || issuerAccepted(item));
        return `<span class="file-chip ${ok ? "ok" : "bad"}" title="${esc(item.original_filename)} · integrity ${esc(label(item.integrity))}${item.issuer ? ` · ${esc(item.issuer.issuer_name)}` : ""}">${ok ? "✓" : "!"} <span>${esc(item.original_filename)}</span></span>`;
      }).join("")
    : '<span class="file-chip bad">No file yet</span>';
  const upload = writable ? `<button class="btn btn-ghost btn-sm upload-evidence" type="button" data-standard="${check.standard_id}">${files.length ? "Add file" : "Upload"}</button>` : "";
  return `<div class="check-meta">${chips}${upload}</div>`;
}

function checkCard(check, writable) {
  const tone = check.result === "FAIL" ? "fail" : checkComplete(check) ? "pass" : "";
  const toggle = writable
    ? `<div class="result-toggle" role="group" aria-label="Result for ${esc(check.check_name)}">
        ${["PASS", "FAIL"].map((value) => `<button type="button" data-result="${value}" data-standard="${check.standard_id}" aria-pressed="${check.result === value}">${value === "PASS" ? "Pass" : "Fail"}</button>`).join("")}
      </div>
      <input class="note-input check-note" data-standard="${check.standard_id}" placeholder="Note (optional)" value="${esc(check.notes || "")}" aria-label="Note for ${esc(check.check_name)}">`
    : `${pill(check.result || "PENDING")}${check.notes ? `<small class="check-note-read" title="${esc(check.notes)}">${esc(check.notes)}</small>` : ""}`;
  return `<article class="glass check-card ${tone}" data-standard="${check.standard_id}">
    <div class="check-top"><div><h3>${esc(check.check_name)}</h3><p>${esc(check.requirement)}</p></div>${infoPopover(check)}</div>
    ${check.evidence_required ? evidenceRow(check, writable) : ""}
    <div class="check-actions">${toggle}</div>
  </article>`;
}

function renderSummaryBar(summary) {
  const pct = summary.required_total ? Math.round((summary.required_passed / summary.required_total) * 100) : 0;
  const context = state.contextType === "RAW_MATERIAL"
    ? state.materials.find((item) => item.id === state.contextId)
    : state.products.find((item) => item.product_code === state.contextId);
  const materialPicker = state.contextType === "RAW_MATERIAL" && state.materials.length > 1
    ? `<select id="materialPicker" aria-label="Material">${state.materials.map((item) => `<option value="${esc(item.id)}" ${item.id === state.contextId ? "selected" : ""}>${esc(item.material_name)} · ${esc(item.internal_batch_id)}</option>`).join("")}</select>`
    : `<span id="qualityContext" class="muted">${esc(context?.material_name || context?.name || state.contextId)} · ${esc(context?.internal_batch_id || context?.batch_number || "")}</span>`;
  $("#qualitySummary").innerHTML = `${materialPicker}
    <span class="ring ${summary.status === "APPROVED" ? "ok" : ""}" style="--p:${pct}"><span>${summary.required_passed}/${summary.required_total}</span></span>
    ${pill(stageStatus(summary))}`;
  countUp($("#qualitySummary .ring span"), summary.required_passed, `/${summary.required_total}`);
  $("#materialPicker")?.addEventListener("change", (event) => selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", event.target.value));
  const blockers = $("#blockingPanel");
  if (summary.status === "APPROVED") {
    blockers.className = "blockers ok"; blockers.textContent = "✓ Stage approved and sealed.";
  } else if (summary.blocking_reasons.length) {
    blockers.className = "blockers bad";
    blockers.innerHTML = `<details><summary>${summary.blocking_reasons.length} thing${summary.blocking_reasons.length === 1 ? "" : "s"} to fix · show</summary><ul>${summary.blocking_reasons.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></details>`;
  } else {
    blockers.className = "blockers ok"; blockers.textContent = "All five done. Ready to approve.";
  }
}

async function renderQuality() {
  if (!state.activeStage || !state.contextId) return renderEmptyBoard();
  const board = $("#qualityChecks");
  board.setAttribute("aria-busy", "true");
  if (state.boardEnter) board.innerHTML = skeletonBoard();
  try {
    const summary = await api(`/api/quality/${state.contextType}/${encodeURIComponent(state.contextId)}/summary?stage=${state.activeStage}`);
    state.activeSummary = summary;
    const writable = canWriteStage(state.activeStage);
    board.innerHTML = LANES.map((lane) => {
      const checks = summary.checks.filter((check) => check.category === lane.category);
      const done = checks.filter(checkComplete).length;
      return `<section class="lane ${lane.category === "Final review" ? "lane-final" : ""}">
        <div class="lane-head"><span class="kind ${lane.cls}">${esc(lane.label)}</span><small class="muted">${esc(lane.hint)}</small><span class="count">${done}/${checks.length}</span></div>
        ${checks.map((check) => checkCard(check, writable)).join("") || '<div class="empty-state">None.</div>'}
      </section>`;
    }).join("");
    board.classList.toggle("entering", state.boardEnter);
    state.boardEnter = false;
    if (state.changedStandard) {
      board.querySelector(`.check-card[data-standard="${state.changedStandard}"]`)?.classList.add("just-changed");
      state.changedStandard = null;
    }
    renderSummaryBar(summary);
    bindBoard();
    updateControls();
  } catch (error) {
    board.innerHTML = '<div class="empty-state board-empty">Checks could not be loaded.</div>';
    reportError(error, "Checks unavailable");
  } finally { board.removeAttribute("aria-busy"); }
}

function findCheck(standardId) {
  return state.activeSummary?.checks.find((check) => String(check.standard_id) === String(standardId));
}

function bindBoard() {
  $$("#qualityChecks .result-toggle button").forEach((button) => button.addEventListener("click", () => {
    const check = findCheck(button.dataset.standard);
    const next = check.result === button.dataset.result ? "PENDING" : button.dataset.result;
    const note = button.closest(".check-card").querySelector(".check-note")?.value || null;
    saveResult(check, next, note, button);
  }));
  $$("#qualityChecks .check-note").forEach((input) => input.addEventListener("change", () => {
    const check = findCheck(input.dataset.standard);
    saveResult(check, check.result || "PENDING", input.value || null, null);
  }));
  $$("#qualityChecks .upload-evidence").forEach((button) => button.addEventListener("click", () => openEvidence(findCheck(button.dataset.standard))));
  $$("#qualityChecks .info").forEach((details) => details.addEventListener("toggle", () => {
    if (details.open) $$("#qualityChecks .info").forEach((other) => { if (other !== details) other.open = false; });
  }));
}

async function postResult(check, result, notes) {
  return api("/api/quality/results", json({
    context_type: state.contextType, context_id: state.contextId,
    standard_id: check.standard_id, result, notes,
  }));
}

async function saveResult(check, result, notes, button) {
  const work = async () => {
    try {
      await postResult(check, result, notes);
      state.changedStandard = check.standard_id;
      if (result === "FAIL") showFeedback("Marked as failed", `${check.check_name} · the stage is now on hold.`, "warning");
      await refreshAfterChange();
    } catch (error) { reportError(error, "Couldn't save"); }
  };
  if (button) await withButton(button, "", work); else await work();
}

async function refreshAfterChange() {
  await refreshRecords(); await renderQuality(); await refreshDashboard();
}

function openEvidence(check) {
  state.evidenceCheck = check;
  $("#evidenceTitle").textContent = check.check_name;
  $("#evidenceHint").textContent = check.trusted_issuer_required
    ? `${label(check.expected_document_type)} from a trusted issuer, with its report number.`
    : `${label(check.expected_document_type)}. The file's fingerprint is recorded on-chain.`;
  const preset = check.expected_document_type === "CERTIFICATE_OF_ANALYSIS" ? "LUMINA_ACTIVES" : "AURELIA_QC_LAB_DEMO";
  $("#evidenceIssuer").innerHTML = state.evidenceIssuers.map((issuer) =>
    `<option value="${esc(issuer.issuer_code)}" ${issuer.issuer_code === preset ? "selected" : ""}>${esc(issuer.issuer_name)} · ${esc(label(issuer.trust_status))}</option>`).join("");
  $("#issuerField").classList.toggle("hidden", !check.trusted_issuer_required);
  $("#reportField").classList.toggle("hidden", !check.trusted_issuer_required);
  $("#evidenceReport").required = Boolean(check.trusted_issuer_required);
  $("#evidenceForm").reset();
  if (check.trusted_issuer_required) $("#evidenceIssuer").value = preset;
  $("#evidencePublic").checked = state.activeStage === "RETAILER";
  $("#evidenceDialog").showModal();
}

$("#evidenceForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const check = state.evidenceCheck;
  withButton($("#evidenceSubmit"), "Uploading…", async () => {
    try {
      let resultId = check.result_id;
      if (!resultId) resultId = (await postResult(check, check.result || "PENDING", check.notes || null)).id;
      const data = new FormData();
      data.append("file", $("#evidenceFile").files[0]);
      data.append("visibility", $("#evidencePublic").checked ? "CONSUMER_VISIBLE" : "INTERNAL");
      data.append("document_type", check.expected_document_type || "OTHER");
      if (check.trusted_issuer_required) {
        data.append("issuer_code", $("#evidenceIssuer").value);
        data.append("issuer_report_number", $("#evidenceReport").value.trim());
      }
      if ($("#evidenceDate").value) data.append("issuer_document_date", $("#evidenceDate").value);
      await api(`/api/quality/results/${resultId}/evidence`, { method: "POST", body: data });
      $("#evidenceDialog").close();
      showFeedback("File uploaded", "Fingerprint recorded. Mark the check as Pass when you're satisfied.", "success");
      await refreshAfterChange();
    } catch (error) { reportError(error, "Upload failed"); }
  });
});

$("#approveStage").addEventListener("click", (event) => withButton(event.currentTarget, "Sealing…", async () => {
  try {
    await api("/api/quality/stages/approve", json({ context_type: state.contextType, context_id: state.contextId, stage: state.activeStage }));
    showFeedback(`${STAGE_NAMES[state.activeStage]} approved`, state.activeStage === "RETAILER" ? "Approved for sale and sealed on the blockchain." : "Sealed on the blockchain.", "success");
    celebrate($("#approveStage"), state.activeStage === "RETAILER" ? 140 : 70);
  } catch (error) { reportError(error, "Can't approve yet"); }
  await refreshAfterChange();
}));

$$(".stage-tabs button").forEach((button) => button.addEventListener("click", async () => {
  const stage = button.dataset.stage;
  if (stage === "RAW_MATERIAL_SUPPLIER") {
    if (!state.materials.length) return showFeedback("No raw material yet", "Register one under Batches.", "warning");
    await selectQuality(stage, "RAW_MATERIAL", state.materials[0].id);
  } else {
    const product = currentProduct();
    if (!product) return showFeedback("No finished batch yet", "The manufacturer registers it under Batches.", "warning");
    await selectQuality(stage, "PRODUCT", product.product_code);
  }
}));

async function transfer(role, button) {
  const product = currentProduct();
  if (!product) return;
  await withButton(button, "Recording on-chain…", async () => {
    try {
      await api("/api/ownership-transfers", json({ product_code: product.product_code, to_role: role }));
      showFeedback(`Sent to ${label(role)}`, "Custody change recorded on the blockchain.", "success");
      await refreshHealth(); await refreshRecords(); await refreshDashboard();
      await selectQuality(role, "PRODUCT", product.product_code);
    } catch (error) { reportError(error, "Transfer blocked"); }
  });
}
$("#transferDistributor").addEventListener("click", (event) => transfer("DISTRIBUTOR", event.currentTarget));
$("#transferRetailer").addEventListener("click", (event) => transfer("RETAILER", event.currentTarget));

function updateControls() {
  const product = currentProduct();
  const role = state.user?.role;
  $("#openProductForm").classList.toggle("hidden", role !== "MANUFACTURER" || Boolean(product));
  $("#openProductForm").disabled = !eligibleMaterials().length;
  $("#registerProductButton").disabled = role !== "MANUFACTURER" || Boolean(product) || !eligibleMaterials().length;
  $("#registerMaterialButton").disabled = role !== "RAW_MATERIAL_SUPPLIER";
  const approvedStages = new Set(state.journey.filter((item) => item.status === "APPROVED").map((item) => item.stage));
  $$(".stage-tabs button").forEach((button) => {
    button.hidden = !canViewStage(button.dataset.stage);
    button.disabled = button.dataset.stage === "RAW_MATERIAL_SUPPLIER" ? !state.materials.length : !product;
    button.classList.toggle("done", approvedStages.has(button.dataset.stage) && !button.classList.contains("active"));
  });
  const autoFill = $("#demoAutofillButton");
  autoFill.disabled = !state.demoMode || !OPERATIONAL_ROLES.includes(role);
  autoFill.textContent = role === "RETAILER" && product?.final_sale_status === "HOLD" ? "Fix the HOLD (auto-fill)" : "Auto-fill my checks";
  $("#demoHoldButton").disabled = !state.demoMode || role !== "RETAILER" || product?.current_stage !== "RETAILER";
  const complete = product?.final_sale_status === "APPROVED_FOR_SALE";
  $("#loadPresentationButton").disabled = role !== "ADMIN" || complete;
  $("#loadPresentationButton").textContent = complete ? "Full demo loaded ✓" : product ? "Finish the demo" : "Load full demo";
  $("#tamperButton").disabled = role !== "ADMIN" || !product || state.verification?.status === "SUSPICIOUS";
  const summary = state.activeSummary;
  const approve = $("#approveStage");
  approve.hidden = !state.activeStage || !canWriteStage(state.activeStage);
  approve.disabled = !summary || summary.status === "APPROVED" || !summary.eligible_for_approval;
  approve.textContent = summary?.status === "APPROVED" ? "Approved ✓" : `Approve ${STAGE_NAMES[state.activeStage] || "stage"}`;
  const toDistributor = $("#transferDistributor");
  toDistributor.hidden = role !== "MANUFACTURER";
  toDistributor.disabled = !(summary && state.activeStage === "MANUFACTURER" && summary.status === "APPROVED" && product?.current_stage === "MANUFACTURER");
  const toRetailer = $("#transferRetailer");
  toRetailer.hidden = role !== "DISTRIBUTOR";
  toRetailer.disabled = !(summary && state.activeStage === "DISTRIBUTOR" && summary.status === "APPROVED" && product?.current_stage === "DISTRIBUTOR");
}

/* ---------- Overview ---------- */
async function operationalJourney(product) {
  const linked = product?.linked_raw_materials || [];
  const pool = linked.length ? linked : state.materials;
  const rawApproved = pool.length > 0 && pool.every((item) => item.quality_status === "APPROVED" && !isExpired(item.expiry_retest_date));
  const journey = [{
    stage: "RAW_MATERIAL_SUPPLIER", display_name: "Raw Materials", status: rawApproved ? "APPROVED" : "PENDING",
    required_passed: rawApproved ? 5 : 0, required_total: 5,
  }];
  const rawSource = linked[0]?.id || state.materials[0]?.id;
  if (rawSource && canViewStage("RAW_MATERIAL_SUPPLIER")) {
    try {
      const raw = await api(`/api/quality/RAW_MATERIAL/${encodeURIComponent(rawSource)}/summary?stage=RAW_MATERIAL_SUPPLIER`);
      Object.assign(journey[0], { status: rawApproved ? "APPROVED" : raw.status, eligible_for_approval: raw.eligible_for_approval, required_passed: raw.required_passed, required_total: raw.required_total, checks: raw.checks });
    } catch (_) { /* permission or not found: keep the estimate */ }
  }
  if (!product) {
    return [...journey, ...STAGES.slice(1).map((stage) => ({ stage, display_name: STAGE_NAMES[stage], status: "PENDING", required_passed: 0, required_total: 5, blocking_reasons: [] }))];
  }
  const summaries = await Promise.all(STAGES.slice(1).map((stage) =>
    api(`/api/quality/PRODUCT/${encodeURIComponent(product.product_code)}/summary?stage=${stage}`)));
  return [...journey, ...summaries];
}

function currentStageOf(product, journey) {
  if (product?.final_sale_status === "APPROVED_FOR_SALE") return "COMPLETE";
  if (product) return product.current_stage;
  return journey[0].status === "APPROVED" ? "MANUFACTURER" : "RAW_MATERIAL_SUPPLIER";
}

function nextStepText(current, journey) {
  if (current === "COMPLETE") return "Ready for customers to verify";
  if (current === "RAW_MATERIAL_SUPPLIER") return state.materials.length ? "Supplier completes 5 checks" : "Supplier registers a raw material";
  if (current === "MANUFACTURER") return !currentProduct() ? "Manufacturer registers the batch" : journey[1].status === "APPROVED" ? "Send to the distributor" : "Manufacturer completes 5 checks";
  if (current === "DISTRIBUTOR") return journey[2].status === "APPROVED" ? "Send to the retailer" : "Distributor completes 5 checks";
  return journey[3].status === "HOLD" ? "Retailer fixes the failed check" : "Retailer completes 5 checks";
}

async function refreshDashboard() {
  if (!state.user) return;
  const product = currentProduct();
  try {
    const journey = await operationalJourney(product);
    state.journey = journey;
    const current = currentStageOf(product, journey);
    $("#journey").innerHTML = journey.map((item, index) => {
      const isCurrent = current === item.stage;
      const status = item.status === "PENDING" && !item.eligible_for_approval && !isCurrent && index > STAGES.indexOf(current) && current !== "COMPLETE" ? "NOT_STARTED" : stageStatus(item);
      const pct = item.required_total ? Math.round((item.required_passed / item.required_total) * 100) : 0;
      return `<li class="${String(item.status).toLowerCase()} ${isCurrent ? "current" : ""}">
        <div class="step-head"><span class="step-num">${item.status === "APPROVED" ? "✓" : index + 1}</span><h3>${esc(STAGE_NAMES[item.stage])}</h3></div>
        ${pill(status)}
        <div class="step-meta"><small>${item.required_passed} of ${item.required_total || 5} checks done</small>
        ${item.commitment_hash && item.status === "APPROVED" ? `<small class="sealed" title="Stage seal (commitment hash)"><b>Seal</b> <span class="mono">${esc(short(item.commitment_hash))}</span></small>` : ""}</div>
        ${(item.checks || []).length ? `<ul class="step-checks">${item.checks.map((check) => `<li class="${checkComplete(check) ? "ok" : check.result === "FAIL" ? "bad" : ""}"><b>${checkComplete(check) ? "✓" : check.result === "FAIL" ? "×" : "○"}</b>${esc(check.check_name)}</li>`).join("")}</ul>` : ""}
        <div class="progress"><span style="width:${pct}%"></span></div></li>`;
    }).join("");
    renderChainTimeline(product, journey);
    renderStats(product, journey);
    $("#overviewBatch").textContent = product ? `${product.batch_number} · ${product.product_code}` : "No batch registered yet";
    $("#overviewStage").textContent = current === "COMPLETE" ? "On the shelf" : STAGE_NAMES[current];
    $("#overviewNext").textContent = nextStepText(current, journey);
    const sale = product?.final_sale_status || "NOT_READY";
    $("#overviewSale").outerHTML = pill(sale, label(sale), "pill-lg").replace("<span", '<span id="overviewSale"');
    updateControls();
  } catch (error) { reportError(error, "Overview couldn't refresh"); }
}

function renderStats(product, journey) {
  const passed = journey.reduce((sum, item) => sum + (item.required_passed || 0), 0);
  const total = journey.reduce((sum, item) => sum + (item.required_total || 5), 0);
  const certificates = journey.slice(1).flatMap((item) => item.checks || [])
    .filter((check) => check.evidence_required).reduce((sum, check) => sum + validEvidence(check).length, 0);
  const days = product?.expiry_date ? Math.ceil((new Date(`${product.expiry_date}T00:00:00`) - new Date()) / 864e5) : null;
  const tiles = [
    { value: passed, suffix: ` / ${total}`, label: "Checks passed" },
    { value: certificates, suffix: " sealed", label: "Certificates" },
    { value: days ?? 0, suffix: days === null ? "" : " days", label: "Shelf life left", empty: days === null },
    { text: product ? label(product.current_stage === "RETAILER" && product.final_sale_status === "APPROVED_FOR_SALE" ? "RETAILER" : product.current_stage) : "—", label: "Held by" },
  ];
  $("#overviewStats").innerHTML = tiles.map((tile, index) => `<div class="stat glass" style="animation-delay:${index * 60}ms"><strong data-count="${tile.text ? "" : tile.value}" data-suffix="${esc(tile.suffix || "")}">${tile.text ? esc(tile.text) : tile.empty ? "—" : `${tile.value}${esc(tile.suffix)}`}</strong><span>${esc(tile.label)}</span></div>`).join("");
  $$("#overviewStats [data-count]").forEach((element) => { if (element.dataset.count !== "") countUp(element, Number(element.dataset.count), element.dataset.suffix); });
}

function renderChainTimeline(product, journey) {
  const events = [];
  if (product?.registration_tx_hash) {
    events.push({ title: "Batch registered", detail: `Block ${product.registration_block_number} · tx ${short(product.registration_tx_hash)}` });
  }
  journey.slice(1).filter((item) => item.status === "APPROVED" && item.commitment_hash).forEach((item) => {
    events.push({ title: `${STAGE_NAMES[item.stage]} sealed`, detail: `${String(item.approved_at || "").slice(0, 16)} · ${short(item.commitment_hash)}` });
  });
  if (product?.final_sale_status === "APPROVED_FOR_SALE") events.push({ title: "Approved for sale", detail: "Verifiable by customers", final: true });
  $("#chainTimeline").innerHTML = events.length
    ? events.map((item) => `<li class="${item.final ? "final" : ""}"><strong>${esc(item.title)}</strong><small class="mono">${esc(item.detail)}</small></li>`).join("")
    : '<li class="muted">Nothing sealed yet. The manufacturer\'s registration is the first entry.</li>';
}

$("#overviewGo").addEventListener("click", async () => {
  const role = state.user?.role;
  const product = currentProduct();
  const stage = ROLE_STAGE[role] || (product && STAGES.includes(product.current_stage) ? product.current_stage : null);
  if (stage === "RAW_MATERIAL_SUPPLIER" && state.materials.length) await selectQuality(stage, "RAW_MATERIAL", state.contextType === "RAW_MATERIAL" ? state.contextId : state.materials[0].id);
  else if (stage && product) await selectQuality(stage, "PRODUCT", product.product_code);
  else if (role === "MANUFACTURER" && !product) { go("batches"); return; }
  go("quality");
});

$("#refreshDashboard").addEventListener("click", (event) => withButton(event.currentTarget, "", async () => {
  await refreshHealth(); await refreshRecords(); await refreshDashboard();
}));

/* ---------- Verify ---------- */
async function verify(code = $("#verifyCode").value.trim(), announce = false) {
  const result = await api(`/api/verify/${encodeURIComponent(code)}`);
  state.verification = result;
  const card = $("#consumerResult");
  if (result.status === "NOT_FOUND") {
    card.innerHTML = `<div class="verdict bad"><div class="seal-mark bad">?</div><div><h2>Not found</h2><p class="muted">${esc(result.message)}</p></div></div>`;
    if (announce) showFeedback("Product not found", "Check the code and try again.", "warning");
    updateControls();
    return result;
  }
  const authentic = result.status === "GENUINE";
  const p = result.product;
  card.innerHTML = `<div class="verdict ${authentic ? "ok" : "bad"}"><div class="seal-mark ${authentic ? "ok" : "bad"}">${authentic ? "✓" : "!"}</div>
      <div><h2>${authentic ? "Authentic" : "Suspicious"}</h2><p class="muted">${authentic ? "Matches the blockchain record." : "Records no longer match the blockchain fingerprint."}</p></div></div>
    ${authentic ? "" : '<div class="alert">Blockchain hash mismatch: product details were changed after registration.</div>'}
    <div class="kv">
      <div><small>Product</small><span>${esc(p.name)}</span></div>
      <div><small>Brand</small><span>${esc(p.brand)}</span></div>
      <div><small>Batch</small><span>${esc(p.batch_number)}</span></div>
      <div><small>Sale status</small><span>${pill(result.final_sale_status)}</span></div>
    </div>
    <div><span class="field-label">Quality journey</span><div class="mini-journey">${result.quality_journey.map((item) => `<div class="${item.status === "APPROVED" ? "ok" : ["HOLD", "REJECTED"].includes(item.status) ? "bad" : ""}">${esc(STAGE_NAMES[item.stage] || item.display_name)}<br><b>${esc(label(item.status))}</b></div>`).join("")}</div></div>
    <div><span class="field-label">Custody chain</span><div class="provenance">${result.ownership_history.map((item) => `<b>${esc(label(item.role))}</b>`).join(" → ")}</div></div>
    ${authentic ? `<div class="row-actions"><button class="btn btn-gold btn-sm" type="button" id="verifyCertificate">View certificate</button></div>` : ""}
    <div><span class="field-label">Public documents</span>${result.public_evidence.length ? `<div class="check-meta">${result.public_evidence.map((item) => `<span class="file-chip ${item.integrity === "VERIFIED" ? "ok" : "bad"}" title="${esc(item.check_name)}">${item.integrity === "VERIFIED" ? "✓" : "!"} <span>${esc(item.check_name)}</span></span>`).join("")}</div>` : '<small class="muted">None shared.</small>'}</div>`;
  $("#verifyCertificate")?.addEventListener("click", () => openCertificate(result.product_code));
  if (announce) showFeedback(authentic ? "Authentic" : "Suspicious product", authentic ? label(result.final_sale_status) : "The record was changed after it was sealed.", authentic ? "success" : "error");
  updateControls();
  return result;
}

function runVerify(announce = true) {
  return withButton($("#verifyForm .btn-primary"), "Checking…", async () => {
    $("#consumerResult").innerHTML = skeletonVerify();
    try {
      const result = await verify(undefined, announce);
      if (announce && result.status === "GENUINE") celebrate($("#consumerResult .seal-mark"), 90);
    } catch (error) { reportError(error, "Verification failed"); }
  });
}
$("#verifyForm").addEventListener("submit", (event) => { event.preventDefault(); runVerify(true); });

/* ---------- Admin ---------- */
async function refreshAudit() {
  if (state.user?.role !== "ADMIN") return;
  const list = $("#auditList");
  try {
    const events = await api("/api/audit?limit=75");
    list.innerHTML = events.length ? events.map((item) => `<div class="audit-row">
      <time>${esc(String(item.created_at).replace("T", " ").slice(0, 19))}</time>
      <div><strong>${esc(label(item.action))}</strong><br><small>${esc(item.entity_id || item.entity_type)}</small></div>
      <div>${esc(item.display_name || item.username || "System")}<br><small>${esc(label(item.actor_role))}</small></div>
      ${pill(item.result)}</div>`).join("") : '<div class="empty-state">No activity yet.</div>';
  } catch (error) {
    list.textContent = "Activity could not be loaded.";
    reportError(error, "Activity unavailable");
  }
}
$("#refreshAudit").addEventListener("click", (event) => withButton(event.currentTarget, "", refreshAudit));

$$("[data-admin-tab]").forEach((tab) => tab.addEventListener("click", () => {
  $$("[data-admin-tab]").forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
  $$("[data-admin-panel]").forEach((panel) => { panel.hidden = panel.dataset.adminPanel !== tab.dataset.adminTab; });
}));

/* ---------- Floating demo menu ---------- */
function applyFabVisibility() {
  const role = state.user?.role;
  $("#fab").classList.toggle("hidden", !state.demoMode);
  $("#fabStage").classList.toggle("hidden", !OPERATIONAL_ROLES.includes(role));
  $("#demoHoldButton").classList.toggle("hidden", role !== "RETAILER");
  $("#fabAdmin").classList.toggle("hidden", role !== "ADMIN");
  $$("[data-quick-role]").forEach((button) => button.classList.toggle("current", state.user?.username === button.dataset.quickRole));
}

function setFab(open) {
  $("#fabMenu").hidden = !open;
  $("#fabButton").setAttribute("aria-expanded", String(open));
}
$("#fabButton").addEventListener("click", () => setFab($("#fabMenu").hidden));
document.addEventListener("click", (event) => {
  if (!$("#fab").contains(event.target)) setFab(false);
  if (!event.target.closest(".info")) $$("#qualityChecks .info[open]").forEach((item) => { item.open = false; });
});
document.addEventListener("keydown", (event) => { if (event.key === "Escape") setFab(false); });
$$(".fab-item").forEach((item) => item.addEventListener("click", () => setFab(false)));

$$("[data-quick-role]").forEach((button) => button.addEventListener("click", async () => {
  const username = button.dataset.quickRole;
  setFab(false);
  if (state.user?.username === username) return;
  try {
    if (state.user) showLoggedOut();
    const user = await signIn(username, DEMO_PASSWORD);
    showFeedback(`Now signed in as ${ROLE_NAMES[user.role]}`, user.display_name, "success");
    go(user.role === "ADMIN" ? "overview" : "quality");
  } catch (error) { reportError(error, "Switch failed"); }
}));

function openConfirm(dialog) {
  dialog.returnValue = "";
  dialog.showModal();
}

function requestDemoAction(action) {
  state.demoAction = action;
  const hold = action === "hold";
  $("#demoActionTitle").textContent = hold ? "Create a HOLD case?" : "Auto-fill your checks?";
  $("#demoActionCopy").textContent = hold
    ? "Fails the seal check through the normal workflow, so the product goes on HOLD until fixed."
    : "Fills your five checks with fictional passing results and files, then approves. Transfers stay manual.";
  $("#confirmDemoAction").textContent = hold ? "Create HOLD" : "Auto-fill";
  openConfirm($("#demoActionDialog"));
}
$("#demoAutofillButton").addEventListener("click", () => requestDemoAction("auto-fill"));
$("#demoHoldButton").addEventListener("click", () => requestDemoAction("hold"));
$("#demoActionDialog").addEventListener("close", () => {
  const action = state.demoAction;
  state.demoAction = null;
  if ($("#demoActionDialog").returnValue === "confirm" && action) runDemoAction(action);
});

async function runDemoAction(action) {
  const hold = action === "hold";
  const button = hold ? $("#demoHoldButton") : $("#demoAutofillButton");
  await withButton(button, hold ? "Creating HOLD…" : "Filling checks…", async () => {
    try {
      const result = await api(hold ? "/api/demo/retailer-hold" : "/api/demo/auto-fill", { method: "POST" });
      await refreshHealth();
      await Promise.all([refreshRecords(), refreshQualityReferences()]);
      await refreshDashboard();
      if (result.context_type === "RAW_MATERIAL") await selectQuality(result.stage, "RAW_MATERIAL", result.context_id);
      else { $("#verifyCode").value = result.product_code; await selectQuality(result.stage, "PRODUCT", result.product_code); }
      showFeedback(hold ? "HOLD created" : result.corrected_hold ? "HOLD fixed" : "Stage complete", result.next_action || result.message, hold ? "warning" : "success");
      go("quality");
    } catch (error) { reportError(error, hold ? "HOLD failed" : "Auto-fill failed"); }
  });
}

$("#tamperButton").addEventListener("click", () => openConfirm($("#tamperDialog")));
$("#tamperDialog").addEventListener("close", () => { if ($("#tamperDialog").returnValue === "confirm") runTamper(); });
async function runTamper() {
  await withButton($("#tamperButton"), "Tampering…", async () => {
    try {
      await api(`/api/demo/tamper/${encodeURIComponent(currentProduct()?.product_code || $("#verifyCode").value.trim())}`, { method: "POST" });
      await refreshRecords();
      go("verify");
      await verify(undefined, false);
      await refreshAudit();
      showFeedback("Data tampered", "Verification now shows Suspicious.", "warning");
    } catch (error) { reportError(error, "Tamper failed"); }
  });
}

$("#readinessButton").addEventListener("click", (event) => withButton(event.currentTarget, "Checking…", async () => {
  const panel = $("#readinessResult");
  try {
    const result = await api("/api/demo/readiness");
    const failed = result.checks.filter((item) => !item.ok);
    panel.className = "readiness";
    panel.innerHTML = `${pill(result.ready ? "READY" : "FAILED", result.ready ? "Demo ready" : "Not ready")}<span class="muted">${result.checks.length - failed.length}/${result.checks.length} checks passed</span>`;
    showFeedback(result.ready ? "Demo is ready" : "Demo is not ready", result.ready ? "Every prerequisite passed." : "", result.ready ? "success" : "error", failed.map((item) => `${item.name}: ${item.detail}`));
    go("admin");
  } catch (error) { reportError(error, "Readiness check failed"); }
}));

$("#loadPresentationButton").addEventListener("click", (event) => withButton(event.currentTarget, "Building demo…", async () => {
  try {
    const result = await api("/api/demo/presentation-seed", { method: "POST" });
    await refreshHealth();
    await Promise.all([refreshRecords(), refreshQualityReferences()]);
    await refreshDashboard();
    await selectQuality("RETAILER", "PRODUCT", result.product_code);
    await verify(result.product_code, false);
    showFeedback("Full demo loaded", "All four stages approved and on sale.", "success");
    go("overview");
  } catch (error) { reportError(error, "Demo couldn't load"); }
}));

$("#resetButton").addEventListener("click", () => openConfirm($("#resetDialog")));
$("#resetDialog").addEventListener("close", () => { if ($("#resetDialog").returnValue === "confirm") runReset(); });
async function runReset() {
  await withButton($("#resetButton"), "Clearing…", async () => {
    try {
      const result = await api("/api/demo/reset", { method: "POST" });
      Object.assign(state, { materials: [], products: [], verification: null, activeStage: null, contextType: null, contextId: null, activeSummary: null });
      renderMaterials(); renderMaterialChoices(); renderProductState(); renderEmptyBoard();
      $("#consumerResult").innerHTML = '<div class="seal-mark" aria-hidden="true">OC</div><p class="muted">Results appear here.</p>';
      await refreshDashboard(); await refreshAudit();
      showFeedback("Fresh demo ready", "Batches and files cleared. For a fully clean chain, restart Hardhat and redeploy.", "warning");
      go("overview");
    } catch (error) { reportError(error, "Reset failed"); }
  });
}

/* ---------- Notice, theme, about ---------- */
$("#noticeClose").addEventListener("click", () => { clearTimeout(showFeedback.timer); $("#notice").classList.add("hidden"); });

$("#themeToggle").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("originchain_theme", next); } catch (_) { /* private mode */ }
});

function selectAboutTab(tab) {
  $$(".about-tabs [role=tab]").forEach((item) => {
    const active = item === tab;
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
    $(`#${item.getAttribute("aria-controls")}`).hidden = !active;
  });
}
function renderAboutStats() {
  const health = state.health;
  $("#aboutChain").textContent = health?.blockchain_connected ? "Online" : "Offline";
  $("#aboutChain").className = health?.blockchain_connected ? "online" : "offline";
  $("#aboutBlock").textContent = health?.blockchain_connected ? `#${health.current_block}` : "—";
}
$("#aboutButton").addEventListener("click", () => {
  renderAboutStats();
  $("#aboutDialog").showModal();
  refreshHealth().then(renderAboutStats);
});
$("#aboutClose").addEventListener("click", () => $("#aboutDialog").close());
$$("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));
$$(".about-tabs [role=tab]").forEach((tab, index, tabs) => {
  tab.addEventListener("click", () => selectAboutTab(tab));
  tab.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const next = tabs[(index + step + tabs.length) % tabs.length];
    selectAboutTab(next); next.focus();
  });
});

/* ---------- Visual helpers ---------- */
function bottleSVG(id) {
  return `<svg class="bottle" viewBox="0 0 120 260" role="img" aria-label="Aurelia Prestige Renewal Serum">
    <defs>
      <linearGradient id="${id}-gold" x1="0" x2="1"><stop offset="0" stop-color="#8f6d3a"/><stop offset=".42" stop-color="#ead39f"/><stop offset=".58" stop-color="#d4b783"/><stop offset="1" stop-color="#8a6833"/></linearGradient>
      <linearGradient id="${id}-liquid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f0d6a3"/><stop offset="1" stop-color="#b9813f"/></linearGradient>
      <linearGradient id="${id}-glass" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".5"/><stop offset=".5" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#fff" stop-opacity=".3"/></linearGradient>
      <clipPath id="${id}-body"><rect x="22" y="96" width="76" height="150" rx="16"/></clipPath>
    </defs>
    <ellipse cx="60" cy="252" rx="42" ry="4.5" fill="#000" opacity=".1" class="bottle-shadow"/>
    <rect x="46" y="4" width="28" height="46" rx="14" fill="#3a0e1a"/>
    <rect x="50" y="10" width="5" height="30" rx="2.5" fill="#fff" opacity=".12"/>
    <rect x="40" y="46" width="40" height="12" rx="3" fill="url(#${id}-gold)"/>
    <rect x="44" y="58" width="32" height="30" rx="3" fill="url(#${id}-gold)"/>
    <rect x="40" y="85" width="40" height="11" rx="3" fill="url(#${id}-gold)"/>
    <rect x="22" y="96" width="76" height="150" rx="16" fill="#fff" fill-opacity=".16" stroke="url(#${id}-gold)" stroke-width="1.2"/>
    <g clip-path="url(#${id}-body)">
      <rect class="liquid" x="22" y="118" width="76" height="132" fill="url(#${id}-liquid)" opacity=".88"/>
      <rect class="glint" x="-30" y="96" width="18" height="150" fill="#fff" opacity=".35" transform="skewX(-12)"/>
    </g>
    <rect x="30" y="146" width="60" height="66" rx="3" fill="#fbf7ef"/>
    <line x1="36" x2="84" y1="155" y2="155" stroke="url(#${id}-gold)" stroke-width=".8"/>
    <text x="60" y="176" text-anchor="middle" font-family="Cormorant Garamond, Georgia, serif" font-size="12" letter-spacing="1.8" fill="#1a1614">AURELIA</text>
    <text x="60" y="189" text-anchor="middle" font-family="Inter, sans-serif" font-size="5.2" letter-spacing="1.6" fill="#8f6d3a">PRESTIGE RENEWAL</text>
    <text x="60" y="198" text-anchor="middle" font-family="Inter, sans-serif" font-size="4.6" letter-spacing="1" fill="#74695e">SERUM · 30 ML</text>
    <line x1="36" x2="84" y1="204" y2="204" stroke="url(#${id}-gold)" stroke-width=".8"/>
    <rect x="29" y="104" width="6" height="134" rx="3" fill="url(#${id}-glass)"/>
  </svg>`;
}
function renderBottles() {
  $$("[data-bottle]").forEach((slot, index) => { slot.innerHTML = bottleSVG(`bottle${index}`); });
}

function skeletonBoard() {
  return LANES.map((lane, index) => `<section class="lane"><div class="lane-head"><span class="kind ${lane.cls}">${esc(lane.label)}</span></div>${Array.from({ length: index === 2 ? 1 : 2 }, () => '<div class="check-card skeleton"><i></i><i></i><i class="short"></i></div>').join("")}</section>`).join("");
}
function skeletonVerify() {
  return '<div class="verdict"><div class="seal-mark skeleton-dot"></div><div class="skeleton-lines"><i></i><i class="short"></i></div></div><div class="skeleton-block"></div><div class="skeleton-block short"></div>';
}

function countUp(element, to, suffix = "") {
  if (!element || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / 900);
    element.textContent = `${Math.round(to * (1 - Math.pow(1 - t, 3)))}${suffix}`;
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function expiryBadge(dateValue) {
  if (!dateValue) return "";
  const days = Math.ceil((new Date(`${dateValue}T00:00:00`) - new Date()) / 864e5);
  const tone = days < 0 ? "bad" : days < 90 ? "" : "ok";
  return `<span class="pill ${tone} pill-xs">${days < 0 ? "Expired" : `${days.toLocaleString()} days left`}</span>`;
}

/* Gold-dust celebration */
function celebrate(origin, count = 80) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const canvas = $("#celebration");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const rect = origin?.getBoundingClientRect?.() || { left: innerWidth / 2, top: innerHeight / 2, width: 0, height: 0 };
  const ox = rect.left + rect.width / 2, oy = rect.top + rect.height / 2;
  const golds = ["#b08d57", "#d4b783", "#ead39f", "#8f6d3a", "#fff3d6"];
  const parts = Array.from({ length: count }, () => {
    const angle = Math.random() * Math.PI * 2, speed = 3 + Math.random() * 7;
    return { x: ox, y: oy, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed - 4, size: 2 + Math.random() * 4,
      rot: Math.random() * Math.PI, vr: (Math.random() - .5) * .3, life: 1, color: golds[Math.floor(Math.random() * golds.length)], diamond: Math.random() > .5 };
  });
  canvas.classList.add("on");
  const tick = () => {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    let alive = 0;
    parts.forEach((p) => {
      if (p.life <= 0) return;
      alive += 1;
      p.vy += .22; p.vx *= .985; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life -= .012;
      ctx.save(); ctx.globalAlpha = Math.max(0, p.life); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.color;
      if (p.diamond) { ctx.beginPath(); ctx.moveTo(0, -p.size); ctx.lineTo(p.size * .6, 0); ctx.lineTo(0, p.size); ctx.lineTo(-p.size * .6, 0); ctx.fill(); }
      else { ctx.beginPath(); ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2); ctx.fill(); }
      ctx.restore();
    });
    if (alive) requestAnimationFrame(tick); else { ctx.clearRect(0, 0, innerWidth, innerHeight); canvas.classList.remove("on"); }
  };
  requestAnimationFrame(tick);
}

/* ---------- Certificate of authenticity ---------- */
async function openCertificate(code) {
  try {
    const result = await api(`/api/verify/${encodeURIComponent(code)}`);
    if (result.status !== "GENUINE") {
      showFeedback("No certificate", result.status === "SUSPICIOUS" ? "This product failed verification." : "Product not found.", "warning");
      return;
    }
    const p = result.product, chain = result.blockchain;
    const issued = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
    $("#certificate").innerHTML = `
      <div class="cert-border">
        <header class="cert-head">
          <img src="/static/logo-mark.svg" alt="" width="44" height="44">
          <span class="eyebrow">OriginChain</span>
          <h1>Certificate of Authenticity</h1>
          <p class="muted">This product's record matches its fingerprint on the blockchain.</p>
        </header>
        <div class="cert-main">
          <div class="cert-bottle">${bottleSVG("cert")}</div>
          <dl class="cert-facts">
            <div><dt>Product</dt><dd>${esc(p.name)}</dd></div>
            <div><dt>House</dt><dd>${esc(p.brand)}</dd></div>
            <div><dt>Batch</dt><dd>${esc(p.batch_number)}</dd></div>
            <div><dt>Product code</dt><dd class="mono">${esc(p.product_code)}</dd></div>
            <div><dt>Made</dt><dd>${esc(p.manufactured_date || "—")}</dd></div>
            <div><dt>Best before</dt><dd>${esc(p.expiry_date || "—")}</dd></div>
            <div><dt>Sale status</dt><dd>${esc(label(result.final_sale_status))}</dd></div>
            <div><dt>Custody</dt><dd>${result.ownership_history.map((item) => esc(label(item.role))).join(" → ")}</dd></div>
          </dl>
          <div class="cert-qr"><img src="/api/qr/${encodeURIComponent(p.product_code)}" alt="QR code" width="120" height="120"><small>Scan to verify</small></div>
        </div>
        <ol class="cert-stages">${result.quality_journey.map((item) => `<li class="${item.status === "APPROVED" ? "ok" : ""}"><b>${item.status === "APPROVED" ? "✓" : "·"}</b><strong>${esc(STAGE_NAMES[item.stage] || item.display_name)}</strong><small>${item.approved_at ? esc(String(item.approved_at).slice(0, 10)) : esc(label(item.status))}</small></li>`).join("")}</ol>
        <div class="cert-hashes mono">
          <span><b>Product key</b> ${esc(chain.product_key)}</span>
          <span><b>Fingerprint</b> ${esc(chain.metadata_hash)}</span>
          <span><b>Registered</b> block ${esc(chain.registration_block_number)} · tx ${esc(chain.registration_tx_hash)}</span>
        </div>
        <footer class="cert-foot">
          <div><span class="cert-sign">OriginChain Registry</span><small>Issued ${esc(issued)}</small></div>
          <div class="wax-seal" aria-hidden="true"><span>OC</span></div>
          <div class="right"><small>Educational demonstration · fictional product · not a regulatory certificate</small></div>
        </footer>
      </div>`;
    $("#certDialog").showModal();
  } catch (error) { reportError(error, "Certificate unavailable"); }
}
$("#certPrint").addEventListener("click", () => window.print());

/* ---------- QR scanner ---------- */
let scanStream = null, scanLoop = null;
async function decodeQR(source) {
  if ("BarcodeDetector" in window) {
    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    const codes = await detector.detect(source);
    return codes[0]?.rawValue || null;
  }
  if (!window.jsQR) {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js";
      script.onload = resolve; script.onerror = () => reject(new Error("QR library could not load (offline?)"));
      document.head.append(script);
    });
  }
  const width = source.videoWidth || source.naturalWidth || source.width;
  const height = source.videoHeight || source.naturalHeight || source.height;
  if (!width || !height) return null;
  const canvas = document.createElement("canvas");
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(source, 0, 0, width, height);
  return window.jsQR(ctx.getImageData(0, 0, width, height).data, width, height)?.data || null;
}
function codeFromQR(value) {
  const match = String(value).match(/#verify\/([^?#]+)/);
  return match ? decodeURIComponent(match[1]) : String(value).trim();
}
function stopScan() {
  cancelAnimationFrame(scanLoop); scanLoop = null;
  scanStream?.getTracks().forEach((track) => track.stop()); scanStream = null;
}
function scanned(value) {
  stopScan();
  $("#scanDialog").close();
  $("#verifyCode").value = codeFromQR(value);
  runVerify(true);
}
$("#scanButton").addEventListener("click", async () => {
  $("#scanStatus").textContent = "Starting the camera…";
  $("#scanDialog").showModal();
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    const video = $("#scanVideo");
    video.srcObject = scanStream; await video.play();
    $("#scanStatus").textContent = "Point the camera at the QR code on the box.";
    const loop = async () => {
      if (!scanStream) return;
      try { const value = await decodeQR(video); if (value) return scanned(value); } catch (_) { /* keep scanning */ }
      scanLoop = requestAnimationFrame(loop);
    };
    loop();
  } catch (_) {
    $("#scanStatus").textContent = "Camera unavailable. Upload a photo of the QR code instead.";
  }
});
$("#scanDialog").addEventListener("close", stopScan);
$("#scanFile").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const image = new Image();
  image.src = URL.createObjectURL(file);
  await image.decode();
  try {
    const value = await decodeQR(image);
    if (value) scanned(value); else $("#scanStatus").textContent = "No QR code found in that photo. Try a closer shot.";
  } catch (error) { $("#scanStatus").textContent = error.message; }
  event.target.value = "";
});

/* ---------- Command palette (⌘K) ---------- */
let paletteIndex = 0, paletteItems = [];
function paletteCommands() {
  const role = state.user?.role;
  const commands = [];
  const add = (group, title, hint, run, when = true) => { if (when) commands.push({ group, title, hint, run }); };
  const views = [["overview", "Overview"], ["batches", "Batches"], ["quality", "Quality checks"], ["verify", "Verify a product"], ["admin", "Admin"]];
  views.forEach(([view, title]) => add("Go to", title, `#${view}`, () => go(view), allowedView(view) === view));
  if (state.user) STAGES.filter(canViewStage).forEach((stage) => add("Stage", `${STAGE_NAMES[stage]} checks`, "Quality", () => { $(`.stage-tabs button[data-stage="${stage}"]`)?.click(); go("quality"); }));
  const product = currentProduct();
  add("Product", "Show certificate of authenticity", product?.product_code || "", () => openCertificate(product.product_code), Boolean(product));
  add("Product", "Scan a QR code", "Verify", () => { go("verify"); setTimeout(() => $("#scanButton").click(), 200); });
  if (state.demoMode) {
    add("Demo", "Auto-fill my checks", ROLE_NAMES[role] || "", () => $("#demoAutofillButton").click(), OPERATIONAL_ROLES.includes(role));
    add("Demo", "Create HOLD case", "Retailer", () => $("#demoHoldButton").click(), role === "RETAILER");
    add("Demo", "Load full demo", "Admin", () => $("#loadPresentationButton").click(), role === "ADMIN");
    add("Demo", "Readiness check", "Admin", () => $("#readinessButton").click(), role === "ADMIN");
    add("Demo", "Tamper product data", "Admin", () => $("#tamperButton").click(), role === "ADMIN");
    add("Demo", "Prepare fresh demo", "Admin", () => $("#resetButton").click(), role === "ADMIN");
    ["supplier", "manufacturer", "distributor", "retailer", "admin"].forEach((username) =>
      add("Switch role", `Sign in as ${username.charAt(0).toUpperCase()}${username.slice(1)}`, "Demo account", () => $(`[data-quick-role="${username}"]`).click(), state.user?.username !== username));
  }
  add("App", `Switch to ${document.documentElement.dataset.theme === "dark" ? "light" : "dark"} theme`, "Theme", () => $("#themeToggle").click());
  add("App", "About OriginChain", "Help", () => $("#aboutButton").click());
  add("App", "Sign out", "", () => $("#logoutButton").click(), Boolean(state.user));
  return commands;
}
function renderPalette() {
  const query = $("#paletteInput").value.trim().toLowerCase();
  paletteItems = paletteCommands().filter((item) => !query || `${item.group} ${item.title} ${item.hint}`.toLowerCase().includes(query));
  paletteIndex = Math.min(paletteIndex, Math.max(0, paletteItems.length - 1));
  let lastGroup = "";
  $("#paletteList").innerHTML = paletteItems.map((item, index) => {
    const header = item.group !== lastGroup ? `<li class="palette-group" role="presentation">${esc(item.group)}</li>` : "";
    lastGroup = item.group;
    return `${header}<li role="option" data-index="${index}" aria-selected="${index === paletteIndex}"><span>${esc(item.title)}</span><small>${esc(item.hint)}</small></li>`;
  }).join("") || '<li class="palette-empty">No matches</li>';
  $("#paletteList [aria-selected=true]")?.scrollIntoView({ block: "nearest" });
}
function openPalette() {
  if ($("#palette").open) return;
  $("#paletteInput").value = ""; paletteIndex = 0;
  renderPalette();
  $("#palette").showModal();
  $("#paletteInput").focus();
}
function runPaletteItem(index) {
  const item = paletteItems[index];
  if (!item) return;
  $("#palette").close();
  item.run();
}
$("#paletteButton").addEventListener("click", openPalette);
$("#paletteInput").addEventListener("input", () => { paletteIndex = 0; renderPalette(); });
$("#paletteInput").addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown") { paletteIndex = Math.min(paletteItems.length - 1, paletteIndex + 1); renderPalette(); event.preventDefault(); }
  if (event.key === "ArrowUp") { paletteIndex = Math.max(0, paletteIndex - 1); renderPalette(); event.preventDefault(); }
  if (event.key === "Enter") { runPaletteItem(paletteIndex); event.preventDefault(); }
});
$("#paletteList").addEventListener("click", (event) => {
  const option = event.target.closest("[data-index]");
  if (option) runPaletteItem(Number(option.dataset.index));
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openPalette(); }
});

/* ---------- Live sync across windows ---------- */
// One request per tick: /api/live returns a data-change version plus chain status.
// Full records are fetched only when that version moves.
let liveVersion = null;
function recordSignature() {
  return JSON.stringify([
    state.products.map((item) => [item.product_code, item.current_stage, item.final_sale_status]),
    state.materials.map((item) => [item.id, item.quality_status]),
  ]);
}
async function liveTick() {
  if (document.visibilityState !== "visible") return;
  if (!state.user) { liveVersion = null; await refreshHealth(true); return; }
  if (document.querySelector("dialog[open]") || document.querySelector("[aria-busy=true]")) return;
  try {
    const live = await api("/api/live");
    applyHealth(live);
    if (liveVersion !== null && live.version !== liveVersion) {
      const before = recordSignature();
      await refreshRecords(); await refreshDashboard();
      if (state.activeStage) await renderQuality();
      if (recordSignature() !== before) {
        showFeedback("Live update", "Another user just changed this batch.", "success");
        if (currentProduct()?.final_sale_status === "APPROVED_FOR_SALE" && !before.includes("APPROVED_FOR_SALE")) celebrate(null, 120);
      }
    }
    liveVersion = live.version;
  } catch (_) { /* offline or signed out: the next tick retries */ }
}
setInterval(liveTick, 5000);

/* ---------- Boot ---------- */
(async function boot() {
  renderBottles();
  try {
    const catalog = await api("/api/demo/catalog");
    state.demoMode = Boolean(catalog.demo_mode);
    applyFabVisibility();
    await refreshHealth();
    if (state.token) {
      const user = await api("/api/auth/me");
      await beginSession(state.token, user);
    } else showLoggedOut();
  } catch (error) {
    showLoggedOut();
    reportError(error, "Saved session could not be restored");
  }
  route();
})();
