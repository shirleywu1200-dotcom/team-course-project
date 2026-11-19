import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "../../api/client";
import { runMutationWithInvalidation } from "../../api/queryCache";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";

type FeedbackSave = components["schemas"]["FeedbackSave"];
type FeedbackSaveOut = components["schemas"]["FeedbackSaveOut"];

export function FeedbackForm({ taskId, rubricId }: { taskId: number; rubricId: number }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  // 面板開啟時固定版本；背景重讀或量表換版不會改這次送出的 rubric_id。
  const [openedRubricId] = useState(rubricId);
  const [stars, setStars] = useState("");
  const [energy, setEnergy] = useState("");
  const [invest, setInvest] = useState("");
  const mutation = useMutation({ mutationFn: () => {
    const body = {
      actual_stars: Number(stars), energy: energy as FeedbackSave["energy"],
      ...(invest ? { invest_vs_expected: invest as FeedbackSave["invest_vs_expected"] } : {}),
      rubric_id: openedRubricId,
    } satisfies FeedbackSave;
    return runMutationWithInvalidation(qc, "PUT /tasks/{task_id}/feedback", () =>
      api<FeedbackSaveOut>(`/tasks/${taskId}/feedback`, { method: "PUT", body }));
  }, onSuccess: result => {
    qc.setQueryData(keys.feedback(taskId), result.feedback);
    navigate("/today", { state: { feedbackSaved: result.feedback } });
  }, onError: error => {
    if (error instanceof ApiError && error.code === "FEEDBACK_EXISTS") {
      void qc.invalidateQueries({ queryKey: keys.feedback(taskId) });
    }
  } });

  return <form className="card" aria-label="完成回報表單" onSubmit={event => {
    event.preventDefault();
    if (stars && energy) mutation.mutate();
  }}>
    <div className="field"><label htmlFor={`stars-${taskId}`}>實際達成星數</label>
      <select id={`stars-${taskId}`} value={stars} onChange={event => setStars(event.target.value)}>
        <option value="">請選擇</option>
        {[1, 2, 3, 4, 5].map(value => <option key={value} value={value}>{value} 星</option>)}
      </select></div>
    <div className="field"><label htmlFor={`energy-${taskId}`}>自評精力</label>
      <select id={`energy-${taskId}`} value={energy} onChange={event => setEnergy(event.target.value)}>
        <option value="">請選擇</option><option value="high">高</option><option value="mid">中</option><option value="low">低</option>
      </select></div>
    <div className="field"><label htmlFor={`invest-${taskId}`}>投入相對預期</label>
      <select id={`invest-${taskId}`} value={invest} onChange={event => setInvest(event.target.value)}>
        <option value="">不填寫</option><option value="less">少於預期</option>
        <option value="as_expected">如期</option><option value="more">多於預期</option>
      </select></div>
    {mutation.error && <ErrorBanner error={mutation.error} />}
    <div className="actions"><button type="submit" className="primary" disabled={!stars || !energy || mutation.isPending}>儲存完成回報</button>
      <button type="button" onClick={() => navigate("/today")}>稍後補</button></div>
  </form>;
}
