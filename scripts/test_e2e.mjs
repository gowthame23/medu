import { chromium } from "playwright";
import { spawn, execSync } from "child_process";

function killPid(pid) {
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /PID ${pid} /T /F`, { stdio: "ignore" });
    } else {
      process.kill(pid, "SIGKILL");
    }
  } catch {}
}

async function waitForHttp(url, timeoutMs = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.status === 200) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 600));
  }
  throw new Error(`Timeout waiting for ${url} after ${timeoutMs}ms`);
}

async function runE2E() {
  console.log("==================================================");
  console.log("=== RUNNING REAL PLAYWRIGHT END-TO-END TEST ===");
  console.log("==================================================");

  console.log("[1/6] Starting FastAPI backend on :8000...");
  const backend = spawn("python", ["-m", "uvicorn", "app.main:app", "--port", "8000"], {
    cwd: "./backend",
    shell: true,
  });

  console.log("[2/6] Starting Next.js production server on :3000...");
  const frontend = spawn("npm", ["run", "start"], {
    shell: true,
  });

  let browser;
  try {
    console.log("[3/6] Waiting for backend (/health) and frontend (/login)...");
    await waitForHttp("http://localhost:8000/health", 25000);
    console.log("  -> Backend is healthy.");
    await waitForHttp("http://localhost:3000/login", 25000);
    console.log("  -> Frontend is ready.");

    // Launch Playwright browser
    console.log("[4/6] Launching Playwright browser...");
    try {
      browser = await chromium.launch({ channel: "msedge", headless: true });
    } catch {
      browser = await chromium.launch({ headless: true });
    }

    const context = await browser.newContext();
    const page = await context.newPage();

    // CSP and Console Event Tracking across entire journey
    const consoleLogs = [];
    const ignoredConsoleErrors = [];
    const unexpectedErrors = [];
    const cspViolations = [];

    // Inject securitypolicyviolation DOM listener
    await page.addInitScript(() => {
      window.__cspViolations = [];
      document.addEventListener("securitypolicyviolation", (e) => {
        window.__cspViolations.push({
          blockedURI: e.blockedURI,
          violatedDirective: e.violatedDirective,
          originalPolicy: e.originalPolicy,
          sourceFile: e.sourceFile,
          lineNumber: e.lineNumber,
        });
      });
    });

    page.on("console", (msg) => {
      const text = msg.text();
      consoleLogs.push(`[${msg.type().toUpperCase()}] ${text}`);
      if (msg.type() === "error") {
        if (
          text.includes("Content Security Policy") ||
          text.includes("violates") ||
          text.includes("CSP")
        ) {
          cspViolations.push(`Console CSP Error: ${text}`);
        } else if (text.includes("401") || text.includes("Unauthorized")) {
          // Expected: on initial unauthenticated mount, AuthContext invokes silent refresh
          ignoredConsoleErrors.push({
            message: text,
            reason: "Expected unauthenticated 401 on initial mount before session cookie is established.",
          });
        } else {
          unexpectedErrors.push(text);
        }
      }
    });

    page.on("pageerror", (err) => {
      if (
        err.message.includes("Content Security Policy") ||
        err.message.includes("violates") ||
        err.message.includes("CSP")
      ) {
        cspViolations.push(`PageError CSP: ${err.message}`);
      } else {
        unexpectedErrors.push(err.message);
      }
    });

    const testTimestamp = Date.now();
    const testEmail = `e2e_user_${testTimestamp}@test.com`;
    const testPassword = "Password123456!";
    const testName = `Playwright User ${testTimestamp.toString().slice(-4)}`;

    // STEP 1: Registration
    console.log(`[5/6] Step 1: Registering new user (${testEmail})...`);
    await page.goto("http://localhost:3000/register", { waitUntil: "load" });
    await page.fill('input[type="text"]', testName);
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL("http://localhost:3000/", { timeout: 10000 });
    console.log("  -> Registered and redirected to dashboard successfully.");

    // STEP 2: Verify Dashboard renders
    console.log("  -> Step 2: Verifying dashboard render and profile display...");
    await page.waitForSelector(`text=${testName}`, { timeout: 8000 });
    console.log("  -> User profile confirmed on dashboard.");

    // STEP 3: Logout to test login flow
    console.log("  -> Step 3: Testing logout...");
    await page.click('button[title="Sign out"]');
    await page.waitForURL("http://localhost:3000/login", { timeout: 8000 });
    console.log("  -> Successfully logged out and redirected to /login.");

    // STEP 4: Login with newly created credentials
    console.log("  -> Step 4: Logging back in with credentials...");
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL("http://localhost:3000/", { timeout: 10000 });
    await page.waitForSelector(`text=${testName}`, { timeout: 8000 });
    console.log("  -> Successfully logged in and landed on dashboard.");

    // STEP 5: Add Personal Bill to Tomorrow's Radar
    console.log("  -> Step 5: Adding a personal bill reminder...");
    await page.click('button[title="Add reminder"]');
    await page.waitForSelector("text=Add Radar Reminder", { timeout: 5000 });

    const billTitle = `E2E Internet ${testTimestamp.toString().slice(-4)}`;
    const billAmount = "1200.00";
    await page.fill('input[placeholder="e.g. Electricity BESCOM, WiFi Fiber"]', billTitle);
    await page.fill('input[placeholder="2450.00"]', billAmount);
    await page.fill('input[placeholder="e.g. CA 4928120"]', "ACC-992182");
    await page.click('button[type="submit"]');

    // Wait for modal to close and bill to appear in list
    await page.waitForSelector(`text=${billTitle}`, { timeout: 8000 });
    console.log(`  -> Bill '${billTitle}' added and visible in Radar.`);

    // STEP 6: Pay the bill via Sandbox UPI
    console.log("  -> Step 6: Paying bill via Sandbox UPI intent...");
    // Find the bill card and click Pay via UPI
    const billCard = page.locator("div.rounded-2xl", { hasText: billTitle });
    const payBtn = billCard.locator('button:has-text("Pay via UPI")');
    await payBtn.click();

    // Verify UPI modal opens
    await page.waitForSelector("text=UPI 1-Tap Payment", { timeout: 5000 });
    console.log("  -> UPI payment sheet open. Executing payment...");

    // Click execute payment
    const executeBtn = page.locator('button:has-text("Execute Payment")');
    await executeBtn.click();

    // Wait for payment confirmation
    await page.waitForSelector("text=Payment Verified & Settled", { timeout: 8000 });
    console.log("  -> Sandbox payment executed and confirmed by provider.");

    // Wait for modal to auto-close and dashboard to refresh
    await page.waitForTimeout(2500);

    // Switch to "All" radar filter to view all bills including settled/paid ones
    console.log("  -> Switching to 'All' bills view to inspect settled state...");
    await page.click('button:has-text("All")');
    await page.waitForTimeout(500);

    // Verify bill now shows Paid & Verified
    const verifiedStatus = billCard.locator("text=Paid & Verified");
    await verifiedStatus.waitFor({ state: "visible", timeout: 8000 });
    console.log("  -> Bill card successfully updated to 'Paid & Verified'!");

    // STEP 7: Final Logout
    console.log("  -> Step 7: Final sign out...");
    await page.click('button[title="Sign out"]');
    await page.waitForURL("http://localhost:3000/login", { timeout: 8000 });
    console.log("  -> Successfully signed out at end of scenario.");

    // Retrieve any DOM securitypolicyviolation events captured
    const domCspEvents = await page.evaluate(() => window.__cspViolations || []);
    for (const evt of domCspEvents) {
      cspViolations.push(
        `DOM CSP Violation: directive=${evt.violatedDirective}, blockedURI=${evt.blockedURI}, file=${evt.sourceFile}:${evt.lineNumber}`
      );
    }

    console.log("\n=== CSP & JOURNEY INTEGRITY AUDIT ===");
    console.log(`Total Console Messages Captured: ${consoleLogs.length}`);
    console.log(`Total Ignored Errors (Allowed): ${ignoredConsoleErrors.length}`);
    ignoredConsoleErrors.forEach((item, idx) => {
      console.log(`  [Ignored #${idx + 1}] "${item.message}" -> Reason: ${item.reason}`);
    });
    console.log(`Total Unexpected Errors: ${unexpectedErrors.length}`);
    if (unexpectedErrors.length > 0) {
      unexpectedErrors.forEach((e) => console.log(`  [Unexpected Error]: ${e}`));
    }
    console.log(`Total CSP Violations Detected: ${cspViolations.length}`);

    if (cspViolations.length > 0) {
      console.error("\n❌ CRITICAL: CSP VIOLATIONS DETECTED DURING USER JOURNEY:");
      cspViolations.forEach((v) => console.error(`  - ${v}`));
      throw new Error(`Test failed with ${cspViolations.length} CSP violation(s)`);
    } else {
      console.log("✅ ZERO CSP VIOLATIONS across entire end-to-end user journey!");
    }

    console.log("\n==================================================");
    console.log("🎉 ALL E2E USER JOURNEY STEPS PASSED SUCCESSFULLY!");
    console.log("==================================================");
  } finally {
    if (browser) await browser.close();
    console.log("[6/6] Shutting down child backend and frontend processes...");
    killPid(backend.pid);
    killPid(frontend.pid);
  }
}

runE2E().catch((err) => {
  console.error("\n❌ E2E TEST FAILED:", err);
  process.exit(1);
});
