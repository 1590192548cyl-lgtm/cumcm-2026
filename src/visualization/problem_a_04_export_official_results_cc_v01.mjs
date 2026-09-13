/** Build the four official Problem A result workbooks from verified CSV outputs. */

import fs from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";

const runtimeRequire = process.env.CUMCM_NODE_MODULES
  ? createRequire(path.join(process.env.CUMCM_NODE_MODULES, "package.json"))
  : createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = runtimeRequire("@oai/artifact-tool");

const projectRoot = process.cwd();
const resultsDir = path.join(projectRoot, "outputs", "results");
const outputDir = path.join(projectRoot, "outputs", "submissions", "problem_a");
const previewDir = path.join(os.tmpdir(), "cumcm2026-problem-a-workbooks");
const target = process.argv[2] ?? "all";

async function readCsv(csvPath, expectedRows, expectedColumns) {
  const text = await fs.readFile(csvPath, "utf8");
  const lines = text.trim().split(/\r?\n/);
  const rows = lines.slice(1).map((line) =>
    line.split(",").map((cell) => {
      if (cell === "") return null;
      const value = Number(cell);
      if (!Number.isFinite(value)) throw new Error(`Nonnumeric value in ${csvPath}`);
      return value;
    }),
  );
  if (
    (expectedRows !== null && rows.length !== expectedRows) ||
    rows.some((row) => row.length !== expectedColumns)
  ) {
    throw new Error(
      `Unexpected shape in ${csvPath}: ${rows.length} rows, expected ${expectedRows}`,
    );
  }
  return rows;
}

function styleResultSheet(sheet, rowCount, columnCount, tabColor) {
  const lastColumn = columnName(columnCount);
  sheet.showGridLines = false;
  sheet.tabColor = tabColor;
  const used = sheet.getRange(`A1:${lastColumn}${rowCount + 1}`);
  used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
  used.format.verticalAlignment = "center";

  const header = sheet.getRange(`A1:${lastColumn}1`);
  header.format = {
    fill: "#1F4E78",
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#17365D" },
  };
  header.format.rowHeight = 32;

  const timeColumn = sheet.getRange(`A2:A${rowCount + 1}`);
  timeColumn.format.fill = "#EAF0F6";
  timeColumn.format.font = {
    name: "Arial",
    size: 10,
    bold: true,
    color: "#1F2937",
  };
  timeColumn.format.horizontalAlignment = "right";
  timeColumn.format.numberFormat = "0";

  const data = sheet.getRange(`B2:${lastColumn}${rowCount + 1}`);
  data.format.horizontalAlignment = "right";
  data.format.numberFormat = "0.0000";
  sheet.getRange(`B1:${lastColumn}1`).format.numberFormat = "0.0";
  sheet.getRange(`A1:A${rowCount + 1}`).format.columnWidth = 24;
  sheet.getRange(`B1:${lastColumn}${rowCount + 1}`).format.columnWidth = 12;
  sheet.getRange(`A2:${lastColumn}${rowCount + 1}`).format.rowHeight = 18;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
}

function columnName(columnCount) {
  let value = columnCount;
  let name = "";
  while (value > 0) {
    value -= 1;
    name = String.fromCharCode(65 + (value % 26)) + name;
    value = Math.floor(value / 26);
  }
  return name;
}

async function addSheet(workbook, spec) {
  const rows = await readCsv(spec.csvPath, spec.expectedRows, spec.headers.length);
  if (
    rows[0][0] !== spec.firstTime ||
    (spec.lastTime !== null && rows.at(-1)[0] !== spec.lastTime)
  ) {
    throw new Error(`Unexpected time coverage in ${spec.csvPath}`);
  }
  if (
    spec.timeStep !== null &&
    rows.slice(1).some((row, index) => row[0] - rows[index][0] !== spec.timeStep)
  ) {
    throw new Error(`Unexpected time step in ${spec.csvPath}`);
  }
  const sheet = workbook.worksheets.add(spec.sheetName);
  const lastColumn = columnName(spec.headers.length);
  sheet.getRange(`A1:${lastColumn}1`).values = [spec.headers];
  sheet.getRange(`A2:${lastColumn}${rows.length + 1}`).values = rows;
  styleResultSheet(
    sheet,
    rows.length,
    spec.headers.length,
    spec.tabColor,
  );
  return sheet;
}

async function verifyAndExport(workbook, fileName, sheetNames) {
  workbook.recalculate();
  for (const sheetName of sheetNames) {
    const sheet = workbook.worksheets.getItem(sheetName);
    const used = sheet.getUsedRange(true);
    const top = await workbook.inspect({
      kind: "table",
      range: `${sheetName}!A1:V6`,
      include: "values,formulas",
      tableMaxRows: 6,
      tableMaxCols: 22,
    });
    const bottomAddress = used.address;
    console.log(`VERIFY ${fileName} ${sheetName} ${bottomAddress}\n${top.ndjson}`);
    const preview = await workbook.render({
      sheetName,
      range: "A1:V25",
      scale: 1,
      format: "png",
    });
    await fs.mkdir(previewDir, { recursive: true });
    await fs.writeFile(
      path.join(previewDir, `${fileName}-${sheetName}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 300 },
    summary: `formula error scan for ${fileName}`,
  });
  console.log(`ERROR_SCAN ${fileName}\n${errors.ndjson}`);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(outputDir, fileName));
}

await fs.mkdir(outputDir, { recursive: true });
const fixedHeaders = [
  "时间\\到药材中心的距离",
  ...Array.from({ length: 21 }, (_, index) => index / 10),
];
const shrinkingHeaders = [
  "时间\\到药材中心的距离",
  ...Array.from({ length: 20 }, (_, index) => index / 10),
  "药材表面",
];

if (target === "1" || target === "all") {
  const result1 = Workbook.create();
  await addSheet(result1, {
  sheetName: "温度",
  csvPath: path.join(resultsDir, "problem_a_result_01_preheat_temperature_v01.csv"),
  expectedRows: 1800,
  headers: fixedHeaders,
  firstTime: 1,
  lastTime: 1800,
  timeStep: 1,
  tabColor: "#1F4E78",
  });
  await addSheet(result1, {
  sheetName: "水分浓度",
  csvPath: path.join(resultsDir, "problem_a_result_02_preheat_moisture_v01.csv"),
  expectedRows: 1800,
  headers: fixedHeaders,
  firstTime: 1,
  lastTime: 1800,
  timeStep: 1,
  tabColor: "#2F855A",
  });
  await verifyAndExport(result1, "result1.xlsx", ["温度", "水分浓度"]);
}

if (target === "2" || target === "all") {
  const result2 = Workbook.create();
  await addSheet(result2, {
  sheetName: "温度",
  csvPath: path.join(resultsDir, "problem_a_result_05_q2_temperature_v01.csv"),
  expectedRows: 10800,
  headers: fixedHeaders,
  firstTime: 1,
  lastTime: 10800,
  timeStep: 1,
  tabColor: "#1F4E78",
  });
  await addSheet(result2, {
  sheetName: "水分浓度",
  csvPath: path.join(resultsDir, "problem_a_result_06_q2_moisture_v01.csv"),
  expectedRows: 10800,
  headers: fixedHeaders,
  firstTime: 1,
  lastTime: 10800,
  timeStep: 1,
  tabColor: "#2F855A",
  });
  await verifyAndExport(result2, "result2.xlsx", ["温度", "水分浓度"]);
}

if (target === "3" || target === "all") {
  const result3 = Workbook.create();
  await addSheet(result3, {
  sheetName: "Sheet1",
  csvPath: path.join(resultsDir, "problem_a_result_07_q3_moisture_v01.csv"),
  expectedRows: null,
  headers: fixedHeaders,
  firstTime: 60,
  lastTime: null,
  timeStep: 60,
  tabColor: "#2F855A",
  });
  await verifyAndExport(result3, "result3.xlsx", ["Sheet1"]);
}

if (target === "4" || target === "all") {
  const result4 = Workbook.create();
  await addSheet(result4, {
  sheetName: "Sheet1",
  csvPath: path.join(resultsDir, "problem_a_result_08_q4_moisture_v01.csv"),
  expectedRows: null,
  headers: shrinkingHeaders,
  firstTime: 60,
  lastTime: null,
  timeStep: 60,
  tabColor: "#2F855A",
  });
  await verifyAndExport(result4, "result4.xlsx", ["Sheet1"]);
}

console.log(`OUTPUT_DIR ${outputDir}`);
