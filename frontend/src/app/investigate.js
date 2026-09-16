import {
  cancelInvestigation,
  getCurrentInvestigation,
  getInvestigation,
  startInvestigation,
} from "../api.js";
import { goHome, rememberQuery } from "./nav.js";

const EVIDENCE_CARDS = [
  { key: "biomedcore", label: "Papers" },
  { key: "patentcore", label: "Patents" },
  { key: "drugcore", label: "Molecules" },
  { key: "genecore", label: "Genes" },
  { key: "trialcore", label: "Clinical trials" },
  { key: "regulatorycore", label: "Regulatory records" },
];

export function renderInvestigate(root, query) {
  rememberQuery(query);

  root.innerHTML = `
    <header class="topbar">
      <a class="brand" href="/" data-home>
        <span class="brand-mark" aria-hidden="true"></span>
        <p class="brand-name">Licensa</p>
      </a>
      <p class="meta">Investigation</p>
    </header>
    <main class="stage">
      <button class="back" type="button" data-home>← New search</button>
      <section class="investigate-head">
        <p class="kicker">Technology search</p>
        <h1 id="investigate-title">Investigating</h1>
        <div class="query-card">
          <p class="query-label">Request</p>
          <p class="query-text"></p>
        </div>
      </section>
      <ol class="timeline" id="timeline"></ol>
      <section class="evidence" id="evidence" hidden></section>
      <p class="note" id="note">
        Each step completes only after that Amass search has returned.
      </p>
    </main>
  `;

  root.querySelector(".query-text").textContent = query;
  root.querySelectorAll("[data-home]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      event.preventDefault();
      stop();
      try {
        await cancelInvestigation();
      } catch {
        // Returning home still clears this screen.
      }
      goHome();
    });
  });

  const title = root.querySelector("#investigate-title");
  const timeline = root.querySelector("#timeline");
  const evidence = root.querySelector("#evidence");
  const note = root.querySelector("#note");
  let timer = 0;
  let stopped = false;

  function stop() {
    stopped = true;
    window.clearTimeout(timer);
  }

  function renderJob(job) {
    title.textContent =
      job.status === "completed"
        ? "Investigation complete"
        : job.status === "error"
          ? "Investigation incomplete"
          : "Investigating";

    timeline.replaceChildren(
      ...job.steps.map((step, index) => {
        const item = document.createElement("li");
        item.className = `step is-${step.status}`;
        item.dataset.step = step.id;
        item.innerHTML = `
          <span class="step-index">${String(index + 1).padStart(2, "0")}</span>
          <div class="step-body">
            <div>
              <p class="step-label"></p>
              <p class="step-detail"></p>
            </div>
            <span class="step-state"></span>
          </div>
        `;
        item.querySelector(".step-label").textContent = step.label;
        const detail = item.querySelector(".step-detail");
        if (step.detail) {
          detail.textContent = step.detail;
        } else {
          detail.remove();
        }
        item.querySelector(".step-state").textContent = step.status.replace("-", " ");
        return item;
      }),
    );

    const cards = EVIDENCE_CARDS.filter((card) => job.evidence[card.key]);
    if (job.organizations.length) {
      cards.push({ key: "organizations", label: "Organizations" });
    }

    if (!cards.length) {
      evidence.hidden = true;
      evidence.replaceChildren();
    } else {
      evidence.hidden = false;
      evidence.innerHTML = `<p class="examples-label">Evidence retrieved</p>`;
      const grid = document.createElement("ul");
      grid.className = "metrics";
      for (const card of cards) {
        const count =
          card.key === "organizations"
            ? job.organizations.length
            : (job.evidence[card.key]?.records ?? []).length;
        const item = document.createElement("li");
        item.className = "metric";
        item.innerHTML = `<strong></strong><span></span>`;
        item.querySelector("strong").textContent = String(count);
        item.querySelector("span").textContent = card.label;
        grid.append(item);
      }
      evidence.append(grid);
    }

    if (job.status === "completed") {
      note.textContent =
        "Counts are the records returned by this investigation, not corpus totals. Relevance ranking comes next.";
    } else if (job.status === "error") {
      note.textContent = "One or more Amass searches failed. Retrieved records below are still from Amass.";
    }
  }

  async function poll(id) {
    if (stopped) {
      return;
    }
    try {
      const job = await getInvestigation(id);
      if (!job) {
        note.textContent = "Investigation was lost. Start a new search.";
        return;
      }
      renderJob(job);
      if (job.status === "completed" || job.status === "error") {
        return;
      }
    } catch {
      note.textContent = "Could not reach the investigation service. Retrying…";
    }
    timer = window.setTimeout(() => poll(id), 600);
  }

  async function boot() {
    try {
      const existing = await getCurrentInvestigation();
      if (existing && existing.query === query) {
        renderJob(existing);
        if (existing.status === "running") {
          poll(existing.id);
        }
        return;
      }
      const job = await startInvestigation(query);
      renderJob(job);
      poll(job.id);
    } catch (error) {
      if (error.code === "busy") {
        const current = await getCurrentInvestigation();
        title.textContent = "Investigation already running";
        note.textContent = current?.query
          ? `Finish or cancel “${current.query}” before starting another search.`
          : "Finish or cancel the current investigation before starting another.";
        return;
      }
      title.textContent = "Investigation could not start";
      note.textContent = "The investigation service is not reachable. Is the backend running?";
    }
  }

  boot();
}
