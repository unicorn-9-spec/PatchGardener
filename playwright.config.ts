import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/browser", timeout: 240000,
  expect: {timeout: 15000}, fullyParallel: false, workers: 1,
  reporter: [["list"], ["json", {outputFile: "docs/browser-results.json"}]],
  use: {baseURL: "http://127.0.0.1:3105", viewport: {width: 1440, height: 1000}, trace: "retain-on-failure"},
  projects: [{name: "chromium", use: {browserName: "chromium"}}]
});
