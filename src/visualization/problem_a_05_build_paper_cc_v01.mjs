import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import path from "node:path";
import fs from "node:fs/promises";

const runtimeRequire = process.env.CUMCM_NODE_MODULES
  ? createRequire(path.join(process.env.CUMCM_NODE_MODULES, "package.json"))
  : createRequire(import.meta.url);
const { chromium } = runtimeRequire("playwright");

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const inputPath = path.join(repoRoot, "docs/paper/problem_a_paper_cc_v01.html");
const outputPath = path.join(
  repoRoot,
  "outputs/submissions/problem_a/problem_a_paper_cc_v01.pdf",
);

await fs.mkdir(path.dirname(outputPath), { recursive: true });

const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage();

await page.goto(pathToFileURL(inputPath).href, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.MathJax?.startup?.promise !== undefined);
await page.evaluate(async () => {
  await window.MathJax.startup.promise;
  await document.fonts.ready;
});

await page.pdf({
  path: outputPath,
  format: "A4",
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: "<div></div>",
  footerTemplate:
    '<div style="width:100%;font-size:8px;color:#666;text-align:center;">' +
    '<span class="pageNumber"></span> / <span class="totalPages"></span>' +
    "</div>",
  margin: { top: "20mm", right: "18mm", bottom: "20mm", left: "18mm" },
  preferCSSPageSize: true,
});

await browser.close();
console.log(outputPath);
