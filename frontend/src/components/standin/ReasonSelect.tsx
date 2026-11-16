import type { ComponentProps } from "react";
import { ReasonSelect as SharedReasonSelect } from "../ReasonSelect";
export { isExternal } from "../ReasonSelect";

// Dev-A 既有頁面已由 MarkChoice 顯示外部提示，保留原行為，避免重複。
export function ReasonSelect(props: ComponentProps<typeof SharedReasonSelect>) {
  return <SharedReasonSelect {...props} showExternalHint={false} />;
}
