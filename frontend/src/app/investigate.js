import {
  cancelInvestigation,
  getCurrentInvestigation,
  getInvestigation,
  startInvestigation,
} from "../api.js";
import { goHome, rememberQuery } from "./nav.js";

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
      <section class="results" id="results" hidden></section>
      <p class="note" id="note">
        One PatentCore search. This screen completes after that search returns.
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
  const results = root.querySelector("#results");
  const note = root.querySelector("#note");
  let timer = 0;
  let stopped = false;

  function stop() {
    stopped = true;
    window.clearTimeout(timer);
  }

  function text(value) {
    return value == null || value === "" ? "" : String(value);
  }

  function renderPatents(records, error) {
    const block = document.createElement("section");
    block.className = "result-block";
    const heading = document.createElement("p");
    heading.className = "examples-label";
    heading.textContent = error
      ? "PatentCore search failed"
      : records.length
        ? `Potentially relevant IP (${records.length})`
        : "No PatentCore records returned";
    block.append(heading);

    if (error) {
      const fail = document.createElement("p");
      fail.className = "result-empty";
      fail.textContent = error;
      block.append(fail);
      return block;
    }

    if (!records.length) {
      const empty = document.createElement("p");
      empty.className = "result-empty";
      empty.textContent = "Amass returned no patents for this query.";
      block.append(empty);
      return block;
    }

    const list = document.createElement("ul");
    list.className = "patent-list";
    for (const record of records) {
      const item = document.createElement("li");
      item.className = "patent-card";
      const number = text(record.publicationNumber);
      const amassId = text(record.amassId);
      const assignees = Array.isArray(record.assignees)
        ? record.assignees.filter(Boolean).join(" · ")
        : "";
      item.innerHTML = `
        <p class="patent-kicker"></p>
        <h2 class="patent-title"></h2>
        <p class="patent-meta"></p>
        <p class="patent-abstract"></p>
      `;
      item.querySelector(".patent-kicker").textContent =
        number || amassId || "PatentCore record";
      item.querySelector(".patent-title").textContent =
        text(record.title) || "Untitled patent";
      const meta = [assignees, text(record.publicationDate), amassId]
        .filter(Boolean)
        .join(" · ");
      const metaEl = item.querySelector(".patent-meta");
      if (meta) {
        metaEl.textContent = meta;
      } else {
        metaEl.remove();
      }
      const abstractEl = item.querySelector(".patent-abstract");
      if (record.abstract) {
        abstractEl.textContent = text(record.abstract);
      } else {
        abstractEl.remove();
      }
      list.append(item);
    }
    block.append(list);
    return block;
  }

  function renderOrganizations(organizations) {
    const block = document.createElement("section");
    block.className = "result-block";
    const heading = document.createElement("p");
    heading.className = "examples-label";
    heading.textContent = organizations.length
      ? `Assignees (${organizations.length})`
      : "No assignees derived";
    block.append(heading);

    if (!organizations.length) {
      const empty = document.createElement("p");
      empty.className = "result-empty";
      empty.textContent = "No organization names were present on the retrieved patents.";
      block.append(empty);
      return block;
    }

    const list = document.createElement("ul");
    list.className = "org-list";
    for (const org of organizations) {
      const item = document.createElement("li");
      item.className = "org-card";
      const count = org.sourceRecordIds?.length ?? 0;
      item.innerHTML = `<strong></strong><span></span>`;
      item.querySelector("strong").textContent = org.name;
      item.querySelector("span").textContent =
        count === 1 ? "1 patent" : `${count} patents`;
      list.append(item);
    }
    block.append(list);
    return block;
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

    const patents = job.evidence.patentcore;
    if (!patents) {
      results.hidden = true;
      results.replaceChildren();
    } else {
      results.hidden = false;
      results.replaceChildren(
        renderPatents(patents.records ?? [], patents.error),
        renderOrganizations(job.organizations ?? []),
      );
    }

    if (job.status === "completed") {
      note.textContent =
        "These are the PatentCore records returned for this query, not a licensing opinion.";
    } else if (job.status === "error") {
      note.textContent =
        "The PatentCore search failed or timed out. Any records below still came from Amass.";
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
    timer = window.setTimeout(() => poll(id), 400);
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
      if (job.status === "completed" || job.status === "error") {
        return;
      }
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
