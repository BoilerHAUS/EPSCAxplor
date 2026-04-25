import process from "node:process";

import {
  buildTableChunks,
  inferHeaders,
  mergeMultiPageTables,
  normalizeFromDocling,
} from "table-preserving-doc-standard";

const AUTO_TABLE_SUFFIX_RE = /\s+[—-]\s+Table\s+\d+$/iu;
const MAX_LEADING_ROWS = 4;

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

function normalizeText(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim().replace(/\s+/gu, " ");
}

function stripAutoTableSuffix(value) {
  return normalizeText(value).replace(AUTO_TABLE_SUFFIX_RE, "");
}

function cellsForRow(table, row) {
  const cellMap = new Map(table.cells.map((cell) => [cell.cellId, cell]));
  return row.cellIds
    .map((cellId) => cellMap.get(cellId))
    .filter((cell) => Boolean(cell))
    .sort((left, right) => left.colIndex - right.colIndex);
}

function sortRows(rows) {
  return [...rows].sort((left, right) => left.rowIndex - right.rowIndex);
}

function rowSignature(table, row) {
  const parts = cellsForRow(table, row)
    .map((cell) => {
      const text = normalizeText(cell.textNormalized || cell.textRaw || "");
      if (!text) {
        return null;
      }
      const rowSpan = cell.rowSpan ?? 1;
      const colSpan = cell.colSpan ?? 1;
      return `${cell.colIndex}:${text}:${rowSpan}:${colSpan}`;
    })
    .filter((part) => Boolean(part));
  return parts.join("|");
}

function headerRowSignatures(table) {
  return sortRows(table.rows)
    .filter((row) => row.rowType === "header")
    .map((row) => rowSignature(table, row))
    .filter((signature) => Boolean(signature));
}

function appendWarnings(table, warnings) {
  const nextWarnings = new Set(table.fidelityWarnings ?? []);
  for (const warning of warnings) {
    if (warning) {
      nextWarnings.add(warning);
    }
  }
  return nextWarnings.size > 0 ? [...nextWarnings] : undefined;
}

function firstPage(table) {
  return table.pages.reduce((minimum, page) => Math.min(minimum, page), Number.POSITIVE_INFINITY);
}

function lastPage(table) {
  return table.pages.reduce((maximum, page) => Math.max(maximum, page), Number.NEGATIVE_INFINITY);
}

function tableTitleKey(table) {
  return normalizeText(table.caption) || stripAutoTableSuffix(table.title);
}

function sameSourceDocument(left, right) {
  return normalizeText(left.sourceDocumentId) === normalizeText(right.sourceDocumentId);
}

function areAdjacentFragments(left, right) {
  const previousLastPage = lastPage(left);
  const nextFirstPage = firstPage(right);
  return (
    Number.isFinite(previousLastPage) &&
    Number.isFinite(nextFirstPage) &&
    nextFirstPage === previousLastPage + 1
  );
}

function hasCompatibleHeaders(groupHeaderSignatures, table) {
  const currentHeaderSignatures = headerRowSignatures(table);
  if (groupHeaderSignatures.length === 0 || currentHeaderSignatures.length === 0) {
    return true;
  }
  const shared = currentHeaderSignatures.filter((signature) =>
    groupHeaderSignatures.includes(signature)
  );
  return shared.length > 0;
}

function shouldMergeIntoGroup(group, table) {
  return (
    sameSourceDocument(group.anchorTable, table) &&
    areAdjacentFragments(group.lastTable, table) &&
    tableTitleKey(group.anchorTable) &&
    tableTitleKey(group.anchorTable) === tableTitleKey(table) &&
    group.anchorTable.columns.length === table.columns.length &&
    hasCompatibleHeaders(group.headerSignatures, table)
  );
}

function markRepeatedHeaderRows(table, repeatedSignatures) {
  if (!Array.isArray(repeatedSignatures) || repeatedSignatures.length === 0) {
    return table;
  }

  const repeatedSignatureSet = new Set(repeatedSignatures);
  const repeatedRowIndexes = new Set();

  for (const row of sortRows(table.rows).slice(0, MAX_LEADING_ROWS)) {
    if (row.rowType === "footer" || row.rowType === "note") {
      break;
    }

    const signature = rowSignature(table, row);
    if (!signature || !repeatedSignatureSet.has(signature)) {
      break;
    }

    repeatedRowIndexes.add(row.rowIndex);
  }

  if (repeatedRowIndexes.size === 0) {
    return table;
  }

  return {
    ...table,
    rows: table.rows.map((row) =>
      repeatedRowIndexes.has(row.rowIndex)
        ? {
            ...row,
            rowType: "header",
            repeatedHeaderRow: true,
          }
        : row
    ),
    cells: table.cells.map((cell) => {
      if (!repeatedRowIndexes.has(cell.rowIndex)) {
        return cell;
      }
      const { inferredHeaders: _inferredHeaders, ...rest } = cell;
      return {
        ...rest,
        isHeader: true,
      };
    }),
    fidelityWarnings: appendWarnings(table, ["repeated-headers-detected"]),
  };
}

function propagateClassificationCells(table) {
  const bodyRows = sortRows(table.rows).filter(
    (row) => row.rowType !== "header" && row.rowType !== "footer" && row.rowType !== "note"
  );
  if (bodyRows.length === 0) return table;

  const lastSeenByCol = new Map();
  const cellFills = new Map();

  for (const row of bodyRows) {
    for (const cell of cellsForRow(table, row)) {
      const text = normalizeText(cell.textNormalized || cell.textRaw || "");
      if (text) {
        lastSeenByCol.set(cell.colIndex, text);
      } else if (lastSeenByCol.has(cell.colIndex)) {
        cellFills.set(cell.cellId, lastSeenByCol.get(cell.colIndex));
      }
    }
  }

  if (cellFills.size === 0) return table;

  return {
    ...table,
    cells: table.cells.map((cell) =>
      cellFills.has(cell.cellId)
        ? { ...cell, textNormalized: cellFills.get(cell.cellId), classificationFilled: true }
        : cell
    ),
    fidelityWarnings: appendWarnings(table, ["classification-propagated"]),
  };
}

function withContinuity(table, groupId, indexInGroup, groupSize) {
  return {
    ...table,
    continuity: {
      ...(table.continuity ?? {}),
      isMultiPage: groupSize > 1,
      logicalTableGroupId: groupId,
      continuedFromPreviousPage: indexInGroup > 0,
      continuesOnNextPage: indexInGroup < groupSize - 1,
    },
  };
}

function prepareTablesForChunking(normalizedTables) {
  const groups = [];

  for (const table of normalizedTables) {
    const currentTable = table;
    const priorGroup = groups.at(-1);
    if (priorGroup && shouldMergeIntoGroup(priorGroup, currentTable)) {
      const withRepeatedHeaders = markRepeatedHeaderRows(
        currentTable,
        priorGroup.headerSignatures
      );
      priorGroup.tables.push(withRepeatedHeaders);
      priorGroup.lastTable = withRepeatedHeaders;
      if (priorGroup.headerSignatures.length === 0) {
        priorGroup.headerSignatures = headerRowSignatures(withRepeatedHeaders);
      }
      continue;
    }

    groups.push({
      groupId: `logical-table-${groups.length + 1}`,
      anchorTable: currentTable,
      lastTable: currentTable,
      headerSignatures: headerRowSignatures(currentTable),
      tables: [currentTable],
    });
  }

  const continuityAnnotatedTables = groups.flatMap((group) =>
    group.tables.map((table, index) =>
      withContinuity(table, group.groupId, index, group.tables.length)
    )
  );

  return mergeMultiPageTables(continuityAnnotatedTables).map((table) => {
    const inferredTable = inferHeaders(table);
    return {
      ...inferredTable,
      fidelityWarnings: appendWarnings(inferredTable, [
        inferredTable.continuity?.isMultiPage ? "multi-page-merged" : null,
        inferredTable.rows.some((row) => row.repeatedHeaderRow)
          ? "repeated-headers-detected"
          : null,
      ]),
    };
  });
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

const preparedTables = prepareTablesForChunking(
  normalizedTables.map(propagateClassificationCells)
);

const tableChunks = preparedTables.flatMap((table) =>
  buildTableChunks(table, chunkOptions)
);

process.stdout.write(
  JSON.stringify({
    normalizedTables: preparedTables,
    tableChunks,
  })
);
