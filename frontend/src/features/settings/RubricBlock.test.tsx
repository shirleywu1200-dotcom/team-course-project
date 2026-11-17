// 12.11 量表區塊的 Dev 元件測試（Vitest＋MSW；SDD D-2(c)、D-3）。

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse } from "msw";

import { apiError, capture, renderWithClient, RUBRIC_V0 } from "../../test/server";
import { QUESTIONS } from "./options";
import { RubricBlock } from "./RubricBlock";

const DRAFT = ["一", "二", "三", "四", "五"].map((s) => `草稿第${s}句`);
const ANSWERS = { q1: QUESTIONS[0].options[0], q2: QUESTIONS[1].options[0], q3: QUESTIONS[2].options[0] };
const okDraft = () => HttpResponse.json({ ai_status: "ok", draft: DRAFT });
const created = () => HttpResponse.json({ id: 2, version: 1 }, { status: 201 });

async function answerAll(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" }));
  for (const q of QUESTIONS) await user.click(screen.getByLabelText(q.options[0]));
}

test("顯示目前版本的 5 句", async () => {
  renderWithClient(<RubricBlock />);
  expect(await screen.findByText(RUBRIC_V0.levels[2])).toBeInTheDocument();
  expect(screen.getByText("v0")).toBeInTheDocument();
});

test("三題都答完才能產生草稿；草稿可改，確認時帶 draft 給後端記 AI 採用情形", async () => {
  const user = userEvent.setup();
  const ask = capture("post", "/rubrics/interview", okDraft);
  const save = capture("post", "/rubrics", created);
  const onConfirmed = vi.fn();
  renderWithClient(<RubricBlock onConfirmed={onConfirmed} />);

  await user.click(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" }));
  const gen = screen.getByRole("button", { name: "產生草稿" });
  await user.click(screen.getByLabelText(QUESTIONS[0].options[0]));
  await user.click(screen.getByLabelText(QUESTIONS[1].options[0]));
  expect(gen).toBeDisabled();
  await user.click(screen.getByLabelText(QUESTIONS[2].options[0]));
  await user.click(gen);

  expect(ask[0].body).toEqual(ANSWERS);
  const third = await screen.findByLabelText("3 星");
  expect(third).toHaveValue(DRAFT[2]);
  await user.clear(third);
  await user.type(third, "我改過的第三句");
  await user.click(screen.getByRole("button", { name: "確認成為 v1" }));

  await waitFor(() => expect(onConfirmed).toHaveBeenCalledWith(1));
  expect(save[0].body).toEqual({
    levels: [DRAFT[0], DRAFT[1], "我改過的第三句", DRAFT[3], DRAFT[4]],
    interview: { ...ANSWERS, draft: DRAFT },
  });
  expect(await screen.findByRole("status")).toHaveTextContent("量表 v1 已確認");
});

test("有一句空白時不能確認", async () => {
  const user = userEvent.setup();
  capture("post", "/rubrics/interview", okDraft);
  renderWithClient(<RubricBlock />);
  await answerAll(user);
  await user.click(screen.getByRole("button", { name: "產生草稿" }));
  await user.clear(await screen.findByLabelText("1 星"));
  expect(screen.getByRole("button", { name: "確認成為 v1" })).toBeDisabled();
});

test("AI 失敗（503）時以目前 5 句為底稿手動改寫，確認時不帶 draft", async () => {
  const user = userEvent.setup();
  capture("post", "/rubrics/interview", () => apiError(503, "AI_UNAVAILABLE"));
  const save = capture("post", "/rubrics", created);
  renderWithClient(<RubricBlock />);
  await answerAll(user);
  await user.click(screen.getByRole("button", { name: "產生草稿" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("AI 暫時無法產生草稿");
  expect(screen.getByLabelText("5 星")).toHaveValue(RUBRIC_V0.levels[4]);
  await user.click(screen.getByRole("button", { name: "確認成為 v1" }));
  await waitFor(() => expect(save).toHaveLength(1));
  expect(save[0].body).toEqual({ levels: RUBRIC_V0.levels, interview: ANSWERS });
});

test("AI 失敗時可直接沿用目前版本，不寫入", async () => {
  const user = userEvent.setup();
  capture("post", "/rubrics/interview", () => apiError(503, "AI_UNAVAILABLE"));
  const save = capture("post", "/rubrics", created);
  renderWithClient(<RubricBlock />);
  await answerAll(user);
  await user.click(screen.getByRole("button", { name: "產生草稿" }));
  await user.click(await screen.findByRole("button", { name: "沿用 v0" }));
  expect(screen.getByRole("button", { name: "用三個問題訂我自己的量表" })).toBeInTheDocument();
  expect(save).toHaveLength(0);
});

test("訪談或草稿進行中時通知外層，回到檢視時解除", async () => {
  const user = userEvent.setup();
  const onEditingChange = vi.fn();
  renderWithClient(<RubricBlock onEditingChange={onEditingChange} />);
  await user.click(await screen.findByRole("button", { name: "用三個問題訂我自己的量表" }));
  expect(onEditingChange).toHaveBeenLastCalledWith(true);
  await user.click(screen.getByRole("button", { name: "取消" }));
  expect(onEditingChange).toHaveBeenLastCalledWith(false);
});
