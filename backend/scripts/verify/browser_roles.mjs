import { chromium } from "../../../frontend/node_modules/@playwright/test/index.mjs";
const frontend = process.env.FRONTEND_BASE_URL ?? "http://localhost:5173";
const api = process.env.API_BASE_URL ?? "http://localhost:8000";
for (const base of [frontend, api]) {
  if (!["localhost", "127.0.0.1"].includes(new URL(base).hostname))
    throw new Error("Synthetic local stack required");
}
if (!process.env.DEMO_PASSWORD) throw new Error("DEMO_PASSWORD required");
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : {}),
});
const results = [];
try {
  for (const [role, path] of [
    ["dispatcher", "/dispatcher/orders"],
    ["loader", "/loader/queue"],
    ["driver", "/driver/home"],
    ["manager", "/store-manager/overview"],
    ["admin", "/administration/team"],
  ]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    const failures = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("response", (r) => {
      if (new URL(r.url()).origin === new URL(api).origin && r.status() >= 400)
        failures.push({ path: new URL(r.url()).pathname, status: r.status() });
    });
    await page.goto(frontend + "/login");
    await page.getByLabel("Email or employee ID").fill(role);
    await page
      .getByLabel("Password", { exact: true })
      .fill(process.env.DEMO_PASSWORD);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.waitForURL("**" + path, { timeout: 20000 });
    await page.waitForLoadState("networkidle");
    if (errors.length || failures.length)
      throw new Error(JSON.stringify({ role, errors, failures }));
    results.push({
      role,
      path,
      uncaught_errors: errors.length,
      api_errors: failures.length,
    });
    await context.close();
  }
  console.log(JSON.stringify({ browser_role_logins: results }));
} finally {
  await browser.close();
}
