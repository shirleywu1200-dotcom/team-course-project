import { Link, Route, Routes } from "react-router-dom";
import type { ComponentType } from "react";

import { BulkShiftPage } from "../features/bulk-shift/BulkShiftPage";
import { TaskDuePage } from "../features/due-adjust/TaskDuePage";
import { ImportPage } from "../features/import/ImportPage";
import { InboxPage } from "../features/inbox/InboxPage";
import { OnboardingPage } from "../features/settings/OnboardingPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { WeeklyReportPage } from "../features/weekly-report/WeeklyReportPage";
import { ONBOARDING_PATH } from "../features/settings/OnboardingGate";
import { AppLayout } from "./AppLayout";
import { navigationRoutes, pageRoutes } from "./routeDefinitions";

const featurePages: Record<string, ComponentType> = {
  "/import": ImportPage,
  "/inbox": InboxPage,
  [ONBOARDING_PATH]: OnboardingPage,
  "/settings": SettingsPage,
  "/reports": WeeklyReportPage,
};

function Home() {
  return (
    <main>
      <h1>工作總覽</h1>
      <p className="muted">選擇要處理的工作。部分功能尚未開放。</p>
      <div className="app-shortcuts">
        {navigationRoutes.map(({ path, title }) => (
          <Link className="card" key={path} to={path}>{title}</Link>
        ))}
      </div>
      <div className="actions">
        <Link to="/tasks/new">新增任務</Link>
        <Link to="/inbox">每日確認</Link>
        <Link to="/setup">啟用設定</Link>
      </div>
    </main>
  );
}

function ReservedPage({ title }: { title: string }) {
  return (
    <main>
      <h1>{title}</h1>
      <p className="muted">此功能尚未開放。</p>
      <Link to="/">回到工作總覽</Link>
    </main>
  );
}

function NotFound() {
  return (
    <main>
      <h1>找不到頁面</h1>
      <p className="muted">請檢查網址，或回到工作總覽選擇功能。</p>
      <Link to="/">回到工作總覽</Link>
    </main>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Home />} />
        {pageRoutes.map(({ path, title }) => {
          const Page = featurePages[path];
          return <Route key={path} path={path} element={Page ? <Page /> : <ReservedPage title={title} />} />;
        })}
        {/* 12.2、12.5 保留原入口；12.3 後續整合正式任務詳情。 */}
        <Route path="/tasks/:taskId" element={<TaskDuePage />} />
        <Route path="/projects/:projectId/bulk-shift" element={<BulkShiftPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
