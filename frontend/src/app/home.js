import { getCurrentInvestigation } from "../api.js";
import { EXAMPLE_SEARCHES } from "../examples.js";
import {
  MAX_QUERY_LENGTH,
  goInvestigate,
  recalledQuery,
} from "./nav.js";

export function renderHome(root) {
  root.innerHTML = `
    <header class="topbar">
      <a class="brand" href="/" data-home>
        <span class="brand-mark" aria-hidden="true"></span>
        <p class="brand-name">Licensa</p>
      </a>
      <p class="meta">Amass × Cursor · DTU Skylab</p>
    </header>
    <main class="stage">
      <p class="kicker">Technology discovery</p>
      <h1 class="wordmark">Licensa</h1>
      <p class="tagline">
        <span>Find the science.</span>
        <span>Find the IP.</span>
        <span>Find the opportunity.</span>
      </p>
      <form id="search-form" class="composer" novalidate>
        <label class="field-label" for="query">What technology are you looking for?</label>
        <div class="field">
          <textarea
            id="query"
            name="query"
            rows="3"
            maxlength="${MAX_QUERY_LENGTH}"
            required
            placeholder="Engineered yeast for sustainable production of pharmaceutical ingredients"
            autocomplete="off"
          ></textarea>
          <div class="field-meta">
            <span id="char-count">0 / ${MAX_QUERY_LENGTH}</span>
          </div>
        </div>
        <button type="submit" class="cta" id="search-btn">
          <span>Find technologies</span>
          <span class="cta-hint">⌘ Enter</span>
        </button>
        <p class="status" id="status" role="status" aria-live="polite"></p>
      </form>
      <p class="examples-label" id="examples-label">Example searches</p>
      <ul class="examples" id="example-list" aria-labelledby="examples-label"></ul>
    </main>
    <p class="foot">Evidence from Amass cores. Insights labeled separately from records.</p>
  `;

  const form = root.querySelector("#search-form");
  const input = root.querySelector("#query");
  const count = root.querySelector("#char-count");
  const status = root.querySelector("#status");
  const list = root.querySelector("#example-list");
  const home = root.querySelector("[data-home]");

  const remembered = recalledQuery();
  if (remembered) {
    input.value = remembered;
  }

  function updateCount() {
    count.textContent = `${input.value.length} / ${MAX_QUERY_LENGTH}`;
  }

  list.replaceChildren(
    ...EXAMPLE_SEARCHES.map((text) => {
      const item = document.createElement("li");
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "example";
      chip.textContent = text;
      chip.addEventListener("click", () => {
        input.value = text;
        updateCount();
        status.textContent = "";
        input.focus();
      });
      item.append(chip);
      return item;
    }),
  );

  home.addEventListener("click", (event) => {
    event.preventDefault();
    input.focus();
  });

  input.addEventListener("input", () => {
    updateCount();
    status.textContent = "";
    document.querySelector("#resume-search")?.remove();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) {
      status.textContent = "Describe the technology you are looking for.";
      input.focus();
      return;
    }

    try {
      const current = await getCurrentInvestigation();
      if (current?.status === "running") {
        if (current.query === query) {
          goInvestigate(query);
          return;
        }
        status.textContent =
          "One investigation is already running. Open it, or cancel it from that screen, before starting another.";
        document.querySelector("#resume-search")?.remove();
        const resume = document.createElement("button");
        resume.type = "button";
        resume.id = "resume-search";
        resume.className = "example";
        resume.textContent = "Open current investigation";
        resume.addEventListener("click", () => goInvestigate(current.query));
        status.after(resume);
        return;
      }
    } catch {
      status.textContent = "Could not reach the investigation service. Try again in a moment.";
      return;
    }

    goInvestigate(query);
  });

  updateCount();
  input.focus();
}
