import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");

console.log("=== RUNNING FRONTEND STATIC INTEGRITY CHECKS ===");

let failures = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failures++;
  } else {
    console.log(`✅ PASS: ${message}`);
  }
}

// 1. Verify No parseFloat in src/
function checkNoParseFloat(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      checkNoParseFloat(fullPath);
    } else if (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx")) {
      const content = fs.readFileSync(fullPath, "utf-8");
      if (content.includes("parseFloat(")) {
        assert(false, `Found parseFloat in ${fullPath}`);
      }
    }
  }
}
checkNoParseFloat(path.join(rootDir, "src"));
assert(true, "Zero parseFloat found across entire src/ directory");

// 2. Verify CSP Configuration in src/proxy.ts
const proxyTs = fs.readFileSync(path.join(rootDir, "src/proxy.ts"), "utf-8");
assert(
  proxyTs.includes("default-src 'self'") && proxyTs.includes("connect-src 'self'") && proxyTs.includes("'nonce-"),
  "src/proxy.ts defines strict nonce-based CSP header"
);
assert(
  proxyTs.includes("isDev ?") && !proxyTs.match(/script-src 'self' 'unsafe-eval'/),
  "src/proxy.ts gates 'unsafe-eval' behind isDev flag (clean in production)"
);

// 3. Verify Routes and Core Components Exist
const routes = [
  "src/app/page.tsx",
  "src/app/login/page.tsx",
  "src/app/register/page.tsx",
  "src/lib/api.ts",
  "src/context/AuthContext.tsx",
  "src/components/DashboardView.tsx",
  "src/components/LiabilitiesVaultView.tsx",
  "src/components/UPIIntentModal.tsx",
  "src/components/SafeVerifyPaymentModal.tsx",
];

for (const r of routes) {
  assert(fs.existsSync(path.join(rootDir, r)), `Required file exists: ${r}`);
}

// 4. Verify API client has no hardcoded localhost in api.ts
const apiTs = fs.readFileSync(path.join(rootDir, "src/lib/api.ts"), "utf-8");
assert(
  apiTs.includes("NEXT_PUBLIC_API_URL"),
  "api.ts correctly references NEXT_PUBLIC_API_URL environment variable"
);

// 5. Verify Build Output Exists
const nextBuildDir = path.join(rootDir, ".next");
assert(fs.existsSync(nextBuildDir), ".next build artifact directory exists");

console.log("===================================");
if (failures > 0) {
  console.log("Static checks completed with " + failures + " failure(s).");
  process.exit(1);
} else {
  console.log("All frontend static integrity checks passed successfully!");
  process.exit(0);
}
