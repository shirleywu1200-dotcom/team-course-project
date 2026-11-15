import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { errorDefinitions, getErrorFixture } from "./errorFixtures";
import { adjustStartFixtures, makeSerializedTask, statusFixtures, dueFixtures } from "./fixtures";
import { adjustStartHandler, errorHandler, markIgnoredHandler, statusHandler } from "./handlers";
import { API, makeTask, reasons, server } from "./server";

const spec = readFileSync(resolve("../docs/spec.md"), "utf8");
const serializer = readFileSync(resolve("../backend/app/api/serialize.py"), "utf8");

test("spec 5.2 的全部 17 個錯誤碼與狀態集中在單一資料集", () => {
  const section = spec.slice(spec.indexOf("### 5.2 "), spec.indexOf("### 5.3 "));
  const expected = [...section.matchAll(/\|\s*(\d{3})\s*\|\s*`([A-Z_]+)`/g)]
    .map(([, status, code]) => [Number(status), code]);
  expect(expected).toHaveLength(17);
  expect(errorDefinitions.map(({ status, code }) => [status, code])).toEqual(expected);
  expect(getErrorFixture("INTERNAL_ERROR").review).toBe("待產品負責人複核");
});

test.each(errorDefinitions)("MSW 錯誤情境 $code 回傳統一格式", async ({ code }) => {
  const fixture = getErrorFixture(code);
  server.use(errorHandler(code));
  const response = await fetch(`${API}/tasks/4`);
  expect(response.status).toBe(fixture.status);
  expect(await response.json()).toEqual(fixture.body);
  expect(fixture.body.error.code).toBe(code);
  expect(fixture.body.error.message).toBeTruthy();
  expect(fixture.body.error.details).toEqual({});
});

test.each(["todo", "doing"] as const)("DA-08 狀態 %s 使用生成請求型別與完整序列化回應", async (status) => {
  const fixture = statusFixtures[status];
  server.use(statusHandler(status));
  const response = await fetch(`${API}/tasks/4/status`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fixture.request),
  });
  expect(response.status).toBe(200);
  const data = await response.json();
  expect(data).toEqual(fixture.response);
  expect(data.task.status).toBe(status);
  expect(data.event).toMatchObject({ kind: "status", field: "status", to_value: status, mark: null, delta_days: null });
});

test("status 的 task／event 欄位全集對照後端 serialize.py，不依殘缺產品型別猜欄位", () => {
  const taskSource = serializer.slice(serializer.indexOf("def task_out"), serializer.indexOf("def event_out"));
  const taskKeys = [...taskSource.matchAll(/"(\w+)"\s*:/g)].map(([, key]) => key);
  const eventSource = serializer.slice(serializer.indexOf("for k in ("), serializer.indexOf("def project_out"));
  const eventKeys = [...eventSource.matchAll(/"(\w+)"/g)].map(([, key]) => key);
  expect(Object.keys(statusFixtures.doing.response.task).sort()).toEqual(taskKeys.sort());
  expect(Object.keys(statusFixtures.doing.response.event).sort()).toEqual(eventKeys.sort());
  expect(statusFixtures.doing.response.event.ts).toMatch(/T\d{2}:\d{2}:\d{2}\+08:00$/);
});

test("DA-11 MARK_IGNORED 仍為 200 警告，不寫入我的註記", async () => {
  server.use(markIgnoredHandler());
  const response = await fetch(`${API}/tasks/4/adjust-due`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dueFixtures.markIgnored.request),
  });
  expect(response.status).toBe(200);
  const data = await response.json();
  expect(data).toEqual(dueFixtures.markIgnored.response);
  expect(data.warnings).toEqual(["MARK_IGNORED"]);
  expect(data.event).toMatchObject({ mine: false, mark: null });
  expect(data.error).toBeUndefined();
});

test("AC-62 adjust-start 成功快照只改開始日與版本，標示待 Dev-A 實作", async () => {
  const fixture = adjustStartFixtures.success;
  const response = await fetch(`${API}/tasks/3/adjust-start`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fixture.request),
  });
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual(fixture.response);
  expect(fixture.response.task).toEqual({ id: 3, start_date: "2026-11-17", orig_due: "2026-11-20", latest_due: "2026-11-20", version: 5 });
  expect(fixture.response.event).toMatchObject({ kind: "task", field: "start_date", mark: null, delta_days: null });
  expect(fixture.implementation).toBe("待 Dev-A 實作（todo 2.11）");
});

test("AC-62 START_AFTER_DUE 是 200 警告，不阻擋開始日調整", async () => {
  server.use(adjustStartHandler("afterDue"));
  const fixture = adjustStartFixtures.afterDue;
  const response = await fetch(`${API}/tasks/3/adjust-start`, { method: "POST", body: JSON.stringify(fixture.request) });
  expect(response.status).toBe(200);
  const data = await response.json();
  expect(data.warnings).toEqual(["START_AFTER_DUE"]);
  expect(data.task.start_date).toBe("2026-11-21");
  expect(data.task.latest_due).toBe("2026-11-20");
  expect(data.error).toBeUndefined();
});

test.each(["taskDone", "noChange", "outOfRange", "staleVersion", "validationError"] as const)(
  "adjust-start 錯誤情境 %s 沿用既有錯誤碼", async (scenario) => {
    const fixture = adjustStartFixtures[scenario];
    server.use(adjustStartHandler(scenario));
    const response = await fetch(`${API}/tasks/3/adjust-start`, { method: "POST", body: JSON.stringify(fixture.request) });
    expect(response.status).toBe(fixture.status);
    expect(await response.json()).toEqual(fixture.response);
    expect(fixture.implementation).toBe("待 Dev-A 實作（todo 2.11）");
  },
);

test("makeTask 與原因選項相容，測試資料可獨立修改而不污染後續情境", async () => {
  const changed = makeSerializedTask();
  changed.title = "範例修改";
  expect(makeSerializedTask().title).toBe(makeTask().title);
  expect(Object.keys(makeTask())).toHaveLength(13);
  const response = await fetch(`${API}/meta/reasons`);
  expect(await response.json()).toEqual(reasons);
  expect(reasons.due.filter((reason) => reason.external).map((reason) => reason.code)).toEqual([
    "wait_external", "scope_change_external", "resource_external",
  ]);
});

test("產品程式不得引用 src/test 的手寫形狀或 fixture", () => {
  const root = resolve("src");
  const forbidden: string[] = [];
  function scan(directory: string) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) { if (entry.name !== "test") scan(path); continue; }
      if (!/\.tsx?$/.test(path) || /\.(test|typecheck)\.tsx?$/.test(path)) continue;
      const source = readFileSync(path, "utf8");
      for (const [, target] of source.matchAll(/(?:from\s*|import\s*)["']([^"']+)["']/g)) {
        if (target.startsWith(".") && resolve(dirname(path), target).startsWith(resolve(root, "test"))) forbidden.push(path);
      }
    }
  }
  scan(root);
  expect(forbidden).toEqual([]);
});
