(() => {
  const indexUrl = new URL("search-index.json", document.currentScript.src);
  const layout = document.getElementById("guide-layout");
  const rail = document.getElementById("guide-rail");
  const railSlot = document.getElementById("rail-sticky");
  const navigator = document.getElementById("guide-navigator");
  const tree = document.getElementById("guide-tree");
  const drawer = document.getElementById("guide-drawer");
  const drawerBody = document.getElementById("drawer-body");
  const toggle = document.getElementById("directory-button");
  const search = document.getElementById("search-trigger");
  const input = document.getElementById("guide-search");
  const status = document.getElementById("search-status");
  const topics = document.getElementById("guide-topics");
  const toolbar = document.querySelector(".guide-toolbar");
  const masthead = document.querySelector(".site-header");
  const narrow = matchMedia("(max-width: 63.999rem)");
  const compact = matchMedia("(max-width: 45.999rem)");
  const key = "adhd-directory-collapsed";
  let collapsed = false;
  try { collapsed = sessionStorage.getItem(key) === "true"; } catch {}

  function syncDock() {
    const isCollapsed = !narrow.matches && collapsed;
    if (!narrow.matches && drawer.open) drawer.close();
    const slot = narrow.matches ? drawerBody : railSlot;
    if (navigator.parentElement !== slot) slot.append(navigator);
    layout.toggleAttribute("data-rail-collapsed", isCollapsed);
    rail.hidden = isCollapsed;
    toggle.setAttribute("aria-controls", narrow.matches ? drawer.id : rail.id);
    toggle.setAttribute("aria-expanded", String(narrow.matches ? drawer.open : !isCollapsed));
    if (narrow.matches) toggle.setAttribute("aria-haspopup", "dialog");
    else toggle.removeAttribute("aria-haspopup");
  }

  function showActiveLink() {
    const active = tree.querySelector("[aria-current='page']");
    if (!active || !active.getClientRects().length) return;
    const bounds = tree.getBoundingClientRect();
    const item = active.getBoundingClientRect();
    if (item.bottom > bounds.bottom) tree.scrollTop += item.bottom - bounds.bottom;
    else if (item.top < bounds.top) tree.scrollTop -= bounds.top - item.top;
  }

  function showDrawer() {
    if (compact.matches) topics.open = false;
    positionDrawer();
    if (!drawer.open) drawer.showModal();
    toggle.setAttribute("aria-expanded", "true");
    showActiveLink();
  }

  function positionDrawer() {
    drawer.style.setProperty("--drawer-top", `${Math.max(0, masthead.getBoundingClientRect().bottom)}px`);
  }

  toggle.addEventListener("click", () => {
    if (narrow.matches) {
      showDrawer();
      return;
    }
    collapsed = !collapsed;
    try { sessionStorage.setItem(key, String(collapsed)); } catch {}
    syncDock();
    showActiveLink();
  });

  function focusSearch() {
    if (narrow.matches) showDrawer();
    else if (collapsed) {
      collapsed = false;
      try { sessionStorage.removeItem(key); } catch {}
      syncDock();
    }
    input.focus();
  }

  search.addEventListener("click", focusSearch);
  drawer.addEventListener("close", syncDock);
  drawer.addEventListener("click", event => {
    if (event.target === drawer) drawer.close();
  });
  narrow.addEventListener("change", () => {
    syncDock();
    showActiveLink();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && compact.matches && topics.open) {
      topics.open = false;
      topics.querySelector("summary").focus();
    }
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey ||
      toolbar.hidden || event.target.closest("input, textarea, select, [contenteditable]")) return;
    event.preventDefault();
    focusSearch();
  });

  const normalize = value => value.normalize("NFKC").toLocaleLowerCase();
  const entries = new Map();
  let opened;
  function filter() {
    const terms = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    const groups = Array.from(tree.querySelectorAll(".tree-group"));
    if (terms.length && !opened) opened = new Map(groups.map(group => [group, group.open]));
    let count = 0;
    for (const link of tree.querySelectorAll("[data-note]")) {
      const text = entries.get(link.dataset.note) ?? normalize(link.dataset.search ?? link.textContent);
      link.hidden = !terms.every(term => text.includes(term));
      if (!link.hidden) count += 1;
    }
    for (const group of groups.reverse()) {
      group.hidden = !group.querySelector("[data-note]:not([hidden])");
      if (terms.length) group.open = !group.hidden;
      else if (opened) group.open = opened.get(group) ?? false;
    }
    if (!terms.length) opened = undefined;
    status.textContent = !terms.length ? "" :
      count ? `找到 ${count} ${layout.dataset.searchUnit}` : "没有匹配结果";
    tree.scrollTop = 0;
  }

  async function loadIndex() {
    try {
      const response = await fetch(indexUrl);
      if (!response.ok) return;
      const data = await response.json();
      for (const [key, value] of Object.entries(data)) entries.set(key, normalize(value));
      filter();
    } catch {
      // The title filter still works if the content index cannot load.
    }
  }

  if (document.body.classList.contains("guide-page")) {
    input.addEventListener("focus", loadIndex, { once: true });
    if (document.querySelector(".guide-library")) {
      const links = topics.querySelectorAll("[data-section]");
      const highlightSection = () => {
        const key = location.hash.slice(1);
        const target = Array.from(links).find(link => link.dataset.section === key) ?? links[0];
        for (const link of links) {
          if (link === target) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        }
      };
      window.addEventListener("hashchange", highlightSection);
      highlightSection();
    }
  }
  input.addEventListener("input", filter);

  const syncTopics = () => { topics.open = !compact.matches; };
  topics.addEventListener("click", event => {
    if (compact.matches && event.target.closest("a")) topics.open = false;
  });
  document.addEventListener("pointerdown", event => {
    if (compact.matches && topics.open && !toolbar.contains(event.target)) topics.open = false;
  });
  compact.addEventListener("change", syncTopics);
  syncTopics();

  function syncSurface() {
    const top = parseFloat(getComputedStyle(toolbar).top);
    toolbar.classList.toggle("is-stuck", toolbar.getBoundingClientRect().top <= top + .5);
  }

  window.addEventListener("scroll", syncSurface, { passive: true });
  window.addEventListener("resize", () => {
    if (drawer.open) positionDrawer();
    syncSurface();
  });
  syncDock();
  document.body.dataset.directoryReady = "";
  toggle.hidden = false;
  search.hidden = false;
  document.getElementById("guide-filter").hidden = false;
  showActiveLink();
  syncSurface();
})();
