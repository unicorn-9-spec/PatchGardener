import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

// Real local model and backend required; no request interception or mock data.
const root = path.resolve("demo/assets");
await fs.mkdir(path.join(root, "screenshots"), {recursive: true});
await fs.mkdir(path.join(root, "video"), {recursive: true});
const browser = await chromium.launch({headless: true});
const context = await browser.newContext({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1, recordVideo: {dir: path.join(root, "video"), size: {width: 1920, height: 1080}}, reducedMotion: "reduce"});
const page = await context.newPage();
const video = page.video();
const pause = async seconds => page.waitForTimeout(seconds * 1000);
const shot = async name => page.screenshot({path: path.join(root, "screenshots", name), fullPage: false});
const choose = async locator => {await locator.scrollIntoViewIfNeeded(); await pause(1); await locator.click();};
let completed = false;

try {
  await page.goto("http://127.0.0.1:3105");
  await page.getByText("qwen3:8b · local").waitFor();
  await shot("01-garden.png"); await pause(9);
  await choose(page.getByRole("button", {name: "Scan repository"}));
  await page.getByRole("button", {name: /`os` imported but unused/}).waitFor();
  await shot("02-evidence-queue.png"); await pause(9);
  await choose(page.getByRole("button", {name: /`hashlib` imported but unused/}));
  await page.getByText("Protected path: requires a specialist review; proposals disabled.").scrollIntoViewIfNeeded();
  await pause(9);
  await choose(page.getByRole("button", {name: /`os` imported but unused/}));
  await page.getByText("Ruff evidence").scrollIntoViewIfNeeded();
  await shot("03-exact-evidence.png"); await pause(7);
  await choose(page.getByRole("button", {name: "Propose a local AI patch"}));
  await page.getByRole("button", {name: "Approve & validate copy"}).waitFor({timeout: 200000});
  await page.getByText("Original", {exact: true}).scrollIntoViewIfNeeded();
  await shot("04-local-ai-diff.png"); await pause(14);
  await page.getByRole("checkbox").scrollIntoViewIfNeeded(); await pause(5);
  await choose(page.getByRole("checkbox")); await pause(4);
  await choose(page.getByRole("button", {name: "Approve & validate copy"}));
  await page.getByText("A small fix. A verified improvement.").waitFor();
  await page.getByText("A small fix. A verified improvement.").scrollIntoViewIfNeeded();
  await pause(4); await shot("05-verified-outcome.png"); await pause(10);
  await page.getByText("After · isolated copy").locator("..").getByText("Fixture unit tests").click();
  await pause(8); await shot("06-real-tests.png");
  const downloadEvent = page.waitForEvent("download");
  await choose(page.getByRole("link", {name: "Export .patch"}));
  await (await downloadEvent).saveAs(path.join(root, "video", "demonstrated.patch"));
  await pause(6);
  await choose(page.getByRole("button", {name: "Activity log"}));
  await page.getByText("approval · recorded").first().waitFor();
  await pause(8); await shot("07-audit.png");
  await choose(page.getByRole("button", {name: "Repository garden"}));
  await page.evaluate(() => window.scrollTo(0, 0)); await pause(6);
  completed = true;
} finally {
  await context.close();
  if (video) {const output = path.join(root, "video", completed ? "demo_silent.webm" : "demo_failed.webm"); const source = await video.path(); await fs.rename(source, output); console.log(output);}
  await browser.close();
}
