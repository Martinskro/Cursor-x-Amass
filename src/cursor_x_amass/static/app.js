const form = document.querySelector("#idea-form");
const idea = document.querySelector("#idea");
const count = document.querySelector("#char-count");
const button = document.querySelector("#analyze-btn");
const status = document.querySelector("#status");
const examples = document.querySelectorAll(".example");

const MAX = 2000;

function updateCount() {
  count.textContent = `${idea.value.length} / ${MAX}`;
}

function setStatus(message) {
  status.textContent = message;
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

examples.forEach((chip) => {
  chip.addEventListener("click", () => {
    idea.value = chip.dataset.idea ?? "";
    updateCount();
    setStatus("");
    idea.focus();
  });
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
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: value }),
    });
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    const data = await response.json();
    setStatus(data.message);
  } catch {
    setStatus("Could not reach the analysis service. Try again in a moment.");
  } finally {
    button.disabled = false;
  }
});

updateCount();
