import type { components } from "../../api/types.generated";

type SourceRef = components["schemas"]["SourceRefOut"];

export function SourceEvidence({ source }: { source: SourceRef }) {
  return <div>
    <span>{source.label}</span>
    {source.purged ? <span>（原文已依設定刪除）</span> : source.quote ? <blockquote>{source.quote}</blockquote> : null}
  </div>;
}
