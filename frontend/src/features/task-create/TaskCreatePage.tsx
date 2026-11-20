import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "../../api/client";
import { runMutationWithInvalidation } from "../../api/queryCache";
import { keys } from "../../api/queryKeys";
import { fetchProjects } from "../../api/queries";
import type { components } from "../../api/types.generated";
import { DatePicker } from "../../components/DatePicker";
import { ErrorBanner } from "../../components/ErrorBanner";

type TaskCreate = components["schemas"]["TaskCreate"];
type TaskOut = components["schemas"]["TaskOut"];
type GoalListOut = components["schemas"]["GoalListOut"];

export function TaskCreatePage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const projects = useQuery({ queryKey: keys.projectList(), queryFn: fetchProjects });
  const goals = useQuery({ queryKey: keys.goals(),
    queryFn: () => api<GoalListOut>("/goals?include_archived=true") });
  const [title, setTitle] = useState("");
  const [owner, setOwner] = useState("我");
  const [due, setDue] = useState("");
  const [start, setStart] = useState("");
  const [scope, setScope] = useState<"work" | "private">("work");
  const [projectId, setProjectId] = useState("");
  const [doneWhen, setDoneWhen] = useState("");
  const [remind, setRemind] = useState<"morning" | "eve_before" | "none">("morning");
  const [goalId, setGoalId] = useState("");
  const [expectedStars, setExpectedStars] = useState(3);
  const [dateError, setDateError] = useState("");
  const [titleError, setTitleError] = useState("");

  const create = useMutation({
    mutationFn: (body: TaskCreate) => runMutationWithInvalidation(qc, "POST /tasks", () =>
      api<TaskOut>("/tasks", { method: "POST", body })),
    onSuccess: result => navigate("/today", { state: { createdTaskId: result.id } }),
  });
  const startFieldError = create.error instanceof ApiError && create.error.code === "VALIDATION_ERROR" &&
    Array.isArray(create.error.details.fields) && create.error.details.fields.includes("start");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      setTitleError("請填寫任務標題。");
      return;
    }
    setTitleError("");
    if (start && start > due) {
      setDateError("開始日不可晚於預計完成日。");
      return;
    }
    setDateError("");
    const body = {
      title: title.trim(), owner: owner.trim() || "我", due,
      project_id: projectId ? Number(projectId) : null,
      ...(!projectId ? { scope } : {}),
      ...(start ? { start } : {}),
      done_when: doneWhen, remind, goal_id: goalId ? Number(goalId) : null,
      expected_stars: expectedStars,
    } satisfies TaskCreate;
    create.mutate(body);
  }

  return <main>
    <h1>新增任務</h1>
    <p className="muted">預計完成日建立後成為原訂日期；之後改期或更正原訂日期請到任務詳情。</p>
    {projects.error && <ErrorBanner error={projects.error} message="專案清單讀取失敗，仍可建立單點任務。" />}
    {goals.error && <ErrorBanner error={goals.error} message="目標清單讀取失敗，仍可不關聯目標。" />}
    {create.error && !startFieldError && <ErrorBanner error={create.error} />}
    <form onSubmit={submit}>
      <div className="field"><label htmlFor="task-title">任務標題</label>
        <input id="task-title" value={title} onChange={event => { setTitle(event.target.value); setTitleError(""); }} required />
      </div>
      {titleError && <p role="alert">{titleError}</p>}
      <div className="field"><label htmlFor="task-owner">負責人</label>
        <input id="task-owner" value={owner} onChange={event => setOwner(event.target.value)} />
      </div>
      <DatePicker id="task-due" label="預計完成日" value={due} onChange={value => {
        setDue(value); setDateError(""); create.reset();
      }} required />
      <DatePicker id="task-start" label="開始日" value={start} onChange={value => {
        setStart(value); setDateError(""); create.reset();
      }} />
      {dateError && <p role="alert">{dateError}</p>}
      {startFieldError && <ErrorBanner error={create.error} message="開始日不符合期限，請確認開始日。" />}
      <div className="field"><label htmlFor="task-project">指定專案</label>
        <select id="task-project" value={projectId} onChange={event => setProjectId(event.target.value)}>
          <option value="">不指定（單點任務）</option>
          {(projects.data?.items ?? []).map(project => <option key={project.id} value={project.id}>
            {project.name}</option>)}
        </select>
      </div>
      {!projectId && <div className="field"><label htmlFor="task-scope">任務範圍</label>
        <select id="task-scope" value={scope} onChange={event => setScope(event.target.value as "work" | "private")}>
          <option value="work">工作</option><option value="private">私人</option>
        </select>
      </div>}
      <div className="field"><label htmlFor="task-done-when">完成條件</label>
        <textarea id="task-done-when" value={doneWhen} onChange={event => setDoneWhen(event.target.value)} />
      </div>
      <div className="field"><label htmlFor="task-remind">提醒</label>
        <select id="task-remind" value={remind} onChange={event => setRemind(event.target.value as typeof remind)}>
          <option value="morning">當天早上</option><option value="eve_before">前一晚</option><option value="none">不提醒</option>
        </select>
      </div>
      <div className="field"><label htmlFor="task-goal">關聯目標</label>
        <select id="task-goal" value={goalId} onChange={event => setGoalId(event.target.value)}>
          <option value="">不關聯</option>
          {(goals.data?.items ?? []).filter(goal => !goal.archived_at).map(goal =>
            <option key={goal.id} value={goal.id}>{goal.title}</option>)}
        </select>
      </div>
      <div className="field"><label htmlFor="task-stars">預設星數</label>
        <select id="task-stars" value={expectedStars} onChange={event => setExpectedStars(Number(event.target.value))}>
          {[1, 2, 3, 4, 5].map(stars => <option key={stars} value={stars}>{stars}</option>)}
        </select>
      </div>
      <button className="primary" type="submit" disabled={create.isPending}>建立任務</button>
    </form>
  </main>;
}
