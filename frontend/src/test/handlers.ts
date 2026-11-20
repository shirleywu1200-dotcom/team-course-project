import { http, HttpResponse } from "msw";
import { getErrorFixture, type ErrorFixtureCode } from "./errorFixtures";
import { adjustStartFixtures, dueFixtures, historyFixtures, makeSerializedTask, makeTaskDetailFixture, overviewFixtures, statusFixtures, timeManagementFixtures, todayFixtures } from "./fixtures";
import { goalFixtures } from "./goalFixtures";
import { reasons } from "./reasons";

export const API = "http://localhost:3000/api/v1";

// 固定 fixture，不驗證請求、不持久化狀態；需要另一情境時以 server.use 覆寫。
export function statusHandler(status: keyof typeof statusFixtures = "doing") {
  const fixture = statusFixtures[status];
  return http.post(`${API}/tasks/${fixture.response.task.id}/status`, () => HttpResponse.json(fixture.response));
}

export function markIgnoredHandler() {
  const fixture = dueFixtures.markIgnored;
  return http.post(`${API}/tasks/${fixture.response.task.id}/adjust-due`, () => HttpResponse.json(fixture.response));
}

// 只測錯誤格式，不代表此端點在產品中會回全部錯誤碼（例如 AI_UNAVAILABLE）。
export function errorHandler(code: ErrorFixtureCode) {
  const fixture = getErrorFixture(code);
  return http.get(`${API}/tasks/4`, () => HttpResponse.json(fixture.body, { status: fixture.status }));
}

// 正式 adjust-start 的測試情境，不會向真正後端補送請求。
export function adjustStartHandler(scenario: keyof typeof adjustStartFixtures = "success") {
  const fixture = adjustStartFixtures[scenario];
  return http.post(`${API}/tasks/3/adjust-start`, () => HttpResponse.json(fixture.response, { status: fixture.status }));
}

export const handlers = [
  http.get(`${API}/goals`, () => HttpResponse.json(goalFixtures.list)),
  http.get(`${API}/goals/1/stats`, () => HttpResponse.json(goalFixtures.insufficient)),
  http.get(`${API}/goals/matrix`, () => HttpResponse.json(goalFixtures.matrix)),
  http.get(`${API}/goal-links/pending`, () => HttpResponse.json(goalFixtures.pending)),
  http.get(`${API}/stats/time-management`, () => HttpResponse.json(timeManagementFixtures.insufficient)),
  http.get(`${API}/meta/reasons`, () => HttpResponse.json(reasons)),
  http.get(`${API}/meta/today`, () => HttpResponse.json(todayFixtures.today)),
  http.get(`${API}/tasks`, () => HttpResponse.json({ items: [makeSerializedTask()], total: 1 })),
  http.get(`${API}/tasks/4`, () => HttpResponse.json(makeTaskDetailFixture())),
  http.get(`${API}/tasks/4/feedback`, () => HttpResponse.json({ error: { code: "NOT_FOUND", message: "NOT_FOUND", details: {} } }, { status: 404 })),
  http.get(`${API}/feedback/pending`, () => HttpResponse.json(todayFixtures.pending)),
  http.get(`${API}/events`, () => HttpResponse.json(historyFixtures.marked)),
  http.get(`${API}/projects/1`, () => HttpResponse.json(overviewFixtures.project)),
  http.get(`${API}/projects/1/gantt`, () => HttpResponse.json(overviewFixtures.gantt)),
  http.post(`${API}/tasks/4/adjust-due`, () => HttpResponse.json(dueFixtures.success.response)),
  statusHandler(),
  adjustStartHandler(),
];
