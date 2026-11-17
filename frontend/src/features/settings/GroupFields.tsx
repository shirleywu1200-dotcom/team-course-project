// todo 12.11 D-4：每組設定一個欄位元件，精靈與設定頁共用；只負責顯示與回報修改，不呼叫 API。
// 量表組另見 RubricBlock（走 POST /rubrics，不在這裡）。

import type { AppSettings, GoalType } from "../../api/types";
import { GOALS, LEVEL_MAX, OPTIONS, type GroupId, type RadioKey } from "./options";

type Change = (patch: Partial<AppSettings>) => void;
interface Props {
  draft: AppSettings;
  onChange: Change;
}

function Radios<K extends RadioKey>({ k, legend, hint, draft, onChange }: Props & { k: K; legend: string; hint?: string }) {
  return (
    <fieldset className="field">
      <legend>{legend}</legend>
      <div className="choices">
        {OPTIONS[k].map(([value, label]) => (
          <label key={String(value)} className="choice">
            <input type="radio" name={k} checked={draft[k] === value}
              onChange={() => onChange({ [k]: value } as Partial<AppSettings>)} />
            {label}
          </label>
        ))}
      </div>
      {hint && <p className="muted small">{hint}</p>}
    </fieldset>
  );
}

function RoleFields(p: Props) {
  return (
    <>
      <Radios {...p} k="role" legend="我的角色" />
      <Radios {...p} k="default_scope" legend="新事項預設範圍" hint="私人範圍的內容不會送給 AI，也不進週報。" />
      <Radios {...p} k="report_audience" legend="週報給誰" />
    </>
  );
}

function InboxInfo() {
  return (
    <dl className="summary">
      <dt>貼上入口</dt>
      <dd><span className="tag tag-ok">已啟用</span> 把對話或訊息貼到「收件匣」，AI 會挑出承諾讓你確認。</dd>
      <dt>LINE 群組</dt>
      <dd><span className="tag tag-warn">本版未開放</span> 之後開放時，需先告知群組成員才能綁定。</dd>
    </dl>
  );
}

const ENERGY = [["energy_def_high", "精力高"], ["energy_def_mid", "精力中"], ["energy_def_low", "精力低"]] as const;

function GoalFields({ draft, onChange }: Props) {
  const toggle = (g: GoalType, on: boolean) => {
    const next = new Set(draft.goal_types_enabled);
    if (on) next.add(g); else next.delete(g);
    onChange({ goal_types_enabled: GOALS.map(([v]) => v).filter((v) => next.has(v)) });
  };
  return (
    <>
      <fieldset className="field">
        <legend>啟用的目標</legend>
        <div className="choices">
          {GOALS.map(([value, label, measure]) => (
            <label key={value} className="choice">
              <input type="checkbox" checked={draft.goal_types_enabled.includes(value)}
                onChange={(e) => toggle(value, e.target.checked)} />
              {label}<span className="muted small">（{measure}）</span>
            </label>
          ))}
        </div>
      </fieldset>
      {ENERGY.map(([k, label]) => (
        <div key={k} className="field">
          <label htmlFor={k}>「{label}」指的是</label>
          <textarea id={k} rows={2} maxLength={LEVEL_MAX} value={draft[k]}
            onChange={(e) => onChange({ [k]: e.target.value })} />
          {draft[k].trim() === "" && <p className="hint">請填寫，不能空白。</p>}
        </div>
      ))}
      <p className="muted small">之後自評精力時，會在選項旁顯示這三句。</p>
    </>
  );
}

function RhythmFields(p: Props) {
  return (
    <>
      <Radios {...p} k="confirm_time" legend="每日確認時間" />
      <Radios {...p} k="confirm_cap_min" legend="每次確認上限" hint="超過上限，剩下的候選留到下一次。" />
      <Radios {...p} k="remind_default" legend="任務提醒預設" hint="新任務的預設值，個別任務可再改。" />
    </>
  );
}

function RetentionFields(p: Props) {
  return <Radios {...p} k="retention_days" legend="原文保存期限" hint="到期只清除貼上的原文；任務、候選與歷程保留。" />;
}

export function GroupFields({ group, ...p }: Props & { group: Exclude<GroupId, "rubric"> }) {
  switch (group) {
    case "role": return <RoleFields {...p} />;
    case "inbox": return <InboxInfo />;
    case "goal": return <GoalFields {...p} />;
    case "rhythm": return <RhythmFields {...p} />;
    case "retention": return <RetentionFields {...p} />;
  }
}

// 精力定義不可空白（後端 ShortText min_length=1）；送出前檢查
export const draftValid = (d: AppSettings) => ENERGY.every(([k]) => d[k].trim() !== "");
