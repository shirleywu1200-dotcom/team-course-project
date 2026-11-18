// 11.5 正式共用元件，保留原有 props 與行為。

import { ApiError } from "../api/client";

const MESSAGES: Record<string, string> = {
  STALE_VERSION: "資料已被其他操作更新，已重新載入，請確認後再操作一次。",
  TASK_DONE: "這個任務已完成，不能再調整。",
  NO_CHANGE: "新日期與目前相同，不需要調整。",
  DATE_OUT_OF_RANGE: "日期超出允許範圍（今天前 365 天到後 730 天）。",
  MARK_REQUIRED: "這是你的任務，請選擇時間管理註記，或選「稍後註記」。",
  INCLUDES_DONE_TASK: "勾選的任務中有已完成任務，請取消勾選。",
  EMPTY_SELECTION: "請至少勾選一項任務。",
  ACK_REQUIRED: "請先勾選聲明再確認。",
  CONFIRMATION_INVALID: "確認憑證已過期、已使用，或任務已變動，請重新預覽。",
  UNAUTHORIZED: "存取 token 錯誤或未設定。",
  CANDIDATE_NOT_OPEN: "這個候選已經處理過，已重新載入清單。",
  PAYLOAD_TOO_LARGE: "貼上的內容太長：收件匣不能超過 20,000 字；匯入最多 500 列、50,000 字。請分段貼上。",
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return MESSAGES[err.code] ?? err.message;
  return "發生未預期的錯誤，請稍後再試。";
}

export function ErrorBanner({ error, message }: { error: unknown; message?: string }) {
  if (!error) return null;
  return (
    <div className="banner banner-error" role="alert">
      {message ?? errorMessage(error)}
    </div>
  );
}
