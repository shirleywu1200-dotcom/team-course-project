import { useSyncExternalStore } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { navigationRoutes } from "./routeDefinitions";
import "./layout.css";

const compactQuery = "(max-width: 767px)";

function subscribe(listener: () => void) {
  const media = window.matchMedia?.(compactQuery);
  media?.addEventListener("change", listener);
  return () => media?.removeEventListener("change", listener);
}

function getCompactSnapshot() {
  return window.matchMedia?.(compactQuery).matches ?? false;
}

export function AppLayout() {
  const compact = useSyncExternalStore(subscribe, getCompactSnapshot, () => false);
  const links = compact
    ? navigationRoutes.filter((route) => route.compactOrder !== undefined)
      .sort((a, b) => a.compactOrder! - b.compactOrder!)
    : navigationRoutes;
  // 僅改導覽與排版，不依載具切換 Outlet，保留頁面元件與未送出的輸入。
  return (
    <div className="app-shell" data-layout={compact ? "compact" : "wide"} data-testid="app-shell">
      <a className="app-skip" href="#page-content">跳至內容</a>
      <header className="app-header">
        <Link className="app-brand" to="/">個人大總管</Link>
        <span className="muted">AI 只提議，你決定</span>
      </header>
      <nav className="app-navigation" aria-label="主要導覽">
        {links.map(({ path, title, compactTitle }) => (
          <NavLink key={path} to={path} className="app-nav-link">{compact ? compactTitle ?? title : title}</NavLink>
        ))}
      </nav>
      <section id="page-content" className="app-content" aria-label="頁面內容" tabIndex={-1}>
        <Outlet />
      </section>
    </div>
  );
}
