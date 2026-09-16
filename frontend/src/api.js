export async function analyzeIdea(idea) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 12_000);
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea }),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    return response.json();
  } finally {
    window.clearTimeout(timer);
  }
}
