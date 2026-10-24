// Same real journey as the Playwright test suite, without worker process forks.
import {chromium, expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs/promises";
const browser = await chromium.connectOverCDP(process.env.PG_CDP_URL || "http://127.0.0.1:9228");
const context = await browser.newContext({viewport: {width: 1440, height: 1000}, acceptDownloads: true});
const page = await context.newPage();
const results = [];
const check = async (name, fn) => {const start=Date.now(); try {await fn(); results.push({name,status:"passed",ms:Date.now()-start}); console.log(`PASS ${name}`);} catch(error) {results.push({name,status:"failed",error:String(error)}); console.error(`FAIL ${name}: ${error}`); throw error;}};
try {
  await check("real AI review, approval, baseline, export and audit", async () => {
    await page.goto("http://127.0.0.1:3105");
    await expect(page.getByText("qwen3:8b · local")).toBeVisible();
    await page.getByRole("button",{name:"Scan repository"}).click();
    await expect(page.getByRole("button",{name:/`os` imported but unused/})).toBeVisible();
    await page.getByRole("button",{name:/`os` imported but unused/}).click();
    await page.getByRole("button",{name:"Propose a local AI patch"}).click();
    const approve=page.getByRole("button",{name:"Approve & validate copy"});
    await expect(approve).toBeVisible({timeout:200000});
    await expect(approve).toBeDisabled();
    await page.getByRole("checkbox").check();
    await approve.click();
    await expect(page.getByText("A small fix. A verified improvement.")).toBeVisible({timeout:30000});
    await expect(page.getByText("1 issue resolved · 0 regressions · original unchanged")).toBeVisible();
    await expect(page.getByText("5 → 4 total findings.",{exact:false})).toBeVisible();
    const downloadPromise=page.waitForEvent("download");
    await page.getByRole("link",{name:"Export .patch"}).click();
    const download=await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^patchgardener-.*\.patch$/);
    await fs.mkdir("test-results",{recursive:true});
    await download.saveAs("test-results/exported.patch");
    expect(await fs.readFile("test-results/exported.patch","utf8")).toContain("-import os");
    await page.screenshot({path:"test-results/verified-desktop.png",fullPage:true});
  });
  await check("desktop accessibility", async () => {
    const report=await new AxeBuilder({page}).analyze();
    await fs.writeFile("test-results/axe-desktop.json",JSON.stringify(report.violations,null,2));
    expect(report.violations.filter(item=>["serious","critical"].includes(item.impact||""))).toEqual([]);
  });
  await check("audit records approval", async () => {
    await page.getByRole("button",{name:"Activity log"}).click();
    await expect(page.getByText("approval · recorded").first()).toBeVisible();
  });
  await check("mobile protection and layout", async () => {
    await page.setViewportSize({width:390,height:844});
    await page.goto("http://127.0.0.1:3105");
    await page.getByRole("button",{name:"Scan repository"}).click();
    await page.getByRole("button",{name:/`hashlib` imported but unused/}).click();
    await expect(page.getByText("Protected path: requires a specialist review; proposals disabled.")).toBeVisible();
    await expect(page.getByRole("button",{name:"Propose a local AI patch"})).toHaveCount(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
    await page.screenshot({path:"test-results/mobile.png",fullPage:true});
    await page.getByRole("button",{name:"Local setup"}).click();
    await expect(page.getByRole("heading",{name:"Keep it close."})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
    const report=await new AxeBuilder({page}).analyze();
    await fs.writeFile("test-results/axe-mobile.json",JSON.stringify(report.violations,null,2));
    expect(report.violations.filter(item=>["serious","critical"].includes(item.impact||""))).toEqual([]);
  });
  await check("invalid and cross-origin API requests", async () => {
    const response=await context.request.post("http://127.0.0.1:3105/api/approvals",{data:{proposal_id:"missing",approved:false}});
    expect(response.status()).toBe(422);
    expect((await context.request.post("http://127.0.0.1:3105/api/scans",{data:{repository_id:"../../outside"}})).status()).toBe(400);
    expect((await context.request.post("http://127.0.0.1:3105/api/scans",{data:{},headers:{origin:"https://evil.example"}})).status()).toBe(403);
  });
} finally {
  await fs.writeFile("docs/browser-results.json",JSON.stringify({measured_at:new Date().toISOString(),method:"Playwright over dedicated loopback Chromium CDP; no worker forks",synthetic_fixture:true,results},null,2));
  await context.close(); await browser.close();
}
