// Optional cross-platform browser smoke. Requires a running app and Chrome/Edge.
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const candidates = process.platform === "darwin" ? [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
] : [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];
const executable = candidates.find(fs.existsSync);
if (!executable) {
  console.error("No supported Chrome or Edge executable found; UI smoke not run.");
  process.exit(1);
}

const port = 9300 + Math.floor(Math.random() * 500);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "originchain-ui-"));
const pageUrl = process.env.ORIGINCHAIN_UI_URL || "http://127.0.0.1:8000/";
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
    const required = ["#access", "#loginForm", "#accountPanel", "#operationalApp", "#dashboard", "#overviewSummary", "#journey", "#materials", "#manufacturing", "#operations", "#consumer", "#materialForm", "#productForm", "#verifyForm", "#admin", "#tamperDialog", "#resetDialog"];
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
    const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
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
    document.querySelector("#verifyForm").requestSubmit();
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
      invalidTokenReturnedToLogin: !document.querySelector("#access").classList.contains("hidden")
        && document.querySelector("#operationalApp").hidden
        && localStorage.getItem("originchain_demo_access_token") === null,
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
    || roleFailure || !interactionResult.invalidTokenReturnedToLogin
    || !role.supplier.materialsVisible || !role.supplier.materialFormVisible || role.supplier.manufacturingVisible
    || !role.manufacturer.materialsVisible || role.manufacturer.materialFormVisible
    || !role.manufacturer.manufacturingVisible || !role.manufacturer.productFormVisible
    || role.distributor.materialsVisible || !role.distributor.manufacturingVisible || role.distributor.productFormVisible
    || role.retailer.materialsVisible || !role.retailer.manufacturingVisible || role.retailer.productFormVisible
    || !role.admin.adminVisible || role.admin.productFormVisible
    || publicVerification.consumerHasQcControls || publicVerification.consumerLeaksWallet
    || publicVerification.consumerLeaksStorageName;
  if (failed) {
    throw new Error(JSON.stringify({ result, interaction: interactionResult, mobile: mobileResult, errors }));
  }
  console.log(JSON.stringify({ page: result, interaction: interactionResult, mobile: mobileResult }, null, 2));
  socket.close();
}

main().finally(async () => {
  if (!browser.killed) browser.kill();
  await delay(300);
  fs.rmSync(profile, { recursive: true, force: true, maxRetries: 4 });
}).catch((error) => { console.error(error); process.exitCode = 1; });
