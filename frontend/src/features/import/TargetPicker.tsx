// 12.7 匯入目標（D-4）：貼上前先選新建或既有專案。私人範圍專案標「不會送 AI」（資安規則 2）。

import { useQuery } from "@tanstack/react-query";

import { fetchProjects, keys } from "../../api/queries";

export interface Dest {
  mode: "new" | "existing";
  newName: string;
  projectId: number | null;
}

export function TargetPicker({ dest, onChange }: { dest: Dest; onChange: (d: Dest) => void }) {
  const projects = useQuery({ queryKey: keys.projects, queryFn: fetchProjects });

  return (
    <section className="card" aria-label="匯入到">
      <h2>匯入到</h2>
      <div className="field">
        <label className="choice">
          <input type="radio" name="import-target" checked={dest.mode === "new"}
            onChange={() => onChange({ ...dest, mode: "new" })} />
          新建專案
        </label>
        <label htmlFor="import-new-name" className="sr-only">新專案名稱</label>
        <input id="import-new-name" value={dest.newName} disabled={dest.mode !== "new"} placeholder="新專案名稱"
          onChange={(e) => onChange({ ...dest, newName: e.target.value })} />
      </div>
      <div className="field">
        <label className="choice">
          <input type="radio" name="import-target" checked={dest.mode === "existing"}
            onChange={() => onChange({ ...dest, mode: "existing" })} />
          既有專案
        </label>
        <label htmlFor="import-project" className="sr-only">選擇專案</label>
        <select id="import-project" value={dest.projectId ?? ""} disabled={dest.mode !== "existing"}
          onChange={(e) => onChange({ ...dest, projectId: e.target.value ? Number(e.target.value) : null })}>
          <option value="">請選擇</option>
          {(projects.data ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.scope === "private" ? `${p.name}（私人・不會送 AI）` : p.name}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}
