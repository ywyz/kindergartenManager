"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const baseUrl = process.env.THEME_BASE_URL;
const adminPassword = process.env.THEME_ADMIN_PASSWORD;
const teacherPassword = process.env.THEME_TEACHER_PASSWORD;
if (!baseUrl || !adminPassword || !teacherPassword) {
  throw new Error("theme browser acceptance requires synthetic runtime inputs");
}
const baseUrlProtocol = new URL(baseUrl).protocol;
const baseUrlHostname = new URL(baseUrl).hostname;
const loopbackHosts = ["127.0.0.1", "localhost", "[::1]"];
if (baseUrlProtocol !== "http:" || !loopbackHosts.includes(baseUrlHostname)) {
  throw new Error("theme browser acceptance is confined to an HTTP loopback origin");
}
const { chromium } = require("playwright-core");

const root = path.resolve(__dirname, "..");
const evidenceDir = path.join(root, "evidence");
fs.mkdirSync(evidenceDir, { recursive: true });
const storageKey = "kindergarten-manager.theme.mode.v1";

const sha256 = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");

async function login(page, username, password) {
  await page.goto(`${baseUrl}/login`);
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await page.waitForURL(`${baseUrl}/home`);
  await page.getByRole("button", { name: "白天模式" }).waitFor();
  await page.waitForFunction((key) => localStorage.getItem(key) !== null, storageKey);
}

async function mode(page) {
  return page.evaluate((key) => ({
    stored: localStorage.getItem(key),
    dataset: document.body.dataset.themeMode,
    dark: document.body.classList.contains("body--dark"),
  }), storageKey);
}

async function colors(page) {
  return page.evaluate(() => {
    const style = (selector) => getComputedStyle(document.querySelector(selector));
    const body = style("body");
    const header = style(".theme-header");
    const drawer = style(".theme-drawer");
    const selected = document.querySelector(".theme-menu-item-selected");
    return {
      bodyBackground: body.backgroundColor,
      bodyText: body.color,
      headerBackground: header.backgroundColor,
      headerBorder: header.borderBottomColor,
      drawerBackground: drawer.backgroundColor,
      drawerText: drawer.color,
      drawerBorder: drawer.borderRightColor,
      selectedBackground: selected ? getComputedStyle(selected).backgroundColor : null,
      selectedText: selected ? getComputedStyle(selected).color : null,
    };
  });
}

(async () => {
  const browser = await chromium.launch({
    executablePath: "/usr/bin/google-chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const screenshots = [];
  try {
    const adminContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const admin = await adminContext.newPage();
    await login(admin, "theme-admin", adminPassword);

    const defaultDay = await mode(admin);
    if (JSON.stringify(defaultDay) !== JSON.stringify({ stored: "day", dataset: "day", dark: false })) {
      throw new Error(`default day mismatch: ${JSON.stringify(defaultDay)}`);
    }
    const dayColors = await colors(admin);
    if (dayColors.bodyBackground !== "rgb(248, 250, 252)") {
      throw new Error(`day body mismatch: ${JSON.stringify(dayColors)}`);
    }
    const dayPath = path.join(evidenceDir, "day-home.png");
    const dayBytes = await admin.screenshot({ path: dayPath, fullPage: true });
    screenshots.push({ file: "day-home.png", size_bytes: dayBytes.length, sha256: sha256(dayBytes) });

    await admin.getByRole("button", { name: "夜间模式" }).click();
    await admin.waitForFunction(() => document.body.classList.contains("body--dark"));
    const firstMenuItem = admin.locator(".theme-menu-item").first();
    const normalMenuBackground = await firstMenuItem.evaluate((element) => getComputedStyle(element).backgroundColor);
    await firstMenuItem.hover();
    await admin.waitForFunction(
      (normal) => getComputedStyle(document.querySelector(".theme-menu-item")).backgroundColor !== normal,
      normalMenuBackground,
    );
    const hoverBackground = await firstMenuItem.evaluate((element) => getComputedStyle(element).backgroundColor);
    if (normalMenuBackground === hoverBackground) {
      throw new Error(`night hover state did not change: ${normalMenuBackground}`);
    }
    const nightPath = path.join(evidenceDir, "night-home-hover.png");
    const nightBytes = await admin.screenshot({ path: nightPath, fullPage: true });
    screenshots.push({ file: "night-home-hover.png", size_bytes: nightBytes.length, sha256: sha256(nightBytes) });

    await admin.getByRole("button", { name: "白天模式" }).click();
    await admin.waitForFunction(() => !document.body.classList.contains("body--dark"));
    await admin.getByRole("button", { name: "夜间模式" }).click();
    await admin.waitForFunction(() => document.body.classList.contains("body--dark"));

    await admin.getByText("学期班级配置", { exact: true }).click();
    await admin.waitForURL(`${baseUrl}/settings`);
    if ((await mode(admin)).stored !== "night") throw new Error("navigation lost night mode");
    await admin.reload();
    await admin.getByRole("button", { name: "夜间模式" }).waitFor();
    await admin.waitForFunction(() => document.body.dataset.themeMode === "night");
    await admin.waitForFunction(() => document.body.classList.contains("body--dark"));
    await admin.waitForFunction(
      () => getComputedStyle(document.querySelector(".theme-menu-item-selected")).backgroundColor === "rgb(30, 58, 95)",
    );
    const refreshedNight = await mode(admin);
    if (JSON.stringify(refreshedNight) !== JSON.stringify({ stored: "night", dataset: "night", dark: true })) {
      throw new Error(`refresh lost night mode: ${JSON.stringify(refreshedNight)}`);
    }
    const nightColors = await colors(admin);
    if (nightColors.bodyBackground !== "rgb(15, 23, 42)" || nightColors.selectedBackground !== "rgb(30, 58, 95)") {
      throw new Error(`night shell mismatch: ${JSON.stringify(nightColors)}`);
    }

    await admin.evaluate((key) => localStorage.setItem(key, "invalid-secret-shaped-value"), storageKey);
    await admin.reload();
    await admin.getByRole("button", { name: "白天模式" }).waitFor();
    await admin.waitForFunction(() => document.body.dataset.themeMode === "day");
    await admin.waitForFunction(() => !document.body.classList.contains("body--dark"));
    if (JSON.stringify(await mode(admin)) !== JSON.stringify({ stored: "day", dataset: "day", dark: false })) {
      throw new Error("invalid storage did not fall back to day");
    }

    const teacherContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const teacher = await teacherContext.newPage();
    await login(teacher, "theme-teacher", teacherPassword);
    if (JSON.stringify(await mode(teacher)) !== JSON.stringify({ stored: "day", dataset: "day", dark: false })) {
      throw new Error("separate browser context did not default to day");
    }
    const themeStorage = await teacher.evaluate(() => ({ ...localStorage }));
    const serializedStorage = JSON.stringify(themeStorage).toLowerCase();
    for (const forbidden of ["theme-teacher", "theme-admin", "pass", "token", "tenant", "user_id", "jti"]) {
      if (serializedStorage.includes(forbidden)) throw new Error(`sensitive theme storage: ${forbidden}`);
    }
    if (JSON.stringify(themeStorage) !== JSON.stringify({ [storageKey]: "day" })) {
      throw new Error(`unexpected local storage: ${JSON.stringify(themeStorage)}`);
    }
    await teacherContext.close();
    await adminContext.close();

    const evidence = {
      status: "PASS",
      browser: "Google Chrome",
      browser_version: browser.version(),
      base_url: "loopback-redacted",
      storage_values: ["day", "night"],
      scenarios: [
        "default_day",
        "day_to_night_to_day",
        "navigation_persists",
        "refresh_persists",
        "invalid_storage_falls_back_to_day",
        "separate_browser_context_defaults_to_day",
        "different_login_has_no_sensitive_theme_storage",
        "header_drawer_body_text_border_hover_selected",
      ],
      colors: { day: dayColors, night: nightColors, nightHoverBackground: hoverBackground },
      screenshots,
    };
    fs.writeFileSync(path.join(evidenceDir, "browser-acceptance.json"), `${JSON.stringify(evidence, null, 2)}\n`, { mode: 0o600 });
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
