import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";
import type { Page } from "@playwright/test";

async function checkAccessibility(page: Page, name: string) {
  const report = await new AxeBuilder({page}).analyze();
  await writeFile(test.info().outputPath(`axe-${name}.json`), JSON.stringify(report.violations, null, 2));
  expect(report.violations.filter(item => ["critical", "serious"].includes(item.impact || "")).map(item => ({id: item.id, nodes: item.nodes.map(node => ({target: node.target, summary: node.failureSummary}))}))).toEqual([]);
}

test("real local AI: evidence → proposal → approval → isolated verification → export", async ({page}) => {
  await page.goto("/");
  await expect(page.getByText("qwen3:8b · local")).toBeVisible();
  await page.getByRole("button", {name: "Scan repository"}).click();
  await expect(page.getByRole("button", {name: /`os` imported but unused/})).toBeVisible();
  await expect(page.getByRole("button", {name: /`hashlib` imported but unused/})).toContainText("Withheld");
  await page.screenshot({path: test.info().outputPath("desktop-queue.png"), fullPage: true});
  await checkAccessibility(page, "queue");
  await page.getByRole("button", {name: /`os` imported but unused/}).click();
  await expect(page.getByText("Ruff evidence")).toBeVisible();
  await page.getByRole("button", {name: "Propose a local AI patch"}).click();
  const approve = page.getByRole("button", {name: "Approve & validate copy"});
  await expect(approve).toBeVisible({timeout: 200000});
  await expect(approve).toBeDisabled();
  await expect(page.getByText("Original", {exact: true})).toBeVisible();
  await checkAccessibility(page, "review");
  await page.getByRole("checkbox").check();
  await approve.click();
  await expect(page.getByText("A small fix. A verified improvement.")).toBeVisible();
  await expect(page.getByText("1 issue resolved · 0 regressions · original unchanged")).toBeVisible();
  await expect(page.getByText("5 → 4 total findings.", {exact:false})).toBeVisible();
  await checkAccessibility(page, "result");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: test.info().outputPath("desktop-result.png"), fullPage: true});
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", {name: "Export .patch"}).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^patchgardener-.*\.patch$/);
  await page.getByRole("button", {name: "Activity log"}).click();
  await expect(page.getByText("approval · recorded").first()).toBeVisible();
});

test("protected paths, mobile layout, and local setup", async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto("/");
  await page.getByRole("button", {name: "Scan repository"}).click();
  await page.getByRole("button", {name: /`hashlib` imported but unused/}).click();
  await expect(page.getByText("Protected path: requires a specialist review; proposals disabled.")).toBeVisible();
  await expect(page.getByRole("button", {name: "Propose a local AI patch"})).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await expect(page.locator(".sidebar-note")).not.toBeVisible();
  await checkAccessibility(page, "mobile-protected");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: test.info().outputPath("mobile-protected.png"), fullPage: true});
  await page.getByRole("button", {name: "Local setup"}).click();
  await expect(page.getByRole("heading", {name: "Keep it close."})).toBeVisible();
  await checkAccessibility(page, "mobile-settings");
});

test("API surfaces malformed requests without executing changes", async ({request}) => {
  expect((await request.post("/api/approvals", {data: {proposal_id: "missing", approved: false}, headers: {origin: "http://127.0.0.1:3105"}})).status()).toBe(422);
  expect((await request.post("/api/approvals", {data: {proposal_id: "missing", approved: false}})).status()).toBe(422);
  expect((await request.post("/api/scans", {data: {repository_id: "../../outside"}})).status()).toBe(400);
  expect((await request.post("/api/scans", {data: {}, headers: {origin: "https://evil.example"}})).status()).toBe(403);
});
