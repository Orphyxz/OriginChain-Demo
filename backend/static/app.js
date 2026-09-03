const state = {
  materials: [], products: [], activeStage: null, contextType: null,
  contextId: null, activeSummary: null, verification: null, user: null,
  qualitySources: [], qualityProfiles: [], productSpecifications: [], evidenceIssuers: [],
  sourceReviews: [], changeRecords: [],
  token: localStorage.getItem("originchain_demo_access_token") || null,
};
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
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
const LABELS = {
  APPROVED_FOR_SALE: "Approved for Sale", NOT_READY: "Not Ready",
  NOT_APPLICABLE: "Not Applicable", CONSUMER_VISIBLE: "Visible to Consumer",
  INTERNAL: "Internal", FILE_MISSING: "File Missing", RAW_MATERIAL: "Raw Materials",
  PENDING: "Pending", APPROVED: "Approved", HOLD: "Hold", REJECTED: "Rejected",
  PASS: "Pass", FAIL: "Fail", VERIFIED: "Verified", MISMATCH: "Mismatch",
  SUSPICIOUS: "Suspicious", GENUINE: "Authentic",
  REGULATORY: "Regulatory Traceability", STANDARD_BASED: "Standard Based",
  INDUSTRY_GUIDANCE: "Industry Guidance", ORIGINCHAIN_INTERNAL: "OriginChain Internal",
  ORGANIZATION_INTERNAL: "Organization Internal", PUBLISHED_CURRENT: "Published Current",
  PUBLISHED_UNDER_REVISION: "Published · Under Revision", DRAFT: "Draft · Not Active",
  SUPERSEDED: "Superseded", WITHDRAWN: "Withdrawn", UNKNOWN: "Status Unknown",
  STANDARD_LEVEL: "Standard-Level Mapping", CERTIFICATE_OF_ANALYSIS: "Certificate of Analysis",
  MICROBIOLOGY_REPORT: "Microbiology Report", PRESERVATIVE_EFFICACY_REPORT: "Preservative-Efficacy Report",
  RAW_MATERIAL_SPECIFICATION: "Raw-Material Specification", BATCH_MANUFACTURING_RECORD: "Batch Manufacturing Record",
  PACKAGING_INSPECTION: "Packaging Inspection", TRANSPORT_RECORD: "Transport Record",
  RETAIL_INSPECTION: "Retail Inspection", OTHER: "Other Evidence",
};
const DOCUMENT_TYPES = ["CERTIFICATE_OF_ANALYSIS", "MICROBIOLOGY_REPORT", "PRESERVATIVE_EFFICACY_REPORT", "RAW_MATERIAL_SPECIFICATION", "BATCH_MANUFACTURING_RECORD", "PACKAGING_INSPECTION", "TRANSPORT_RECORD", "RETAIL_INSPECTION", "OTHER"];

function esc(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function label(value) {
  if (!value) return "Not Started";
  return LABELS[value] || String(value).toLowerCase().split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function showFeedback(title, detail = "", type = "error", items = []) {
  const box = $("#notice");
  box.setAttribute("role", type === "error" ? "alert" : "status");
  box.className = `notice ${type}`;
  box.innerHTML = `<strong>${esc(title)}</strong>${detail ? `<span>${esc(detail)}</span>` : ""}${items.length ? `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}`;
  clearTimeout(showFeedback.timer);
  showFeedback.timer = setTimeout(() => box.classList.add("hidden"), type === "error" ? 10000 : 6500);
}

class ApiError extends Error {
  constructor(title, detail, items, status) {
    super(detail || title);
    this.title = title;
    this.detail = detail;
    this.items = items;
    this.status = status;
  }
}

function parseApiError(body, status) {
  const detail = body?.detail ?? body;
  if (typeof detail === "string") return new ApiError("Request could not be completed", detail, [], status);
  if (Array.isArray(detail)) {
    const items = detail.map((item) => `${(item.loc || []).slice(1).join(" → ")}: ${item.msg}`);
    return new ApiError("Please review the form", "Some values need attention.", items, status);
  }
  if (detail?.message) {
    const items = detail.blocking_reasons || (detail.guidance ? [detail.guidance] : []);
    return new ApiError(detail.message, items.length ? "Review the requirements below." : "", items, status);
  }
  return new ApiError("Request could not be completed", `Server returned HTTP ${status}.`, [], status);
}

async function api(path, options = {}) {
  let response;
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  try { response = await fetch(path, { ...options, headers }); }
  catch (_) { throw new ApiError("Application is unavailable", "Check that the FastAPI server is running.", [], 0); }
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("json") ? await response.json() : await response.text();
  if (response.status === 401 && path !== "/api/auth/login") showLoggedOut();
  if (!response.ok) throw parseApiError(body, response.status);
  return body;
}

function reportError(error, fallbackTitle = "Action could not be completed") {
  showFeedback(error.title || fallbackTitle, error.detail || error.message, "error", error.items || []);
}

async function withButton(button, pendingText, work) {
  if (!button || button.getAttribute("aria-busy") === "true") return;
  const original = button.textContent;
  const originallyDisabled = button.disabled;
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  button.textContent = pendingText;
  try { return await work(); }
  finally {
    button.removeAttribute("aria-busy");
    button.textContent = original;
    button.disabled = originallyDisabled;
    updateControls();
  }
}

function nullifyBlankFields(payload, fields) {
  fields.forEach((field) => { if (payload[field] === "") payload[field] = null; });
  return payload;
}

function currentProduct() {
  return state.products.find((item) => item.product_code === "OC-LUX-SERUM-0001") || state.products[0] || null;
}

function canWriteStage(stage) {
  return Boolean(state.user && ROLE_STAGE[state.user.role] === stage);
}

function canViewStage(stage) {
  return Boolean(state.user && (ROLE_STAGE_VIEWS[state.user.role] || []).includes(stage));
}

function showLoggedOut(message = "") {
  state.token = null; state.user = null; state.materials = []; state.products = [];
  state.activeStage = null; state.contextType = null; state.contextId = null; state.activeSummary = null;
  state.qualitySources = []; state.qualityProfiles = []; state.productSpecifications = [];
  state.evidenceIssuers = []; state.sourceReviews = []; state.changeRecords = [];
  localStorage.removeItem("originchain_demo_access_token");
  $("#access").classList.remove("hidden");
  $("#operationalApp").hidden = true;
  $("#accountPanel").classList.add("hidden");
  $("#admin").classList.add("hidden");
  $$(".operational-nav, .admin-nav").forEach((item) => item.classList.add("hidden"));
  document.body.removeAttribute("data-role");
  if (message) showFeedback("Session ended", message, "warning");
}

function applyRoleUI() {
  const role = state.user?.role;
  if (!role) return showLoggedOut();
  document.body.dataset.role = role;
  $("#access").classList.add("hidden");
  $("#operationalApp").hidden = false;
  $("#accountPanel").classList.remove("hidden");
  $("#accountName").textContent = state.user.display_name;
  $("#accountOrganization").textContent = state.user.organization_name;
  $("#accountRole").textContent = label(role);
  $$(".operational-nav").forEach((item) => item.classList.remove("hidden"));
  const showMaterials = ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "ADMIN"].includes(role);
  const showManufacturing = ["MANUFACTURER", "DISTRIBUTOR", "RETAILER", "ADMIN"].includes(role);
  const navigationCopy = {
    RAW_MATERIAL_SUPPLIER: { materials: "Raw Materials", product: "Manufacturing", quality: "Raw Material QC" },
    MANUFACTURER: { materials: "Approved Raw Materials", product: "Manufacturing", quality: "Manufacturer QC" },
    DISTRIBUTOR: { materials: "Raw Materials", product: "Received Product", quality: "Distribution QC" },
    RETAILER: { materials: "Raw Materials", product: "Received Product", quality: "Retail QC" },
    ADMIN: { materials: "Raw Materials", product: "Product Record", quality: "All Quality Stages" },
  }[role];
  $('[data-nav-role="materials"]').textContent = navigationCopy.materials;
  $('[data-nav-role="manufacturing"]').textContent = navigationCopy.product;
  $('[data-nav-role="operations"]').textContent = navigationCopy.quality;
  $("#materials").classList.toggle("hidden", !showMaterials);
  $("#materials").classList.toggle("read-only-section", role !== "RAW_MATERIAL_SUPPLIER");
  $("#materialRegistrationPanel").classList.toggle("hidden", role !== "RAW_MATERIAL_SUPPLIER");
  $("#manufacturing").classList.toggle("hidden", !showManufacturing);
  $("#productForm").classList.toggle("hidden", role !== "MANUFACTURER");
  $("#productSectionHeading").textContent = role === "MANUFACTURER" ? "Create the finished batch"
    : role === "ADMIN" ? "Finished-product record" : "Received finished product";
  $("#productSectionIntro").textContent = role === "MANUFACTURER"
    ? "Only approved raw-material batches can be linked. The resulting lineage receives a deterministic integrity commitment."
    : "Read-only batch, custody, and approved raw-material lineage for the authenticated downstream actor.";
  $('[data-nav-role="materials"]').classList.toggle("hidden", !showMaterials);
  $('[data-nav-role="manufacturing"]').classList.toggle("hidden", !showManufacturing);
  $("#admin").classList.toggle("hidden", role !== "ADMIN");
  $(".admin-nav").classList.toggle("hidden", role !== "ADMIN");
  $$(".stage-tabs button").forEach((button) => {
    button.hidden = !canViewStage(button.dataset.stage);
  });
  updateControls();
}

async function beginSession(token, user) {
  state.token = token; state.user = user;
  localStorage.setItem("originchain_demo_access_token", token);
  applyRoleUI();
  await Promise.all([refreshRecords(), refreshQualityReferences()]);
  await refreshDashboard();
  const stage = ROLE_STAGE[user.role];
  if (stage === "RAW_MATERIAL_SUPPLIER" && state.materials.length) {
    await selectQuality(stage, "RAW_MATERIAL", state.materials[0].id);
  } else if (stage && currentProduct()) {
    await selectQuality(stage, "PRODUCT", currentProduct().product_code);
  }
  if (user.role === "ADMIN") { renderQualityReferences(); await refreshAudit(); }
}

async function refreshQualityReferences() {
  [state.qualitySources, state.qualityProfiles, state.productSpecifications, state.evidenceIssuers] = await Promise.all([
    api("/api/quality/sources"), api("/api/quality/profiles"),
    api(`/api/product-specifications?approved_only=${state.user?.role === "ADMIN" ? "false" : "true"}`), api("/api/evidence/issuers"),
  ]);
  if (state.user?.role === "ADMIN") {
    [state.sourceReviews, state.changeRecords] = await Promise.all([
      api("/api/quality/source-reviews"), api("/api/quality/change-records?limit=50"),
    ]);
  }
  renderSpecificationSelection();
  if (state.user?.role === "ADMIN") renderQualityReferences();
}

function renderSpecificationSelection() {
  const select = $("#specificationSelect");
  const applicable = state.productSpecifications.filter((item) => item.status === "APPROVED" && item.active);
  select.innerHTML = applicable.length
    ? applicable.map((item) => `<option value="${esc(item.specification_code)}">${esc(item.specification_name)} · v${esc(item.version)}</option>`).join("")
    : '<option value="">No approved effective specification</option>';
  const spec = applicable[0];
  const card = $("#manufacturerSpecification");
  if (!spec) {
    card.className = "specification-card empty-state";
    card.textContent = "No approved product specification is available.";
    return;
  }
  card.className = "specification-card";
  card.innerHTML = `<small>Product Specification</small><strong>${esc(spec.specification_name)}</strong><span>Version ${esc(spec.version)} · <b class="status ${esc(spec.status)}">${esc(label(spec.status))}</b></span><span>Applicable to ${esc(label(spec.product_type))}</span><span>${esc(spec.visual_requirement_count)} visual requirements · Quality Profile ${esc(state.qualityProfiles[0]?.profile_code || "Not assigned")}</span><p>${esc(spec.disclaimer)}</p>`;
}

function renderQualityReferences() {
  const profile = state.qualityProfiles[0];
  if (profile) {
    $("#profileSummary").className = "profile-summary";
    $("#profileSummary").innerHTML = `<strong>${esc(profile.name)}</strong><span>${esc(profile.profile_code)} · v${esc(profile.version)} · ${esc(label(profile.jurisdiction))}</span><p>${esc(profile.disclaimer)}</p><small>${esc(profile.requirement_count)} mapped requirements</small>`;
  }
  const registry = $("#sourceRegistry");
  if (!state.qualitySources.length) {
    registry.className = "source-registry empty-state";
    registry.textContent = "No controlled sources are registered.";
    return;
  }
  registry.className = "source-registry";
  registry.innerHTML = state.qualitySources.map((source) => `<article>
    <div><strong>${esc(source.source_code)}</strong><small>${esc(source.authority)} · ${esc(source.edition)}</small><span>${esc(source.title)}</span></div>
    <div><span class="status ${esc(source.status)}">${esc(label(source.status))}</span><small>Verified ${esc(source.last_verified_at)} · ${esc(source.mapped_requirement_count)} active mapping${source.mapped_requirement_count === 1 ? "" : "s"}</small></div>
    <a href="${esc(source.source_url)}" target="_blank" rel="noopener noreferrer">Official source ↗</a>
  </article>`).join("");

  const specs = $("#specificationRegistry");
  specs.className = "governance-list";
  specs.innerHTML = state.productSpecifications.map((item) => `<article><div><strong>${esc(item.specification_name)}</strong><small>${esc(item.product_type)} · ${esc(item.requirement_count)} requirements · ${esc(item.visual_requirement_count)} visual</small></div><div><span>v${esc(item.version)}</span><span class="status ${esc(item.status)}">${esc(label(item.status))}</span><small>Effective ${esc(item.effective_from || "Not set")}</small></div></article>`).join("") || '<div class="empty-state">No specifications registered.</div>';

  const issuers = $("#issuerRegistry");
  issuers.className = "governance-list";
  issuers.innerHTML = state.evidenceIssuers.map((item) => `<article><div><strong>${esc(item.issuer_name)}</strong><small>${esc(label(item.issuer_type))} · ${esc(item.issuer_code)}</small></div><span class="status ${esc(item.trust_status)}">${esc(label(item.trust_status))}</span></article>`).join("") || '<div class="empty-state">No evidence issuers registered.</div>';

  const reviews = $("#sourceReviewRegistry");
  reviews.className = "governance-list";
  reviews.innerHTML = state.sourceReviews.map((item) => `<article><div><strong>${esc(item.source_code)}</strong><small>${esc(item.title)} · Owner ${esc(item.review_owner_name || item.review_owner_user_id || "Unassigned")}</small></div><div><span class="status ${esc(item.review_status)}">${esc(label(item.review_status))}</span><small>Last reviewed ${esc(item.reviewed_at || "Not reviewed")} · Next ${esc(item.next_review_due || "Not scheduled")}</small></div></article>`).join("") || '<div class="empty-state">No source reviews registered.</div>';

  const changes = $("#changeRegistry");
  changes.className = "governance-list";
  changes.innerHTML = state.changeRecords.map((item) => `<article><div><strong>${esc(label(item.change_type))}</strong><small>${esc(item.target_code)}${item.previous_version || item.new_version ? ` · ${esc(item.previous_version || "New")} → ${esc(item.new_version || "Current")}` : ""}</small><span>${esc(item.change_summary)}</span></div><span class="status ${esc(item.status)}">${esc(label(item.status))}</span></article>`).join("") || '<div class="empty-state">No change records registered.</div>';
}

function isExpired(dateValue) {
  if (!dateValue) return false;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return new Date(`${dateValue}T00:00:00`) < today;
}

function eligibleMaterials() {
  return state.materials.filter((item) => item.quality_status === "APPROVED" && !isExpired(item.expiry_retest_date));
}

async function refreshHealth() {
  try {
    const health = await api("/api/health");
    $("#chainPill").classList.toggle("online", health.blockchain_connected);
    $("#chainPill").lastChild.textContent = health.blockchain_connected ? " Connected" : " Offline";
    $("#networkName").textContent = health.blockchain_connected
      ? `${label(health.network || "Hardhat Local")} · block ${health.current_block}` : "Hardhat offline";
  } catch (error) {
    $("#chainPill").classList.remove("online");
    $("#chainPill").lastChild.textContent = " Offline";
    $("#networkName").textContent = "API unavailable";
    reportError(error, "Connection check failed");
  }
}

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
    list.textContent = "No raw-material batches yet. Register the first material batch to begin the serum supply-chain workflow.";
    return;
  }
  list.className = "record-list";
  list.innerHTML = state.materials.map((item) => {
    const expired = isExpired(item.expiry_retest_date);
    const effectiveStatus = expired ? "EXPIRED" : item.quality_status;
    return `<article class="record">
      <div><strong>${esc(item.material_name)}</strong><small>${esc(item.internal_batch_id)} · supplier lot ${esc(item.supplier_lot_number)}</small>
      <div class="record-meta"><span>${esc(item.supplier_name)}</span><span>${esc(item.quantity)} ${esc(item.unit)}</span><span>Received ${esc(item.received_date)}</span>${item.expiry_retest_date ? `<span>Retest ${esc(item.expiry_retest_date)}</span>` : ""}</div>
      <span class="status ${esc(effectiveStatus)}">${esc(label(effectiveStatus))}</span></div>
      <button class="quiet inspect-material" data-id="${esc(item.id)}">Open quality checks</button></article>`;
  }).join("");
  $$(".inspect-material").forEach((button) => button.addEventListener("click", () =>
    selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", button.dataset.id)));
}

function renderMaterialChoices() {
  const approved = eligibleMaterials();
  const choices = $("#materialChoices");
  if (!approved.length) {
    choices.className = "choices empty-state";
    choices.textContent = "No eligible materials. Complete supplier QC for at least one unexpired material batch.";
  } else {
    choices.className = "choices";
    choices.innerHTML = approved.map((item) => `<label><input type="checkbox" value="${esc(item.id)}" checked>
      <span><strong>${esc(item.material_name)}</strong> · ${esc(item.internal_batch_id)} <span class="status APPROVED">Approved</span></span></label>`).join("");
  }
}

function renderProductState() {
  const product = currentProduct();
  const result = $("#productResult");
  if (!product) {
    result.className = "result muted";
    result.textContent = "No finished serum batch registered yet. Approve a raw material to unlock registration.";
    return;
  }
  $("#verifyCode").value = product.product_code;
  const materials = product.linked_raw_materials || [];
  const spec = product.product_specification;
  result.className = "result";
  result.innerHTML = `<strong>${esc(product.name)}</strong><div class="record-meta"><span>${esc(product.product_code)}</span><span>Batch ${esc(product.batch_number)}</span><span>${esc(label(product.current_stage))} custody</span></div>
    <span class="status ${esc(product.final_sale_status)}">${esc(label(product.final_sale_status))}</span>
    ${spec ? `<p><strong>Reference Specification</strong><br>${esc(spec.specification_name)} · v${esc(spec.version)} <span class="status APPROVED">Recorded</span></p>` : ""}
    <p><strong>Linked materials</strong><br>${materials.length ? materials.map((item) => `${esc(item.material_name)} · ${esc(item.internal_batch_id)} (${esc(label(item.quality_status))})`).join("<br>") : "No linked materials"}</p>`;
}

function updateControls() {
  const product = currentProduct();
  const productButton = $("#registerProductButton");
  if (product) {
    productButton.disabled = true;
    productButton.textContent = "Finished batch already registered";
    $$("#productForm input, #productForm textarea, #productForm select").forEach((field) => { field.disabled = true; });
  } else {
    $$("#productForm input, #productForm textarea, #productForm select").forEach((field) => { field.disabled = false; });
    productButton.disabled = state.user?.role !== "MANUFACTURER" || eligibleMaterials().length === 0;
    productButton.textContent = "Register batch on blockchain";
  }
  $$(".stage-tabs button").forEach((button) => {
    button.hidden = !canViewStage(button.dataset.stage);
    button.disabled = button.dataset.stage === "RAW_MATERIAL_SUPPLIER" ? !state.materials.length : !product;
  });
  $("#registerMaterialButton").disabled = state.user?.role !== "RAW_MATERIAL_SUPPLIER";
  const presentationButton = $("#loadPresentationButton");
  if (presentationButton) {
    const presentationComplete = product?.final_sale_status === "APPROVED_FOR_SALE";
    presentationButton.disabled = state.user?.role !== "ADMIN" || presentationComplete;
    presentationButton.textContent = presentationComplete
      ? "Presentation Demo Loaded"
      : product ? "Complete Existing Presentation Demo" : "Load Complete Presentation Demo";
  }
  $("#tamperButton").disabled = state.user?.role !== "ADMIN" || !product || state.verification?.status === "SUSPICIOUS";
  if (!state.activeSummary) {
    $("#approveStage").hidden = !state.activeStage || !canWriteStage(state.activeStage);
    $("#approveStage").disabled = true;
    $("#transferDistributor").hidden = state.user?.role !== "MANUFACTURER";
    $("#transferDistributor").disabled = true;
    $("#transferRetailer").hidden = state.user?.role !== "DISTRIBUTOR";
    $("#transferRetailer").disabled = true;
    return;
  }
  const summary = state.activeSummary;
  const approve = $("#approveStage");
  approve.hidden = !canWriteStage(state.activeStage);
  approve.disabled = !canWriteStage(state.activeStage) || summary.status === "APPROVED";
  approve.textContent = summary.status === "APPROVED"
    ? `${summary.display_name} Approved`
    : `Review & Approve ${summary.display_name}`;
  $("#transferDistributor").hidden = state.user?.role !== "MANUFACTURER";
  $("#transferDistributor").disabled = !(
    state.user?.role === "MANUFACTURER" &&
    state.activeStage === "MANUFACTURER" && summary.status === "APPROVED" && product?.current_stage === "MANUFACTURER"
  );
  $("#transferRetailer").hidden = state.user?.role !== "DISTRIBUTOR";
  $("#transferRetailer").disabled = !(
    state.user?.role === "DISTRIBUTOR" &&
    state.activeStage === "DISTRIBUTOR" && summary.status === "APPROVED" && product?.current_stage === "DISTRIBUTOR"
  );
}

$$('.demo-account').forEach((button) => button.addEventListener("click", () => {
  $("#loginUsername").value = button.dataset.username;
  $("#loginPassword").focus();
}));

$("#loginForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#loginButton"), "Signing in…", async () => {
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      await beginSession(result.access_token, result.user);
      showFeedback("Signed in", `${result.user.display_name} · ${label(result.user.role)}`, "success");
      $("#dashboard").scrollIntoView({ behavior: "smooth" });
    } catch (error) { reportError(error, "Sign in failed"); }
  });
});

$("#logoutButton").addEventListener("click", () => {
  showLoggedOut("You have signed out of the operational workspace.");
  $("#loginPassword").value = "";
  $("#access").scrollIntoView({ behavior: "smooth" });
});

$("#materialForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#registerMaterialButton"), "Registering…", async () => {
    const payload = nullifyBlankFields(
      Object.fromEntries(new FormData(event.currentTarget).entries()),
      ["manufacturing_date", "expiry_retest_date", "country_source", "notes"],
    );
    payload.quantity = Number(payload.quantity);
    try {
      const created = await api("/api/raw-materials", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      await refreshRecords(); await refreshDashboard();
      showFeedback("Material batch registered", `${created.material_name} · ${created.internal_batch_id}. Complete supplier quality checks next.`, "success");
      await selectQuality("RAW_MATERIAL_SUPPLIER", "RAW_MATERIAL", created.id);
      $("#operations").scrollIntoView({ behavior: "smooth" });
    } catch (error) { reportError(error, "Material registration failed"); }
  });
});

$("#productForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter || $("#registerProductButton"), "Registering on blockchain…", async () => {
    const payload = nullifyBlankFields(
      Object.fromEntries(new FormData(event.currentTarget).entries()),
      ["manufactured_date", "expiry_date"],
    );
    payload.name = "Aurelia Prestige Renewal Serum";
    payload.brand = "Aurelia Maison";
    payload.description = "Luxury anti-aging facial serum demonstration batch";
    payload.raw_material_batch_ids = $$("#materialChoices input:checked").map((input) => input.value);
    if (!payload.raw_material_batch_ids.length) {
      showFeedback("Select an approved material", "At least one eligible raw-material batch is required.", "warning");
      return;
    }
    try {
      const created = await api("/api/products/register", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      await refreshRecords(); await refreshDashboard();
      showFeedback("Serum batch registered", "The product and raw-material lineage commitments are now recorded.", "success");
      await selectQuality("MANUFACTURER", "PRODUCT", created.product_code);
      $("#operations").scrollIntoView({ behavior: "smooth" });
    } catch (error) { reportError(error, "Finished-batch registration failed"); }
  });
});

async function selectQuality(stage, type, id) {
  state.activeStage = stage; state.contextType = type; state.contextId = id; state.activeSummary = null;
  updateControls();
  $$(".stage-tabs button").forEach((button) => {
    const active = button.dataset.stage === stage;
    button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active));
  });
  const context = type === "RAW_MATERIAL"
    ? state.materials.find((item) => item.id === id)
    : state.products.find((item) => item.product_code === id);
  const linked = type === "PRODUCT" ? context?.linked_raw_materials || [] : [];
  const spec = type === "PRODUCT" ? context?.product_specification : null;
  $("#qualityContext").innerHTML = `<strong>${esc(STAGE_NAMES[stage])}</strong> · ${esc(context?.material_name || context?.name || id)} · ${esc(context?.internal_batch_id || context?.batch_number || "")}${spec ? `<br><small>Reference Specification: ${esc(spec.specification_name)} · v${esc(spec.version)}</small>` : ""}${linked.length ? `<br><small>Linked approved materials: ${linked.map((item) => `${esc(item.material_name)} (${esc(item.internal_batch_id)})`).join(", ")}</small>` : ""}`;
  await renderQuality();
}

function evidenceSatisfiesGate(check, item) {
  return item.integrity === "VERIFIED" && (!check.trusted_issuer_required || item.verification_status === "VERIFIED_DEMO");
}

function checkComplete(check) {
  const validEvidence = !check.evidence_required || (check.evidence || []).some((item) => evidenceSatisfiesGate(check, item));
  return check.result === "PASS" && validEvidence;
}

function categoryMarkup(category, checks) {
  const required = checks.filter((check) => check.required);
  const complete = required.filter(checkComplete).length;
  const failed = checks.filter((check) => check.result === "FAIL").length;
  const missingEvidence = checks.filter((check) => check.evidence_required && !(check.evidence || []).some((item) => evidenceSatisfiesGate(check, item))).length;
  const status = failed ? "Needs Attention" : complete === required.length ? "Complete" : "In Progress";
  const statusClass = failed ? "HOLD" : complete === required.length ? "APPROVED" : "PENDING";
  const details = [failed ? `${failed} failed` : "", missingEvidence ? `${missingEvidence} missing evidence` : ""].filter(Boolean).join(" · ");
  return `<section class="quality-category"><header class="category-head"><div><h3>${esc(category)}</h3><p>${complete} of ${required.length} required checks complete${details ? ` · ${esc(details)}` : ""}</p></div><span class="status ${statusClass}">${status}</span></header>${checks.map(checkRow).join("")}</section>`;
}

function evidenceMarkup(check) {
  if (!(check.evidence || []).length) {
    return check.evidence_required ? '<div class="evidence-missing">Evidence required · none uploaded</div>' : "";
  }
  return `<div class="evidence-list">${check.evidence.map((item) => `<div class="evidence-item">
    <span class="evidence-name">${esc(item.original_filename)}</span>
    <span>${esc(label(item.document_type || "OTHER"))}${item.report_reference ? ` · ${esc(item.report_reference)}` : ""}</span>
    <span>File Integrity: <b class="status ${esc(item.integrity)}">${esc(label(item.integrity))}</b></span>
    ${item.issuer ? `<span>Issuer: ${esc(item.issuer.issuer_name)}</span><span>Evidence Verification: <b class="status ${esc(item.verification_status)}">${esc(label(item.verification_status))}</b></span>${item.issuer.current_trust_status && item.issuer.current_trust_status !== item.issuer.trust_status_at_submission ? `<span class="trust-warning">Accepted as ${esc(label(item.issuer.trust_status_at_submission))}; current issuer status ${esc(label(item.issuer.current_trust_status))}</span>` : ""}` : '<span>Issuer: Not recorded</span>'}
    <span>${esc(label(item.visibility))}</span>
  </div>`).join("")}</div>`;
}

function sourceTraceabilityMarkup(check) {
  const sources = check.sources || [];
  const badges = `<span class="requirement-badge ${esc(check.classification)}">${esc(label(check.classification))}</span>${sources.map((source) => `<span class="source-badge ${esc(source.status)}">${esc(source.source_code)}</span>`).join("")}`;
  const sourceRows = sources.length ? sources.map((source) => `<li><a href="${esc(source.source_url)}" target="_blank" rel="noopener noreferrer">${esc(source.source_code)} · ${esc(source.edition)}</a><span class="status ${esc(source.status)}">${esc(label(source.status))}</span><small>${esc(label(source.mapping_precision))}${source.last_verified_at ? ` · verified ${esc(source.last_verified_at)}` : ""}${source.snapshotted_at ? ` · frozen ${esc(source.snapshotted_at)}` : ""}</small></li>`).join("") : '<li><span>No external source mapping.</span><small>This is an explicitly internal OriginChain or organization gate.</small></li>';
  const specRows = (check.specification_requirements || []).map((item) => `<li><span><strong>Product Specification v${esc(item.specification_version)}</strong> · ${esc(item.description)}</span><small>Expected: ${esc(item.expected_characteristic)}</small></li>`).join("");
  return `<div class="source-badges">${badges}</div><details class="requirement-details"><summary>Requirement rationale & source traceability</summary><p><strong>Why this gate exists</strong><br>${esc(check.requirement_rationale)}</p><p><strong>Expected evidence</strong><br>${esc(check.evidence_expectation)}</p>${check.package_component ? `<p><strong>Structured visual context</strong><br>${esc(check.package_component)} · ${esc(check.expected_visual_characteristic || "Organization-defined")}${check.defect_categories?.length ? `<br>Defect categories: ${check.defect_categories.map(esc).join(", ")}` : ""}</p>` : ""}${specRows ? `<ul class="spec-reference">${specRows}</ul>` : ""}<ul>${sourceRows}</ul><small>A mapping records evidence relevance; it does not certify compliance.</small></details>`;
}

function documentTypeOptions(selected) {
  return DOCUMENT_TYPES.map((value) => `<option value="${value}" ${selected === value ? "selected" : ""}>${esc(label(value))}</option>`).join("");
}

function issuerOptions(check) {
  const selectedCode = check.expected_document_type === "CERTIFICATE_OF_ANALYSIS"
    ? "LUMINA_ACTIVES"
    : ["MICROBIOLOGY_REPORT", "PRESERVATIVE_EFFICACY_REPORT"].includes(check.expected_document_type)
      ? "AURELIA_QC_LAB_DEMO" : "";
  return `<option value="">No issuer recorded</option>${state.evidenceIssuers.map((issuer) => `<option value="${esc(issuer.issuer_code)}" ${issuer.issuer_code === selectedCode ? "selected" : ""}>${esc(issuer.issuer_name)} · ${esc(label(issuer.trust_status))}</option>`).join("")}`;
}

function checkRow(check) {
  const stateClass = check.result === "FAIL" ? "failed" : checkComplete(check) ? "complete" : "";
  const id = `check-${check.standard_id}`;
  if (!canWriteStage(state.activeStage)) {
    return `<div class="check-row readonly ${stateClass}" data-standard="${check.standard_id}">
      <div><strong>${esc(check.check_name)}</strong><small>${esc(check.requirement)}</small>${sourceTraceabilityMarkup(check)}
        ${check.evidence_required ? '<small>Evidence required for the responsible stage actor</small>' : ""}${evidenceMarkup(check)}</div>
      <div><small>Recorded result</small><span class="status ${esc(check.result)}">${esc(label(check.result))}</span></div>
      <div><small>Inspection note</small><span>${check.notes ? esc(check.notes) : "Restricted or not recorded"}</span></div>
    </div>`;
  }
  return `<div class="check-row ${stateClass}" data-standard="${check.standard_id}">
    <div><strong>${esc(check.check_name)}</strong><small>${esc(check.requirement)}</small>${sourceTraceabilityMarkup(check)}
      ${check.evidence_required ? '<small>Evidence required · PDF, PNG or JPEG · maximum 5 MiB</small>' : '<small>Supporting evidence optional</small>'}${evidenceMarkup(check)}</div>
    <label for="${id}-result">Inspection result<select id="${id}-result" class="check-result">
      ${["PENDING", "PASS", "FAIL", "NOT_APPLICABLE"].map((value) => `<option value="${value}" ${check.result === value ? "selected" : ""}>${esc(label(value))}</option>`).join("")}
    </select></label>
    <div class="check-actions"><label for="${id}-note">Inspection note<input id="${id}-note" class="check-note" placeholder="Brief finding or corrective note" value="${esc(check.notes || "")}"></label>
      ${check.evidence_required ? `<label>Document type<select class="check-document-type">${documentTypeOptions(check.expected_document_type)}</select></label><label for="${id}-file">Supporting evidence<input id="${id}-file" class="check-file" type="file" accept=".pdf,.png,.jpg,.jpeg"></label><div class="evidence-metadata"><label>Registered issuer<select class="check-issuer">${issuerOptions(check)}</select></label><label>Issuer report number<input class="check-issuer-report" maxlength="160" placeholder="${check.trusted_issuer_required ? "Required for trusted evidence" : "Optional"}"></label><label>Issuer document date<input class="check-issuer-date" type="date"></label><label>Laboratory name on document<input class="check-laboratory" maxlength="180" placeholder="Optional document metadata"></label><label>Report reference<input class="check-report-reference" maxlength="120" placeholder="Optional document identifier"></label><label>Test date<input class="check-test-date" type="date"></label><label>Test-method source<select class="check-test-method"><option value="">Not stated</option>${(check.sources || []).map((source) => `<option value="${esc(source.source_code)}">${esc(source.source_code)}</option>`).join("")}</select></label></div>${check.trusted_issuer_required ? '<small>Trusted Demo issuer and report number required. This is local workflow acceptance, not certification or accreditation.</small>' : ""}<label class="visibility-control"><input class="check-public" type="checkbox"> Visible to Consumer</label>` : ""}
      <button class="save-check" data-standard="${check.standard_id}">Save inspection</button></div>
  </div>`;
}

function renderQualitySummary(summary) {
  const evidence = summary.checks.flatMap((check) => check.evidence || []);
  const verified = evidence.filter((item) => item.integrity === "VERIFIED").length;
  $("#qualitySummary").className = "quality-summary";
  $("#qualitySummary").innerHTML = `<div><small>Stage status</small><strong><span class="status ${esc(summary.status)}">${esc(label(summary.status))}</span></strong></div>
    <div><small>Required checks</small><strong>${summary.required_passed} of ${summary.required_total} passed</strong></div>
    <div><small>Blocking issues</small><strong>${summary.blocking_reasons.length}</strong></div>
    <div><small>Evidence integrity</small><strong>${verified} of ${evidence.length} verified</strong></div>`;
  const blockers = $("#blockingPanel");
  if (summary.blocking_reasons.length) {
    blockers.classList.remove("hidden");
    blockers.innerHTML = `<strong>${summary.display_name} cannot be approved yet.</strong><span>${summary.blocking_reasons.length} requirement${summary.blocking_reasons.length === 1 ? "" : "s"} need attention:</span><ul>${summary.blocking_reasons.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
  } else {
    blockers.classList.add("hidden"); blockers.innerHTML = "";
  }
}

async function renderQuality() {
  if (!state.activeStage || !state.contextId) return;
  $("#qualityChecks").className = "quality-checks empty-state";
  $("#qualityChecks").textContent = "Loading quality standards and inspection state…";
  $("#qualityChecks").setAttribute("aria-busy", "true");
  try {
    const summary = await api(`/api/quality/${state.contextType}/${encodeURIComponent(state.contextId)}/summary?stage=${state.activeStage}`);
    state.activeSummary = summary;
    const groups = summary.checks.reduce((result, check) => {
      (result[check.category] ||= []).push(check); return result;
    }, {});
    renderQualitySummary(summary);
    $("#qualityChecks").className = "quality-checks";
    $("#qualityChecks").innerHTML = Object.entries(groups).map(([category, checks]) => categoryMarkup(category, checks)).join("");
    $$(".save-check").forEach((button) => button.addEventListener("click", () => saveCheck(button)));
    updateControls();
  } catch (error) {
    $("#qualityChecks").className = "quality-checks empty-state";
    $("#qualityChecks").textContent = "Quality checks could not be loaded. Review the message above and retry.";
    reportError(error, "Quality state could not be loaded");
  } finally { $("#qualityChecks").removeAttribute("aria-busy"); }
}

async function saveCheck(button) {
  const row = button.closest(".check-row");
  const standardId = Number(button.dataset.standard);
  await withButton(button, "Saving…", async () => {
    try {
      const result = await api("/api/quality/results", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
          context_type: state.contextType, context_id: state.contextId, standard_id: standardId,
          result: row.querySelector(".check-result").value,
          notes: row.querySelector(".check-note").value || null,
        }),
      });
      const file = row.querySelector(".check-file")?.files[0];
      if (file) {
        const data = new FormData(); data.append("file", file);
        data.append("visibility", row.querySelector(".check-public")?.checked ? "CONSUMER_VISIBLE" : "INTERNAL");
        data.append("document_type", row.querySelector(".check-document-type")?.value || "OTHER");
        const optionalEvidenceFields = {
          laboratory_name: ".check-laboratory", report_reference: ".check-report-reference",
          test_date: ".check-test-date", test_method_source_code: ".check-test-method",
          issuer_code: ".check-issuer", issuer_report_number: ".check-issuer-report",
          issuer_document_date: ".check-issuer-date",
        };
        Object.entries(optionalEvidenceFields).forEach(([name, selector]) => {
          const value = row.querySelector(selector)?.value?.trim(); if (value) data.append(name, value);
        });
        await api(`/api/quality/results/${result.id}/evidence`, { method: "POST", body: data });
      }
      showFeedback("Inspection saved", file ? "The result and evidence commitment were recorded." : "The quality result was updated.", "success");
      await refreshRecords(); await renderQuality(); await refreshDashboard();
    } catch (error) { reportError(error, "Inspection could not be saved"); }
  });
}

$("#approveStage").addEventListener("click", (event) => withButton(event.currentTarget, "Checking requirements…", async () => {
  try {
    await api("/api/quality/stages/approve", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        context_type: state.contextType, context_id: state.contextId, stage: state.activeStage,
      }),
    });
    showFeedback(`${STAGE_NAMES[state.activeStage]} approved`, "The stage commitment is recorded and the next workflow action is now available.", "success");
  } catch (error) { reportError(error, `${STAGE_NAMES[state.activeStage]} cannot be approved yet`); }
  await refreshRecords(); await renderQuality(); await refreshDashboard();
}));

$$(`.stage-tabs button`).forEach((button) => button.addEventListener("click", async () => {
  const stage = button.dataset.stage;
  if (stage === "RAW_MATERIAL_SUPPLIER") {
    if (!state.materials.length) return showFeedback("No raw-material batch selected", "Register the first supplier batch before opening QC.", "warning");
    await selectQuality(stage, "RAW_MATERIAL", state.materials[0].id);
  } else {
    const product = currentProduct();
    if (!product) return showFeedback("No finished batch registered", "Approve raw materials and register the serum batch first.", "warning");
    await selectQuality(stage, "PRODUCT", product.product_code);
  }
}));

async function transfer(role, button) {
  const product = currentProduct();
  if (!product) return;
  await withButton(button, "Recording transfer…", async () => {
    try {
      await api("/api/ownership-transfers", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_code: product.product_code, to_role: role }),
      });
      showFeedback(`Transferred to ${label(role)}`, `Custody is recorded on-chain. Complete ${label(role)} quality checks next.`, "success");
      await refreshHealth(); await refreshRecords(); await refreshDashboard();
      await selectQuality(role, "PRODUCT", product.product_code);
    } catch (error) { reportError(error, `Transfer to ${label(role)} is blocked`); }
  });
}
$("#transferDistributor").addEventListener("click", (event) => transfer("DISTRIBUTOR", event.currentTarget));
$("#transferRetailer").addEventListener("click", (event) => transfer("RETAILER", event.currentTarget));

function publicEvidenceMarkup(items) {
  if (!items.length) return '<div class="empty-state">No evidence has been marked visible to consumers.</div>';
  return `<div class="public-evidence">${items.map((item) => `<article><strong>${esc(item.filename)}</strong><small>${esc(item.check_name)} · ${esc(STAGE_NAMES[item.stage] || label(item.stage))} · ${esc(label(item.document_type || "OTHER"))}</small>${item.issuer_name ? `<small>Issuer: ${esc(item.issuer_name)}</small>` : ""}<span class="status ${esc(item.integrity)}">Integrity: ${esc(label(item.integrity))}</span> <span>Visible to Consumer</span></article>`).join("")}</div>`;
}

async function verify(code = $("#verifyCode").value.trim(), announce = false) {
  const result = await api(`/api/verify/${encodeURIComponent(code)}`);
  state.verification = result;
  if (result.status === "NOT_FOUND") {
    $("#consumerResult").innerHTML = `<span class="seal">OC</span><div class="eyebrow">Verification result</div><h3 class="verified-title">Product Not Found</h3><p>${esc(result.message)}</p><div class="empty-state">Check the product code and try again.</div>`;
    if (announce) showFeedback("Product not found", "No OriginChain record matches that code.", "warning");
    return result;
  }
  const authentic = result.status === "GENUINE";
  const sale = result.approved_for_sale;
  const integrityMismatch = !result.metadata_integrity;
  $("#consumerResult").innerHTML = `<span class="seal">OC</span><div class="eyebrow">Consumer verification · read only</div>
    <h3 class="verified-title">${authentic ? "Authentic" : "Suspicious"}</h3>
    <p>${authentic ? (sale ? "Approved for Sale" : "Quality Review Incomplete") : "Blockchain Hash Mismatch"}</p>
    ${integrityMismatch ? '<div class="tamper-warning"><strong>Metadata integrity failed</strong><br>Blockchain hash mismatch detected. Local product information has changed since registration.</div>' : ""}
    <div class="consumer-details"><div><small>Product</small><strong>${esc(result.product.name)}</strong></div><div><small>Brand</small><strong>${esc(result.product.brand)}</strong></div><div><small>Batch</small><strong>${esc(result.product.batch_number)}</strong></div><div><small>Product type</small><strong>${esc(label(result.product.product_type))}</strong></div></div>
    <div class="consumer-status good"><span>Product Configuration</span><strong>${result.product.product_configuration?.verified_against_recorded_specification ? `Verified against recorded specification v${esc(result.product.product_configuration.specification_version)}` : "Not recorded"}</strong></div>
    <div class="consumer-status ${authentic ? "good" : "bad"}"><span>Blockchain authenticity</span><strong>${authentic ? "Verified" : "Suspicious"}</strong></div>
    <div class="consumer-status ${result.metadata_integrity ? "good" : "bad"}"><span>Metadata integrity</span><strong>${result.metadata_integrity ? "Verified" : "Hash Mismatch"}</strong></div>
    <div class="consumer-status ${sale ? "good" : "bad"}"><span>Final retail status</span><strong>${esc(label(result.final_sale_status))}</strong></div>
    <h4>Quality Journey</h4><div class="public-journey">${result.quality_journey.map((item) => `<div><span>${esc(item.display_name)}</span><strong class="status ${esc(item.status)}">${esc(label(item.status))}</strong></div>`).join("")}</div>
    <h4>Provenance</h4><p>${result.ownership_history.map((item) => esc(label(item.role))).join(" → ")}</p>
    <h4>Public Evidence</h4>${publicEvidenceMarkup(result.public_evidence)}
    <p><small>Required evidence integrity: ${esc(label(result.document_integrity))}. Internal evidence and inspection notes remain private.</small></p>`;
  if (announce) showFeedback(
    authentic ? "Authenticity verified" : "Suspicious product metadata",
    authentic ? label(result.final_sale_status) : "The local metadata no longer matches the immutable blockchain commitment.",
    authentic ? "success" : "error",
  );
  return result;
}

$("#verifyForm").addEventListener("submit", (event) => {
  event.preventDefault();
  withButton(event.submitter, "Verifying…", async () => {
    try { await verify(undefined, true); }
    catch (error) { reportError(error, "Product verification failed"); }
  });
});

function openDialog(dialog, fallbackMessage, confirmed) {
  if (typeof dialog.showModal === "function") dialog.showModal();
  else if (window.confirm(fallbackMessage)) confirmed();
}

$("#tamperButton").addEventListener("click", () => openDialog(
  $("#tamperDialog"), "Intentionally tamper local metadata for this demonstration?", runTamper,
));
$("#tamperDialog").addEventListener("close", () => {
  if ($("#tamperDialog").returnValue === "confirm") runTamper();
});
async function runTamper() {
  const button = $("#tamperButton");
  await withButton(button, "Tampering local metadata…", async () => {
    try {
      await api(`/api/demo/tamper/${encodeURIComponent($("#verifyCode").value.trim())}`, { method: "POST" });
      await refreshRecords(); await verify(undefined, false);
      await refreshAudit();
      showFeedback("Demo tamper completed", "Metadata integrity now shows a blockchain hash mismatch and Suspicious status.", "warning");
    } catch (error) { reportError(error, "Tamper demonstration failed"); }
  });
}

function renderJourney(journey, currentStage) {
  const approvedCount = journey.filter((item) => item.status === "APPROVED").length;
  const currentIndex = currentStage === "COMPLETE" ? -1 : STAGES.indexOf(currentStage);
  $("#journey").innerHTML = journey.map((item, index) => {
    const isCurrent = currentIndex === index;
    const future = currentIndex >= 0 && index > currentIndex && item.status === "PENDING";
    const shownStatus = future ? "NOT_STARTED" : item.status;
    const marker = isCurrent ? "Current stage" : item.status === "APPROVED" ? "Completed" : future ? "Upcoming" : "";
    return `<article class="${item.status.toLowerCase()} ${isCurrent ? "current" : ""} ${future ? "future" : ""}"><span class="stage-marker">${esc(marker)}</span><i>0${index + 1}</i><h3>${esc(item.display_name)}</h3><b>${esc(label(shownStatus))}</b><p>${item.required_total ? `${item.required_passed} of ${item.required_total} requirements passed` : index === 0 ? "Register and approve supplier batches" : "Waiting for the preceding stage"}</p></article>`;
  }).join("");
  return approvedCount;
}

async function operationalJourney(product) {
  const linked = product?.linked_raw_materials || [];
  const rawApproved = linked.length
    ? linked.every((item) => item.quality_status === "APPROVED" && !isExpired(item.expiry_retest_date))
    : state.materials.length > 0 && state.materials.every((item) => item.quality_status === "APPROVED" && !isExpired(item.expiry_retest_date));
  const journey = [{
    stage: "RAW_MATERIAL_SUPPLIER", display_name: "Raw Materials",
    status: rawApproved ? "APPROVED" : "PENDING",
    required_passed: (linked.length ? linked : state.materials).filter((item) => item.quality_status === "APPROVED").length,
    required_total: (linked.length ? linked : state.materials).length,
  }];
  if (!product) {
    return [...journey, ...STAGES.slice(1).map((stage) => ({ stage, display_name: STAGE_NAMES[stage], status: "PENDING", required_passed: 0, required_total: 0, blocking_reasons: [] }))];
  }
  const summaries = await Promise.all(STAGES.slice(1).map((stage) =>
    api(`/api/quality/PRODUCT/${encodeURIComponent(product.product_code)}/summary?stage=${stage}`)));
  return [...journey, ...summaries];
}

function fallbackCurrentStage(product, journey) {
  if (product?.final_sale_status === "APPROVED_FOR_SALE") return "COMPLETE";
  if (product) return product.current_stage;
  return journey[0].status === "APPROVED" ? "MANUFACTURER" : "RAW_MATERIAL_SUPPLIER";
}

async function refreshDashboard() {
  const product = currentProduct();
  try {
    const journey = await operationalJourney(product);
    const currentStage = fallbackCurrentStage(product, journey);
    const approvedCount = renderJourney(journey, currentStage);
    const currentSummary = journey.find((item) => item.stage === currentStage);
    const blockers = currentSummary?.blocking_reasons || [];
    $("#overviewBatch").textContent = product ? product.batch_number : "Not registered";
    $("#overviewProduct").textContent = product ? product.name : "Aurelia Prestige Renewal Serum";
    $("#overviewStage").textContent = currentStage === "COMPLETE" ? "Workflow Complete" : STAGE_NAMES[currentStage];
    $("#overviewQuality").textContent = `${approvedCount} of 4 stages approved`;
    $("#overviewIssues").textContent = blockers.length ? `${blockers.length} blocking issue${blockers.length === 1 ? "" : "s"}` : approvedCount === 4 ? "Every stage approved" : "Continue the current stage";
    const sale = product?.final_sale_status || "NOT_READY";
    $("#overviewSale").textContent = label(sale);
    $("#overviewSale").className = `display-status ${sale === "APPROVED_FOR_SALE" ? "approved" : sale.toLowerCase()}`;
    $("#overviewNext").textContent = currentStage === "COMPLETE" ? "Ready for consumer verification"
      : currentStage === "MANUFACTURER" && journey[1].status === "APPROVED" ? "Ready for Distributor transfer"
      : currentStage === "DISTRIBUTOR" && journey[2].status === "APPROVED" ? "Ready for Retailer transfer"
      : currentStage === "RETAILER" ? "Complete final sale-readiness QC"
      : currentStage === "MANUFACTURER" ? "Register or release the finished batch"
      : currentStage === "DISTRIBUTOR" ? "Complete receiving and logistics QC"
      : "Register and approve supplier batches";
  } catch (error) { reportError(error, "Dashboard state could not be refreshed"); }
}

$("#refreshDashboard").addEventListener("click", (event) => withButton(event.currentTarget, "Refreshing…", async () => {
  try { await refreshHealth(); await refreshRecords(); await refreshDashboard(); }
  catch (error) { reportError(error, "Dashboard refresh failed"); }
}));

async function refreshAudit() {
  if (state.user?.role !== "ADMIN") return;
  const list = $("#auditList");
  list.className = "audit-list empty-state";
  list.textContent = "Loading recent attributed activity…";
  try {
    const events = await api("/api/audit?limit=75");
    if (!events.length) {
      list.textContent = "No audit events yet. Actor actions will appear here.";
      return;
    }
    list.className = "audit-list";
    list.innerHTML = events.map((item) => `<article>
      <time>${esc(item.created_at)}</time>
      <div><strong>${esc(label(item.action))}</strong><small>${esc(item.entity_type)}${item.entity_id ? ` · ${esc(item.entity_id)}` : ""}</small></div>
      <div><span>${esc(item.display_name || item.username || "System")}</span><small>${esc(label(item.actor_role))} · ${esc(item.organization_name || "")}</small></div>
      <span class="status ${esc(item.result)}">${esc(label(item.result))}</span>
    </article>`).join("");
  } catch (error) {
    list.textContent = "Audit activity could not be loaded.";
    reportError(error, "Audit activity unavailable");
  }
}

$("#refreshAudit").addEventListener("click", (event) => withButton(
  event.currentTarget, "Refreshing…", refreshAudit,
));

$("#loadPresentationButton").addEventListener("click", (event) => withButton(
  event.currentTarget, "Creating the complete demo…", async () => {
    try {
      const result = await api("/api/demo/presentation-seed", { method: "POST" });
      await refreshHealth();
      await Promise.all([refreshRecords(), refreshQualityReferences()]);
      await refreshDashboard();
      await refreshAudit();
      await selectQuality("RETAILER", "PRODUCT", result.product_code);
      await verify(result.product_code, false);
      showFeedback(
        "Complete presentation demo loaded",
        "All four stages are approved and the product is ready for public verification.",
        "success",
      );
      $("#dashboard").scrollIntoView({ behavior: "smooth" });
    } catch (error) { reportError(error, "Presentation demo could not be loaded"); }
  },
));

$("#resetButton").addEventListener("click", () => openDialog(
  $("#resetDialog"), "Clear local database and uploads? The blockchain is not reset.", runReset,
));
$("#resetDialog").addEventListener("close", () => {
  if ($("#resetDialog").returnValue === "confirm") runReset();
});
async function runReset() {
  await withButton($("#resetButton"), "Resetting local data…", async () => {
    try {
      const result = await api("/api/demo/reset", { method: "POST" });
      state.materials = []; state.products = []; state.verification = null;
      state.activeStage = null; state.contextType = null; state.contextId = null; state.activeSummary = null;
      renderMaterials(); renderMaterialChoices(); renderProductState(); updateControls();
      $("#qualityContext").textContent = "Select a registered material or product stage.";
      $("#qualitySummary").className = "quality-summary empty-state";
      $("#qualitySummary").textContent = "Register or select a batch before performing quality checks.";
      $("#blockingPanel").classList.add("hidden");
      $("#qualityChecks").className = "quality-checks empty-state";
      $("#qualityChecks").textContent = "Quality categories and checks will appear here.";
      $("#consumerResult").innerHTML = '<span class="seal">OC</span><p>Enter the product code to view the consumer-safe record.</p>';
      await refreshDashboard();
      await refreshAudit();
      showFeedback("Local demo data reset", result.message, "warning");
    } catch (error) { reportError(error, "Local reset failed"); }
  });
}

(async function boot() {
  $("#journey").innerHTML = '<div class="empty-state">Loading current supply-chain state…</div>';
  try {
    await refreshHealth();
    if (state.token) {
      const user = await api("/api/auth/me");
      await beginSession(state.token, user);
    } else showLoggedOut();
  } catch (error) {
    showLoggedOut();
    reportError(error, "Saved session could not be restored");
  }
})();
