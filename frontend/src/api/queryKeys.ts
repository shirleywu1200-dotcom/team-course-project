import type { paths } from "./types.generated";

type TaskFilter = NonNullable<paths["/api/v1/tasks"]["get"]["parameters"]["query"]>;
type ProjectFilter = NonNullable<paths["/api/v1/projects"]["get"]["parameters"]["query"]>;
type StatsFilter = NonNullable<paths["/api/v1/stats/time-management"]["get"]["parameters"]["query"]>;

export const queryRoots = {
  tasks: ["tasks"], projects: ["projects"], timeManagement: ["stats", "time-management"],
  reasons: ["meta", "reasons"], health: ["meta", "health"],
} as const;

const projectTasks = (id: number) => [...queryRoots.tasks, "project", id] as const;
export const keys = {
  reasons: queryRoots.reasons,
  health: queryRoots.health,
  task: (id: number) => [...queryRoots.tasks, id] as const,
  projectTasks,
  taskList: (filter: TaskFilter = {}) => {
    const populated = Object.fromEntries(Object.entries(filter).filter(([, value]) => value != null));
    const project = populated.project_id;
    if (Object.keys(populated).length === 1 && typeof project === "string" && /^\d+$/.test(project)) return projectTasks(Number(project));
    return [...queryRoots.tasks, "list", populated] as const;
  },
  project: (id: number) => [...queryRoots.projects, id] as const,
  projectList: (filter: ProjectFilter = {}) => [...queryRoots.projects, "list", { include_archived: filter.include_archived ?? false }] as const,
  timeManagement: (filter: StatsFilter = {}) => [...queryRoots.timeManagement, filter] as const,
};
