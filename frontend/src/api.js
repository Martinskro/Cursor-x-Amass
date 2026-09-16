export async function getCurrentInvestigation() {
  const response = await fetch("/api/investigations/current");
  if (!response.ok) {
    throw new Error(`Could not load investigation (${response.status})`);
  }
  return response.json();
}

export async function startInvestigation(query) {
  const response = await fetch("/api/investigations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (response.status === 409) {
    const error = new Error("An investigation is already running.");
    error.code = "busy";
    throw error;
  }
  if (!response.ok) {
    throw new Error(`Could not start investigation (${response.status})`);
  }
  return response.json();
}

export async function cancelInvestigation() {
  const response = await fetch("/api/investigations/current", { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Could not cancel investigation (${response.status})`);
  }
}

export async function getInvestigation(id) {
  const response = await fetch(`/api/investigations/${id}`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Could not load investigation (${response.status})`);
  }
  return response.json();
}
