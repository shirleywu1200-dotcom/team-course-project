import type { ReactNode } from "react";
import { ApiError } from "../../api/client";
import { ErrorBanner } from "../ErrorBanner";

// 僅用於 spec 5.4／6.6 的量表訪談，既有量表內容永遠留在相同位置。
export function RubricInterviewFallback({ error, children }: { error: unknown; children: ReactNode }) {
  const unavailable = error instanceof ApiError && error.status === 503 && error.code === "AI_UNAVAILABLE";
  return <>
    {unavailable
      ? <p className="banner banner-warn" role="alert">AI 訪談暫時無法使用，目前量表版本維持不變。</p>
      : <ErrorBanner error={error} />}
    {children}
  </>;
}
