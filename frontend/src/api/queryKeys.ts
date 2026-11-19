import type { paths } from "./types.generated";

type TaskFilter = NonNullable<paths["/api/v1/tasks"]["get"]["parameters"]["query"]>;
type ProjectFilter = NonNullable<paths["/api/v1/projects"]["get"]["parameters"]["query"]>;
export type StatsFilter = NonNullable<paths["/api/v1/stats/time-management"]["get"]["parameters"]["query"]>;
export type EventFilter = NonNullable<paths["/api/v1/events"]["get"]["parameters"]["query"]>;
type EventFilterInput = URLSearchParams | EventFilter;

const eventKinds = new Set(["due", "annotation", "status", "task", "feedback", "goal", "baseline", "project"]);

// 12.10：URL、請求與 query key 共用；空值省略，日期不轉換時區。
export function normalizeTimeManagementFilter(filter: StatsFilter = {}) {
  return {
    ...(filter.from ? { from: filter.from } : {}),
    ...(filter.to ? { to: filter.to } : {}),
  };
}

// URL、請求參數與 query key 共用；日期保持伺服器的 YYYY-MM-DD 字串。
export function normalizeEventFilters(input: EventFilterInput = {}): EventFilter {
  const read = (field: keyof EventFilter) => input instanceof URLSearchParams ? input.get(field) : input[field];
  const result: EventFilter = { limit: 100, offset: 0 };
  const project = read("project_id");
  if (project === "none") result.project_id = "none";
  else if (project != null && /^\d+$/.test(String(project))) result.project_id = BigInt(String(project)).toString();
  for (const field of ["task_id", "batch_id", "limit", "offset"] as const) {
    const raw = read(field);
    if (raw == null || raw === "") continue;
    const value = Number(raw);
    if (Number.isSafeInteger(value) && value >= 0) result[field] = value;
  }
  for (const field of ["from", "to"] as const) {
    const value = read(field);
    if (typeof value === "string" && value !== "") result[field] = value;
  }
  const kind = read("kind");
  if (typeof kind === "string" && eventKinds.has(kind)) result.kind = kind as EventFilter["kind"];
  return result;
}

export const queryRoots = {
  tasks: ["tasks"], projects: ["projects"], timeManagement: ["stats", "time-management"],
  gantt: ["gantt"], events: ["events"],
  reasons: ["meta", "reasons"], health: ["meta", "health"],
  today: ["meta", "today"], feedbackPending: ["feedback", "pending"],
  candidates: ["candidates"], settings: ["settings"], rubrics: ["rubrics"],
  weeklyReports: ["reports", "weekly"],
} as const;

const projectTasks = (id: number) => [...queryRoots.tasks, "project", id] as const;
export const keys = {
  reasons: queryRoots.reasons,
  health: queryRoots.health,
  today: queryRoots.today,
  feedbackPending: () => queryRoots.feedbackPending,
  feedback: (taskId: number) => ["feedback", "task", taskId] as const,
  task: (id: number) => [...queryRoots.tasks, id] as const,
  projectTasks,
  taskList: (filter: TaskFilter = {}) => {
    const populated = Object.fromEntries(Object.entries(filter).filter(([, value]) => value != null));
    const project = populated.project_id;
    if (Object.keys(populated).length === 1 && typeof project === "string" && /^\d+$/.test(project)) return projectTasks(Number(project));
    return [...queryRoots.tasks, "list", populated] as const;
  },
  project: (id: number) => [...queryRoots.projects, id] as const,
  gantt: (projectId: number) => [...queryRoots.gantt, projectId] as const,
  events: (filters: EventFilterInput = {}) => [...queryRoots.events, normalizeEventFilters(filters)] as const,
  projectList: (filter: ProjectFilter = {}) => [...queryRoots.projects, "list", { include_archived: filter.include_archived ?? false }] as const,
  timeManagement: (filter: StatsFilter = {}) => [...queryRoots.timeManagement, normalizeTimeManagementFilter(filter)] as const,
  // Dev-B 12.8 收件匣、12.11 設定與量表
  candidates: (state: "open" | "confirmed" | "ignored") => [...queryRoots.candidates, state] as const,
  ingestJob: (id: number) => ["ingest", "jobs", id] as const,
  settings: queryRoots.settings,
  activeRubric: [...queryRoots.rubrics, "active"] as const,
  weeklyReport: (id: number) => [...queryRoots.weeklyReports, id] as const,
  weeklyReportByWeek: (weekStart: string) => [...queryRoots.weeklyReports, "week", weekStart] as const,
};
