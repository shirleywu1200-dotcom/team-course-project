// MSW 模擬後端（只對 spec 第 5 章的契約，不需要後端執行；todo 0.1 第 4 點）。
// 暫代 Dev-C todo 11.7 的 MSW 資料集：只涵蓋 Dev-A 三頁用到的端點。

import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { ReactElement } from "react";

import { makeQueryClient } from "../App";
import type { ReasonsMeta, Task } from "../api/types";

export const API = "http://localhost:3000/api/v1";

export const reasons: ReasonsMeta = {
  due: [
    { code: "finished_early", label: "提早完成條件達成", direction: "earlier", external: false },
    { code: "less_work", label: "工作量比預期少", direction: "earlier", external: false },
    { code: "prereq_early", label: "前置工作提早到位", direction: "earlier", external: false },
    { code: "other", label: "其他", direction: "earlier", external: false },
    { code: "underestimated", label: "估計不準（我低估）", direction: "later", external: false },
    { code: "self_interrupt", label: "被其他事插隊（我自己排程）", direction: "later", external: false },
    { code: "wait_external", label: "等對方或客戶回覆（外部）", direction: "later", external: true },
    { code: "scope_change_external", label: "需求變更（外部）", direction: "later", external: true },
    { code: "resource_external", label: "資源或環境未到位（外部）", direction: "later", external: true },
    { code: "other", label: "其他", direction: "later", external: false },
  ],
  baseline_types: [
    { code: "correction", label: "更正錯誤" },
    { code: "rebaseline", label: "客戶或主管正式改變承諾日" },
  ],
  baseline_reasons: [
    { code: "input_error", label: "匯入或輸入錯誤" },
    { code: "plan_date_wrong", label: "原計畫日期寫錯" },
    { code: "formal_commitment_change", label: "客戶或主管正式改變承諾日" },
    { code: "other", label: "其他" },
  ],
};

export function makeTask(over: Partial<Task> = {}): Task {
  return {
    id: 4, project_id: 1, title: "確認驗收條件", owner: "我", scope: "work", start: "2026-11-14",
    orig_due: "2026-11-18", latest_due: "2026-11-18", delta_days: 0, status: "todo", blocked: false,
    done_date: null, version: 1, ...over,
  };
}

export function apiError(status: number, code: string, details = {}) {
  return HttpResponse.json({ error: { code, message: code, details } }, { status });
}

export const server = setupServer(http.get(`${API}/meta/reasons`, () => HttpResponse.json(reasons)));

export function renderWithClient(ui: ReactElement) {
  const client = makeQueryClient();
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}
