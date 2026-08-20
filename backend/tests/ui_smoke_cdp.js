const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

const chromePath = chromeCandidates.find((candidate) => fs.existsSync(candidate));
if (!chromePath) {
  console.error("No Chrome or Edge executable found for UI smoke.");
  process.exit(1);
}

const port = 9300 + Math.floor(Math.random() * 500);
const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "originchain-chrome-"));
const pageUrl = process.env.ORIGINCHAIN_UI_URL || "http://127.0.0.1:8000/";
const errors = [];

const chrome = spawn(chromePath, [
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${userDataDir}`,
  "about:blank",
], { stdio: "ignore" });

async function cleanup() {
  if (!chrome.killed) {
    chrome.kill();
    await delay(500);
  }
  try {
    fs.rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  } catch (_error) {
    // Chrome can hold profile locks for a moment on Windows; the temp directory is disposable.
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getJson(url, attempts = 30) {
  let lastError;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch (error) {
      lastError = error;
    }
    await delay(250);
  }
  throw lastError || new Error(`Unable to fetch ${url}`);
}

async function openCdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  const pending = new Map();
  let id = 0;

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
      return;
    }

    if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
      errors.push(`console.error: ${message.params.args.map((arg) => arg.value || arg.description).join(" ")}`);
    }
    if (message.method === "Runtime.exceptionThrown") {
      errors.push(`exception: ${message.params.exceptionDetails.text}`);
    }
  });

  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });

  return {
    send(method, params = {}) {
      id += 1;
      ws.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    close() {
      ws.close();
    },
  };
}

async function main() {
  try {
    await getJson(`http://127.0.0.1:${port}/json/version`);
    const response = await fetch(
      `http://127.0.0.1:${port}/json/new?${encodeURIComponent(pageUrl)}`,
      { method: "PUT" }
    );
    if (!response.ok) {
      throw new Error(`Unable to create Chrome target: HTTP ${response.status}`);
    }
    const page = await response.json();
    const cdp = await openCdp(page.webSocketDebuggerUrl);

    await cdp.send("Runtime.enable");
    await cdp.send("Page.enable");
    await delay(2000);

    const result = await cdp.send("Runtime.evaluate", {
      awaitPromise: true,
      returnByValue: true,
      expression: `
        (async () => {
          const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
          const text = (selector) => document.querySelector(selector)?.textContent || "";
          const waitFor = async (predicate, label, timeout = 20000) => {
            const started = Date.now();
            while (Date.now() - started < timeout) {
              if (predicate()) return true;
              await delay(200);
            }
            throw new Error("Timed out waiting for " + label);
          };
          const click = async (selector) => {
            const element = document.querySelector(selector);
            if (!element) throw new Error("Missing element " + selector);
            await waitFor(() => !element.disabled, selector + " enabled");
            element.click();
            await delay(100);
          };
          const visibleEnabled = (selector) => {
            const element = document.querySelector(selector);
            return element && !element.classList.contains("hidden") && !element.disabled;
          };

          await waitFor(() => text("#chainStatus").includes("Connected"), "blockchain status");
          await click("#resetButton");
          await waitFor(() => text("#verificationResult").includes("Local metadata cleared"), "reset");
          await click("#registerButton");
          await waitFor(() => text("#registrationResult").includes("Product registered on blockchain"), "registration");
          await waitFor(() => visibleEnabled("#transferDistributorButton"), "transfer distributor button");
          await click("#transferDistributorButton");
          await waitFor(() => text("#transferLog").includes("MANUFACTURER") && text("#transferLog").includes("DISTRIBUTOR"), "transfer distributor");
          await waitFor(() => visibleEnabled("#transferRetailerButton"), "transfer retailer button");
          await click("#transferRetailerButton");
          await waitFor(() => text("#transferLog").includes("DISTRIBUTOR") && text("#transferLog").includes("RETAILER"), "transfer retailer");
          await click("#verifyButton");
          await waitFor(() => text("#verificationResult").includes("Genuine Product") && text("#verificationResult").includes("RETAILER"), "genuine verification");

          document.querySelector("#verifyCode").value = "OC-UNKNOWN-9999";
          await click("#verifyButton");
          await waitFor(() => text("#verificationResult").includes("Product not found"), "unknown verification");

          document.querySelector("#verifyCode").value = document.querySelector("#productCode").value;
          await click("#verifyButton");
          await waitFor(() => text("#verificationResult").includes("Genuine Product"), "restore genuine verification");
          await click("#tamperButton");
          await waitFor(() => text("#verificationResult").includes("Suspicious"), "tamper suspicious verification");

          return {
            title: document.querySelector("h1").textContent,
            chainStatus: text("#chainStatus"),
            contract: text("#contractAddress"),
            registration: text("#registrationResult"),
            transfers: text("#transferLog"),
            verification: text("#verificationResult"),
            tamper: text("#tamperResult"),
          };
        })()
      `,
    });

    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    }

    cdp.close();

    if (errors.length) {
      throw new Error(`Browser console/runtime errors: ${errors.join("; ")}`);
    }

    console.log(JSON.stringify(result.result.value, null, 2));
  } finally {
    await cleanup();
  }
}

main().catch((error) => {
  console.error(error);
  cleanup().finally(() => {
    process.exit(1);
  });
});
