// 審查：TargetPicker 與其他頁共用 keys.projectList() 時，快取內容必須是 API 原形（ProjectListOut）。

import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { keys } from "../../api/queries";
import { API, renderWithClient, server } from "../../test/server";
import { TargetPicker } from "./TargetPicker";

const LIST = { items: [{ id: 3, name: "家裡的事", scope: "private", audience: "none", line_group_id: null,
  created_at: "2026-11-01T09:00:00+08:00", updated_at: "2026-11-01T09:00:00+08:00", archived_at: null }], total: 1 };
const DEST = { mode: "existing" as const, newName: "", projectId: null };

test("專案清單快取存 API 原形，其他頁以同一個鍵預先放入的資料也能顯示", async () => {
  server.use(http.get(`${API}/projects`, () => HttpResponse.json(LIST)));
  const { client } = renderWithClient(<TargetPicker dest={DEST} onChange={() => {}} />);
  expect(await screen.findByRole("option", { name: "家裡的事（私人・不會送 AI）" })).toBeInTheDocument();
  expect(client.getQueryData(keys.projectList())).toEqual(LIST);
});
