// FR-DUE-05、FR-MRK-03：保留既有選項、方向、external 與順序。
import type { ReasonsMeta } from "../api/types";

export const reasons: ReasonsMeta = {
  due: [
    { code: "finished_early", label: "提早完成條件達成", direction: "earlier", external: false },
    { code: "less_work", label: "工作量比預期少", direction: "earlier", external: false },
    { code: "prereq_early", label: "前置工作提早到位", direction: "earlier", external: false },
    { code: "other", label: "其他", direction: "earlier", external: false },
    { code: "underestimated", label: "估計不準（我低估）", direction: "later", external: false },
    { code: "self_interrupt", label: "被其他事插隊（我自己排程）", direction: "later", external: false },
    { code: "wait_external", label: "等對方或客戶回覆（外部）", direction: "later", external: true },
    { code: "scope_change_external", label: "需求變更（外部）", direction: "later", external: true },
    { code: "resource_external", label: "資源或環境未到位（外部）", direction: "later", external: true },
    { code: "other", label: "其他", direction: "later", external: false },
  ],
  baseline_types: [
    { code: "correction", label: "更正錯誤" },
    { code: "rebaseline", label: "客戶或主管正式改變承諾日" },
  ],
  baseline_reasons: [
    { code: "input_error", label: "匯入或輸入錯誤" },
    { code: "plan_date_wrong", label: "原計畫日期寫錯" },
    { code: "formal_commitment_change", label: "客戶或主管正式改變承諾日" },
    { code: "other", label: "其他" },
  ],
};
