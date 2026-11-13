// 暫代 Dev-C todo 11.5「註記面板（三選一＋稍後註記）」。Phase 11 完成後改用共用元件。
// 手刻原因：Phase 11 共用元件尚未建立。
// FR-AI-06：預設不選任何一項，由使用者自己判斷。

import type { Mark } from "../../api/types";

export type MarkValue = Mark | "defer" | null;

const OPTIONS: { value: Exclude<MarkValue, null>; label: string }[] = [
  { value: "better", label: "變好" },
  { value: "worse", label: "變差" },
  { value: "none", label: "不計入" },
  { value: "defer", label: "稍後註記" },
];

interface Props {
  name: string;
  value: MarkValue;
  onChange: (v: MarkValue) => void;
  externalHint?: boolean;
}

export function MarkChoice({ name, value, onChange, externalHint = false }: Props) {
  return (
    <fieldset className="field">
      <legend>要計入時間管理嗎？</legend>
      <div className="choices">
        {OPTIONS.map((o) => (
          <label key={o.value} className="choice">
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
            />
            {o.label}
          </label>
        ))}
      </div>
      {externalHint && (
        <p className="hint" role="note">
          這個原因屬於外部因素，建議選「不計入」。這只是提示，請你自己決定。
        </p>
      )}
    </fieldset>
  );
}

export function markPayload(v: MarkValue): { mark: Mark | null; defer_mark: boolean } {
  return v === "defer" || v === null ? { mark: null, defer_mark: v === "defer" } : { mark: v, defer_mark: false };
}
