import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../../app/AppRoutes";
import { goalFixtures } from "../../test/goalFixtures";
import { API, renderWithClient, server } from "../../test/server";

function open() {
  return renderWithClient(<MemoryRouter initialEntries={["/projects"]}>
    <AppRoutes />
  </MemoryRouter>);
}

test("FR-PRJ-03：只查未封存專案，列出範圍並整列連到專案現況", async () => {
  const requests: string[] = [];
  server.use(http.get(`${API}/projects`, ({ request }) => {
    requests.push(new URL(request.url).search);
    return HttpResponse.json(goalFixtures.projects);
  }));
  open();
  const row = await screen.findByRole("listitem", { name: "範例專案，工作範圍" });
  expect(within(row).getByRole("link", { name: "範例專案，工作範圍" })).toHaveAttribute("href", "/projects/1");
  expect(requests).toEqual(["?include_archived=false"]);
  expect(screen.queryByText("此功能尚未開放。")).not.toBeInTheDocument();
});

test("空專案清單引導到匯入頁，載入時不假裝已有資料", async () => {
  server.use(http.get(`${API}/projects`, () => HttpResponse.json({ items: [], total: 0 })));
  open();
  expect(screen.getByRole("status")).toHaveTextContent("載入專案中");
  const list = screen.getByRole("region", { name: "專案清單" });
  const link = await within(list).findByRole("link", { name: "匯入專案" });
  expect(link.closest("p")).toHaveTextContent("還沒有專案，先去『匯入專案』建立。");
  expect(link).toHaveAttribute("href", "/import");
});

test("專案讀取失敗顯示錯誤並可重試，不當成空清單", async () => {
  let reads = 0;
  server.use(http.get(`${API}/projects`, () => {
    reads++;
    return reads === 1
      ? HttpResponse.json({ error: { code: "INTERNAL_ERROR", message: "暫時無法讀取", details: {} } }, { status: 500 })
      : HttpResponse.json(goalFixtures.projects);
  }));
  open();
  expect(await screen.findByRole("alert")).toHaveTextContent("暫時無法讀取");
  expect(within(screen.getByRole("region", { name: "專案清單" })).queryByRole("link", { name: "匯入專案" })).not.toBeInTheDocument();
  screen.getByRole("button", { name: "重試" }).click();
  await waitFor(() => expect(reads).toBe(2));
  expect(await screen.findByRole("link", { name: "範例專案，工作範圍" })).toBeInTheDocument();
});
