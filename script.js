// Theme + view-mode toggles. Page is fully readable without this script.
(function () {
  "use strict";

  const root = document.documentElement;
  const body = document.body;

  // ---- theme (light / dark) ----
  const THEME_KEY = "kciii.theme";
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") {
    root.setAttribute("data-theme", stored);
  }

  const themeBtn = document.querySelector("[data-theme-toggle]");
  const themeLabel = document.querySelector("[data-theme-label]");
  const updateThemeLabel = () => {
    if (!themeLabel) return;
    const dark = root.getAttribute("data-theme") === "dark"
      || (!root.hasAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    themeLabel.textContent = dark ? "Light" : "Dark";
  };
  updateThemeLabel();

  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = root.getAttribute("data-theme")
        || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem(THEME_KEY, next);
      updateThemeLabel();
    });
  }

  // ---- view mode (english / both / classical) ----
  const VIEW_KEY = "kciii.view";
  const validViews = ["english", "both", "classical"];
  const storedView = localStorage.getItem(VIEW_KEY);
  if (validViews.includes(storedView)) {
    root.setAttribute("data-view", storedView);
  }

  const buttons = document.querySelectorAll("[data-view-set]");
  const syncButtons = () => {
    const active = root.getAttribute("data-view") || "both";
    buttons.forEach(b => {
      b.setAttribute("aria-pressed", String(b.dataset.viewSet === active));
    });
  };
  syncButtons();

  buttons.forEach(b => {
    b.addEventListener("click", () => {
      const v = b.dataset.viewSet;
      if (!validViews.includes(v)) return;
      root.setAttribute("data-view", v);
      localStorage.setItem(VIEW_KEY, v);
      syncButtons();
    });
  });

  // ---- footnote drawer: open the parent <details> when a fn-li becomes the URL target ----
  // The drawer toggles natively without JS; this only enhances "click superscript → drawer opens".
  const openTargetDrawer = () => {
    const id = location.hash.slice(1);
    if (!id) return;
    const el = document.getElementById(id);
    if (!el || !el.matches("li[id^='p']")) return;
    const drawer = el.closest("details.notes");
    if (drawer && !drawer.open) drawer.open = true;
  };
  window.addEventListener("hashchange", openTargetDrawer);
  openTargetDrawer();
})();
