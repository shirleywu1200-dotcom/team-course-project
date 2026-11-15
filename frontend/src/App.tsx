// 路由與共用版面由 11.1 管理；TokenGate 與 QueryClient 設定沿用既有實作。

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { getToken, setToken } from "./api/client";
import { AppRoutes } from "./app/AppRoutes";

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

export function App() {
  const [client] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={client}>
      <TokenGate>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </TokenGate>
    </QueryClientProvider>
  );
}
