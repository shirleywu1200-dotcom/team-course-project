import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";

type ProjectListOut = components["schemas"]["ProjectListOut"];

export function ProjectListPage() {
  const projects = useQuery({ queryKey: keys.projectList(),
    queryFn: () => api<ProjectListOut>("/projects?include_archived=false") });

  return <main>
    <h1>專案現況</h1>
    <section aria-label="專案清單">
      <h2>專案清單</h2>
      {!projects.data && !projects.error && <p role="status">載入專案中…</p>}
      {projects.error && <><ErrorBanner error={projects.error} />
        <button type="button" onClick={() => { void projects.refetch(); }}>重試</button></>}
      {projects.data && !projects.error && (projects.data.items.length === 0
        ? <p>還沒有專案，先去『<Link to="/import">匯入專案</Link>』建立。</p>
        : <ul>{projects.data.items.map(project => {
          const label = `${project.name}，${project.scope === "private" ? "私人" : "工作"}範圍`;
          return <li className="card" key={project.id} aria-label={label}>
            <Link to={`/projects/${project.id}`} aria-label={label}>{project.name} · {project.scope === "private" ? "私人" : "工作"}範圍</Link>
          </li>;
        })}</ul>)}
    </section>
  </main>;
}
