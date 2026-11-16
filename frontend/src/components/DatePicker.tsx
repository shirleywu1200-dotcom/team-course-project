interface Props {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  disabled?: boolean;
  required?: boolean;
}

// V4 原生日期選擇；只傳 ISO 字串，不推算日期或轉換時區。
export function DatePicker({ id, label, value, onChange, ...props }: Props) {
  return <div className="field">
    <label htmlFor={id}>{label}</label>
    <input {...props} id={id} type="date" value={value} onChange={e => onChange(e.target.value)} />
    {value && <output className="date-value" htmlFor={id}>{value}</output>}
  </div>;
}
