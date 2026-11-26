(() => {
  const key = "adhd-helper-appearance";
  const systemDark = matchMedia("(prefers-color-scheme: dark)");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const labels = { system: "跟随系统", light: "浅色", dark: "深色" };
  const modes = Object.keys(labels);
  let preference = "system";
  try {
    const saved = localStorage.getItem(key);
    if (modes.includes(saved)) preference = saved;
  } catch {}

  const root = document.documentElement;
  const effectiveTheme = () => preference === "system" ? (systemDark.matches ? "dark" : "light") : preference;
  const nextMode = () => modes[(modes.indexOf(preference) + 1) % modes.length];
  let pendingTransition;
  function updateTheme(animate) {
    pendingTransition?.skipTransition();
    const theme = effectiveTheme();
    if (root.dataset.theme === theme) return;
    const apply = () => { root.dataset.theme = effectiveTheme(); };
    if (animate && document.startViewTransition && !reducedMotion.matches && !document.hidden) {
      pendingTransition = document.startViewTransition(apply);
      pendingTransition.ready.catch(() => {});
    } else {
      apply();
    }
  }

  updateTheme(false);
  systemDark.addEventListener("change", () => updateTheme(false));
  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("theme-button");
    const syncControl = () => {
      const label = `当前${labels[preference]}，点击切换到${labels[nextMode()]}`;
      button.dataset.appearance = preference;
      button.setAttribute("aria-label", `外观，${label}`);
      button.title = label;
    };
    button.addEventListener("click", () => {
      preference = nextMode();
      try { localStorage.setItem(key, preference); } catch {}
      syncControl();
      updateTheme(true);
    });
    syncControl();
    button.hidden = false;
  });
})();
