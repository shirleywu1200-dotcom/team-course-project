// todo 12.11：啟用精靈（US-01～03；FR-SET-01；SDD D-1、D-2、D-5(a)）。
// 6 步只能上一步／下一步。各步答案只存在本頁狀態，「完成設定」才寫入（requests.completeOnboarding）；
// 「略過」丟掉已填。量表例外：按確認當下入庫；草稿未確認就離開該步時先詢問。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fetchSettings, keys } from "../../api/queries";
import type { AppSettings } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { draftValid, GroupFields } from "./GroupFields";
import { stepName, WIZARD_STEPS } from "./options";
import { completeOnboarding } from "./requests";
import { RubricBlock } from "./RubricBlock";

export const LEAVE_DRAFT = "量表草稿還沒確認，離開這一步會捨棄草稿。要離開嗎？";

function Welcome() {
  return (
    <>
      <h2>歡迎使用個人大總管</h2>
      <p>這裡記下你答應別人、別人答應你的事。AI 只提議，你確認後才寫入。</p>
      <p className="muted">接下來 5 步約 3 分鐘。每一步都有預設值，不想設定可以直接略過，之後在「設定」都能改。</p>
    </>
  );
}

function Wizard({ saved }: { saved: AppSettings }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState(saved);
  const [rubricVersion, setRubricVersion] = useState<number | null>(null);
  const [rubricEditing, setRubricEditing] = useState(false);

  // 寫回 onboarded_at 後由 OnboardingGate 導回首頁
  const complete = useMutation({
    mutationFn: (skipped: boolean) => completeOnboarding(saved, draft, skipped),
    onSuccess: (settings) => qc.setQueryData(keys.settings, settings),
  });

  // 量表草稿未確認時，換步或略過前先問
  const leave = (action: () => void) => {
    if (rubricEditing && !window.confirm(LEAVE_DRAFT)) return;
    action();
  };

  const group = WIZARD_STEPS[step];
  const last = step === WIZARD_STEPS.length - 1;
  const valid = draftValid(draft);

  return (
    <main>
      <h1>開始設定</h1>
      <ol className="steps" aria-label="設定步驟">
        {WIZARD_STEPS.map((id, i) => (
          <li key={i} className={i === step ? "on" : i < step ? "done" : ""} aria-current={i === step ? "step" : undefined}>
            <span className="steps-n">{i + 1}.</span> <span className="steps-name">{stepName(id)}</span>
          </li>
        ))}
      </ol>
      <section className="card" aria-label={stepName(group)}>
        {group ? <h2>{stepName(group)}</h2> : <Welcome />}
        {group === "rubric" && <RubricBlock onConfirmed={setRubricVersion} onEditingChange={setRubricEditing} />}
        {group && group !== "rubric" && (
          <GroupFields group={group} draft={draft} onChange={(p) => setDraft((d) => ({ ...d, ...p }))} />
        )}
      </section>
      <ErrorBanner error={complete.error} />
      <div className="head">
        <span className="actions">
          <button type="button" className="link-button" disabled={complete.isPending} onClick={() => leave(() => complete.mutate(true))}>
            {rubricVersion === null ? "略過，全部用預設" : "略過其餘設定"}
          </button>
          {rubricVersion !== null && <span className="muted small">量表已確認為 v{rubricVersion}，略過不會撤回。</span>}
        </span>
        <span className="actions">
          <button type="button" disabled={step === 0} onClick={() => leave(() => setStep(step - 1))}>上一步</button>
          {last ? (
            <button type="button" className="primary" disabled={!valid || complete.isPending} onClick={() => complete.mutate(false)}>
              完成設定
            </button>
          ) : (
            <button type="button" className="primary" onClick={() => leave(() => setStep(step + 1))}>{step === 0 ? "開始" : "下一步"}</button>
          )}
        </span>
      </div>
      {last && !valid && <p className="hint">「目標與精力」的精力定義有空白，請回上一步填寫。</p>}
    </main>
  );
}

export function OnboardingPage() {
  const settings = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
  if (!settings.data) return <main><ErrorBanner error={settings.error} /></main>;
  return <Wizard saved={settings.data} />;
}
