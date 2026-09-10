/** Export Problem A question 1 CSV results to the required two-sheet workbook. */

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = process.cwd();
const resultsDir = path.join(projectRoot, "outputs", "results");
const outputPath = path.join(resultsDir, "problem_a_result_04_preheat_full_grid_v01.xlsx");
const previewDir = path.join(os.tmpdir(), "cumcm2026-result1-preview");

async function readNumericCsv(csvPath) {
  const text = await fs.readFile(csvPath, "utf8");
  const lines = text.trim().split(/\r?\n/);
  const rows = lines.slice(1).map((line) => line.split(",").map(Number));
  const valid =
    rows.length === 1800 &&
    rows.every(
      (row) => row.length === 22 && row.every((value) => Number.isFinite(value)),
    );
  if (!valid) {
    throw new Error(`Unexpected CSV shape or nonnumeric value in ${csvPath}`);
  }
  return rows;
}

const temperatureRows = await readNumericCsv(
  path.join(resultsDir, "problem_a_result_01_preheat_temperature_v01.csv"),
);
const moistureRows = await readNumericCsv(
  path.join(resultsDir, "problem_a_result_02_preheat_moisture_v01.csv"),
);

const workbook = Workbook.create();
const temperatureSheet = workbook.worksheets.add("温度");
const moistureSheet = workbook.worksheets.add("水分浓度");
const radiusHeaders = Array.from({ length: 21 }, (_, index) => index / 10);
const header = [["时间\\到药材中心的距离", ...radiusHeaders]];

function populateResultSheet(sheet, rows, tabColor) {
  sheet.showGridLines = false;
  sheet.tabColor = tabColor;
  sheet.getRange("A1:V1").values = header;
  sheet.getRange("A2:V1801").values = rows;

  const used = sheet.getRange("A1:V1801");
  used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
  used.format.verticalAlignment = "center";

  const tableHeader = sheet.getRange("A1:V1");
  tableHeader.format = {
    fill: "#1F4E78",
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#17365D" },
  };
  tableHeader.format.rowHeight = 32;

  const timeColumn = sheet.getRange("A2:A1801");
  timeColumn.format.fill = "#EAF0F6";
  timeColumn.format.font = {
    name: "Arial",
    size: 10,
    bold: true,
    color: "#1F2937",
  };
  timeColumn.format.horizontalAlignment = "right";
  timeColumn.format.numberFormat = "0";

  const dataRange = sheet.getRange("B2:V1801");
  dataRange.format.horizontalAlignment = "right";
  dataRange.format.numberFormat = "0.0000";
  sheet.getRange("B1:V1").format.numberFormat = "0.0";

  sheet.getRange("A1:A1801").format.columnWidth = 24;
  sheet.getRange("B1:V1801").format.columnWidth = 12;
  sheet.getRange("A2:V1801").format.rowHeight = 18;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
}

populateResultSheet(temperatureSheet, temperatureRows, "#1F4E78");
populateResultSheet(moistureSheet, moistureRows, "#2F855A");

workbook.recalculate();

for (const sheetName of ["温度", "水分浓度"]) {
  const top = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!A1:V6`,
    include: "values,formulas",
    tableMaxRows: 6,
    tableMaxCols: 22,
  });
  const bottom = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!A1797:V1801`,
    include: "values,formulas",
    tableMaxRows: 5,
    tableMaxCols: 22,
  });
  console.log(`INSPECT ${sheetName} TOP\n${top.ndjson}`);
  console.log(`INSPECT ${sheetName} BOTTOM\n${bottom.ndjson}`);

  const preview = await workbook.render({
    sheetName,
    range: "A1:V25",
    scale: 1,
    format: "png",
  });
  await fs.mkdir(previewDir, { recursive: true });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(`ERROR_SCAN\n${errors.ndjson}`);

await fs.mkdir(resultsDir, { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`OUTPUT ${outputPath}`);
