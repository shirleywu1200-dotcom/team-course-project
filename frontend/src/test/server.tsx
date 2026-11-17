// 11.7 MSW 共用入口；既有匯出保留，資料與 handlers 各有單一來源。
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { http } from "msw";
import { setupServer } from "msw/node";
import type { ReactElement } from "react";

import { makeQueryClient } from "../App";
import { devbHandlers } from "./devbFixtures";
import { API, handlers } from "./handlers";

export { API } from "./handlers";
export { reasons } from "./reasons";
export { makeTask } from "./fixtures";
export { apiError } from "./errorFixtures";
export { makeCandidate, makeSettings, RUBRIC_V0 } from "./devbFixtures";

export const server = setupServer(...handlers, ...devbHandlers);

export interface Captured {
  method: string;
  path: string;
  body: unknown;
}

// Dev-B：攔截寫入請求並記下本文；傳入同一個 log 可記錄跨端點的呼叫順序
export function capture(method: "post" | "put", path: string, respond: (body: any) => Response, log: Captured[] = []) {
  server.use(
    http[method](`${API}${path}`, async ({ request }) => {
      const body = await request.json();
      log.push({ method: method.toUpperCase(), path, body });
      return respond(body);
    }),
  );
  return log;
}

export function renderWithClient(ui: ReactElement) {
  const client = makeQueryClient();
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}
