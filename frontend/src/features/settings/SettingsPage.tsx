// todo 12.11：設定頁（FR-SET-02、03；SDD D-4、D-5(b)～(d)）。
// 左側分類導覽，一次編一組；每組「還原／儲存」，PUT /settings 只送這組有改的欄位。
// 量表組沒有儲存鈕，走 RubricBlock 的確認流程；切換分類時有未存修改或未確認的量表草稿，先問是否捨棄。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fetchSettings, keys } from "../../api/queries";
import type { AppSettings } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { draftValid, GroupFields } from "./GroupFields";
import { changedFields, groupOf, GROUPS, type GroupId } from "./options";
import { saveSettings } from "./requests";
import { RubricBlock } from "./RubricBlock";

function Page({ saved }: { saved: AppSettings }) {
  const qc = useQueryClient();
  const [groupId, setGroupId] = useState<GroupId>("role");
  const [draft, setDraft] = useState(saved);
  const [rubricEditing, setRubricEditing] = useState(false);
  const group = groupOf(groupId);
  const patch = changedFields(saved, draft, group.keys);
  const dirty = Object.keys(patch).length > 0;

  const save = useMutation({
    mutationFn: saveSettings,
    onSuccess: (settings) => qc.setQueryData(keys.settings, settings),
  });

  const revert = () => setDraft((d) => ({ ...d, ...Object.fromEntries(group.keys.map((k) => [k, saved[k]])) }));
  const switchTo = (id: GroupId) => {
    if (id === groupId) return;
    const unsaved = dirty ? "有未存的修改" : rubricEditing ? "的草稿還沒確認" : null;
    if (unsaved && !window.confirm(`「${group.name}」${unsaved}，要捨棄嗎？`)) return;
    revert();
    save.reset();
    setGroupId(id);
  };

  return (
    <main className="wide">
      <h1>設定</h1>
      <p className="muted">隨時可改。量表每次確認都會產生新版本，舊版本保留，過去的星數照舊版本解讀。</p>
      <div className="settings-split">
        <nav className="settings-nav" aria-label="設定分類">
          {GROUPS.map((g) => (
            <button key={g.id} type="button" aria-current={g.id === groupId ? "page" : undefined} onClick={() => switchTo(g.id)}>
              {g.name}
            </button>
          ))}
        </nav>
        <section className="card" aria-label={group.name}>
          <h2>{group.name}</h2>
          {groupId === "rubric" ? (
            <RubricBlock onEditingChange={setRubricEditing} />
          ) : (
            <GroupFields group={groupId} draft={draft} onChange={(p) => { save.reset(); setDraft((d) => ({ ...d, ...p })); }} />
          )}
          {group.keys.length > 0 && (
            <>
              {save.isSuccess && !dirty && <p className="banner banner-ok" role="status">已儲存。</p>}
              <ErrorBanner error={save.error} />
              <div className="head">
                <span className="muted small">{dirty ? "有未存的修改" : ""}</span>
                <span className="actions">
                  <button type="button" disabled={!dirty} onClick={revert}>還原</button>
                  <button type="button" className="primary" disabled={!dirty || !draftValid(draft) || save.isPending}
                    onClick={() => save.mutate(patch)}>
                    儲存
                  </button>
                </span>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

export function SettingsPage() {
  const settings = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
  if (!settings.data) return <main><ErrorBanner error={settings.error} /></main>;
  return <Page saved={settings.data} />;
}
