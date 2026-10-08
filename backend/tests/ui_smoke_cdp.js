// Optional cross-platform browser smoke. Requires a running app and Chrome/Edge.
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const candidates = process.platform === "darwin" ? [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
] : [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
];
const executable = candidates.find(fs.existsSync);
if (!executable) {
  console.error("No supported Chrome or Edge executable found; UI smoke not run.");
  process.exit(1);
}

const port = 9300 + Math.floor(Math.random() * 500);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "originchain-ui-"));
const pageUrl = process.env.ORIGINCHAIN_UI_URL || "http://127.0.0.1:8000/";
const runFullDemo = process.env.ORIGINCHAIN_UI_FULL_DEMO === "1";
const browser = spawn(executable, ["--headless=new", "--disable-gpu", "--no-first-run",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function json(url, attempts = 40) {
  for (let index = 0; index < attempts; index += 1) {
    try { const response = await fetch(url); if (response.ok) return response.json(); } catch (_) { /* retry */ }
    await delay(250);
  }
  throw new Error(`Unable to reach ${url}`);
}

async function main() {
  const version = await json(`http://127.0.0.1:${port}/json/version`);
  if (!version.Browser) throw new Error("Browser debugging endpoint did not identify a browser");
  const targetResponse = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(pageUrl)}`, { method: "PUT" });
  const target = await targetResponse.json();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  const pending = new Map(); let sequence = 0; const errors = [];
  socket.addEventListener("message", ({ data }) => {
    const event = JSON.parse(data);
    if (event.id && pending.has(event.id)) {
      const item = pending.get(event.id); pending.delete(event.id);
      return event.error ? item.reject(new Error(event.error.message)) : item.resolve(event.result);
    }
    if (event.method === "Runtime.exceptionThrown") errors.push(event.params.exceptionDetails.text);
  });
  await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    sequence += 1; pending.set(sequence, { resolve, reject }); socket.send(JSON.stringify({ id: sequence, method, params }));
  });
  await send("Runtime.enable"); await send("Page.enable"); await delay(1800);
  const evaluated = await send("Runtime.evaluate", { returnByValue: true, expression: `(() => {
    const required = ["#access", "#loginForm", "#accountPanel", "#operationalApp", "#dashboard", "#overviewSummary", "#demoProgress", "#demoTools", "#demoAutofillButton", "#demoHoldButton", "#journey", "#materials", "#manufacturing", "#operations", "#consumer", "#materialForm", "#productForm", "#verifyForm", "#admin", "#readinessButton", "#tamperDialog", "#resetDialog", "#demoActionDialog"];
    const missing = required.filter((selector) => !document.querySelector(selector));
    return { title: document.title, h1: document.querySelector("h1")?.textContent, missing,
      sections: document.querySelectorAll("main section").length,
      chain: document.querySelector("#chainPill")?.textContent.trim(),
      loginVisible: !document.querySelector("#access").classList.contains("hidden"),
      operationalHidden: document.querySelector("#operationalApp").hidden,
      publicVerifyVisible: document.querySelector("#consumer").getClientRects().length > 0,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
  })()` });
  const result = evaluated.result.value;
  const interaction = await send("Runtime.evaluate", { returnByValue: true, awaitPromise: true, expression: `(async () => {
    const runFullDemo = ${JSON.stringify(runFullDemo)};
    const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
    const until = async (predicate, label, attempts = 160) => {
      for (let index = 0; index < attempts; index += 1) {
        if (predicate()) return;
        await pause(100);
      }
      throw new Error(\`Timed out waiting for \${label}\`);
    };
    const visible = (selector) => {
      const element = document.querySelector(selector);
      return Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== "hidden");
    };
    const login = async (username) => {
      document.querySelector("#loginUsername").value = username;
      document.querySelector("#loginPassword").value = "OriginDemo2026!";
      document.querySelector("#loginForm").requestSubmit();
      await pause(1400);
      const stages = [...document.querySelectorAll(".stage-tabs button")]
        .filter((button) => !button.hidden).map((button) => button.dataset.stage);
      const snapshot = {
        username,
        roleBadge: document.querySelector("#accountRole").textContent.trim(),
        loginHidden: document.querySelector("#access").classList.contains("hidden"),
        accountVisible: visible("#accountPanel"),
        materialsVisible: visible("#materials"),
        materialFormVisible: visible("#materialRegistrationPanel"),
        manufacturingVisible: visible("#manufacturing"),
        productFormVisible: visible("#productForm"),
        adminVisible: visible("#admin"),
        demoToolsVisible: visible("#demoTools"),
        demoHoldVisible: visible("#demoHoldButton"),
        readinessVisible: visible("#readinessButton"),
        stages,
      };
      document.querySelector("#logoutButton").click();
      await pause(150);
      snapshot.loggedOut = !document.querySelector("#access").classList.contains("hidden")
        && document.querySelector("#operationalApp").hidden;
      return snapshot;
    };
    document.querySelector('a[href="#consumer"]').click();
    await pause(100);
    document.querySelector("#verifyCode").value = "OC-LUX-SERUM-0001";
    document.querySelector("#verifyForm button").click();
    await pause(900);
    const consumerText = document.querySelector("#consumerResult").textContent.replace(/\\s+/g, " ").trim();
    const publicVerification = {
      consumerResult: consumerText,
      consumerHasQcControls: Boolean(document.querySelector("#consumerResult select, #consumerResult .check-row, #consumerResult .save-check")),
      consumerLeaksWallet: /0x[a-fA-F0-9]{40}/.test(consumerText),
      consumerLeaksStorageName: consumerText.includes("stored_filename"),
    };
    const roles = [];
    for (const username of ["supplier", "manufacturer", "distributor", "retailer", "admin"]) {
      roles.push(await login(username));
    }
    let fullDemoResult = null;
    if (runFullDemo) {
      const signIn = async (username) => {
        document.querySelector("#loginUsername").value = username;
        document.querySelector("#loginPassword").value = "OriginDemo2026!";
        document.querySelector("#loginButton").click();
        await until(() => state.user?.username === username && document.querySelector("#loginButton").getAttribute("aria-busy") !== "true", \`\${username} login\`);
      };
      const signOut = async () => {
        document.querySelector("#logoutButton").click();
        await until(() => !state.user, "logout");
      };
      const confirmDialog = async (openSelector, confirmSelector) => {
        document.querySelector(openSelector).click();
        await until(() => document.querySelector(confirmSelector).closest("dialog").open, \`\${openSelector} dialog\`);
        document.querySelector(confirmSelector).click();
      };

      await signIn("admin");
      document.querySelector("#readinessButton").click();
      await until(() => document.querySelector("#readinessResult").textContent.includes("READY"), "readiness result");
      const readiness = document.querySelector("#readinessResult").textContent.includes("READY");
      await confirmDialog("#resetButton", "#confirmReset");
      await until(() => state.products.length === 0 && state.materials.length === 0, "fresh demo reset");
      await signOut();

      await signIn("supplier");
      await confirmDialog("#demoAutofillButton", "#confirmDemoAction");
      await until(() => state.materials[0]?.quality_status === "APPROVED", "supplier approval");
      const supplierStatus = state.materials[0].quality_status;
      await signOut();

      await signIn("manufacturer");
      await confirmDialog("#demoAutofillButton", "#confirmDemoAction");
      await until(() => state.activeSummary?.stage === "MANUFACTURER" && state.activeSummary?.status === "APPROVED", "manufacturer approval");
      const productCode = state.products[0].product_code;
      document.querySelector("#transferDistributor").click();
      await until(() => state.products[0]?.current_stage === "DISTRIBUTOR" && document.querySelector("#transferDistributor").getAttribute("aria-busy") !== "true", "Distributor transfer");
      await signOut();

      await signIn("distributor");
      await confirmDialog("#demoAutofillButton", "#confirmDemoAction");
      await until(() => state.activeSummary?.stage === "DISTRIBUTOR" && state.activeSummary?.status === "APPROVED", "Distributor approval");
      document.querySelector("#transferRetailer").click();
      await until(() => state.products[0]?.current_stage === "RETAILER" && document.querySelector("#transferRetailer").getAttribute("aria-busy") !== "true", "Retailer transfer");
      await signOut();

      await signIn("retailer");
      await confirmDialog("#demoHoldButton", "#confirmDemoAction");
      await until(() => state.products[0]?.final_sale_status === "HOLD", "Retail HOLD");
      const holdStatus = state.products[0].final_sale_status;
      await confirmDialog("#demoAutofillButton", "#confirmDemoAction");
      await until(() => state.products[0]?.final_sale_status === "APPROVED_FOR_SALE", "Retail correction");
      const finalSaleStatus = state.products[0].final_sale_status;
      await signOut();

      document.querySelector("#verifyCode").value = productCode;
      state.verification = null;
      document.querySelector("#verifyForm button").click();
      await until(() => state.verification?.status === "GENUINE", "genuine consumer result");
      const genuine = state.verification.status;

      await signIn("admin");
      await confirmDialog("#tamperButton", "#confirmTamper");
      await until(() => state.verification?.status === "SUSPICIOUS", "tampered verification");
      await signOut();
      state.verification = null;
      document.querySelector("#verifyForm button").click();
      await until(() => state.verification?.status === "SUSPICIOUS", "public suspicious result");
      fullDemoResult = {
        readiness,
        supplierStatus,
        productCode,
        holdStatus,
        finalSaleStatus,
        genuine,
        suspicious: state.verification.status,
      };
    }
    document.querySelector("#loginUsername").value = "supplier";
    document.querySelector("#loginPassword").value = "OriginDemo2026!";
    document.querySelector("#loginForm").requestSubmit();
    await pause(1200);
    state.token = "malformed.saved.token";
    try { await api("/api/products"); } catch (_) { /* expected invalid-token response */ }
    await pause(100);
    return {
      hash: location.hash,
      publicVerification,
      roles,
      fullDemoResult,
      invalidTokenReturnedToLogin: !document.querySelector("#access").classList.contains("hidden")
        && document.querySelector("#operationalApp").hidden
        && localStorage.getItem("originchain_demo_access_token") === null,
    };
  })()` });
  if (interaction.exceptionDetails) {
    throw new Error(JSON.stringify(interaction.exceptionDetails));
  }
  const loginForReload = await send("Runtime.evaluate", { returnByValue: true, awaitPromise: true, expression: `(async () => {
    document.querySelector("#loginUsername").value = "supplier";
    document.querySelector("#loginPassword").value = "OriginDemo2026!";
    document.querySelector("#loginButton").click();
    for (let index = 0; index < 100 && state.user?.username !== "supplier"; index += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return Boolean(state.user?.username === "supplier" && localStorage.getItem("originchain_demo_access_token"));
  })()` });
  if (!loginForReload.result.value) throw new Error("Could not establish the reload-persistence session");
  await send("Page.reload");
  await delay(2200);
  const reloadCheck = await send("Runtime.evaluate", { returnByValue: true, awaitPromise: true, expression: `(async () => {
    for (let index = 0; index < 120 && state.user?.username !== "supplier"; index += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return {
      restored: state.user?.username === "supplier",
      role: state.user?.role,
      activeStage: state.activeStage,
      operationalVisible: !document.querySelector("#operationalApp").hidden,
    };
  })()` });
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await delay(350);
  const mobile = await send("Runtime.evaluate", { returnByValue: true, expression: `({
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    journeyColumns: getComputedStyle(document.querySelector("#journey")).gridTemplateColumns,
    actionWidth: document.querySelector("#verifyForm button")?.getBoundingClientRect().width,
  })` });
  const interactionResult = interaction.result.value;
  const mobileResult = mobile.result.value;
  const reloadResult = reloadCheck.result.value;
  const publicVerification = interactionResult.publicVerification;
  const role = Object.fromEntries(interactionResult.roles.map((item) => [item.username, item]));
  const expectedStages = {
    supplier: ["RAW_MATERIAL_SUPPLIER"],
    manufacturer: ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER"],
    distributor: ["MANUFACTURER", "DISTRIBUTOR"],
    retailer: ["MANUFACTURER", "DISTRIBUTOR", "RETAILER"],
    admin: ["RAW_MATERIAL_SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER"],
  };
  const roleFailure = interactionResult.roles.some((item) => !item.loginHidden || !item.accountVisible
    || !item.loggedOut || item.roleBadge.length === 0
    || JSON.stringify(item.stages) !== JSON.stringify(expectedStages[item.username]));
  const failed = result.missing.length || errors.length || result.horizontalOverflow
    || !result.loginVisible || !result.operationalHidden || !result.publicVerifyVisible
    || interactionResult.hash !== "#consumer" || mobileResult.horizontalOverflow
    || !reloadResult.restored || reloadResult.role !== "RAW_MATERIAL_SUPPLIER"
    || reloadResult.activeStage !== "RAW_MATERIAL_SUPPLIER" || !reloadResult.operationalVisible
    || roleFailure || !interactionResult.invalidTokenReturnedToLogin
    || !role.supplier.materialsVisible || !role.supplier.materialFormVisible || role.supplier.manufacturingVisible
    || !role.manufacturer.materialsVisible || role.manufacturer.materialFormVisible
    || !role.manufacturer.manufacturingVisible || !role.manufacturer.productFormVisible
    || role.distributor.materialsVisible || !role.distributor.manufacturingVisible || role.distributor.productFormVisible
    || role.retailer.materialsVisible || !role.retailer.manufacturingVisible || role.retailer.productFormVisible
    || !role.supplier.demoToolsVisible || !role.manufacturer.demoToolsVisible
    || !role.distributor.demoToolsVisible || !role.retailer.demoToolsVisible
    || role.supplier.demoHoldVisible || role.manufacturer.demoHoldVisible || role.distributor.demoHoldVisible
    || !role.retailer.demoHoldVisible || role.admin.demoToolsVisible
    || !role.admin.adminVisible || !role.admin.readinessVisible || role.admin.productFormVisible
    || publicVerification.consumerHasQcControls || publicVerification.consumerLeaksWallet
    || publicVerification.consumerLeaksStorageName
    || (runFullDemo && (!interactionResult.fullDemoResult?.readiness
      || interactionResult.fullDemoResult.supplierStatus !== "APPROVED"
      || interactionResult.fullDemoResult.holdStatus !== "HOLD"
      || interactionResult.fullDemoResult.finalSaleStatus !== "APPROVED_FOR_SALE"
      || interactionResult.fullDemoResult.genuine !== "GENUINE"
      || interactionResult.fullDemoResult.suspicious !== "SUSPICIOUS"));
  if (failed) {
    throw new Error(JSON.stringify({ result, interaction: interactionResult, reload: reloadResult, mobile: mobileResult, errors }));
  }
  console.log(JSON.stringify({ page: result, interaction: interactionResult, reload: reloadResult, mobile: mobileResult }, null, 2));
  socket.close();
}

main().finally(async () => {
  if (!browser.killed) browser.kill();
  await delay(300);
  fs.rmSync(profile, { recursive: true, force: true, maxRetries: 4 });
}).catch((error) => { console.error(error); process.exitCode = 1; });
