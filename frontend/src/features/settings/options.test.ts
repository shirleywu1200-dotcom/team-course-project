import { makeSettings } from "../../test/server";
import { changedFields } from "./options";

test("只回傳指定欄位中有改的值", () => {
  const saved = makeSettings();
  const draft = makeSettings({ confirm_time: "21:00", role: "both" });
  expect(changedFields(saved, draft, ["confirm_time", "confirm_cap_min"])).toEqual({ confirm_time: "21:00" });
});

test("陣列欄位以內容比較，順序不同視為有改", () => {
  const saved = makeSettings();
  expect(changedFields(saved, makeSettings({ goal_types_enabled: ["growth", "time", "expectation"] }), ["goal_types_enabled"])).toEqual({});
  expect(changedFields(saved, makeSettings({ goal_types_enabled: ["growth"] }), ["goal_types_enabled"]))
    .toEqual({ goal_types_enabled: ["growth"] });
});
