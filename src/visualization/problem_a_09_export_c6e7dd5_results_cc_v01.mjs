/**
 * Restore the full-period result2.xlsx directly from c6e7dd5, then use this
 * builder to write that commit's unrounded arrays back into result1.xlsx,
 * result3.xlsx, and result4.xlsx without changing their workbook structure.
 * The Python preprocessing step supplies temporary JSON payloads; all XLSX
 * authoring is performed through @oai/artifact-tool.
 *
 * Usage:
 *   node src/visualization/problem_a_09_export_c6e7dd5_results_cc_v01.mjs \
 *     /absolute/path/to/json-dir outputs/submissions/problem_a
 */

import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourceDir = process.argv[2];
const outputDir = process.argv[3];
const selectedOutput = process.argv[4];
if (!sourceDir || !outputDir) {
  throw new Error("Expected source JSON directory and output directory.");
}

const specifications = [
  ["result1.json", "result1.xlsx"],
  ["result3.json", "result3.xlsx"],
  ["result4.json", "result4.xlsx"],
];

await fs.mkdir(outputDir, { recursive: true });

for (const [jsonName, xlsxName] of specifications) {
  if (selectedOutput && xlsxName !== selectedOutput) {
    continue;
  }
  const payload = JSON.parse(await fs.readFile(path.join(sourceDir, jsonName), "utf8"));
  const targetPath = path.join(outputDir, xlsxName);
  const input = await FileBlob.load(targetPath);
  const workbook = await SpreadsheetFile.importXlsx(input);
  for (const sheetPayload of payload.sheets) {
    const sheet = workbook.worksheets.getItem(sheetPayload.name);
    const rows = sheetPayload.rows.slice(1);
    const lastColumn = sheetPayload.rows[0].length;
    sheet.getRangeByIndexes(1, 0, rows.length, lastColumn).write(rows);
    sheet.getRangeByIndexes(1, 0, rows.length, 1).format.numberFormat = "0";
    sheet.getRangeByIndexes(1, 1, rows.length, lastColumn - 1).format.numberFormat = "0.0000";
  }
  workbook.recalculate();
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(targetPath);
}
