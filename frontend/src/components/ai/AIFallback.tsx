import type { ReactNode } from "react";

interface Props {
  // UI 選擇狀態（spec 5.3），不是 API 回應模型。端點型別仍須由 OpenAPI 生成。
  aiStatus: "ok" | "unavailable" | "invalid_output";
  children: ReactNode;
  fallback: ReactNode;
}

const notices = {
  unavailable: "AI 暫時無法使用，以下顯示可用內容。",
  invalid_output: "AI 回傳內容未通過檢查，以下顯示可用內容。",
};

// spec 5.3：200 降級不是錯誤；退路由呼叫者提供，不推論資料或代替使用者確認。
export function AIFallback({ aiStatus, children, fallback }: Props) {
  if (aiStatus === "ok") return <>{children}</>;
  return <>
    <p className="banner banner-warn" role="status">{notices[aiStatus]}</p>
    {fallback}
  </>;
}
