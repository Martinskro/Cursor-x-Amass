import { analyzeIdea } from "./api.js";
import { EXAMPLE_IDEAS } from "./examples.js";
import "./styles.css";

const form = document.querySelector("#idea-form");
const idea = document.querySelector("#idea");
const count = document.querySelector("#char-count");
const button = document.querySelector("#analyze-btn");
const status = document.querySelector("#status");
const exampleList = document.querySelector("#example-list");

const MAX = 2000;

function updateCount() {
  count.textContent = `${idea.value.length} / ${MAX}`;
}

function setStatus(message) {
  status.textContent = message;
}

function renderExamples() {
  exampleList.replaceChildren(
    ...EXAMPLE_IDEAS.map((text) => {
      const item = document.createElement("li");
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "example";
      chip.textContent = text;
      chip.addEventListener("click", () => {
        idea.value = text;
        updateCount();
        setStatus("");
        idea.focus();
      });
      item.append(chip);
      return item;
    }),
  );
}

idea.addEventListener("input", () => {
  updateCount();
  setStatus("");
});

idea.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = idea.value.trim();
  if (!value) {
    setStatus("Enter a scientific idea or technology to continue.");
    idea.focus();
    return;
  }

  button.disabled = true;
  setStatus("Holding this idea for analysis.");

  try {
    const data = await analyzeIdea(value);
    setStatus(data.message);
  } catch {
    setStatus("Could not reach the analysis service. Try again in a moment.");
  } finally {
    button.disabled = false;
  }
});

renderExamples();
updateCount();
