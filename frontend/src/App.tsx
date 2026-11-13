// 暫代 Dev-C todo 11.1（路由與版面）：只掛 Dev-A 的三個頁面。Phase 11 完成後併入正式路由。

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";

import { getToken, setToken } from "./api/client";
import { BulkShiftPage } from "./features/bulk-shift/BulkShiftPage";
import { TaskDuePage } from "./features/due-adjust/TaskDuePage";

export function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
}

function TokenGate({ children }: { children: ReactNode }) {
  const [token, setLocal] = useState(getToken());
  const [draft, setDraft] = useState("");
  if (token) return <>{children}</>;
  return (
    <main>
      <h1>設定存取 token</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setToken(draft);
          setLocal(draft);
        }}
      >
        <div className="field">
          <label htmlFor="token">後端 G4_API_TOKEN</label>
          <input id="token" type="password" value={draft} onChange={(e) => setDraft(e.target.value)} />
        </div>
        <button type="submit" className="primary">
          儲存
        </button>
      </form>
    </main>
  );
}

function Home() {
  return (
    <main>
      <h1>個人大總管（Dev-A 頁面）</h1>
      <p className="muted">
        日期調整與基準更正：<code>/tasks/:taskId</code>；整批順延：<code>/projects/:projectId/bulk-shift</code>
      </p>
      <Link to="/projects/1/bulk-shift">專案 1 整批順延</Link>
    </main>
  );
}

export function App() {
  const [client] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={client}>
      <TokenGate>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/tasks/:taskId" element={<TaskDuePage />} />
            <Route path="/projects/:projectId/bulk-shift" element={<BulkShiftPage />} />
          </Routes>
        </BrowserRouter>
      </TokenGate>
    </QueryClientProvider>
  );
}
