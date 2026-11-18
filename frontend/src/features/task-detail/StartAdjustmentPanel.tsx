import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../../api/client";
import { keys, queryRoots } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { DatePicker } from "../../components/DatePicker";
import { ErrorBanner } from "../../components/ErrorBanner";

type Task = components["schemas"]["TaskOut"];
type AdjustStart = components["schemas"]["AdjustStart"];
type AdjustStartOut = components["schemas"]["AdjustStartOut"];

export function StartAdjustmentPanel({ task, onClose }: { task: Task; onClose: () => void }) {
  const qc = useQueryClient();
  const [newStart, setNewStart] = useState("");
  const [notice, setNotice] = useState("");
  const previousVersion = useRef(task.version);
  const mutation = useMutation({
    mutationFn: () => api<AdjustStartOut>(`/tasks/${task.id}/adjust-start`, {
      body: { new_start: newStart, expected_version: task.version } satisfies AdjustStart,
    }),
    onSuccess: response => {
      setNewStart("");
      qc.setQueryData(keys.task(task.id), response.task);
      void qc.invalidateQueries({ queryKey: queryRoots.events });
      void qc.invalidateQueries({ queryKey: queryRoots.gantt });
      setNotice(response.warnings.includes("START_AFTER_DUE") ? "開始日晚於最新預計日；期限未變。" : "開始日已更新。");
    },
    onError: error => {
      if (error instanceof ApiError && error.code === "STALE_VERSION") {
        setNewStart("");
        void qc.invalidateQueries({ queryKey: keys.task(task.id) });
      }
    },
  });
  useEffect(() => {
    if (previousVersion.current === task.version) return;
    previousVersion.current = task.version;
    setNewStart("");
  }, [task.version]);

  return <section className="card" aria-label="調整開始日面板">
    <h2>調整開始日</h2>
    <DatePicker id="detail-new-start" label="新的開始日" value={newStart} onChange={setNewStart} />
    {mutation.error && <ErrorBanner error={mutation.error} />}
    {notice && <p role="status">{notice}</p>}
    <button type="button" disabled={!newStart || mutation.isPending} onClick={() => mutation.mutate()}>確認開始日</button>
    <button type="button" onClick={onClose}>關閉</button>
  </section>;
}
