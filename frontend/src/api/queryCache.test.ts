import { readFileSync } from "node:fs";
import { QueryObserver } from "@tanstack/react-query";
import { keys } from "./queries";
import { normalizeEventFilters } from "./queryKeys";
import { makeQueryClient } from "./queryClient";
import { mutationInvalidations, runMutationWithInvalidation } from "./queryCache";

const expected = [
  ["POST /projects", ["projects"]],
  ["PATCH /projects/{project_id}", ["projects"]],
  ["POST /projects/{project_id}/archive", ["projects"]],
  ["POST /projects/{project_id}/bulk-shift/preview", []],
  ["POST /projects/{project_id}/bulk-shift/commit", ["tasks", "timeManagement", "gantt", "events"]],
  ["POST /tasks", ["tasks", "projects", "gantt", "events"]],
  ["PATCH /tasks/{task_id}/owner", ["tasks", "gantt", "events"]],
  ["POST /tasks/{task_id}/status", ["tasks", "gantt", "events"]],
  ["POST /tasks/{task_id}/block", ["tasks", "gantt", "events"]],
  ["POST /tasks/{task_id}/adjust-start", ["tasks", "gantt", "events"]],
  ["POST /tasks/{task_id}/complete", ["tasks", "timeManagement", "gantt", "events", "feedbackPending"]],
  ["POST /tasks/{task_id}/adjust-due", ["tasks", "timeManagement", "gantt", "events"]],
  ["POST /tasks/{task_id}/baseline-correction/preview", []],
  ["POST /tasks/{task_id}/baseline-correction/commit", ["tasks", "projects", "gantt", "events"]],
  ["POST /events/{event_id}/annotations", ["tasks", "timeManagement", "events"]],
] as const;

test("OpenAPI 的全部動作都列入失效規則，11.3 的 15 個動作列入 README", () => {
  const schema = JSON.parse(readFileSync("openapi.json", "utf8"));
  const operations = Object.entries(schema.paths).flatMap(([path, item]) =>
    Object.keys(item as object).map(method => `${method.toUpperCase()} ${path.replace('/api/v1', '')}`));
  expect(operations.length).toBeGreaterThan(0);
  expect(operations.filter(op => !op.startsWith("GET ")).sort()).toEqual(Object.keys(mutationInvalidations).sort());
  const readme = readFileSync("README.md", "utf8");
  for (const [action, resources] of expected) {
    expect(readme).toContain(`| \`${action}\` | ${resources.join("、") || "無"} |`);
    expect(mutationInvalidations[action]).toEqual(resources);
  }
});

for (const [action, resources] of expected) {
  test(`${action} 成功只使對照表指定的查詢失效`, async () => {
    const client = makeQueryClient();
    const entries = [
      ["tasks", keys.task(4)], ["tasks", keys.projectTasks(1)],
      ["tasks", keys.taskList({ owner: "我", due_before: "2026-11-20" })],
      ["projects", keys.project(1)], ["projects", keys.projectList()],
      ["gantt", keys.gantt(1)], ["events", keys.events({ task_id: 4 })],
      ["timeManagement", keys.timeManagement()], ["reasons", keys.reasons], ["health", keys.health],
    ] as const;
    for (const [, key] of entries) client.setQueryData(key, { value: 1 });
    const response = { version: 2 };
    const write = vi.fn().mockResolvedValue(response);
    expect(await runMutationWithInvalidation(client, action, write)).toBe(response);
    expect(write).toHaveBeenCalledTimes(1);
    for (const [resource, key] of entries) {
      expect(client.getQueryState(key)?.isInvalidated).toBe((resources as readonly string[]).includes(resource));
    }
    client.clear();
  });
}

test("失敗不失效、不重送，也不攔截 STALE_VERSION", async () => {
  const client = makeQueryClient();
  client.setQueryData(keys.task(4), { version: 1 });
  const error = { code: "STALE_VERSION" };
  const write = vi.fn().mockRejectedValue(error);
  await expect(runMutationWithInvalidation(client, "POST /tasks/{task_id}/adjust-start", write)).rejects.toBe(error);
  expect(write).toHaveBeenCalledTimes(1);
  expect(client.getQueryState(keys.task(4))?.isInvalidated).toBe(false);
  client.clear();
});

test("12.9：完成與保存回報使待補清單失效，保存回報也刷新任務與統計", async () => {
  expect(keys.feedbackPending()).toEqual(["feedback", "pending"]);
  expect(mutationInvalidations["POST /tasks/{task_id}/complete"]).toContain("feedbackPending");
  expect(mutationInvalidations["PUT /tasks/{task_id}/feedback"]).toEqual(expect.arrayContaining([
    "tasks", "timeManagement", "feedbackPending",
  ]));
  for (const action of ["POST /tasks/{task_id}/complete", "PUT /tasks/{task_id}/feedback"] as const) {
    const client = makeQueryClient();
    client.setQueryData(keys.feedbackPending(), { items: [], total: 0 });
    await runMutationWithInvalidation(client, action, async () => undefined);
    expect(client.getQueryState(keys.feedbackPending())?.isInvalidated).toBe(true);
    client.clear();
  }
});

test("S：URL、query key 與請求共用同一份歷程 filters 正規化", () => {
  const url = new URLSearchParams("project_id=0012&task_id=4&batch_id=8&limit=25&offset=50&from=2026-11-01&to=2026-11-30&kind=due");
  const normalized = normalizeEventFilters(url);
  expect(normalized).toEqual({ project_id: "12", task_id: 4, batch_id: 8, limit: 25, offset: 50,
    from: "2026-11-01", to: "2026-11-30", kind: "due" });
  expect(keys.events(url)).toEqual(keys.events(normalized));
  expect(keys.events({ task_id: 4 })).toEqual(["events", { task_id: 4, limit: 100, offset: 0 }]);
  expect(normalizeEventFilters(new URLSearchParams("project_id=none&task_id=&from=")))
    .toEqual({ project_id: "none", limit: 100, offset: 0 });
  expect(keys.gantt(12)).toEqual(["gantt", 12]);
});

test.each([
  "POST /projects/import/commit",
  "POST /ingest",
  "POST /candidates/{candidate_id}/confirm",
  "POST /candidates/{candidate_id}/clarify",
  "POST /candidates/{candidate_id}/create-task",
  "POST /candidates/{candidate_id}/ignore",
] as const)("S：%s 造成任務或待確認候選變動時使 gantt 失效", action => {
  expect(mutationInvalidations[action]).toContain("gantt");
});

test("成功會等待使用中的查詢重新讀取；未使用的查詢只標失效", async () => {
  const client = makeQueryClient();
  const read = vi.fn().mockResolvedValue({ version: 2 });
  client.setQueryData(keys.task(4), { version: 1 });
  client.setQueryData(keys.projectTasks(1), []);
  const observer = new QueryObserver(client, { queryKey: keys.task(4), queryFn: read, staleTime: Infinity });
  const unsubscribe = observer.subscribe(() => {});
  await runMutationWithInvalidation(client, "POST /tasks/{task_id}/adjust-start", async () => undefined);
  expect(read).toHaveBeenCalledTimes(1);
  expect(client.getQueryData(keys.task(4))).toEqual({ version: 2 });
  expect(client.getQueryState(keys.projectTasks(1))?.isInvalidated).toBe(true);
  unsubscribe(); client.clear();
});

test("舊查詢鍵相容、篩選鍵獨立且日期不轉時區", () => {
  expect(keys.task(4)).toEqual(["tasks", 4]);
  expect(keys.projectTasks(1)).toEqual(["tasks", "project", 1]);
  expect(keys.reasons).toEqual(["meta", "reasons"]);
  expect(keys.taskList({ project_id: "1" })).toEqual(keys.projectTasks(1));
  expect(keys.taskList({ project_id: "none" })).not.toEqual(keys.taskList());
  expect(keys.taskList({ due_before: "2026-11-20" })).toContainEqual({ due_before: "2026-11-20" });
  expect(keys.projectList()).toEqual(keys.projectList({ include_archived: false }));
});

test("QueryClient 保留既有重試與視窗焦點設定", () => {
  const client = makeQueryClient();
  expect(client.getDefaultOptions().queries).toEqual({ retry: false, refetchOnWindowFocus: false });
  client.clear();
});

test("12.13：週報鍵按週與 id 分開；產稿和儲存人工版都登記 weeklyReports 失效", () => {
  expect(keys.weeklyReportByWeek("2026-11-09")).toEqual(["reports", "weekly", "week", "2026-11-09"]);
  expect(keys.weeklyReport(7)).toEqual(["reports", "weekly", 7]);
  expect(mutationInvalidations["POST /reports/weekly/draft"]).toEqual(["weeklyReports"]);
  expect(mutationInvalidations["PUT /reports/weekly/{report_id}/manual"]).toEqual(["weeklyReports"]);
});
