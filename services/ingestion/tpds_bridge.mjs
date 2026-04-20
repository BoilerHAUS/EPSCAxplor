import process from "node:process";

import {
  buildTableChunks,
  normalizeFromDocling,
} from "table-preserving-doc-standard";

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

const rawInput = await readStdin();

if (!rawInput.trim()) {
  fail("TPDS bridge received no input.");
}

let input;
try {
  input = JSON.parse(rawInput);
} catch (error) {
  fail(
    `Failed to parse TPDS bridge input as JSON: ${
      error instanceof Error ? error.message : String(error)
    }`
  );
}

if (!Array.isArray(input.tables)) {
  fail("TPDS bridge input must include a 'tables' array.");
}

const chunkOptions =
  input.chunkOptions && typeof input.chunkOptions === "object"
    ? input.chunkOptions
    : {};

const normalizedTables = input.tables.map((entry, index) => {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    fail(`tables[${index}] must be an object containing tableItem and options.`);
  }

  if (!("tableItem" in entry)) {
    fail(`tables[${index}] is missing required property 'tableItem'.`);
  }

  const options =
    entry.options && typeof entry.options === "object" && !Array.isArray(entry.options)
      ? entry.options
      : {};

  return normalizeFromDocling(entry.tableItem, options);
});

const tableChunks = normalizedTables.flatMap((table) =>
  buildTableChunks(table, chunkOptions)
);

process.stdout.write(
  JSON.stringify({
    normalizedTables,
    tableChunks,
  })
);
