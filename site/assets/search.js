const search = document.querySelector(".search");
const input = document.querySelector("#guide-search");
const status = document.querySelector("#search-status");
const empty = document.querySelector("#no-results");
const parts = document.querySelectorAll("[data-part]");
const rows = Array.from(document.querySelectorAll("[data-note]"));
const normalize = (value) => value.normalize("NFKC").toLocaleLowerCase();
const entries = new Map(rows.map((row) => [row.dataset.note, normalize(row.textContent)]));
let searchIndex;

function filter() {
  const terms = normalize(input.value).trim().split(/\s+/).filter(Boolean);
  let count = 0;
  for (const row of rows) {
    const text = entries.get(row.dataset.note);
    row.hidden = !terms.every((term) => text.includes(term));
    if (!row.hidden) count += 1;
  }
  for (const part of parts) {
    part.hidden = !part.querySelector("[data-note]:not([hidden])");
    for (const chapter of part.querySelectorAll("[data-chapter]")) {
      chapter.hidden = !chapter.querySelector("[data-note]:not([hidden])");
    }
  }
  for (const link of document.querySelectorAll(".part-nav a")) {
    link.hidden = document.getElementById(link.hash.slice(1)).hidden;
  }
  document.querySelector(".part-nav").hidden = count === 0;
  status.hidden = terms.length === 0;
  status.textContent = `找到 ${count} 篇`;
  empty.hidden = count !== 0;
}

async function loadIndex() {
  try {
    const response = await fetch("assets/search-index.json");
    if (!response.ok) return;
    const index = await response.json();
    for (const [key, value] of Object.entries(index)) entries.set(key, normalize(value));
    filter();
  } catch {
    // Title search remains available when the text index cannot be loaded.
  }
}

input.addEventListener("focus", () => { searchIndex ??= loadIndex(); }, { once: true });
input.addEventListener("input", filter);
search.hidden = false;
