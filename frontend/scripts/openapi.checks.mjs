import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { checkGenerated, checkPendingResponses, exportSchema, generateTypes } from "./openapi-tools.mjs";

const operation = (schema) => ({ responses: { 200: { content: { "application/json": { schema } } } } });
const document = (schema) => ({
  openapi: "3.1.0", info: { title: "fixture", version: "1" },
  paths: { "/tasks": { get: operation(schema) } },
});
const pending = "// pending-response: GET /tasks\n";

test("empty success schemas may remain pending", () => {
  assert.doesNotThrow(() => checkPendingResponses(document({}), pending));
});

test("a modeled success response must leave the pending list", () => {
  assert.throws(() => checkPendingResponses(document({ type: "object" }), pending), /GET \/tasks/);
});

test("201 and referenced response schemas also trigger removal", () => {
  const doc = document({});
  doc.paths["/tasks"].get.responses[201] = {
    content: { "application/json": { schema: { $ref: "#/components/schemas/Task" } } },
  };
  assert.throws(() => checkPendingResponses(doc, pending), /GET \/tasks/);
});

test("a changed error schema does not trigger pending removal", () => {
  const doc = document({});
  doc.paths["/tasks"].get.responses[422] = operation({ type: "object" }).responses[200];
  assert.doesNotThrow(() => checkPendingResponses(doc, pending));
});

test("unknown and missing pending entries fail instead of silently passing", () => {
  assert.throws(() => checkPendingResponses(document({}), "// pending-response: POST /tasks\n"), /POST \/tasks/);
  assert.throws(() => checkPendingResponses(document({}), ""), /pending-response/);
});

test("an explicit zero-pending marker requires every success schema to be modeled", () => {
  const none = "// pending-response-count: 0\n";
  assert.equal(checkPendingResponses(document({ type: "object" }), none), 0);
  assert.throws(() => checkPendingResponses(document({}), none), /GET \/tasks/);
});

test("generation is repeatable and detects a stale generated file", async () => {
  const dir = await mkdtemp(join(tmpdir(), "dev-c-openapi-"));
  try {
    const target = join(dir, "types.ts");
    const doc = document({});
    doc.components = { schemas: { TaskCreate: {
      type: "object", required: ["title"], properties: {
        title: { type: "string" }, owner: { type: "string", default: "我" },
      },
    } } };
    await generateTypes(doc, target);
    const first = await readFile(target, "utf8");
    assert.match(first, /TaskCreate:/);
    assert.match(first, /title: string/);
    assert.match(first, /owner\?: string/);
    await generateTypes(doc, target);
    assert.equal(await readFile(target, "utf8"), first);
    await checkGenerated(doc, target);
    await writeFile(target, first.replace(/\n/g, "\r\n"));
    await checkGenerated(doc, target);
    doc.components.schemas.TaskCreate.required.push("due");
    doc.components.schemas.TaskCreate.properties.due = { type: "string" };
    await assert.rejects(checkGenerated(doc, target), /types:generate/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test("failed Python export preserves the previous snapshot", async () => {
  const dir = await mkdtemp(join(tmpdir(), "dev-c-export-"));
  try {
    const target = join(dir, "openapi.json");
    await writeFile(target, "previous snapshot\n");
    await assert.rejects(exportSchema(join(dir, "missing-python"), target), /OpenAPI/);
    assert.equal(await readFile(target, "utf8"), "previous snapshot\n");
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
