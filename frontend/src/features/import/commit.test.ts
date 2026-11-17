// 12.7 保存條件與 commit 內容（SDD 第 2 節）。

import type { ImportPreview, ImportRow } from "../../api/types";
import { buildCommitBody, canCommit } from "./commit";

const row = (index: number, over: Partial<ImportRow> = {}): ImportRow => ({
  index, title: `任務 ${index}`, owner: "我", start: "2026-11-16", end: "2026-11-18", blocking: false, issues: [], ...over,
});

const preview = (rows: ImportRow[], mapped_by: ImportPreview["column_map"]["mapped_by"] = "rule"): ImportPreview => ({
  ai_status: "ok",
  header: ["任務", "負責人", "開始", "結束"],
  column_map: { title: 0, owner: 1, start: 2, end: 3, mapped_by },
  rows,
  summary: { importable: rows.filter((r) => !r.blocking).length, blocking: rows.filter((r) => r.blocking).length },
});

const bad = row(1, { end: null, blocking: true, issues: [{ level: "error", code: "END_MISSING", message: "缺結束日" }] });

test("規則對應、無錯誤列：可保存", () => {
  expect(canCommit(preview([row(0)]), false, new Set())).toEqual({ ok: true });
});

test("AI 對應未確認：不能保存", () => {
  expect(canCommit(preview([row(0)], "ai"), false, new Set())).toEqual({ ok: false, reason: "請先確認欄位對應" });
  expect(canCommit(preview([row(0)], "ai"), true, new Set())).toEqual({ ok: true });
});

test("錯誤列未略過：不能保存；略過後可以", () => {
  expect(canCommit(preview([row(0), bad]), false, new Set())).toEqual({ ok: false, reason: "還有 1 列錯誤未處理" });
  expect(canCommit(preview([row(0), bad]), false, new Set([1]))).toEqual({ ok: true });
});

test("全部略過、沒有可匯入的列：不能保存", () => {
  expect(canCommit(preview([row(0), bad]), false, new Set([0, 1]))).toEqual({ ok: false, reason: "至少要有 1 列可匯入" });
});

test("還沒對應到必填欄位（mapped_by=null）：不能保存", () => {
  expect(canCommit(preview([], null), false, new Set())).toEqual({ ok: false, reason: "請先指定任務名稱與結束欄位" });
});

test("commit 原樣帶回 preview 的列並加上 skip", () => {
  const body = buildCommitBody({ target: "new", newName: "官網改版" }, [row(0), bad], new Set([1]));
  expect(body).toEqual({
    target: "new",
    new_name: "官網改版",
    rows: [
      { index: 0, title: "任務 0", owner: "我", start: "2026-11-16", end: "2026-11-18", skip: false },
      { index: 1, title: "任務 1", owner: "我", start: "2026-11-16", end: null, skip: true },
    ],
  });
});

test("匯入既有專案時不送 new_name", () => {
  expect(buildCommitBody({ target: 3, newName: "" }, [row(0)], new Set())).toEqual({
    target: 3,
    rows: [{ index: 0, title: "任務 0", owner: "我", start: "2026-11-16", end: "2026-11-18", skip: false }],
  });
});
