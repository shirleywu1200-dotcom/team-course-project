// 11.7 MSW 共用入口；既有匯出保留，資料與 handlers 各有單一來源。
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { setupServer } from "msw/node";
import type { ReactElement } from "react";

import { makeQueryClient } from "../App";
import { handlers } from "./handlers";

export { API } from "./handlers";
export { reasons } from "./reasons";
export { makeTask } from "./fixtures";
export { apiError } from "./errorFixtures";

export const server = setupServer(...handlers);

export function renderWithClient(ui: ReactElement) {
  const client = makeQueryClient();
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}
