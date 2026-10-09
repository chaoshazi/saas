// Capture UI screenshots of the AICRM SaaS console for the README.
//
// Usage (dev servers must be running):
//   node scripts/capture-screenshots.mjs
//   BASE_URL=http://localhost:5173 OUT_DIR=docs/screenshots UI_LANG=en node scripts/capture-screenshots.mjs
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:5173";
const OUT_DIR = process.env.OUT_DIR ?? "docs/screenshots";
const EMAIL = process.env.DEMO_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.DEMO_PASSWORD ?? "Admin123456!";
const LANG = process.env.UI_LANG ?? "zh";
// Project card opened for the kanban/board screenshot.
const BOARD_PROJECT = process.env.BOARD_PROJECT ?? "AICRM 客户管理系统";

const PAGES = [
  ["dashboard", "/dashboard"],
  ["projects", "/projects"],
  ["board", null], // resolved by clicking the BOARD_PROJECT card
  ["documents", "/documents"],
  ["teams", "/teams"],
  ["notifications", "/notifications"],
  ["billing", "/billing"],
  ["settings", "/settings"],
  ["admin-users", "/admin/users"],
  ["admin-audit", "/admin/audit"],
];

async function settle(page) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
}

async function shoot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  const size = (fs.statSync(file).size / 1024).toFixed(0);
  console.log(`  captured ${file} (${size} KB)`);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    locale: LANG === "en" ? "en-US" : "zh-CN",
  });
  const page = await context.newPage();
  page.on("pageerror", (err) => console.warn("  page error:", err.message));

  console.log("Signing in...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate((lang) => localStorage.setItem("locale", lang), LANG);
  await page.reload({ waitUntil: "domcontentloaded" });
  await settle(page);
  await shoot(page, "login");

  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard", { timeout: 20000 });
  await settle(page);

  for (const [name, url] of PAGES) {
    if (!url) {
      const card = page.locator("div.cursor-pointer").filter({ hasText: BOARD_PROJECT }).first();
      if ((await card.count()) === 0) {
        console.warn(`  skipping board: no card matching "${BOARD_PROJECT}"`);
        continue;
      }
      await card.click();
      await page.waitForURL(/\/projects\/\d+/, { timeout: 15000 });
      await settle(page);
      await shoot(page, name);
      continue;
    }
    console.log(`Visiting ${url}`);
    await page.goto(`${BASE_URL}${url}`, { waitUntil: "domcontentloaded" });
    await settle(page);
    await shoot(page, name);
  }

  await browser.close();
  console.log(`Done. Screenshots in ${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});