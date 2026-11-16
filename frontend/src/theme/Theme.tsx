import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "system" | "light" | "dark";
const storageKey = "g4.theme";
const ThemeContext = createContext<{ theme: Theme; setTheme: (theme: Theme) => void } | null>(null);

function loadTheme(): Theme {
  try {
    const value = localStorage.getItem(storageKey);
    if (value === "light" || value === "dark") return value;
  } catch { /* 儲存受限仍可使用系統主題。 */ }
  return "system";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(loadTheme);
  useEffect(() => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.dataset.theme = theme;
  }, [theme]);
  function chooseTheme(value: Theme) {
    setTheme(value);
    try { localStorage.setItem(storageKey, value); }
    catch { /* 僅略過保存，本次選擇仍有效。 */ }
  }
  return <ThemeContext.Provider value={{ theme, setTheme: chooseTheme }}>{children}</ThemeContext.Provider>;
}

export function ThemeControl() {
  const context = useContext(ThemeContext);
  if (!context) return null;
  return <label className="theme-control">色彩主題{" "}
    <select value={context.theme} onChange={e => context.setTheme(e.target.value as Theme)}>
      <option value="system">跟隨系統</option>
      <option value="light">亮色</option>
      <option value="dark">暗色</option>
    </select>
  </label>;
}
