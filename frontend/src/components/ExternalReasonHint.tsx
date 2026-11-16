// FR-MRK-03：只提示，永不代選。
export function ExternalReasonHint() {
  return <p className="hint" role="note">這個原因屬於外部因素，建議選「不計入」。這只是提示，請你自己決定。</p>;
}
