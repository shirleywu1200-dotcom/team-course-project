// todo 12.11 D-1：尚未啟用（onboarded_at 為空）時，除 /onboarding 外的路由都導向精靈；
// 已啟用時 /onboarding 導回首頁：精靈完成後靠這條離開（精靈本身不導向，避免兩個導向互搶），
// 已啟用者也不會重進精靈（「略過＝用預設」只對首次啟用成立）。
// 讀設定失敗時不攔，交給各頁顯示自己的錯誤（例如 token 錯誤）。

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { fetchSettings, keys } from "../../api/queries";

export const ONBOARDING_PATH = "/onboarding";

export function OnboardingGate({ children }: { children: ReactNode }) {
  const settings = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
  const { pathname } = useLocation();
  // 只在第一次讀取時攔。失敗過後頁面自己重讀會讓狀態回到 pending，若再攔就會卸載頁面、重讀、再失敗，無限迴圈
  if (settings.isPending && settings.errorUpdateCount === 0) return <main><p className="muted">載入中…</p></main>;
  const onboarded = settings.data ? settings.data.onboarded_at !== null : null;
  if (onboarded === false && pathname !== ONBOARDING_PATH) return <Navigate to={ONBOARDING_PATH} replace />;
  if (onboarded === true && pathname === ONBOARDING_PATH) return <Navigate to="/" replace />;
  return <>{children}</>;
}
