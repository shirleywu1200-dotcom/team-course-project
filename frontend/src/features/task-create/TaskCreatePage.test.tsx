import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../../app/AppRoutes";
import { keys } from "../../api/queryKeys";
import { goalFixtures } from "../../test/goalFixtures";
import { makeTask } from "../../test/fixtures";
import { API, renderWithClient, server } from "../../test/server";

function open(path = "/tasks/new") {
  return renderWithClient(<MemoryRouter initialEntries={[path]}>
    <AppRoutes />
  </MemoryRouter>);
}

beforeEach(() => server.use(
  http.get(`${API}/projects`, () => HttpResponse.json(goalFixtures.projects)),
));

test("US-07／FR-TSK-01：必填標題與預計完成日未填時不送出，預設單點工作任務與 3 星", async () => {
  const user = userEvent.setup();
  let writes = 0;
  server.use(http.post(`${API}/tasks`, () => { writes++; return HttpResponse.json(makeTask(), { status: 201 }); }));
  open();
  expect(await screen.findByRole("heading", { name: "新增任務" })).toBeInTheDocument();
  expect(screen.getByLabelText("指定專案")).toHaveValue("");
  expect(screen.getByLabelText("任務範圍")).toHaveValue("work");
  expect(screen.getByLabelText("預設星數")).toHaveValue("3");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(writes).toBe(0);
  expect(screen.getByLabelText("任務標題")).toBeInvalid();
  await user.type(screen.getByLabelText("任務標題"), "整理範例資料");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(writes).toBe(0);
  expect(screen.getByLabelText("預計完成日")).toBeInvalid();
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-19");
  await user.clear(screen.getByLabelText("任務標題"));
  await user.type(screen.getByLabelText("任務標題"), "   ");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(writes).toBe(0);
  expect(screen.getByRole("alert")).toHaveTextContent("請填寫任務標題");
});

test("201 建立單點任務：只送允許欄位、成功提示連任務詳情、相關快取失效", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/tasks`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json(makeTask({ id: 220, title: "整理範例資料", project_id: null,
      start: "2026-11-19", orig_due: "2026-11-19", latest_due: "2026-11-19" }), { status: 201 });
  }));
  const { client } = open();
  client.setQueryData(keys.taskList(), { items: [], total: 0 });
  await screen.findByRole("option", { name: "範例專案" });
  await user.type(screen.getByLabelText("任務標題"), "整理範例資料");
  await user.type(screen.getByLabelText("完成條件"), "文件已整理");
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-19");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(await screen.findByRole("heading", { name: "今日", level: 1 })).toBeInTheDocument();
  expect(await screen.findByText("已建立任務 #220。")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "查看任務" })).toHaveAttribute("href", "/tasks/220");
  expect(bodies).toEqual([{ title: "整理範例資料", owner: "我", due: "2026-11-19",
    scope: "work", project_id: null, done_when: "文件已整理", remind: "morning",
    expected_stars: 3 }]);
  expect(client.getQueryState(keys.taskList())?.isInvalidated).toBe(true);
});

test("指定專案時省略 scope，手動星數與提醒照選擇送出", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.post(`${API}/tasks`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json(makeTask({ id: 221, project_id: 1 }), { status: 201 });
  }));
  const { client } = open();
  client.setQueryData(keys.gantt(1), { sample: true });
  await screen.findByRole("option", { name: "範例專案" });
  await user.selectOptions(screen.getByLabelText("任務範圍"), "private");
  await user.selectOptions(screen.getByLabelText("指定專案"), "1");
  await user.selectOptions(screen.getByLabelText("預設星數"), "5");
  await user.selectOptions(screen.getByLabelText("提醒"), "none");
  await user.type(screen.getByLabelText("任務標題"), "專案任務");
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-22");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  await waitFor(() => expect(bodies).toHaveLength(1));
  expect(bodies[0]).toMatchObject({ project_id: 1, expected_stars: 5, remind: "none" });
  expect(bodies[0]).not.toHaveProperty("goal_id");
  expect(bodies[0]).not.toHaveProperty("scope");
  expect(bodies[0]).not.toHaveProperty("suggested_stars");
  await waitFor(() => expect(client.getQueryState(keys.gantt(1))?.isInvalidated).toBe(true));
});

test("FR-TSK-08：明填開始日晚於期限時前端阻擋；後端欄位錯誤仍顯示在 start", async () => {
  const user = userEvent.setup();
  let writes = 0;
  server.use(http.post(`${API}/tasks`, () => {
    writes++;
    return HttpResponse.json({ error: { code: "VALIDATION_ERROR", message: "日期不符", details: { fields: ["start"] } } }, { status: 422 });
  }));
  open();
  await user.type(screen.getByLabelText("任務標題"), "範例任務");
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-20");
  await user.type(screen.getByLabelText("開始日"), "2026-11-21");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(writes).toBe(0);
  expect(screen.getByRole("alert")).toHaveTextContent("開始日不可晚於預計完成日");
  await user.clear(screen.getByLabelText("開始日"));
  await user.type(screen.getByLabelText("開始日"), "2026-11-19");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("開始日");
  expect(writes).toBe(1);
});

test("零專案仍能建立私人單點任務；首頁入口可到新增頁", async () => {
  const user = userEvent.setup();
  const bodies: unknown[] = [];
  server.use(http.get(`${API}/projects`, () => HttpResponse.json({ items: [], total: 0 })),
    http.post(`${API}/tasks`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(makeTask({ id: 222, project_id: null, scope: "private" }), { status: 201 });
    }));
  open("/");
  await user.click(screen.getByRole("link", { name: "新增任務" }));
  await user.selectOptions(screen.getByLabelText("任務範圍"), "private");
  await user.type(screen.getByLabelText("任務標題"), "私人練習");
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-19");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(await screen.findByRole("heading", { name: "今日", level: 1 })).toBeInTheDocument();
  expect(await screen.findByText("已建立任務 #222。")).toBeInTheDocument();
  expect(bodies[0]).toMatchObject({ project_id: null, scope: "private" });
  expect(bodies[0]).not.toHaveProperty("goal_id");
});

test("空庫入口流程：專案清單引導匯入，首頁建立單點任務後今日頁能看到", async () => {
  const user = userEvent.setup();
  const task = makeTask({ id: 223, project_id: null, title: "今日練習任務", start: "2026-11-19",
    orig_due: "2026-11-19", latest_due: "2026-11-19" });
  let created = false;
  server.use(http.get(`${API}/projects`, () => HttpResponse.json({ items: [], total: 0 })),
    http.get(`${API}/tasks`, () => HttpResponse.json({ items: created ? [task] : [], total: created ? 1 : 0 })),
    http.post(`${API}/tasks`, () => { created = true; return HttpResponse.json(task, { status: 201 }); }));
  open("/");
  await user.click(within(screen.getByRole("navigation", { name: "主要導覽" })).getByRole("link", { name: "專案現況" }));
  expect(await within(screen.getByRole("region", { name: "專案清單" })).findByRole("link", { name: "匯入專案" })).toHaveAttribute("href", "/import");
  await user.click(screen.getByRole("link", { name: "個人大總管" }));
  await user.click(screen.getByRole("link", { name: "新增任務" }));
  await user.type(screen.getByLabelText("任務標題"), task.title);
  await user.type(screen.getByLabelText("預計完成日"), "2026-11-19");
  await user.click(screen.getByRole("button", { name: "建立任務" }));
  expect(await screen.findByRole("heading", { name: "今日", level: 1 })).toBeInTheDocument();
  expect(await screen.findByText("已建立任務 #223。")).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: task.title })).toHaveAttribute("href", "/tasks/223");
});
