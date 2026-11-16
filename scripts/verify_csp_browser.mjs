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

async function run() {
  console.log("=== STARTING BACKEND (FASTAPI) ===");
  const backend = spawn("python", ["-m", "uvicorn", "app.main:app", "--port", "8000"], {
    cwd: "./backend",
    shell: true,
  });

  console.log("=== STARTING FRONTEND (NEXT PRODUCTION) ===");
  const frontend = spawn("npm", ["run", "start"], {
    shell: true,
  });

  // Give servers time to spin up
  await new Promise((r) => setTimeout(r, 6000));

  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const consoleErrors = [];
  const cspViolations = [];
  const allConsole = [];

  page.on("console", (msg) => {
    allConsole.push(`[${msg.type().toUpperCase()}] ${msg.text()}`);
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
      if (
        msg.text().includes("Content Security Policy") ||
        msg.text().includes("violates") ||
        msg.text().includes("CSP")
      ) {
        cspViolations.push(msg.text());
      }
    }
  });

  page.on("pageerror", (err) => {
    consoleErrors.push(err.message);
    if (
      err.message.includes("Content Security Policy") ||
      err.message.includes("violates") ||
      err.message.includes("CSP")
    ) {
      cspViolations.push(err.message);
    }
  });

  console.log("--> Navigating to http://localhost:3000/login");
  const loginRes = await page.goto("http://localhost:3000/login", { waitUntil: "load" });
  console.log(`Login HTTP Status: ${loginRes?.status()}`);

  console.log("--> Navigating to http://localhost:3000/register");
  const regRes = await page.goto("http://localhost:3000/register", { waitUntil: "load" });
  console.log(`Register HTTP Status: ${regRes?.status()}`);

  // Test full register and login flow in browser
  console.log("--> Testing registration in browser");
  await page.goto("http://localhost:3000/register", { waitUntil: "load" });
  const testEmail = `csp_user_${Date.now()}@test.com`;
  await page.fill('input[type="text"]', "CSP Test User");
  await page.fill('input[type="email"]', testEmail);
  await page.fill('input[type="password"]', "Password123456!");
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard /
  await page.waitForTimeout(3000);
  console.log(`Current URL after registration: ${page.url()}`);

  await browser.close();

  killPid(backend.pid);
  killPid(frontend.pid);

  console.log("\n=== CSP & BROWSER VERIFICATION REPORT ===");
  console.log(`Total Console Messages: ${allConsole.length}`);
  console.log(`Total Console Errors: ${consoleErrors.length}`);
  console.log(`Total CSP Violations: ${cspViolations.length}`);

  if (cspViolations.length > 0) {
    console.error("❌ VERBATIM CSP VIOLATIONS DETECTED:");
    cspViolations.forEach((v) => console.error(`  - ${v}`));
    process.exit(1);
  } else {
    console.log("✅ ZERO CSP VIOLATIONS. All scripts loaded cleanly.");
    if (consoleErrors.length > 0) {
      console.log("Non-CSP Console errors captured:");
      consoleErrors.forEach((e) => console.log(`  - ${e}`));
    }
    process.exit(0);
  }
}

run().catch((e) => {
  console.error("Test execution failed:", e);
  process.exit(1);
});
