// 11.1：12.x 的路由骨架；todo 編號只供開發追蹤，不顯示在產品介面。
export const pageRoutes = [
  { path: "/projects", title: "專案現況", todo: "12.1", nav: true },
  { path: "/projects/:projectId", title: "專案現況", todo: "12.1" },
  { path: "/tasks", title: "任務", todo: "12.3", nav: true, compactOrder: 3 },
  { path: "/tasks/new", title: "新增任務", todo: "12.15" },
  { path: "/history", title: "歷程", todo: "12.6", nav: true },
  { path: "/projects/:projectId/history", title: "專案歷程", todo: "12.6" },
  { path: "/import", title: "匯入專案", todo: "12.7", nav: true },
  { path: "/inbox", title: "收件匣", todo: "12.8", nav: true, compactOrder: 1 },
  { path: "/confirmations", title: "每日確認", todo: "12.8" },
  { path: "/today", title: "今日", todo: "12.9", nav: true, compactOrder: 2 },
  { path: "/tasks/:taskId/feedback", title: "完成回報", todo: "12.9" },
  { path: "/time-management", title: "時間管理統計", todo: "12.10", nav: true },
  { path: "/setup", title: "啟用設定", todo: "12.11" },
  { path: "/settings", title: "設定", todo: "12.11", nav: true, compactOrder: 5 },
  { path: "/goals", title: "目標與精力", todo: "12.12", nav: true, compactOrder: 4, compactTitle: "目標" },
  { path: "/reports", title: "週報", todo: "12.13", nav: true },
  { path: "/data-control", title: "資料控制", todo: "12.14", nav: true },
];

export const navigationRoutes = pageRoutes.filter((route) => route.nav);
