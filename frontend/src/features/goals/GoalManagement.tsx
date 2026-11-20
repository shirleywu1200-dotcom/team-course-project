import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { runMutationWithInvalidation } from "../../api/queryCache";
import { keys } from "../../api/queryKeys";
import { fetchProjects } from "../../api/queries";
import type { components } from "../../api/types.generated";
import { ConfirmationPanel } from "../../components/ConfirmationPanel";
import { ErrorBanner } from "../../components/ErrorBanner";

type Goal = components["schemas"]["GoalOut"];
type GoalCreate = components["schemas"]["GoalCreate"];
type GoalPatch = components["schemas"]["GoalPatch"];
type GoalPatchOut = components["schemas"]["GoalPatchOut"];
type GoalType = GoalCreate["type"];
type Energy = GoalCreate["energy_plan"];
type Settings = components["schemas"]["SettingsOut"];
const typeLabels = { growth: "能力成長", time: "時間配置", expectation: "績效期待" };
const energyLabels = { high: "高", mid: "中", low: "低" };
const targetUnit = (type: string) => type === "time" ? "（分鐘／週）" : "（件）";

function GoalCreateForm({ allowedTypes, onClose }: { allowedTypes: GoalType[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [type, setType] = useState("");
  const [title, setTitle] = useState("");
  const [period, setPeriod] = useState("");
  const [definition, setDefinition] = useState("");
  const [target, setTarget] = useState("");
  const [energy, setEnergy] = useState("");
  const [projectId, setProjectId] = useState("");
  const projects = useQuery({ queryKey: keys.projectList(), queryFn: fetchProjects, enabled: type === "expectation" });
  const validTarget = target === "" || (Number.isSafeInteger(Number(target)) && Number(target) >= 0);
  const valid = type && title.trim() && period.trim() && energy && validTarget
    && (type !== "expectation" || (projectId && projects.data?.items.some(project => project.id === Number(projectId) && !project.archived_at)));
  const mutation = useMutation({ mutationFn: () => {
    const body = { type: type as GoalType, title: title.trim(), period: period.trim(), energy_plan: energy as Energy,
      ...(definition ? { definition } : {}), ...(target && type !== "expectation" ? { target: Number(target) } : {}),
      project_id: type === "expectation" ? Number(projectId) : null } satisfies GoalCreate;
    return runMutationWithInvalidation(qc, "POST /goals", () => api<Goal>("/goals", { method: "POST", body }));
  }, onSuccess: onClose });
  return <form className="card" aria-label="新增目標表單" onSubmit={event => { event.preventDefault(); if (valid) mutation.mutate(); }}>
    <div className="field"><label htmlFor="goal-type">目標類型</label>
      <select id="goal-type" value={type} onChange={event => { setType(event.target.value); setProjectId(""); }}>
        <option value="">請選擇</option>{allowedTypes.map(value => <option key={value} value={value}>{typeLabels[value]}</option>)}
      </select></div>
    <div className="field"><label htmlFor="goal-title">名稱</label><input id="goal-title" value={title} onChange={event => setTitle(event.target.value)} /></div>
    <div className="field"><label htmlFor="goal-period">期間</label><input id="goal-period" value={period} onChange={event => setPeriod(event.target.value)} /></div>
    <div className="field"><label htmlFor="goal-definition">定義</label><textarea id="goal-definition" value={definition} onChange={event => setDefinition(event.target.value)} /></div>
    {type !== "expectation" && <div className="field"><label htmlFor="goal-target">衡量目標{targetUnit(type)}</label>
      <input id="goal-target" type="number" min="0" step="1" value={target} onChange={event => setTarget(event.target.value)} /></div>}
    {type === "expectation" && <div className="field"><label htmlFor="goal-project">指定專案</label>
      {projects.error && <ErrorBanner error={projects.error} />}
      <select id="goal-project" value={projectId} onChange={event => setProjectId(event.target.value)}>
        <option value="">請選擇</option>{projects.data?.items.filter(project => !project.archived_at).map(project =>
          <option key={project.id} value={project.id}>{project.name}</option>)}
      </select></div>}
    <div className="field"><label htmlFor="goal-energy">預期精力</label>
      <select id="goal-energy" value={energy} onChange={event => setEnergy(event.target.value)}>
        <option value="">請選擇</option>{Object.entries(energyLabels).map(([value, label]) =>
          <option key={value} value={value}>{label}</option>)}</select></div>
    {mutation.error && <ErrorBanner error={mutation.error} />}
    <div className="actions"><button type="submit" className="primary" disabled={!valid || mutation.isPending}>儲存新目標</button>
      <button type="button" onClick={onClose}>取消</button></div>
  </form>;
}

function GoalEditForm({ goal, onClose }: { goal: Goal; onClose: () => void }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState(goal.title);
  const [period, setPeriod] = useState(goal.period);
  const [definition, setDefinition] = useState(goal.definition);
  const [target, setTarget] = useState(String(goal.target));
  const [energy, setEnergy] = useState<Energy>(goal.energy_plan);
  const changes: GoalPatch = {
    ...(title.trim() !== goal.title ? { title: title.trim() } : {}),
    ...(period.trim() !== goal.period ? { period: period.trim() } : {}),
    ...(definition !== goal.definition ? { definition } : {}),
    ...(goal.type !== "expectation" && target !== String(goal.target) ? { target: Number(target) } : {}),
    ...(energy !== goal.energy_plan ? { energy_plan: energy } : {}),
  };
  const valid = title.trim() && period.trim() && (goal.type === "expectation" || (target !== "" && Number.isSafeInteger(Number(target)) && Number(target) >= 0));
  const mutation = useMutation({ mutationFn: () => runMutationWithInvalidation(qc, "PATCH /goals/{goal_id}", () =>
    api<GoalPatchOut>(`/goals/${goal.id}`, { method: "PATCH", body: changes })), onSuccess: onClose });
  return <form className="card" aria-label={`編輯${goal.title}表單`}
    onSubmit={event => { event.preventDefault(); if (valid && Object.keys(changes).length) mutation.mutate(); }}>
    <p>類型：{typeLabels[goal.type]} · 指定專案：{goal.project_id ?? "無"}</p>
    <div className="field"><label htmlFor={`edit-title-${goal.id}`}>編輯名稱</label>
      <input id={`edit-title-${goal.id}`} value={title} onChange={event => setTitle(event.target.value)} /></div>
    <div className="field"><label htmlFor={`edit-period-${goal.id}`}>編輯期間</label>
      <input id={`edit-period-${goal.id}`} value={period} onChange={event => setPeriod(event.target.value)} /></div>
    <div className="field"><label htmlFor={`edit-definition-${goal.id}`}>編輯定義</label>
      <textarea id={`edit-definition-${goal.id}`} value={definition} onChange={event => setDefinition(event.target.value)} /></div>
    {goal.type !== "expectation" && <div className="field"><label htmlFor={`edit-target-${goal.id}`}>編輯衡量目標{targetUnit(goal.type)}</label>
      <input id={`edit-target-${goal.id}`} type="number" min="0" step="1" value={target} onChange={event => setTarget(event.target.value)} /></div>}
    <div className="field"><label htmlFor={`edit-energy-${goal.id}`}>編輯預期精力</label>
      <select id={`edit-energy-${goal.id}`} value={energy} onChange={event => setEnergy(event.target.value as Energy)}>
        {Object.entries(energyLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
    {mutation.error && <ErrorBanner error={mutation.error} />}
    <div className="actions"><button type="submit" className="primary" disabled={!valid || !Object.keys(changes).length || mutation.isPending}>儲存修改</button>
      <button type="button" onClick={onClose}>取消</button></div>
  </form>;
}

function GoalArchiveAction({ goal, onClose }: { goal: Goal; onClose: () => void }) {
  const qc = useQueryClient();
  const mutation = useMutation({ mutationFn: () => runMutationWithInvalidation(qc, "POST /goals/{goal_id}/archive", () =>
    api<Goal>(`/goals/${goal.id}/archive`, { method: "POST" })), onSuccess: onClose });
  return <><ConfirmationPanel title={`封存${goal.title}`} canConfirm={!mutation.isPending}
    onCancel={onClose} onConfirm={() => mutation.mutate()}>
    <p>封存後仍可查看與編輯，不能再新增關聯。</p>
  </ConfirmationPanel>{mutation.error && <ErrorBanner error={mutation.error} />}</>;
}

export function GoalManagement({ goals, loading, error, onRetry, selectedId, onSelect }: {
  goals: Goal[] | undefined; loading: boolean; error: Error | null; onRetry: () => void;
  selectedId: number | null; onSelect: (id: number) => void;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [archiving, setArchiving] = useState<number | null>(null);
  const settings = useQuery({ queryKey: keys.settings, queryFn: () => api<Settings>("/settings") });
  const editGoal = goals?.find(goal => goal.id === editing);
  const archiveGoal = goals?.find(goal => goal.id === archiving);
  return <section className="card" aria-label="目標管理">
    <h2>目標管理</h2>
    <div aria-label="可建立目標類型">
      {settings.error ? <ErrorBanner error={settings.error} /> : !settings.data ? <p role="status">載入目標設定中…</p>
        : <p>可建立：{settings.data.goal_types_enabled.map(type => typeLabels[type]).join("、") || "目前未啟用目標類型"}</p>}
    </div>
    <button type="button" disabled={!settings.data?.goal_types_enabled.length} onClick={() => setCreateOpen(true)}>新增目標</button>
    {createOpen && settings.data && <GoalCreateForm allowedTypes={settings.data.goal_types_enabled} onClose={() => setCreateOpen(false)} />}
    {error ? <><ErrorBanner error={error} /><button type="button" onClick={onRetry}>重試目標清單</button></>
      : loading ? <p role="status">載入目標清單中…</p>
        : goals?.length === 0 ? <p>尚無目標。</p>
          : <ul>{goals?.map(goal => <li key={goal.id} className="card">
            <span>{goal.title} · {typeLabels[goal.type]}{goal.archived_at && " · 已封存"}</span>
            <div className="actions">
              <button type="button" aria-pressed={selectedId === goal.id} onClick={() => onSelect(goal.id)}>查看{goal.title}統計</button>
              <button type="button" onClick={() => { setEditing(goal.id); setArchiving(null); }}>編輯{goal.title}</button>
              {!goal.archived_at && <button type="button" onClick={() => { setArchiving(goal.id); setEditing(null); }}>封存{goal.title}</button>}
            </div>
          </li>)}</ul>}
    {editGoal && <GoalEditForm key={editGoal.id} goal={editGoal} onClose={() => setEditing(null)} />}
    {archiveGoal && <GoalArchiveAction goal={archiveGoal} onClose={() => setArchiving(null)} />}
  </section>;
}
