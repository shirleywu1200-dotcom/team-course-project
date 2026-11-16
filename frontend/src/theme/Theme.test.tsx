import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ThemeProvider, ThemeControl } from "./Theme";

afterEach(() => { localStorage.clear(); document.documentElement.removeAttribute("data-theme"); vi.restoreAllMocks(); });

test("預設跟隨系統，不強制亮色或暗色", async () => {
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  expect(screen.getByRole("combobox", { name: "色彩主題" })).toHaveValue("system");
  expect(document.documentElement).not.toHaveAttribute("data-theme");
});

test("手動亮暗色切換會保存，重新掛載仍沿用，切回系統移除覆寫", async () => {
  const first = render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  fireEvent.change(screen.getByLabelText("色彩主題"), { target: { value: "dark" } });
  await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme", "dark"));
  expect(localStorage.getItem("g4.theme")).toBe("dark");
  first.unmount();
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  expect(screen.getByLabelText("色彩主題")).toHaveValue("dark");
  fireEvent.change(screen.getByLabelText("色彩主題"), { target: { value: "light" } });
  expect(document.documentElement).toHaveAttribute("data-theme", "light");
  fireEvent.change(screen.getByLabelText("色彩主題"), { target: { value: "system" } });
  expect(document.documentElement).not.toHaveAttribute("data-theme");
});

test("無效保存值回到系統，主題操作不改 token", () => {
  localStorage.setItem("g4.theme", "unexpected");
  localStorage.setItem("g4.token", "example-only");
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  expect(screen.getByLabelText("色彩主題")).toHaveValue("system");
  fireEvent.change(screen.getByLabelText("色彩主題"), { target: { value: "dark" } });
  expect(localStorage.getItem("g4.token")).toBe("example-only");
});

test("localStorage 讀寫失敗仍能切換，不阻擋介面", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  render(<ThemeProvider><ThemeControl /></ThemeProvider>);
  fireEvent.change(screen.getByLabelText("色彩主題"), { target: { value: "dark" } });
  expect(document.documentElement).toHaveAttribute("data-theme", "dark");
});
